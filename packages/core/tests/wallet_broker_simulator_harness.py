from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db import Base
from quantagent.core.wallet import (
    CreateTradingAccountCommand,
    ExecutionIngestionResult,
    OrderSide,
    OrderType,
    PaperExecutionSnapshot,
    PaperOrderSnapshot,
    RecordCashAdjustmentCommand,
    RecordPaperExecutionCommand,
    RecordPaperOrderCommand,
    WalletFacts,
    WalletLedgerEntrySnapshot,
    WalletLedgerEntryType,
    WalletService,
)


DecimalLike = Decimal | str | int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BrokerSimulatorAccount:
    account_id: str
    name: str
    base_currency: str = "USD"


@dataclass(frozen=True)
class BrokerSimulatorCashBalance:
    currency: str
    total: DecimalLike
    source_key: str | None = None


@dataclass(frozen=True)
class BrokerSimulatorPositionContext:
    instrument: str
    market: str
    currency: str
    quantity: DecimalLike
    average_cost: DecimalLike | None = None


@dataclass(frozen=True)
class BrokerSimulatorFixture:
    account: BrokerSimulatorAccount
    cash_balances: tuple[BrokerSimulatorCashBalance, ...] = ()
    position_contexts: tuple[BrokerSimulatorPositionContext, ...] = ()


@dataclass(frozen=True)
class BrokerSimulatorOrderInput:
    instrument: str
    market: str
    side: OrderSide
    order_type: OrderType
    quantity: DecimalLike
    currency: str
    broker_order_id: str | None = None
    client_order_id: str | None = None
    limit_price: DecimalLike | None = None
    requested_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class BrokerSimulatorExecutionInput:
    source_key: str
    instrument: str
    market: str
    side: OrderSide
    quantity: DecimalLike
    price: DecimalLike
    currency: str
    external_execution_id: str | None = None
    broker_order_id: str | None = None
    fee_amount: DecimalLike = Decimal("0")
    fee_currency: str | None = None
    executed_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class BrokerSimulatorErrorInput:
    code: str
    message: str
    broker_status: str = "rejected"
    related_order_id: str | None = None
    related_source_key: str | None = None


@dataclass(frozen=True)
class BrokerSimulatorErrorResult:
    code: str
    message: str
    broker_status: str
    ingested: bool = False


class BrokerSimulatorHarness:
    def __init__(self, fixture: BrokerSimulatorFixture) -> None:
        self.fixture = fixture
        self.engine: Engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.service = WalletService(self.session_factory)
        self.account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id=fixture.account.account_id,
                name=fixture.account.name,
                base_currency=fixture.account.base_currency,
            )
        )
        self._seed_cash_balances()

    def __enter__(self) -> BrokerSimulatorHarness:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        self.engine.dispose()

    @property
    def account_id(self) -> str:
        return self.account.account_id

    def place_order(self, order: BrokerSimulatorOrderInput) -> PaperOrderSnapshot:
        return self.service.record_paper_order(
            RecordPaperOrderCommand(
                account_id=self.account_id,
                order_id=order.broker_order_id,
                client_order_id=order.client_order_id,
                instrument=order.instrument,
                market=order.market,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                currency=order.currency,
                limit_price=order.limit_price,
                requested_at=order.requested_at,
            )
        )

    def ingest_execution(self, execution: BrokerSimulatorExecutionInput) -> ExecutionIngestionResult:
        return self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=self.account_id,
                execution_id=execution.external_execution_id,
                order_id=execution.broker_order_id,
                idempotency_key=execution.source_key,
                instrument=execution.instrument,
                market=execution.market,
                side=execution.side,
                quantity=execution.quantity,
                price=execution.price,
                currency=execution.currency,
                fee_amount=execution.fee_amount,
                fee_currency=execution.fee_currency,
                executed_at=execution.executed_at,
            )
        )

    def ingest_partial_fill(
        self,
        execution: BrokerSimulatorExecutionInput,
        *,
        filled_quantity: DecimalLike,
    ) -> PaperExecutionSnapshot:
        raise NotImplementedError(
            "Partial fill is deferred in broker simulator harness V1."
            f" source_key={execution.source_key} filled_quantity={filled_quantity}"
        )

    def report_broker_error(self, error: BrokerSimulatorErrorInput) -> BrokerSimulatorErrorResult:
        return BrokerSimulatorErrorResult(
            code=error.code,
            message=error.message,
            broker_status=error.broker_status,
        )

    def list_cash_balances(self):
        return self.service.list_cash_balances(self.account_id)

    def list_positions(self):
        return self.service.list_positions(self.account_id)

    def list_paper_orders(self):
        return self.service.list_paper_orders(self.account_id)

    def list_paper_executions(self):
        return self.service.list_paper_executions(self.account_id)

    def list_ledger_entries(self):
        return self.service.list_ledger_entries(self.account_id)

    def get_wallet_facts(self) -> WalletFacts:
        return self.service.get_wallet_facts(self.account_id)

    def assert_position_contexts_match(self, expected_contexts: Iterable[BrokerSimulatorPositionContext]) -> None:
        expected_by_key = {
            self._position_key(context.instrument, context.market, context.currency): context for context in expected_contexts
        }
        actual_by_key = {
            self._position_key(position.instrument, position.market, position.currency): position
            for position in self.service.list_positions(self.account_id)
        }
        if set(expected_by_key) != set(actual_by_key):
            raise AssertionError(
                f"Broker simulator position contexts do not match actual wallet positions:"
                f" expected={sorted(expected_by_key)} actual={sorted(actual_by_key)}"
            )

        for key, context in expected_by_key.items():
            position = actual_by_key[key]
            expected_quantity = Decimal(str(context.quantity))
            if position.quantity != expected_quantity:
                raise AssertionError(
                    f"Broker simulator position context quantity mismatch for {key}:"
                    f" expected={expected_quantity} actual={position.quantity}"
                )
            if context.average_cost is not None:
                expected_average_cost = Decimal(str(context.average_cost))
                if position.average_cost != expected_average_cost:
                    raise AssertionError(
                        f"Broker simulator position context average_cost mismatch for {key}:"
                        f" expected={expected_average_cost} actual={position.average_cost}"
                    )

    def _seed_cash_balances(self) -> None:
        for balance in self.fixture.cash_balances:
            self.service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=self.account_id,
                    currency=balance.currency,
                    amount=balance.total,
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                    source_ref=balance.source_key or f"broker-sim:cash:{balance.currency.strip().lower()}",
                )
            )

    def _position_key(self, instrument: str, market: str, currency: str) -> str:
        return f"{instrument}:{market}:{currency}"
