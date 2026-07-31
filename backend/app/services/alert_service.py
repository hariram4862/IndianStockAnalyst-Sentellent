from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_activity import AlertRule, TriggeredAlert
from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.services.notification_service import NotificationService

VALID_RULE_TYPES = {"negative_sentiment", "positive_sentiment", "debt_threshold"}
# Don't re-notify for the same condition more than once a day even if the
# scheduled job runs every few hours and the condition is still true.
TRIGGER_COOLDOWN = timedelta(hours=24)


class AlertService:
    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    def create_rule(
        self, db: Session, user: User, ticker: str, rule_type: str, threshold: float | None
    ) -> AlertRule:
        if rule_type not in VALID_RULE_TYPES:
            raise ValueError(f"Unknown rule_type '{rule_type}'. Must be one of {sorted(VALID_RULE_TYPES)}.")
        if rule_type == "debt_threshold" and threshold is None:
            raise ValueError("debt_threshold rules require a threshold value.")

        normalized_ticker = ticker.strip().upper()
        followed = db.execute(
            select(FollowedStock)
            .join(StockEntity, StockEntity.id == FollowedStock.stock_id)
            .where(
                FollowedStock.user_id == user.id,
                FollowedStock.is_active.is_(True),
                StockEntity.ticker == normalized_ticker,
            )
        ).scalar_one_or_none()
        if followed is None:
            raise ValueError(f"You are not following {normalized_ticker}.")

        # Idempotent: re-submitting the same rule (e.g. a double-click, or a
        # client retry) reactivates/returns the existing one instead of
        # accumulating duplicate rules that would each fire independently.
        existing = db.execute(
            select(AlertRule).where(
                AlertRule.user_id == user.id,
                AlertRule.stock_id == followed.stock_id,
                AlertRule.rule_type == rule_type,
                AlertRule.threshold == threshold,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

        rule = AlertRule(
            user_id=user.id,
            stock_id=followed.stock_id,
            rule_type=rule_type,
            threshold=threshold,
            is_active=True,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    def list_rules(self, db: Session, user: User) -> list[AlertRule]:
        return list(
            db.execute(
                select(AlertRule).where(AlertRule.user_id == user.id, AlertRule.is_active.is_(True))
            ).scalars()
        )

    def delete_rule(self, db: Session, user: User, rule_id: int) -> None:
        rule = db.execute(
            select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == user.id)
        ).scalar_one_or_none()
        if rule is None:
            raise ValueError(f"Alert rule {rule_id} not found.")
        db.delete(rule)
        db.commit()

    def list_notifications(self, db: Session, user: User, limit: int = 30) -> list[TriggeredAlert]:
        return list(
            db.execute(
                select(TriggeredAlert)
                .where(TriggeredAlert.user_id == user.id)
                .order_by(TriggeredAlert.created_at.desc())
                .limit(limit)
            ).scalars()
        )

    def mark_notifications_read(self, db: Session, user: User) -> None:
        unread = db.execute(
            select(TriggeredAlert).where(TriggeredAlert.user_id == user.id, TriggeredAlert.is_read.is_(False))
        ).scalars()
        for notification in unread:
            notification.is_read = True
        db.commit()

    # --- Called by the scheduled job after a stock has just been refreshed ---

    def evaluate_alerts_for_stock(self, db: Session, stock: StockEntity) -> int:
        """Checks every active rule on this stock and fires the ones whose
        condition is met and aren't still in cooldown. Returns how many
        TriggeredAlerts were created (used for the job's summary log)."""
        rules = db.execute(
            select(AlertRule).where(AlertRule.stock_id == stock.id, AlertRule.is_active.is_(True))
        ).scalars()

        fired = 0
        for rule in rules:
            if self._in_cooldown(rule):
                continue
            message = self._condition_message(rule, stock)
            if message is None:
                continue

            db.add(TriggeredAlert(alert_rule_id=rule.id, user_id=rule.user_id, stock_id=stock.id, message=message))
            rule.last_triggered_at = datetime.now(timezone.utc)
            fired += 1

            self.notification_service.send(subject=f"Stock Analyst alert: {stock.ticker}", body=message)

        if fired:
            db.commit()
        return fired

    def _in_cooldown(self, rule: AlertRule) -> bool:
        if rule.last_triggered_at is None:
            return False
        last_triggered = rule.last_triggered_at
        if last_triggered.tzinfo is None:
            last_triggered = last_triggered.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_triggered < TRIGGER_COOLDOWN

    def _condition_message(self, rule: AlertRule, stock: StockEntity) -> str | None:
        if rule.rule_type == "negative_sentiment":
            if stock.rolling_sentiment_label == "negative":
                return f"{stock.ticker} sentiment turned negative (score {stock.rolling_sentiment_score})."
            return None

        if rule.rule_type == "positive_sentiment":
            if stock.rolling_sentiment_label == "positive":
                return f"{stock.ticker} sentiment turned positive (score {stock.rolling_sentiment_score})."
            return None

        if rule.rule_type == "debt_threshold":
            debt_to_equity = stock.debt_to_equity
            threshold = rule.threshold
            if debt_to_equity is not None and threshold is not None and float(debt_to_equity) > float(threshold):
                return f"{stock.ticker} debt-to-equity ({debt_to_equity}) breached your threshold of {threshold}."
            return None

        return None
