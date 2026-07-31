from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.market import (
    IndexIntradayPointResponse,
    IndexQuoteResponse,
    MarketHeadlineResponse,
    MarketMoversResponse,
)
from app.services.market_data_service import MarketDataService
from app.services.news_provider import NewsProvider

router = APIRouter(prefix="/market", tags=["Market"])
market_data_service = MarketDataService()
news_provider = NewsProvider()


@router.get("/indices", response_model=list[IndexQuoteResponse])
def get_indices(current_user: User = Depends(get_current_user)):
    return market_data_service.get_index_quotes()


@router.get("/indices/{symbol}/intraday", response_model=list[IndexIntradayPointResponse])
def get_index_intraday(symbol: str, current_user: User = Depends(get_current_user)):
    return market_data_service.get_index_intraday(f"^{symbol.upper()}" if not symbol.startswith("^") else symbol)


@router.get("/movers", response_model=MarketMoversResponse)
def get_movers(current_user: User = Depends(get_current_user)):
    return market_data_service.get_market_movers()


@router.get("/news", response_model=list[MarketHeadlineResponse])
def get_market_news(current_user: User = Depends(get_current_user)):
    return news_provider.fetch_market_headlines()
