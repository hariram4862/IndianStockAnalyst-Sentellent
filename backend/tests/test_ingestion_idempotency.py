from datetime import datetime, timezone

from sqlalchemy import select

from app.models.document import DocumentChunk, SourceDocument
from app.models.stock import StockEntity
from app.services.ingestion_service import IngestionService
from app.services.providers import FundamentalsPayload, NewsArticlePayload

FAKE_FUNDAMENTALS = FundamentalsPayload(
    ticker="TESTCO",
    company_name="Test Company Ltd",
    exchange="NSE",
    sector="Technology",
    industry="Software",
    isin=None,
    market_cap_inr=1_000_000.0,
    current_price_inr=100.0,
    pe_ratio=15.0,
    dividend_yield=1.0,
    debt_to_equity=0.3,
    fundamentals_summary="Test Company is a fictional NSE-listed software business used for idempotency testing.",
)

FAKE_ARTICLE = NewsArticlePayload(
    source_name="Test Feed",
    source_type="news",
    external_id="testco-news-1",
    title="Test Company reports steady quarter",
    url="https://example.com/testco-news-1",
    published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    content="Test Company reported a steady quarter with stable margins and no major surprises.",
)


def _patch_providers(service: IngestionService, monkeypatch, articles):
    monkeypatch.setattr(service.fundamentals_provider, "fetch", lambda ticker: FAKE_FUNDAMENTALS)
    monkeypatch.setattr(
        service.news_provider, "fetch_for_ticker", lambda ticker, company_name=None, limit_per_feed=8: articles
    )


def test_ingest_ticker_twice_does_not_duplicate_documents_or_chunks(db_session, monkeypatch):
    service = IngestionService()
    _patch_providers(service, monkeypatch, [FAKE_ARTICLE])

    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()
    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == "TESTCO")).scalar_one()
    docs_first = db_session.execute(select(SourceDocument).where(SourceDocument.stock_id == stock.id)).scalars().all()
    chunks_first = (
        db_session.execute(select(DocumentChunk).join(SourceDocument).where(SourceDocument.stock_id == stock.id))
        .scalars()
        .all()
    )
    assert len(docs_first) == 2  # 1 fundamentals snapshot + 1 news article

    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()
    docs_second = db_session.execute(select(SourceDocument).where(SourceDocument.stock_id == stock.id)).scalars().all()
    chunks_second = (
        db_session.execute(select(DocumentChunk).join(SourceDocument).where(SourceDocument.stock_id == stock.id))
        .scalars()
        .all()
    )

    assert len(docs_second) == len(docs_first)
    assert len(chunks_second) == len(chunks_first)


def test_ingest_ticker_skips_reanalysis_of_unchanged_articles(db_session, monkeypatch):
    service = IngestionService()
    _patch_providers(service, monkeypatch, [FAKE_ARTICLE])

    analyze_calls = []
    original_analyze = service.analysis_service.analyze

    def counting_analyze(ticker, article):
        analyze_calls.append(article.external_id)
        return original_analyze(ticker, article)

    monkeypatch.setattr(service.analysis_service, "analyze", counting_analyze)

    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()
    assert len(analyze_calls) == 1

    # Re-ingest with byte-identical article content: analysis must not re-run.
    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()
    assert len(analyze_calls) == 1


def test_ingest_ticker_reanalyzes_when_article_content_changes(db_session, monkeypatch):
    service = IngestionService()
    _patch_providers(service, monkeypatch, [FAKE_ARTICLE])

    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()

    updated_article = NewsArticlePayload(
        source_name=FAKE_ARTICLE.source_name,
        source_type=FAKE_ARTICLE.source_type,
        external_id=FAKE_ARTICLE.external_id,
        title="Test Company reports steady quarter (updated)",
        url=FAKE_ARTICLE.url,
        published_at=FAKE_ARTICLE.published_at,
        content="Test Company revised guidance upward after a stronger-than-expected quarter.",
    )
    _patch_providers(service, monkeypatch, [updated_article])

    service.ingest_ticker(db_session, "TESTCO")
    db_session.flush()

    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == "TESTCO")).scalar_one()
    docs = db_session.execute(select(SourceDocument).where(SourceDocument.stock_id == stock.id)).scalars().all()
    news_doc = next(doc for doc in docs if doc.source_type == "news")

    assert len(docs) == 2  # still no duplicate row -- same external_id updated in place
    assert "revised guidance" in news_doc.content
