from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.document import SourceDocument
from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.schemas.stock import (
    FollowedStockResponse,
    StockDetailResponse,
    StockFollowRequest,
    StockIngestionResponse,
    StockRefreshResponse,
    StockSummaryResponse,
    StockUnfollowResponse,
)
from app.services.citation_utils import build_citation
from app.services.ingestion_service import IngestionService

MAX_DETAIL_DOCUMENTS = 20


class StockService:
    def __init__(self) -> None:
        self.ingestion_service = IngestionService()

    def follow_stock(
        self,
        db: Session,
        user: User,
        payload: StockFollowRequest,
    ) -> StockIngestionResponse:
        ticker = payload.ticker.strip().upper()
        stock, ingested_documents, ingested_chunks, source_mode = self.ingestion_service.ingest_ticker(db, ticker)
        followed_stock = self._get_or_create_follow(db, user.id, stock.id)
        followed_stock.last_ingested_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(followed_stock)
        db.refresh(stock)

        return StockIngestionResponse(
            followed_stock=self._to_followed_stock_response(followed_stock),
            ingested_documents=ingested_documents,
            ingested_chunks=ingested_chunks,
            message=f"{ticker} is now available for grounded research using {source_mode} ingestion.",
        )

    def list_followed_stocks(self, db: Session, user: User) -> list[FollowedStockResponse]:
        stmt = (
            select(FollowedStock)
            .where(FollowedStock.user_id == user.id, FollowedStock.is_active.is_(True))
            .options(selectinload(FollowedStock.stock))
            .order_by(FollowedStock.followed_at.desc())
        )
        followed = db.execute(stmt).scalars().all()
        return [self._to_followed_stock_response(item) for item in followed]

    def refresh_stock(
        self,
        db: Session,
        user: User,
        ticker: str,
    ) -> StockRefreshResponse:
        normalized_ticker = ticker.strip().upper()
        stock, ingested_documents, ingested_chunks, source_mode = self.ingestion_service.ingest_ticker(
            db, normalized_ticker
        )
        followed_stock = self._get_or_create_follow(db, user.id, stock.id)
        followed_stock.last_ingested_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(followed_stock)
        db.refresh(stock)

        return StockRefreshResponse(
            followed_stock=self._to_followed_stock_response(followed_stock),
            ingested_documents=ingested_documents,
            ingested_chunks=ingested_chunks,
            message=f"{normalized_ticker} refreshed using {source_mode} ingestion.",
        )

    def unfollow_stock(self, db: Session, user: User, ticker: str) -> StockUnfollowResponse:
        normalized_ticker = ticker.strip().upper()
        stock = db.execute(select(StockEntity).where(StockEntity.ticker == normalized_ticker)).scalar_one_or_none()
        if stock is None:
            raise ValueError(f"{normalized_ticker} is not a known ticker.")

        followed_stock = db.execute(
            select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
        ).scalar_one_or_none()
        if followed_stock is None or not followed_stock.is_active:
            raise ValueError(f"You are not following {normalized_ticker}.")

        followed_stock.is_active = False
        db.commit()

        return StockUnfollowResponse(ticker=normalized_ticker, message=f"Unfollowed {normalized_ticker}.")

    def get_stock_detail(self, db: Session, user: User, ticker: str) -> StockDetailResponse:
        normalized_ticker = ticker.strip().upper()
        stock = db.execute(select(StockEntity).where(StockEntity.ticker == normalized_ticker)).scalar_one_or_none()
        if stock is None:
            raise ValueError(f"{normalized_ticker} is not a known ticker.")

        followed_stock = db.execute(
            select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
        ).scalar_one_or_none()
        if followed_stock is None or not followed_stock.is_active:
            raise ValueError(f"You are not following {normalized_ticker}.")

        documents = db.execute(
            select(SourceDocument)
            .where(SourceDocument.stock_id == stock.id)
            .order_by(SourceDocument.published_at.desc().nullslast(), SourceDocument.created_at.desc())
            .limit(MAX_DETAIL_DOCUMENTS)
        ).scalars().all()

        return StockDetailResponse(
            stock=self._to_stock_summary(stock),
            is_followed=True,
            followed_at=followed_stock.followed_at,
            last_ingested_at=followed_stock.last_ingested_at,
            documents=[build_citation(stock, document, document.content, None) for document in documents],
        )

    def _get_or_create_follow(self, db: Session, user_id: int, stock_id: int) -> FollowedStock:
        stmt = select(FollowedStock).where(
            FollowedStock.user_id == user_id,
            FollowedStock.stock_id == stock_id,
        )
        followed_stock = db.execute(stmt).scalar_one_or_none()
        if followed_stock is None:
            followed_stock = FollowedStock(user_id=user_id, stock_id=stock_id, is_active=True)
            db.add(followed_stock)
            db.flush()
        else:
            followed_stock.is_active = True
        return followed_stock

    def _to_followed_stock_response(self, followed_stock: FollowedStock) -> FollowedStockResponse:
        return FollowedStockResponse(
            id=followed_stock.id,
            is_active=followed_stock.is_active,
            followed_at=followed_stock.followed_at,
            last_ingested_at=followed_stock.last_ingested_at,
            stock=self._to_stock_summary(followed_stock.stock),
        )

    def _to_stock_summary(self, stock: StockEntity) -> StockSummaryResponse:
        return StockSummaryResponse(
            id=stock.id,
            ticker=stock.ticker,
            company_name=stock.company_name,
            exchange=stock.exchange,
            sector=stock.sector,
            industry=stock.industry,
            current_price_inr=float(stock.current_price_inr) if stock.current_price_inr is not None else None,
            market_cap_inr=float(stock.market_cap_inr) if stock.market_cap_inr is not None else None,
            pe_ratio=float(stock.pe_ratio) if stock.pe_ratio is not None else None,
            dividend_yield=float(stock.dividend_yield) if stock.dividend_yield is not None else None,
            debt_to_equity=float(stock.debt_to_equity) if stock.debt_to_equity is not None else None,
            fundamentals_summary=stock.fundamentals_summary,
            rolling_sentiment_label=stock.rolling_sentiment_label,
            rolling_sentiment_score=float(stock.rolling_sentiment_score)
            if stock.rolling_sentiment_score is not None
            else None,
        )
