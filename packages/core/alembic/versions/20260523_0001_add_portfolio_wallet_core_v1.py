"""add portfolio wallet core v1

Revision ID: 20260523_0001
Revises: None
Create Date: 2026-05-23 00:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260523_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 先建账户与汇率基础表，再建 snapshot / order / execution / ledger，避免外键顺序问题。
    op.create_table(
        "trading_accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.Enum("paper", name="accountmode", native_enum=False, length=32), nullable=False),
        sa.Column("base_currency", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fx_rate_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("from_currency", sa.String(length=16), nullable=False),
        sa.Column("to_currency", sa.String(length=16), nullable=False),
        sa.Column("rate", sa.Numeric(24, 8), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_currency", "to_currency", "captured_at", name="uq_fx_rates_pair_time"),
    )
    op.create_table(
        "cash_balances",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("total", sa.Numeric(24, 8), nullable=False),
        sa.Column("available", sa.Numeric(24, 8), nullable=False),
        sa.Column("locked", sa.Numeric(24, 8), nullable=False),
        sa.Column("unsettled", sa.Numeric(24, 8), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "currency", name="uq_cash_balances_account_currency"),
    )
    op.create_index("ix_cash_balances_account_id", "cash_balances", ["account_id"], unique=False)
    op.create_table(
        "paper_orders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("client_order_id", sa.String(length=96), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("side", sa.Enum("buy", "sell", name="orderside", native_enum=False, length=32), nullable=False),
        sa.Column("order_type", sa.Enum("market", "limit", name="ordertype", native_enum=False, length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("limit_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "filled", "cancelled", "rejected", name="paperorderstatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "client_order_id", name="uq_paper_orders_account_client_order"),
    )
    op.create_index("ix_paper_orders_account_id_requested_at", "paper_orders", ["account_id", "requested_at"], unique=False)
    op.create_table(
        "positions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("side", sa.Enum("long", name="positionside", native_enum=False, length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("sellable_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("average_cost", sa.Numeric(24, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(24, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "instrument",
            "market",
            "side",
            "currency",
            name="uq_positions_account_instrument_market_side_currency",
        ),
    )
    op.create_index("ix_positions_account_id", "positions", ["account_id"], unique=False)
    op.create_table(
        "paper_executions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("side", sa.Enum("buy", "sell", name="orderside", native_enum=False, length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("gross_amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("fee_amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("fee_currency", sa.String(length=16), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_paper_executions_account_idempotency_key"),
    )
    op.create_index(
        "ix_paper_executions_account_id_executed_at",
        "paper_executions",
        ["account_id", "executed_at"],
        unique=False,
    )
    op.create_table(
        "wallet_ledger_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column(
            "entry_type",
            sa.Enum(
                "deposit",
                "withdrawal",
                "adjustment",
                "trade",
                "fee",
                "dividend",
                "interest",
                "fx",
                name="walletledgerentrytype",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("manual", "paper_order", "paper_execution", name="walletledgersourcetype", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("source_ref", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=True),
        sa.Column("execution_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["paper_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wallet_ledger_entries_account_id_occurred_at",
        "wallet_ledger_entries",
        ["account_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wallet_ledger_entries_account_id_occurred_at", table_name="wallet_ledger_entries")
    op.drop_table("wallet_ledger_entries")
    op.drop_index("ix_paper_executions_account_id_executed_at", table_name="paper_executions")
    op.drop_table("paper_executions")
    op.drop_index("ix_positions_account_id", table_name="positions")
    op.drop_table("positions")
    op.drop_index("ix_paper_orders_account_id_requested_at", table_name="paper_orders")
    op.drop_table("paper_orders")
    op.drop_index("ix_cash_balances_account_id", table_name="cash_balances")
    op.drop_table("cash_balances")
    op.drop_table("fx_rate_snapshots")
    op.drop_table("trading_accounts")
