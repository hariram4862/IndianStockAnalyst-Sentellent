from datetime import datetime

from pydantic import BaseModel


class IndexQuoteResponse(BaseModel):
    name: str
    symbol: str
    price: float
    change: float
    change_percent: float


class IndexIntradayPointResponse(BaseModel):
    time: str
    price: float


class MarketMoverResponse(BaseModel):
    ticker: str
    price: float
    change_percent: float


class MarketMoversResponse(BaseModel):
    gainers: list[MarketMoverResponse]
    losers: list[MarketMoverResponse]


class MarketHeadlineResponse(BaseModel):
    title: str
    url: str
    source_name: str
    published_at: datetime | None
