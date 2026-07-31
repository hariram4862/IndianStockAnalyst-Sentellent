from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class FundamentalsPayload:
    ticker: str
    company_name: str
    exchange: str
    sector: str | None
    industry: str | None
    isin: str | None
    market_cap_inr: float | None
    current_price_inr: float | None
    pe_ratio: float | None
    dividend_yield: float | None
    debt_to_equity: float | None
    fundamentals_summary: str


@dataclass
class NewsArticlePayload:
    source_name: str
    source_type: str
    external_id: str
    title: str
    url: str | None
    published_at: datetime | None
    content: str
