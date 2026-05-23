from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base
from quantagent.core.wallet.domain import (
    AccountMode,
    OrderSide,
    OrderType,
    PaperOrderStatus,
    PositionSide,
    WalletLedgerEntryType,
    WalletLedgerSourceType,
    utcnow,
)


DECIMAL_PRECISION = 24
DECIMAL_SCALE = 8
# 统一金额/数量精度，保证 ORM、迁移和测试断言使用同一套定点语义。
MoneyNumeric = Numeric(DECIMAL_PRECISION, DECIMAL_SCALE)
QuantityNumeric = Numeric(DECIMAL_PRECISION, DECIMAL_SCALE)


class TradingAccountModel(Base):
    __tablename__ = "trading_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[AccountMode] = mapped_column(
        Enum(AccountMode, native_enum=False, length=32),
        nullable=False,
    )
    base_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CashBalanceModel(Base):
    __tablename__ = "cash_balances"
    __table_args__ = (UniqueConstraint("account_id", "currency", name="uq_cash_balances_account_currency"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    total: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    available: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    locked: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    unsettled: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PositionModel(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "instrument",
            "market",
            "side",
            "currency",
            name="uq_positions_account_instrument_market_side_currency",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[PositionSide] = mapped_column(
        Enum(PositionSide, native_enum=False, length=32),
        nullable=False,
    )
    quantity: Mapped[Any] = mapped_column(QuantityNumeric, nullable=False, default=0)
    sellable_quantity: Mapped[Any] = mapped_column(QuantityNumeric, nullable=False, default=0)
    average_cost: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    market_value: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    unrealized_pnl: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PaperOrderModel(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (UniqueConstraint("account_id", "client_order_id", name="uq_paper_orders_account_client_order"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_order_id: Mapped[str] = mapped_column(String(96), nullable=False)
    instrument: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide, native_enum=False, length=32), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, native_enum=False, length=32),
        nullable=False,
    )
    quantity: Mapped[Any] = mapped_column(QuantityNumeric, nullable=False)
    limit_price: Mapped[Any | None] = mapped_column(MoneyNumeric, nullable=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[PaperOrderStatus] = mapped_column(
        Enum(PaperOrderStatus, native_enum=False, length=32),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaperExecutionModel(Base):
    __tablename__ = "paper_executions"
    __table_args__ = (
        UniqueConstraint("account_id", "idempotency_key", name="uq_paper_executions_account_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[str | None] = mapped_column(ForeignKey("paper_orders.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    instrument: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide, native_enum=False, length=32), nullable=False)
    quantity: Mapped[Any] = mapped_column(QuantityNumeric, nullable=False)
    price: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False)
    gross_amount: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    fee_amount: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False, default=0)
    fee_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WalletLedgerEntryModel(Base):
    __tablename__ = "wallet_ledger_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type: Mapped[WalletLedgerEntryType] = mapped_column(
        Enum(WalletLedgerEntryType, native_enum=False, length=32),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False)
    source_type: Mapped[WalletLedgerSourceType] = mapped_column(
        Enum(WalletLedgerSourceType, native_enum=False, length=32),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("paper_orders.id", ondelete="SET NULL"), nullable=True)
    execution_id: Mapped[str | None] = mapped_column(
        ForeignKey("paper_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FxRateSnapshotModel(Base):
    __tablename__ = "fx_rate_snapshots"
    __table_args__ = (UniqueConstraint("from_currency", "to_currency", "captured_at", name="uq_fx_rates_pair_time"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    rate: Mapped[Any] = mapped_column(MoneyNumeric, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_cash_balances_account_id", CashBalanceModel.account_id)
Index("ix_positions_account_id", PositionModel.account_id)
Index("ix_paper_orders_account_id_requested_at", PaperOrderModel.account_id, PaperOrderModel.requested_at)
Index("ix_paper_executions_account_id_executed_at", PaperExecutionModel.account_id, PaperExecutionModel.executed_at)
Index("ix_wallet_ledger_entries_account_id_occurred_at", WalletLedgerEntryModel.account_id, WalletLedgerEntryModel.occurred_at)
