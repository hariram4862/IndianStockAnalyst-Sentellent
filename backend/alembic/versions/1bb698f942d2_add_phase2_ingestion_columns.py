"""add phase2 ingestion columns

Revision ID: 1bb698f942d2
Revises: cd9368bdf1a4
Create Date: 2026-07-30 19:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1bb698f942d2"
down_revision: Union[str, Sequence[str], None] = "cd9368bdf1a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_entities", sa.Column("rolling_sentiment_label", sa.String(length=32), nullable=True))
    op.add_column("stock_entities", sa.Column("rolling_sentiment_score", sa.Numeric(5, 2), nullable=True))
    op.add_column("stock_entities", sa.Column("last_news_refresh_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("source_documents", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("source_documents", sa.Column("sentiment_label", sa.String(length=32), nullable=True))
    op.add_column("source_documents", sa.Column("sentiment_score", sa.Numeric(5, 2), nullable=True))
    op.add_column("source_documents", sa.Column("impact_label", sa.String(length=32), nullable=True))
    op.add_column("source_documents", sa.Column("event_type", sa.String(length=64), nullable=True))
    op.add_column("source_documents", sa.Column("mentioned_tickers", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_source_documents_content_hash"), "source_documents", ["content_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_source_documents_content_hash"), table_name="source_documents")
    op.drop_column("source_documents", "mentioned_tickers")
    op.drop_column("source_documents", "event_type")
    op.drop_column("source_documents", "impact_label")
    op.drop_column("source_documents", "sentiment_score")
    op.drop_column("source_documents", "sentiment_label")
    op.drop_column("source_documents", "content_hash")

    op.drop_column("stock_entities", "last_news_refresh_at")
    op.drop_column("stock_entities", "rolling_sentiment_score")
    op.drop_column("stock_entities", "rolling_sentiment_label")
