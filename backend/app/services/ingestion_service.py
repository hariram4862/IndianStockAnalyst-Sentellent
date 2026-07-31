from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk, SourceDocument
from app.models.stock import StockEntity
from app.services.article_analysis_service import ArticleAnalysisService
from app.services.embedding_service import EmbeddingService
from app.services.fundamentals_provider import FundamentalsProvider
from app.services.news_provider import NewsProvider
from app.services.providers import FundamentalsPayload, NewsArticlePayload
from app.services.seed_data import SEED_STOCKS


class IngestionService:
    def __init__(self) -> None:
        self.fundamentals_provider = FundamentalsProvider()
        self.news_provider = NewsProvider()
        self.analysis_service = ArticleAnalysisService()
        self.embedding_service = EmbeddingService()

    def ingest_ticker(self, db: Session, ticker: str) -> tuple[StockEntity, int, int, str]:
        # Transaction-scoped advisory lock keyed on the ticker: if a scheduled
        # refresh and a manual follow race for the same ticker, the second one
        # blocks here until the first commits/rolls back, instead of racing on
        # the same SourceDocument/DocumentChunk rows. Different tickers use
        # different lock keys and never block each other. Released
        # automatically at transaction end — no manual unlock needed.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:ticker)::bigint)"), {"ticker": ticker})

        fundamentals = self.fundamentals_provider.fetch(ticker)
        source_mode = "real"
        if fundamentals is None:
            if ticker not in SEED_STOCKS:
                raise ValueError(
                    f"'{ticker}' doesn't look like a valid NSE ticker (checked as {ticker}.NS). "
                    "Double-check the symbol, e.g. RELIANCE, TCS, HDFCBANK, INFY."
                )
            fundamentals = self._seed_fundamentals(ticker)
            source_mode = "seeded"

        stock = self._upsert_stock_from_fundamentals(db, ticker, fundamentals)
        ingested_documents = 0
        ingested_chunks = 0

        ingested_documents += self._upsert_fundamentals_document(db, stock, fundamentals)
        ingested_chunks += self._rechunk_document(
            db,
            stock.id,
            "fundamentals",
            f"{ticker.lower()}-fundamentals-phase2",
        )

        articles = self.news_provider.fetch_for_ticker(ticker)
        if not articles and ticker in SEED_STOCKS:
            articles = self._seed_articles(ticker)
            source_mode = "seeded" if source_mode != "real" else "mixed"

        scores: list[float] = []
        for article in articles:
            doc, created = self._upsert_news_document(db, stock, ticker, article)
            ingested_documents += 1 if created else 0
            ingested_chunks += self._rechunk_document(db, stock.id, doc.source_type, doc.external_id)
            if doc.sentiment_score is not None:
                scores.append(float(doc.sentiment_score))

        self._update_rolling_sentiment(stock, scores)
        stock.last_news_refresh_at = datetime.now(timezone.utc)
        db.flush()

        return stock, ingested_documents, ingested_chunks, source_mode

    def _upsert_stock_from_fundamentals(
        self,
        db: Session,
        ticker: str,
        payload: FundamentalsPayload,
    ) -> StockEntity:
        stock = db.execute(select(StockEntity).where(StockEntity.ticker == ticker)).scalar_one_or_none()
        if stock is None:
            stock = StockEntity(ticker=ticker, company_name=payload.company_name, exchange=payload.exchange)
            db.add(stock)
            db.flush()

        stock.company_name = payload.company_name
        stock.exchange = payload.exchange
        stock.sector = payload.sector
        stock.industry = payload.industry
        stock.isin = payload.isin
        stock.market_cap_inr = payload.market_cap_inr
        stock.current_price_inr = payload.current_price_inr
        stock.pe_ratio = payload.pe_ratio
        stock.dividend_yield = payload.dividend_yield
        stock.debt_to_equity = payload.debt_to_equity
        stock.fundamentals_summary = payload.fundamentals_summary
        return stock

    def _upsert_fundamentals_document(
        self,
        db: Session,
        stock: StockEntity,
        payload: FundamentalsPayload,
    ) -> int:
        external_id = f"{stock.ticker.lower()}-fundamentals-phase2"
        content = payload.fundamentals_summary
        content_hash = self._hash_content(content)

        document = db.execute(
            select(SourceDocument).where(
                SourceDocument.stock_id == stock.id,
                SourceDocument.source_type == "fundamentals",
                SourceDocument.external_id == external_id,
            )
        ).scalar_one_or_none()

        created = 0
        if document is None:
            document = SourceDocument(
                stock_id=stock.id,
                source_type="fundamentals",
                external_id=external_id,
                title=f"{stock.ticker} fundamentals snapshot",
                url=None,
                published_at=None,
                content_hash=content_hash,
                content=content,
                mentioned_tickers=stock.ticker,
                metadata_json=None,
            )
            db.add(document)
            db.flush()
            created = 1
        else:
            document.title = f"{stock.ticker} fundamentals snapshot"
            document.content_hash = content_hash
            document.content = content
            document.mentioned_tickers = stock.ticker

        return created

    def _upsert_news_document(
        self,
        db: Session,
        stock: StockEntity,
        ticker: str,
        article: NewsArticlePayload,
    ) -> tuple[SourceDocument, bool]:
        content_hash = self._hash_content(article.content)
        document = db.execute(
            select(SourceDocument).where(
                SourceDocument.stock_id == stock.id,
                SourceDocument.source_type == article.source_type,
                SourceDocument.external_id == article.external_id,
            )
        ).scalar_one_or_none()

        # Only pay for an LLM sentiment/impact tagging call when the article is
        # new or its content actually changed — a re-ingest of unchanged news
        # (e.g. a scheduled refresh re-fetching the same RSS items) must not
        # re-run analysis it already has the answer for.
        created = False
        if document is None:
            analysis = self.analysis_service.analyze(ticker, article)
            document = SourceDocument(
                stock_id=stock.id,
                source_type=article.source_type,
                external_id=article.external_id,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                content_hash=content_hash,
                content=article.content,
                sentiment_label=analysis["sentiment_label"],
                sentiment_score=analysis["sentiment_score"],
                impact_label=analysis["impact_label"],
                event_type=analysis["event_type"],
                mentioned_tickers=analysis["mentioned_tickers"],
                metadata_json=analysis["metadata_json"],
            )
            db.add(document)
            db.flush()
            created = True
        elif document.content_hash != content_hash:
            analysis = self.analysis_service.analyze(ticker, article)
            document.title = article.title
            document.url = article.url
            document.published_at = article.published_at
            document.content_hash = content_hash
            document.content = article.content
            document.sentiment_label = analysis["sentiment_label"]
            document.sentiment_score = analysis["sentiment_score"]
            document.impact_label = analysis["impact_label"]
            document.event_type = analysis["event_type"]
            document.mentioned_tickers = analysis["mentioned_tickers"]
            document.metadata_json = analysis["metadata_json"]

        return document, created

    def _rechunk_document(
        self,
        db: Session,
        stock_id: int,
        source_type: str,
        external_id: str,
    ) -> int:
        document = db.execute(
            select(SourceDocument).where(
                SourceDocument.stock_id == stock_id,
                SourceDocument.source_type == source_type,
                SourceDocument.external_id == external_id,
            )
        ).scalar_one()

        chunks = self._chunk_text(document.content)
        existing_chunks = db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index)
        ).scalars().all()

        changed = 0
        existing_by_index = {chunk.chunk_index: chunk for chunk in existing_chunks}
        for index, chunk_text in enumerate(chunks):
            embedding = self.embedding_service.embed_text(chunk_text)
            existing = existing_by_index.get(index)
            if existing is None:
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk_text,
                        embedding=embedding,
                    )
                )
                changed += 1
            elif existing.content != chunk_text:
                existing.content = chunk_text
                existing.embedding = embedding
                changed += 1

        for extra_chunk in existing_chunks[len(chunks) :]:
            db.delete(extra_chunk)

        return changed

    def _update_rolling_sentiment(self, stock: StockEntity, scores: list[float]) -> None:
        if not scores:
            return
        average = sum(scores) / len(scores)
        stock.rolling_sentiment_score = round(average, 2)
        if average > 0.15:
            stock.rolling_sentiment_label = "positive"
        elif average < -0.15:
            stock.rolling_sentiment_label = "negative"
        else:
            stock.rolling_sentiment_label = "neutral"

    def _seed_fundamentals(self, ticker: str) -> FundamentalsPayload:
        seed = SEED_STOCKS[ticker]
        return FundamentalsPayload(
            ticker=ticker,
            company_name=seed["company_name"],
            exchange=seed["exchange"],
            sector=seed["sector"],
            industry=seed["industry"],
            isin=None,
            market_cap_inr=seed["market_cap_inr"],
            current_price_inr=seed["current_price_inr"],
            pe_ratio=seed["pe_ratio"],
            dividend_yield=seed["dividend_yield"],
            debt_to_equity=seed["debt_to_equity"],
            fundamentals_summary=seed["fundamentals_summary"],
        )

    def _seed_articles(self, ticker: str) -> list[NewsArticlePayload]:
        seed_documents = SEED_STOCKS[ticker]["documents"]
        articles: list[NewsArticlePayload] = []
        for doc in seed_documents:
            if doc["source_type"] != "news":
                continue
            articles.append(
                NewsArticlePayload(
                    source_name="Seeded Phase 1 Corpus",
                    source_type="news",
                    external_id=doc["external_id"],
                    title=doc["title"],
                    url=doc["url"],
                    published_at=self._parse_datetime(doc["published_at"]),
                    content=doc["content"],
                )
            )
        return articles

    def _chunk_text(self, text: str, chunk_size: int = 350, overlap: int = 60) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = max(end - overlap, start + 1)
        return chunks

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)
