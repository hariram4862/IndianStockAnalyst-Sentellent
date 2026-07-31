from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StockEntity(Base):
    __tablename__ = "stock_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="NSE")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_cap_inr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    current_price_inr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    fundamentals_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rolling_sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rolling_sentiment_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_news_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    followed_by: Mapped[list["FollowedStock"]] = relationship(back_populates="stock")
    source_documents: Mapped[list["SourceDocument"]] = relationship(back_populates="stock")


class FollowedStock(Base):
    __tablename__ = "followed_stocks"
    __table_args__ = (
        UniqueConstraint("user_id", "stock_id", name="uq_followed_stocks_user_stock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stock_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="followed_stocks")
    stock: Mapped["StockEntity"] = relationship(back_populates="followed_by")


class UserPersonaMemory(Base):
    __tablename__ = "user_persona_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    investment_style: Mapped[str | None] = mapped_column(String(128), nullable=True)
    constraints_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="persona_memory")
