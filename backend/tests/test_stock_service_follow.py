from datetime import datetime, timezone

from sqlalchemy import select

from app.models.user import User
from app.schemas.stock import StockFollowRequest
from app.services.providers import FundamentalsPayload, NewsArticlePayload
from app.services.stock_service import StockService

FAKE_FUNDAMENTALS = FundamentalsPayload(
    ticker="FOLLOWCO",
    company_name="Follow Company Ltd",
    exchange="NSE",
    sector="Technology",
    industry="Software",
    isin=None,
    market_cap_inr=1_000_000.0,
    current_price_inr=100.0,
    pe_ratio=15.0,
    dividend_yield=1.0,
    debt_to_equity=0.3,
    fundamentals_summary="Follow Company is a fictional NSE-listed software business used for follow/unfollow tests.",
)

FAKE_ARTICLE = NewsArticlePayload(
    source_name="Test Feed",
    source_type="news",
    external_id="followco-news-1",
    title="Follow Company reports steady quarter",
    url="https://example.com/followco-news-1",
    published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    content="Follow Company reported a steady quarter with stable margins.",
)


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Follow Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _patch_providers(service: StockService, monkeypatch):
    monkeypatch.setattr(service.ingestion_service.fundamentals_provider, "fetch", lambda ticker: FAKE_FUNDAMENTALS)
    monkeypatch.setattr(
        service.ingestion_service.news_provider, "fetch_for_ticker", lambda ticker, limit_per_feed=8: [FAKE_ARTICLE]
    )


def test_unfollow_removes_stock_from_active_list(db_session, monkeypatch):
    service = StockService()
    _patch_providers(service, monkeypatch)
    user = _get_or_create_test_user(db_session, "unfollow-test@example.com")

    service.follow_stock(db_session, user, StockFollowRequest(ticker="FOLLOWCO"))
    assert "FOLLOWCO" in [f.stock.ticker for f in service.list_followed_stocks(db_session, user)]

    service.unfollow_stock(db_session, user, "FOLLOWCO")
    assert "FOLLOWCO" not in [f.stock.ticker for f in service.list_followed_stocks(db_session, user)]


def test_unfollow_raises_when_not_following(db_session, monkeypatch):
    service = StockService()
    _patch_providers(service, monkeypatch)
    user = _get_or_create_test_user(db_session, "unfollow-not-following@example.com")

    try:
        service.unfollow_stock(db_session, user, "FOLLOWCO")
        assert False, "expected ValueError for a ticker the user never followed"
    except ValueError:
        pass


def test_refollow_after_unfollow_does_not_duplicate_documents(db_session, monkeypatch):
    from app.models.document import SourceDocument
    from app.models.stock import StockEntity

    service = StockService()
    _patch_providers(service, monkeypatch)
    user = _get_or_create_test_user(db_session, "refollow-test@example.com")

    service.follow_stock(db_session, user, StockFollowRequest(ticker="FOLLOWCO"))
    service.unfollow_stock(db_session, user, "FOLLOWCO")
    service.follow_stock(db_session, user, StockFollowRequest(ticker="FOLLOWCO"))

    followed = service.list_followed_stocks(db_session, user)
    assert "FOLLOWCO" in [f.stock.ticker for f in followed]

    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == "FOLLOWCO")).scalar_one()
    docs = db_session.execute(select(SourceDocument).where(SourceDocument.stock_id == stock.id)).scalars().all()
    assert len(docs) == 2  # 1 fundamentals snapshot + 1 news article, no duplicates from re-following


def test_get_stock_detail_returns_fundamentals_and_documents(db_session, monkeypatch):
    service = StockService()
    _patch_providers(service, monkeypatch)
    user = _get_or_create_test_user(db_session, "detail-test@example.com")

    service.follow_stock(db_session, user, StockFollowRequest(ticker="FOLLOWCO"))
    detail = service.get_stock_detail(db_session, user, "FOLLOWCO")

    assert detail.stock.ticker == "FOLLOWCO"
    assert detail.is_followed is True
    assert len(detail.documents) == 2
    assert {doc.source_type for doc in detail.documents} == {"fundamentals", "news"}


def test_get_stock_detail_raises_when_not_following(db_session, monkeypatch):
    service = StockService()
    _patch_providers(service, monkeypatch)
    user = _get_or_create_test_user(db_session, "detail-not-following@example.com")

    try:
        service.get_stock_detail(db_session, user, "FOLLOWCO")
        assert False, "expected ValueError for a ticker the user does not follow"
    except ValueError:
        pass
