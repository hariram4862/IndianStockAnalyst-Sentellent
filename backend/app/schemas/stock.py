from datetime import datetime

from pydantic import BaseModel


class StockFollowRequest(BaseModel):
    ticker: str


class StockSummaryResponse(BaseModel):
    id: int
    ticker: str
    company_name: str
    exchange: str
    sector: str | None
    industry: str | None
    current_price_inr: float | None
    market_cap_inr: float | None
    pe_ratio: float | None
    dividend_yield: float | None
    debt_to_equity: float | None
    fundamentals_summary: str | None
    rolling_sentiment_label: str | None = None
    rolling_sentiment_score: float | None = None


class FollowedStockResponse(BaseModel):
    id: int
    is_active: bool
    followed_at: datetime
    last_ingested_at: datetime | None
    stock: StockSummaryResponse


class StockIngestionResponse(BaseModel):
    followed_stock: FollowedStockResponse
    ingested_documents: int
    ingested_chunks: int
    message: str


class StockRefreshResponse(StockIngestionResponse):
    pass
