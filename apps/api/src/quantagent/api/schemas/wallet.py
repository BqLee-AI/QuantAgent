from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from quantagent.core.wallet import (
    CashBalanceSnapshot,
    PaperExecutionSnapshot,
    PaperOrderSnapshot,
    PositionSnapshot,
    TradingAccountSnapshot,
    WalletLedgerEntrySnapshot,
)


AccountModeValue = Literal["paper"]
PositionSideValue = Literal["long"]
OrderSideValue = Literal["buy", "sell"]
OrderTypeValue = Literal["market", "limit"]
PaperOrderStatusValue = Literal["open", "filled", "cancelled", "rejected"]
WalletLedgerEntryTypeValue = Literal[
    "deposit",
    "withdrawal",
    "adjustment",
    "trade",
    "fee",
    "dividend",
    "interest",
    "fx",
]
WalletLedgerSourceTypeValue = Literal["manual", "paper_order", "paper_execution"]


class WalletAccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    mode: AccountModeValue
    base_currency: str = Field(min_length=1)
    created_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: TradingAccountSnapshot) -> Self:
        return cls(
            account_id=snapshot.account_id,
            name=snapshot.name,
            mode=snapshot.mode.value,
            base_currency=snapshot.base_currency,
            created_at=snapshot.created_at,
        )


class WalletCashBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    total: Decimal
    available: Decimal
    locked: Decimal
    unsettled: Decimal
    updated_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: CashBalanceSnapshot) -> Self:
        return cls(
            account_id=snapshot.account_id,
            currency=snapshot.currency,
            total=snapshot.total,
            available=snapshot.available,
            locked=snapshot.locked,
            unsettled=snapshot.unsettled,
            updated_at=snapshot.updated_at,
        )


class WalletPositionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    market: str = Field(min_length=1)
    side: PositionSideValue
    quantity: Decimal
    sellable_quantity: Decimal
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    currency: str = Field(min_length=1)
    updated_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: PositionSnapshot) -> Self:
        return cls(
            account_id=snapshot.account_id,
            instrument=snapshot.instrument,
            market=snapshot.market,
            side=snapshot.side.value,
            quantity=snapshot.quantity,
            sellable_quantity=snapshot.sellable_quantity,
            average_cost=snapshot.average_cost,
            market_value=snapshot.market_value,
            unrealized_pnl=snapshot.unrealized_pnl,
            currency=snapshot.currency,
            updated_at=snapshot.updated_at,
        )


class WalletLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    entry_type: WalletLedgerEntryTypeValue
    currency: str = Field(min_length=1)
    amount: Decimal
    source_type: WalletLedgerSourceTypeValue
    source_ref: str = Field(min_length=1)
    occurred_at: datetime
    order_id: str | None = None
    execution_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: WalletLedgerEntrySnapshot) -> Self:
        return cls(
            entry_id=snapshot.entry_id,
            account_id=snapshot.account_id,
            entry_type=snapshot.entry_type.value,
            currency=snapshot.currency,
            amount=snapshot.amount,
            source_type=snapshot.source_type.value,
            source_ref=snapshot.source_ref,
            occurred_at=snapshot.occurred_at,
            order_id=snapshot.order_id,
            execution_id=snapshot.execution_id,
            metadata=dict(snapshot.metadata),
            created_at=snapshot.created_at,
        )


class WalletPaperOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    client_order_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    market: str = Field(min_length=1)
    side: OrderSideValue
    order_type: OrderTypeValue
    quantity: Decimal
    limit_price: Decimal | None = None
    currency: str = Field(min_length=1)
    status: PaperOrderStatusValue
    requested_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_snapshot(cls, snapshot: PaperOrderSnapshot) -> Self:
        return cls(
            order_id=snapshot.order_id,
            account_id=snapshot.account_id,
            client_order_id=snapshot.client_order_id,
            instrument=snapshot.instrument,
            market=snapshot.market,
            side=snapshot.side.value,
            order_type=snapshot.order_type.value,
            quantity=snapshot.quantity,
            limit_price=snapshot.limit_price,
            currency=snapshot.currency,
            status=snapshot.status.value,
            requested_at=snapshot.requested_at,
            completed_at=snapshot.completed_at,
        )


class WalletPaperExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    order_id: str | None = None
    idempotency_key: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    market: str = Field(min_length=1)
    side: OrderSideValue
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    currency: str = Field(min_length=1)
    fee_amount: Decimal
    fee_currency: str = Field(min_length=1)
    executed_at: datetime
    created_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: PaperExecutionSnapshot) -> Self:
        return cls(
            execution_id=snapshot.execution_id,
            account_id=snapshot.account_id,
            order_id=snapshot.order_id,
            idempotency_key=snapshot.idempotency_key,
            instrument=snapshot.instrument,
            market=snapshot.market,
            side=snapshot.side.value,
            quantity=snapshot.quantity,
            price=snapshot.price,
            gross_amount=snapshot.gross_amount,
            currency=snapshot.currency,
            fee_amount=snapshot.fee_amount,
            fee_currency=snapshot.fee_currency,
            executed_at=snapshot.executed_at,
            created_at=snapshot.created_at,
        )
