from sqlalchemy import select

from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.gemini_service import GeminiService
from app.services.research_service import ResearchService


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Recommend Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _follow_stock(db_session, user: User, ticker: str) -> StockEntity:
    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        stock = StockEntity(
            ticker=ticker,
            company_name=f"{ticker} Ltd",
            exchange="NSE",
            pe_ratio=18.0,
            dividend_yield=2.0,
            debt_to_equity=0.4,
            rolling_sentiment_label="positive",
            rolling_sentiment_score=0.5,
        )
        db_session.add(stock)
        db_session.flush()

    followed = db_session.execute(
        select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
    ).scalar_one_or_none()
    if followed is None:
        db_session.add(FollowedStock(user_id=user.id, stock_id=stock.id, is_active=True))
    db_session.flush()
    return stock


def test_recommend_chat_response_exposes_intent_and_ranked_stocks(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "recommend-response@example.com")
    _follow_stock(db_session, user, "RANKCO")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="Recommend stocks for my profile"))

    assert response.intent == "recommend"
    assert len(response.ranked_stocks) == 1
    assert response.ranked_stocks[0].ticker == "RANKCO"
    assert response.ranked_stocks[0].composite_score > 0


def test_recommend_intent_and_ranked_stocks_survive_session_history_replay(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "recommend-history@example.com")
    _follow_stock(db_session, user, "HISTCO")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="Recommend stocks for my profile"))
    messages = service.get_session_messages(db_session, user, response.session_id)
    assistant_message = messages[-1]

    assert assistant_message.intent == "recommend"
    assert len(assistant_message.ranked_stocks) == 1
    assert assistant_message.ranked_stocks[0].ticker == "HISTCO"


def test_research_intent_chat_response_has_empty_ranked_stocks(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "research-intent@example.com")
    _follow_stock(db_session, user, "PLAINCO")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="What's the sentiment on PLAINCO this week?"))

    assert response.intent == "research"
    assert response.ranked_stocks == []
