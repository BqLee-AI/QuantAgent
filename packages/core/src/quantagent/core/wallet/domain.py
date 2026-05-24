from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


DecimalLike = Decimal | str | int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_decimal(value: DecimalLike) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {value}") from exc


class AccountMode(StrEnum):
    PAPER = "paper"


class PositionSide(StrEnum):
    LONG = "long"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class PaperOrderStatus(StrEnum):
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class WalletLedgerEntryType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    ADJUSTMENT = "adjustment"
    TRADE = "trade"
    FEE = "fee"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FX = "fx"


class WalletLedgerSourceType(StrEnum):
    MANUAL = "manual"
    PAPER_ORDER = "paper_order"
    PAPER_EXECUTION = "paper_execution"


@dataclass(frozen=True)
class TradingAccountSnapshot:
    account_id: str
    name: str
    mode: AccountMode
    base_currency: str
    created_at: datetime


@dataclass(frozen=True)
class CashBalanceSnapshot:
    account_id: str
    currency: str
    total: Decimal
    available: Decimal
    locked: Decimal
    unsettled: Decimal
    updated_at: datetime


@dataclass(frozen=True)
class PositionSnapshot:
    account_id: str
    instrument: str
    market: str
    side: PositionSide
    quantity: Decimal
    sellable_quantity: Decimal
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    currency: str
    updated_at: datetime


@dataclass(frozen=True)
class PaperOrderSnapshot:
    order_id: str
    account_id: str
    client_order_id: str
    instrument: str
    market: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None
    currency: str
    status: PaperOrderStatus
    requested_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class PaperExecutionSnapshot:
    execution_id: str
    account_id: str
    order_id: str | None
    idempotency_key: str
    instrument: str
    market: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    currency: str
    fee_amount: Decimal
    fee_currency: str
    executed_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class WalletLedgerEntrySnapshot:
    entry_id: str
    account_id: str
    entry_type: WalletLedgerEntryType
    currency: str
    amount: Decimal
    source_type: WalletLedgerSourceType
    source_ref: str
    occurred_at: datetime
    order_id: str | None
    execution_id: str | None
    metadata: Mapping[str, str]
    created_at: datetime


@dataclass(frozen=True)
class FxRateSnapshotRecord:
    snapshot_id: str
    from_currency: str
    to_currency: str
    rate: Decimal
    source: str
    captured_at: datetime


@dataclass(frozen=True)
class WalletFacts:
    account_id: str
    mode: AccountMode
    available_cash: Mapping[str, Decimal]
    locked_cash: Mapping[str, Decimal]
    unsettled_cash: Mapping[str, Decimal]
    position_quantities: Mapping[str, Decimal]
    sellable_positions: Mapping[str, Decimal]
    single_instrument_exposure: Mapping[str, Decimal]
    paper_execution_allowed: bool


@dataclass(frozen=True)
class CreateTradingAccountCommand:
    name: str
    base_currency: str
    account_id: str | None = None
    mode: AccountMode = AccountMode.PAPER


@dataclass(frozen=True)
class RecordCashAdjustmentCommand:
    account_id: str
    currency: str
    amount: DecimalLike
    entry_type: WalletLedgerEntryType = WalletLedgerEntryType.ADJUSTMENT
    source_ref: str | None = None
    note: str | None = None
    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RecordPaperOrderCommand:
    account_id: str
    instrument: str
    market: str
    side: OrderSide
    order_type: OrderType
    quantity: DecimalLike
    currency: str
    client_order_id: str | None = None
    order_id: str | None = None
    limit_price: DecimalLike | None = None
    requested_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RecordPaperExecutionCommand:
    account_id: str
    idempotency_key: str
    instrument: str
    market: str
    side: OrderSide
    quantity: DecimalLike
    price: DecimalLike
    currency: str
    fee_amount: DecimalLike = Decimal("0")
    fee_currency: str | None = None
    order_id: str | None = None
    execution_id: str | None = None
    executed_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RecordFxRateSnapshotCommand:
    from_currency: str
    to_currency: str
    rate: DecimalLike
    source: str
    snapshot_id: str | None = None
    captured_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class ExecutionIngestionResult:
    execution: PaperExecutionSnapshot
    created: bool


def freeze_decimal_mapping(values: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
    return MappingProxyType(dict(values))
