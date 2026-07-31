from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AlertRule(Base):
    """A user-configured watch condition on a followed stock, evaluated by the
    scheduled agent job after each refresh (see app/jobs/scheduled_agent_job.py)."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stock_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "negative_sentiment" | "positive_sentiment" | "debt_threshold"
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
    stock: Mapped["StockEntity"] = relationship()


class TriggeredAlert(Base):
    """A historical firing of an AlertRule -- backs both the notification email
    body and the in-app notification bell (read/unread)."""

    __tablename__ = "triggered_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alert_rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stock_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
    stock: Mapped["StockEntity"] = relationship()


class AgentDecision(Base):
    """A paper-only buy/hold/avoid call the agent made autonomously (as part of
    a daily briefing), logged so its track record can be reviewed later --
    never executes a real trade."""

    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stock_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # "buy" | "hold" | "avoid"
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    composite_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    price_at_decision_inr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
    stock: Mapped["StockEntity"] = relationship()
