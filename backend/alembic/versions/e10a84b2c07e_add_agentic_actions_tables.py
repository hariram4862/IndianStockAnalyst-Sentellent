"""add agentic actions tables (alert_rules, triggered_alerts, agent_decisions)

Revision ID: e10a84b2c07e
Revises: 1bb698f942d2
Create Date: 2026-07-31 17:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e10a84b2c07e"
down_revision: Union[str, Sequence[str], None] = "1bb698f942d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "stock_id",
            sa.Integer(),
            sa.ForeignKey("stock_entities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "triggered_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "alert_rule_id",
            sa.Integer(),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "stock_id",
            sa.Integer(),
            sa.ForeignKey("stock_entities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "stock_id",
            sa.Integer(),
            sa.ForeignKey("stock_entities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("price_at_decision_inr", sa.Numeric(18, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_decisions")
    op.drop_table("triggered_alerts")
    op.drop_table("alert_rules")
