from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from quantagent.core.wallet.domain import (
    AccountMode,
    CashBalanceSnapshot,
    CreateTradingAccountCommand,
    ExecutionIngestionResult,
    FxRateSnapshotRecord,
    OrderSide,
    OrderType,
    PaperExecutionSnapshot,
    PaperOrderSnapshot,
    PaperOrderStatus,
    PositionSide,
    PositionSnapshot,
    RecordCashAdjustmentCommand,
    RecordFxRateSnapshotCommand,
    RecordPaperExecutionCommand,
    RecordPaperOrderCommand,
    TradingAccountSnapshot,
    WalletFacts,
    WalletLedgerEntrySnapshot,
    WalletLedgerEntryType,
    WalletLedgerSourceType,
    freeze_decimal_mapping,
    to_decimal,
)
from quantagent.core.wallet.models import (
    CashBalanceModel,
    FxRateSnapshotModel,
    PaperExecutionModel,
    PaperOrderModel,
    PositionModel,
    TradingAccountModel,
    WalletLedgerEntryModel,
)
from quantagent.core.wallet.repository import WalletRepository


class WalletService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_trading_account(self, command: CreateTradingAccountCommand) -> TradingAccountSnapshot:
        if command.mode is not AccountMode.PAPER:
            raise ValueError("Portfolio Wallet Core V1 only supports paper accounts.")
        if not command.name.strip():
            raise ValueError("Trading account name must not be empty.")

        account_id = self._normalize_optional_identifier(command.account_id) or self._new_id("acct")
        with self._session_factory.begin() as session:
            repository = WalletRepository(session)
            if repository.get_account(account_id) is not None:
                raise ValueError(f"Trading account already exists: {account_id}")

            model = TradingAccountModel(
                id=account_id,
                name=command.name,
                mode=command.mode,
                base_currency=self._normalize_currency(command.base_currency),
            )
            repository.add(model)
            repository.flush()
            return self._to_account_snapshot(model)

    def get_trading_account(self, account_id: str) -> TradingAccountSnapshot | None:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            account = repository.get_account(account_id)
            return None if account is None else self._to_account_snapshot(account)

    def record_cash_adjustment(self, command: RecordCashAdjustmentCommand) -> WalletLedgerEntrySnapshot:
        amount = to_decimal(command.amount)
        if amount == 0:
            raise ValueError("Cash adjustment amount must not be zero.")
        currency = self._normalize_currency(command.currency)
        occurred_at = self._normalize_timestamp(command.occurred_at, field_name="Cash adjustment occurred_at")
        source_ref = self._normalize_optional_identifier(command.source_ref)
        self._validate_manual_entry_type(command.entry_type, amount)
        with self._session_factory.begin() as session:
            repository = WalletRepository(session)
            self._require_paper_account(repository, command.account_id)
            balance = repository.get_or_create_cash_balance(
                command.account_id,
                currency,
                balance_id=self._new_id("bal"),
            )
            self._apply_balance_delta(balance, total_delta=amount, available_delta=amount)
            self._touch_snapshot(balance, occurred_at)
            entry = WalletLedgerEntryModel(
                id=self._new_id("led"),
                account_id=command.account_id,
                entry_type=command.entry_type,
                currency=currency,
                amount=amount,
                source_type=WalletLedgerSourceType.MANUAL,
                source_ref=source_ref or f"manual:{command.entry_type.value}:{uuid4().hex}",
                occurred_at=occurred_at,
                metadata_json=self._note_metadata(command.note),
            )
            repository.add(entry)
            repository.flush()
            return self._to_ledger_snapshot(entry)

    def record_paper_order(self, command: RecordPaperOrderCommand) -> PaperOrderSnapshot:
        quantity = self._require_positive_decimal(command.quantity, "Order quantity")
        limit_price = None if command.limit_price is None else to_decimal(command.limit_price)
        if limit_price is not None and limit_price <= 0:
            raise ValueError("Order limit_price must be greater than zero.")
        if command.order_type is OrderType.LIMIT and limit_price is None:
            raise ValueError("LIMIT orders require a positive limit_price.")
        if command.order_type is OrderType.MARKET and limit_price is not None:
            raise ValueError("MARKET orders must not include limit_price.")
        requested_at = self._normalize_timestamp(command.requested_at, field_name="Order requested_at")
        order_id = self._normalize_optional_identifier(command.order_id) or self._new_id("ord")
        client_order_id = self._normalize_optional_identifier(command.client_order_id) or order_id
        try:
            with self._session_factory.begin() as session:
                repository = WalletRepository(session)
                self._require_paper_account(repository, command.account_id)
                order = PaperOrderModel(
                    id=order_id,
                    account_id=command.account_id,
                    client_order_id=client_order_id,
                    instrument=self._require_non_empty(command.instrument, "Order instrument"),
                    market=self._require_non_empty(command.market, "Order market"),
                    side=command.side,
                    order_type=command.order_type,
                    quantity=quantity,
                    limit_price=limit_price,
                    currency=self._normalize_currency(command.currency),
                    status=PaperOrderStatus.OPEN,
                    requested_at=requested_at,
                )
                repository.add(order)
                repository.flush()
                return self._to_order_snapshot(order)
        except IntegrityError:
            with self._session_factory() as session:
                repository = WalletRepository(session)
                duplicate_order = repository.get_order_by_client_order_id(command.account_id, client_order_id)
                if duplicate_order is not None:
                    raise ValueError(f"Duplicate paper order client_order_id for account: {client_order_id}") from None
                if repository.get_order(order_id) is not None:
                    raise ValueError(f"Paper order already exists: {order_id}") from None
                raise

    def ingest_paper_execution(self, command: RecordPaperExecutionCommand) -> ExecutionIngestionResult:
        quantity = self._require_positive_decimal(command.quantity, "Execution quantity")
        price = self._require_positive_decimal(command.price, "Execution price")
        fee_amount = to_decimal(command.fee_amount)
        if fee_amount < 0:
            raise ValueError("Execution fee_amount must not be negative.")
        trade_currency = self._normalize_currency(command.currency)
        fee_currency = self._normalize_currency(command.fee_currency or command.currency)
        idempotency_key = self._require_non_empty(command.idempotency_key, "Execution idempotency_key")
        instrument = self._require_non_empty(command.instrument, "Execution instrument")
        market = self._require_non_empty(command.market, "Execution market")
        executed_at = self._normalize_timestamp(command.executed_at, field_name="Execution executed_at")
        with self._session_factory() as read_session:
            repository = WalletRepository(read_session)
            existing = repository.get_execution_by_idempotency_key(command.account_id, idempotency_key)
            if existing is not None:
                return ExecutionIngestionResult(execution=self._to_execution_snapshot(existing), created=False)

        try:
            with self._session_factory.begin() as session:
                repository = WalletRepository(session)
                self._require_paper_account(repository, command.account_id)

                order = None
                if command.order_id is not None:
                    order = repository.get_order(command.order_id)
                    if order is None or order.account_id != command.account_id:
                        raise ValueError(f"Unknown paper order: {command.order_id}")
                    self._validate_execution_against_order(
                        order=order,
                        instrument=instrument,
                        market=market,
                        side=command.side,
                        quantity=quantity,
                        price=price,
                        currency=trade_currency,
                    )

                gross_amount = quantity * price
                execution_id = command.execution_id or self._new_id("exe")
                execution = PaperExecutionModel(
                    id=execution_id,
                    account_id=command.account_id,
                    order_id=command.order_id,
                    idempotency_key=idempotency_key,
                    instrument=instrument,
                    market=market,
                    side=command.side,
                    quantity=quantity,
                    price=price,
                    gross_amount=gross_amount,
                    currency=trade_currency,
                    fee_amount=fee_amount,
                    fee_currency=fee_currency,
                    executed_at=executed_at,
                )
                repository.add(execution)

                # 先抢占账户内唯一幂等键, 再推进 snapshot / ledger, 避免并发重复入账.
                repository.flush()

                # 现金、持仓、成交和账本必须在同一事务内推进, 避免留下半笔入账状态.
                trade_cash_delta = gross_amount if command.side is OrderSide.SELL else -gross_amount
                cash_balance = repository.get_or_create_cash_balance(
                    command.account_id,
                    trade_currency,
                    balance_id=self._new_id("bal"),
                )
                self._apply_balance_delta(
                    cash_balance,
                    total_delta=trade_cash_delta,
                    available_delta=trade_cash_delta,
                )
                self._touch_snapshot(cash_balance, executed_at)

                fee_balance = cash_balance
                if fee_amount > 0:
                    if fee_currency != trade_currency:
                        fee_balance = repository.get_or_create_cash_balance(
                            command.account_id,
                            fee_currency,
                            balance_id=self._new_id("bal"),
                        )
                    self._apply_balance_delta(
                        fee_balance,
                        total_delta=-fee_amount,
                        available_delta=-fee_amount,
                    )
                    self._touch_snapshot(fee_balance, executed_at)

                position = repository.get_or_create_position(
                    command.account_id,
                    instrument,
                    market,
                    PositionSide.LONG,
                    trade_currency,
                    position_id=self._new_id("pos"),
                )
                # V1 没有独立市价快照, 当前持仓市值先以最新成交价近似, 后续再由行情/估值模块接管.
                self._apply_execution_to_position(
                    position=position,
                    side=command.side,
                    quantity=quantity,
                    price=price,
                    fee_amount=fee_amount if fee_currency == trade_currency else Decimal("0"),
                )
                self._touch_snapshot(position, executed_at)

                repository.add(
                    WalletLedgerEntryModel(
                        id=self._new_id("led"),
                        account_id=command.account_id,
                        entry_type=WalletLedgerEntryType.TRADE,
                        currency=trade_currency,
                        amount=trade_cash_delta,
                        source_type=WalletLedgerSourceType.PAPER_EXECUTION,
                        source_ref=idempotency_key,
                        occurred_at=executed_at,
                        order_id=command.order_id,
                        execution_id=execution_id,
                        metadata_json={
                            "instrument": instrument,
                            "market": market,
                            "side": command.side.value,
                        },
                    )
                )
                if fee_amount > 0:
                    repository.add(
                        WalletLedgerEntryModel(
                            id=self._new_id("led"),
                            account_id=command.account_id,
                            entry_type=WalletLedgerEntryType.FEE,
                            currency=fee_currency,
                            amount=-fee_amount,
                            source_type=WalletLedgerSourceType.PAPER_EXECUTION,
                            source_ref=idempotency_key,
                            occurred_at=executed_at,
                            order_id=command.order_id,
                            execution_id=execution_id,
                            metadata_json={"fee_currency": fee_currency},
                        )
                    )

                if order is not None:
                    order.status = PaperOrderStatus.FILLED
                    order.completed_at = executed_at

                repository.flush()
                return ExecutionIngestionResult(
                    execution=self._to_execution_snapshot(execution),
                    created=True,
                )
        except IntegrityError:
            with self._session_factory() as session:
                repository = WalletRepository(session)
                existing = repository.get_execution_by_idempotency_key(command.account_id, idempotency_key)
                if existing is None:
                    raise
                return ExecutionIngestionResult(execution=self._to_execution_snapshot(existing), created=False)

    def record_fx_rate_snapshot(self, command: RecordFxRateSnapshotCommand) -> FxRateSnapshotRecord:
        captured_at = self._normalize_timestamp(command.captured_at, field_name="FX captured_at")
        from_currency = self._normalize_currency(command.from_currency)
        to_currency = self._normalize_currency(command.to_currency)
        try:
            with self._session_factory.begin() as session:
                repository = WalletRepository(session)
                snapshot = FxRateSnapshotModel(
                    id=self._normalize_optional_identifier(command.snapshot_id) or self._new_id("fx"),
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=self._require_positive_decimal(command.rate, "FX rate"),
                    source=self._require_non_empty(command.source, "FX source"),
                    captured_at=captured_at,
                )
                repository.add(snapshot)
                repository.flush()
                return self._to_fx_snapshot(snapshot)
        except IntegrityError:
            with self._session_factory() as session:
                repository = WalletRepository(session)
                existing = repository.get_fx_rate_snapshot(from_currency, to_currency, captured_at)
                if existing is not None:
                    raise ValueError(
                        f"FX snapshot already exists for {from_currency}/{to_currency} at {captured_at.isoformat()}"
                    ) from None
                raise

    def list_cash_balances(self, account_id: str) -> Sequence[CashBalanceSnapshot]:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_cash_snapshot(balance) for balance in repository.list_cash_balances(account_id)]

    def list_positions(self, account_id: str) -> Sequence[PositionSnapshot]:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_position_snapshot(position) for position in repository.list_positions(account_id)]

    def list_paper_orders(self, account_id: str) -> Sequence[PaperOrderSnapshot]:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_order_snapshot(order) for order in repository.list_orders(account_id)]

    def list_paper_executions(self, account_id: str) -> Sequence[PaperExecutionSnapshot]:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_execution_snapshot(execution) for execution in repository.list_executions(account_id)]

    def list_ledger_entries(self, account_id: str, *, limit: int | None = None) -> Sequence[WalletLedgerEntrySnapshot]:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero.")
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_ledger_snapshot(entry) for entry in repository.list_ledger_entries(account_id, limit=limit)]

    def list_fx_rate_snapshots(self) -> Sequence[FxRateSnapshotRecord]:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            return [self._to_fx_snapshot(snapshot) for snapshot in repository.list_fx_rate_snapshots()]

    def get_wallet_facts(self, account_id: str) -> WalletFacts:
        with self._session_factory() as session:
            repository = WalletRepository(session)
            account = self._require_paper_account(repository, account_id)
            balances = repository.list_cash_balances(account_id)
            positions = repository.list_positions(account_id)

            available_cash = {balance.currency: Decimal(balance.available) for balance in balances}
            locked_cash = {balance.currency: Decimal(balance.locked) for balance in balances}
            unsettled_cash = {balance.currency: Decimal(balance.unsettled) for balance in balances}
            position_quantities = {
                self._position_key(position.instrument, position.market, position.currency): Decimal(position.quantity)
                for position in positions
            }
            sellable_positions = {
                self._position_key(position.instrument, position.market, position.currency): Decimal(
                    position.sellable_quantity
                )
                for position in positions
            }
            single_instrument_exposure = {
                self._position_key(position.instrument, position.market, position.currency): Decimal(position.market_value)
                for position in positions
            }
            return WalletFacts(
                account_id=account.id,
                mode=account.mode,
                available_cash=freeze_decimal_mapping(available_cash),
                locked_cash=freeze_decimal_mapping(locked_cash),
                unsettled_cash=freeze_decimal_mapping(unsettled_cash),
                position_quantities=freeze_decimal_mapping(position_quantities),
                sellable_positions=freeze_decimal_mapping(sellable_positions),
                single_instrument_exposure=freeze_decimal_mapping(single_instrument_exposure),
                paper_execution_allowed=account.mode is AccountMode.PAPER,
            )

    def _require_paper_account(self, repository: WalletRepository, account_id: str) -> TradingAccountModel:
        account = repository.get_account(account_id)
        if account is None:
            raise ValueError(f"Unknown trading account: {account_id}")
        if account.mode is not AccountMode.PAPER:
            raise ValueError("Portfolio Wallet Core V1 only supports paper accounts.")
        return account

    def _apply_execution_to_position(
        self,
        *,
        position: PositionModel,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        fee_amount: Decimal,
    ) -> None:
        current_quantity = Decimal(position.quantity)
        current_average_cost = Decimal(position.average_cost)

        if side is OrderSide.BUY:
            new_quantity = current_quantity + quantity
            new_cost_basis = (current_quantity * current_average_cost) + (quantity * price) + fee_amount
            new_average_cost = Decimal("0") if new_quantity == 0 else new_cost_basis / new_quantity
        else:
            current_sellable_quantity = Decimal(position.sellable_quantity)
            if current_sellable_quantity < quantity:
                raise ValueError("Sell quantity exceeds current sellable position.")
            new_quantity = current_quantity - quantity
            new_average_cost = Decimal("0") if new_quantity == 0 else current_average_cost

        market_value = new_quantity * price
        position.quantity = new_quantity
        position.sellable_quantity = new_quantity
        position.average_cost = new_average_cost
        position.market_value = market_value
        position.unrealized_pnl = market_value - (new_quantity * new_average_cost)

    def _apply_balance_delta(
        self,
        balance: CashBalanceModel,
        *,
        total_delta: Decimal,
        available_delta: Decimal,
        locked_delta: Decimal = Decimal("0"),
        unsettled_delta: Decimal = Decimal("0"),
    ) -> None:
        balance.total = Decimal(balance.total) + total_delta
        balance.available = Decimal(balance.available) + available_delta
        balance.locked = Decimal(balance.locked) + locked_delta
        balance.unsettled = Decimal(balance.unsettled) + unsettled_delta

        if balance.total < 0 or balance.available < 0 or balance.locked < 0 or balance.unsettled < 0:
            raise ValueError("Cash balance cannot become negative in paper wallet V1.")

    def _note_metadata(self, note: str | None) -> Mapping[str, str]:
        return {} if note is None else {"note": note}

    def _validate_execution_against_order(
        self,
        *,
        order: PaperOrderModel,
        instrument: str,
        market: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        currency: str,
    ) -> None:
        if order.status is not PaperOrderStatus.OPEN:
            raise ValueError(f"Paper order is not open: {order.id}")
        if order.instrument != instrument or order.market != market or order.side != side or order.currency != currency:
            raise ValueError("Paper execution does not match the referenced paper order.")
        if Decimal(order.quantity) != quantity:
            raise ValueError("Paper execution quantity must match the referenced paper order in V1.")
        if order.limit_price is not None:
            limit_price = Decimal(order.limit_price)
            if side is OrderSide.BUY and price > limit_price:
                raise ValueError("Buy execution price must not exceed the order limit_price.")
            if side is OrderSide.SELL and price < limit_price:
                raise ValueError("Sell execution price must not be below the order limit_price.")

    def _touch_snapshot(self, model: CashBalanceModel | PositionModel, occurred_at: datetime) -> None:
        model.updated_at = self._normalize_timestamp(occurred_at, field_name="Snapshot occurred_at")

    def _validate_manual_entry_type(self, entry_type: WalletLedgerEntryType, amount: Decimal) -> None:
        if entry_type is WalletLedgerEntryType.DEPOSIT and amount < 0:
            raise ValueError("Deposit amount must be positive.")
        if entry_type is WalletLedgerEntryType.WITHDRAWAL and amount > 0:
            raise ValueError("Withdrawal amount must be negative.")

    def _require_positive_decimal(self, value: Decimal | str | int, field_name: str) -> Decimal:
        decimal_value = to_decimal(value)
        if decimal_value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")
        return decimal_value

    def _require_non_empty(self, value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty.")
        return normalized

    def _normalize_optional_identifier(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_currency(self, currency: str) -> str:
        normalized = currency.strip().upper()
        if not normalized:
            raise ValueError("Currency must not be empty.")
        return normalized

    def _normalize_timestamp(self, timestamp: datetime, *, field_name: str) -> datetime:
        if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
            raise ValueError(f"{field_name} must be timezone-aware.")
        return timestamp.astimezone(timezone.utc)

    def _position_key(self, instrument: str, market: str, currency: str) -> str:
        return f"{instrument}:{market}:{currency}"

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    def _to_account_snapshot(self, model: TradingAccountModel) -> TradingAccountSnapshot:
        return TradingAccountSnapshot(
            account_id=model.id,
            name=model.name,
            mode=model.mode,
            base_currency=model.base_currency,
            created_at=model.created_at,
        )

    def _to_cash_snapshot(self, model: CashBalanceModel) -> CashBalanceSnapshot:
        return CashBalanceSnapshot(
            account_id=model.account_id,
            currency=model.currency,
            total=Decimal(model.total),
            available=Decimal(model.available),
            locked=Decimal(model.locked),
            unsettled=Decimal(model.unsettled),
            updated_at=model.updated_at,
        )

    def _to_position_snapshot(self, model: PositionModel) -> PositionSnapshot:
        return PositionSnapshot(
            account_id=model.account_id,
            instrument=model.instrument,
            market=model.market,
            side=model.side,
            quantity=Decimal(model.quantity),
            sellable_quantity=Decimal(model.sellable_quantity),
            average_cost=Decimal(model.average_cost),
            market_value=Decimal(model.market_value),
            unrealized_pnl=Decimal(model.unrealized_pnl),
            currency=model.currency,
            updated_at=model.updated_at,
        )

    def _to_order_snapshot(self, model: PaperOrderModel) -> PaperOrderSnapshot:
        return PaperOrderSnapshot(
            order_id=model.id,
            account_id=model.account_id,
            client_order_id=model.client_order_id,
            instrument=model.instrument,
            market=model.market,
            side=model.side,
            order_type=model.order_type,
            quantity=Decimal(model.quantity),
            limit_price=None if model.limit_price is None else Decimal(model.limit_price),
            currency=model.currency,
            status=model.status,
            requested_at=model.requested_at,
            completed_at=model.completed_at,
        )

    def _to_execution_snapshot(self, model: PaperExecutionModel) -> PaperExecutionSnapshot:
        return PaperExecutionSnapshot(
            execution_id=model.id,
            account_id=model.account_id,
            order_id=model.order_id,
            idempotency_key=model.idempotency_key,
            instrument=model.instrument,
            market=model.market,
            side=model.side,
            quantity=Decimal(model.quantity),
            price=Decimal(model.price),
            gross_amount=Decimal(model.gross_amount),
            currency=model.currency,
            fee_amount=Decimal(model.fee_amount),
            fee_currency=model.fee_currency,
            executed_at=model.executed_at,
            created_at=model.created_at,
        )

    def _to_ledger_snapshot(self, model: WalletLedgerEntryModel) -> WalletLedgerEntrySnapshot:
        return WalletLedgerEntrySnapshot(
            entry_id=model.id,
            account_id=model.account_id,
            entry_type=model.entry_type,
            currency=model.currency,
            amount=Decimal(model.amount),
            source_type=model.source_type,
            source_ref=model.source_ref,
            occurred_at=model.occurred_at,
            order_id=model.order_id,
            execution_id=model.execution_id,
            metadata=dict(model.metadata_json),
            created_at=model.created_at,
        )

    def _to_fx_snapshot(self, model: FxRateSnapshotModel) -> FxRateSnapshotRecord:
        return FxRateSnapshotRecord(
            snapshot_id=model.id,
            from_currency=model.from_currency,
            to_currency=model.to_currency,
            rate=Decimal(model.rate),
            source=model.source,
            captured_at=model.captured_at,
        )
