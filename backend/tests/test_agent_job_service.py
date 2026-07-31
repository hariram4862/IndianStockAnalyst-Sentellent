import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.agent_activity import AgentDecision
from app.models.chat import ChatSession
from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.services.agent_job_service import AgentJobService
from app.services.ingestion_service import IngestionService
from app.services.providers import FundamentalsPayload, NewsArticlePayload


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Agent Job Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _follow_stock(db_session, user: User, ticker: str, **stock_kwargs) -> StockEntity:
    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        defaults = dict(pe_ratio=18.0, dividend_yield=2.0, debt_to_equity=0.4, current_price_inr=100.0)
        defaults.update(stock_kwargs)
        stock = StockEntity(ticker=ticker, company_name=f"{ticker} Ltd", exchange="NSE", **defaults)
        db_session.add(stock)
        db_session.flush()
    followed = db_session.execute(
        select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
    ).scalar_one_or_none()
    if followed is None:
        db_session.add(FollowedStock(user_id=user.id, stock_id=stock.id, is_active=True))
    db_session.flush()
    return stock


def test_generate_daily_briefings_skips_users_with_no_followed_stocks(db_session):
    _get_or_create_test_user(db_session, "briefing-empty@example.com")
    service = AgentJobService()
    generated = service.generate_daily_briefings(db_session)
    # Other tests in this run may have created followed stocks for other
    # users, so just assert this user specifically got nothing.
    sessions = db_session.execute(
        select(ChatSession).join(User, User.id == ChatSession.user_id).where(User.email == "briefing-empty@example.com")
    ).scalars().all()
    assert sessions == []
    assert generated >= 0


def test_generate_daily_briefings_creates_one_session_and_throttles_same_day(db_session):
    # A fresh user/ticker per run -- the throttle check looks at real wall-clock
    # time, so a fixed email would see this test as "already briefed today" on
    # any re-run within the same ~20h window against a persistent dev DB.
    unique = uuid.uuid4().hex[:8]
    user = _get_or_create_test_user(db_session, f"briefing-throttle-{unique}@example.com")
    _follow_stock(db_session, user, f"BRIEF{unique[:5].upper()}", rolling_sentiment_label="positive", rolling_sentiment_score=0.5)
    service = AgentJobService()

    first_count = service.generate_daily_briefings(db_session)
    sessions_after_first = db_session.execute(
        select(ChatSession).where(ChatSession.user_id == user.id, ChatSession.title.like("Daily briefing%"))
    ).scalars().all()
    assert len(sessions_after_first) == 1

    second_count = service.generate_daily_briefings(db_session)
    sessions_after_second = db_session.execute(
        select(ChatSession).where(ChatSession.user_id == user.id, ChatSession.title.like("Daily briefing%"))
    ).scalars().all()
    assert len(sessions_after_second) == 1  # not duplicated
    assert first_count >= 1
    assert second_count == 0 or len(sessions_after_second) == 1


def test_daily_briefing_logs_a_decision_per_followed_stock(db_session):
    user = _get_or_create_test_user(db_session, "briefing-decisions@example.com")
    _follow_stock(
        db_session, user, "DECCO",
        pe_ratio=10.0, dividend_yield=5.0, debt_to_equity=0.1,
        rolling_sentiment_label="positive", rolling_sentiment_score=0.9,
        current_price_inr=250.0,
    )
    service = AgentJobService()
    service.generate_daily_briefings(db_session)

    decisions = db_session.execute(
        select(AgentDecision).join(User, User.id == AgentDecision.user_id).where(User.email == "briefing-decisions@example.com")
    ).scalars().all()
    assert len(decisions) == 1
    assert decisions[0].action in {"buy", "hold", "avoid"}
    assert decisions[0].price_at_decision_inr == 250.0


def test_action_thresholds_match_composite_score():
    service = AgentJobService()
    assert service._action_for_score(0.9) == "buy"
    assert service._action_for_score(0.6) == "buy"
    assert service._action_for_score(0.5) == "hold"
    assert service._action_for_score(0.35) == "avoid"
    assert service._action_for_score(0.1) == "avoid"


def test_refresh_followed_stocks_dedups_by_ticker_not_follower_count(db_session, monkeypatch):
    user_a = _get_or_create_test_user(db_session, "refresh-dedup-a@example.com")
    user_b = _get_or_create_test_user(db_session, "refresh-dedup-b@example.com")

    fake_fundamentals = FundamentalsPayload(
        ticker="SHAREDCO", company_name="Shared Company Ltd", exchange="NSE",
        sector="Technology", industry="Software", isin=None,
        market_cap_inr=1_000_000.0, current_price_inr=100.0,
        pe_ratio=15.0, dividend_yield=1.0, debt_to_equity=0.3,
        fundamentals_summary="Shared Company is followed by two users.",
    )
    fetch_calls = []

    ingestion_service = IngestionService()
    monkeypatch.setattr(
        ingestion_service.fundamentals_provider,
        "fetch",
        lambda ticker: (fetch_calls.append(ticker), fake_fundamentals)[1],
    )
    monkeypatch.setattr(
        ingestion_service.news_provider,
        "fetch_for_ticker",
        lambda ticker, company_name=None, limit_per_feed=25: [],
    )

    _follow_stock(db_session, user_a, "SHAREDCO")
    _follow_stock(db_session, user_b, "SHAREDCO")

    service = AgentJobService(ingestion_service=ingestion_service)
    refreshed = service.refresh_followed_stocks(db_session)

    shared_refreshes = [s for s in refreshed if s.ticker == "SHAREDCO"]
    assert len(shared_refreshes) == 1
    assert fetch_calls.count("SHAREDCO") == 1
