import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.agent_activity import AlertRule, TriggeredAlert
from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService


def _unique() -> str:
    # This suite runs repeatedly against a persistent local dev DB (services
    # commit internally, so the db_session fixture's rollback doesn't undo
    # prior runs' rows). A fresh suffix per call keeps every test's
    # user/ticker isolated from its own history instead of accumulating
    # duplicate rows that change what "exactly N" assertions actually count.
    return uuid.uuid4().hex[:8]


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Alert Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _follow_stock(db_session, user: User, ticker: str, **stock_kwargs) -> StockEntity:
    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        stock = StockEntity(ticker=ticker, company_name=f"{ticker} Ltd", exchange="NSE", **stock_kwargs)
        db_session.add(stock)
        db_session.flush()
    else:
        for key, value in stock_kwargs.items():
            setattr(stock, key, value)
    followed = db_session.execute(
        select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
    ).scalar_one_or_none()
    if followed is None:
        db_session.add(FollowedStock(user_id=user.id, stock_id=stock.id, is_active=True))
    db_session.flush()
    return stock


class _NoopNotificationService(NotificationService):
    def __init__(self):
        self.sent = []

    def send(self, subject: str, body: str) -> bool:
        self.sent.append((subject, body))
        return True


def test_create_rule_requires_following_the_ticker(db_session):
    user = _get_or_create_test_user(db_session, f"alert-not-following-{_unique()}@example.com")
    service = AlertService()
    try:
        service.create_rule(db_session, user, "GHOSTCO", "negative_sentiment", None)
        assert False, "expected ValueError for a ticker the user doesn't follow"
    except ValueError:
        pass


def test_debt_threshold_rule_requires_a_threshold(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-debt-no-threshold-{unique}@example.com")
    ticker = f"DEBT{unique[:6].upper()}"
    _follow_stock(db_session, user, ticker)
    service = AlertService()
    try:
        service.create_rule(db_session, user, ticker, "debt_threshold", None)
        assert False, "expected ValueError when debt_threshold rule has no threshold"
    except ValueError:
        pass


def test_create_rule_is_idempotent_for_the_same_condition(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-idempotent-{unique}@example.com")
    ticker = f"IDEM{unique[:6].upper()}"
    _follow_stock(db_session, user, ticker)
    service = AlertService()

    first = service.create_rule(db_session, user, ticker, "negative_sentiment", None)
    second = service.create_rule(db_session, user, ticker, "negative_sentiment", None)

    assert first.id == second.id
    rules = db_session.execute(select(AlertRule).where(AlertRule.user_id == user.id)).scalars().all()
    assert len(rules) == 1


def test_negative_sentiment_rule_fires_when_sentiment_flips_negative(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-negative-{unique}@example.com")
    ticker = f"NEG{unique[:6].upper()}"
    stock = _follow_stock(db_session, user, ticker, rolling_sentiment_label="neutral")
    notifications = _NoopNotificationService()
    service = AlertService(notification_service=notifications)
    service.create_rule(db_session, user, ticker, "negative_sentiment", None)

    stock.rolling_sentiment_label = "negative"
    stock.rolling_sentiment_score = -0.7
    fired = service.evaluate_alerts_for_stock(db_session, stock)

    assert fired == 1
    assert len(notifications.sent) == 1
    triggered = db_session.execute(select(TriggeredAlert).where(TriggeredAlert.user_id == user.id)).scalars().all()
    assert len(triggered) == 1
    assert ticker in triggered[0].message


def test_debt_threshold_rule_fires_only_when_breached(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-debt-{unique}@example.com")
    ticker = f"SAFE{unique[:6].upper()}"
    stock = _follow_stock(db_session, user, ticker, debt_to_equity=0.5)
    service = AlertService(notification_service=_NoopNotificationService())
    service.create_rule(db_session, user, ticker, "debt_threshold", 1.0)

    assert service.evaluate_alerts_for_stock(db_session, stock) == 0

    stock.debt_to_equity = 1.5
    assert service.evaluate_alerts_for_stock(db_session, stock) == 1


def test_rule_respects_cooldown_and_does_not_re_fire_immediately(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-cooldown-{unique}@example.com")
    ticker = f"COOL{unique[:6].upper()}"
    stock = _follow_stock(db_session, user, ticker, rolling_sentiment_label="negative", rolling_sentiment_score=-0.5)
    service = AlertService(notification_service=_NoopNotificationService())
    rule = service.create_rule(db_session, user, ticker, "negative_sentiment", None)

    assert service.evaluate_alerts_for_stock(db_session, stock) == 1
    # Still negative on the very next refresh -- must not re-notify immediately.
    assert service.evaluate_alerts_for_stock(db_session, stock) == 0

    # Simulate the cooldown having elapsed.
    db_session.execute(
        select(AlertRule).where(AlertRule.id == rule.id)
    ).scalar_one().last_triggered_at = datetime.now(timezone.utc) - timedelta(hours=25)
    assert service.evaluate_alerts_for_stock(db_session, stock) == 1


def test_evaluating_one_stock_does_not_trigger_another_stocks_rule(db_session):
    unique = _unique()
    user = _get_or_create_test_user(db_session, f"alert-isolation-{unique}@example.com")
    ticker_a = f"ISOA{unique[:5].upper()}"
    ticker_b = f"ISOB{unique[:5].upper()}"
    stock_a = _follow_stock(db_session, user, ticker_a, rolling_sentiment_label="negative")
    stock_b = _follow_stock(db_session, user, ticker_b, rolling_sentiment_label="negative")
    service = AlertService(notification_service=_NoopNotificationService())
    service.create_rule(db_session, user, ticker_a, "negative_sentiment", None)

    assert service.evaluate_alerts_for_stock(db_session, stock_b) == 0
    assert service.evaluate_alerts_for_stock(db_session, stock_a) == 1
