from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.wallet.domain import PositionSide
from quantagent.core.wallet.models import (
    CashBalanceModel,
    FxRateSnapshotModel,
    PaperExecutionModel,
    PaperOrderModel,
    PositionModel,
    TradingAccountModel,
    WalletLedgerEntryModel,
)


class WalletRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, model: object) -> None:
        self._session.add(model)

    def flush(self) -> None:
        self._session.flush()

    def get_account(self, account_id: str) -> TradingAccountModel | None:
        return self._session.get(TradingAccountModel, account_id)

    def get_cash_balance(self, account_id: str, currency: str) -> CashBalanceModel | None:
        statement = select(CashBalanceModel).where(
            CashBalanceModel.account_id == account_id,
            CashBalanceModel.currency == currency,
        )
        return self._session.scalar(statement)

    def get_or_create_cash_balance(self, account_id: str, currency: str, *, balance_id: str) -> CashBalanceModel:
        balance = self.get_cash_balance(account_id, currency)
        if balance is not None:
            return balance

        balance = CashBalanceModel(
            id=balance_id,
            account_id=account_id,
            currency=currency,
            total=0,
            available=0,
            locked=0,
            unsettled=0,
        )
        try:
            # 初始 snapshot 行受唯一约束保护; 并发首笔入账时用 savepoint 吃掉重复插入.
            with self._session.begin_nested():
                self._session.add(balance)
                self._session.flush()
            return balance
        except IntegrityError:
            existing = self.get_cash_balance(account_id, currency)
            if existing is None:
                raise
            return existing

    def get_position(
        self,
        account_id: str,
        instrument: str,
        market: str,
        side: PositionSide,
        currency: str,
    ) -> PositionModel | None:
        statement = select(PositionModel).where(
            PositionModel.account_id == account_id,
            PositionModel.instrument == instrument,
            PositionModel.market == market,
            PositionModel.side == side,
            PositionModel.currency == currency,
        )
        return self._session.scalar(statement)

    def get_or_create_position(
        self,
        account_id: str,
        instrument: str,
        market: str,
        side: PositionSide,
        currency: str,
        *,
        position_id: str,
    ) -> PositionModel:
        position = self.get_position(account_id, instrument, market, side, currency)
        if position is not None:
            return position

        position = PositionModel(
            id=position_id,
            account_id=account_id,
            instrument=instrument,
            market=market,
            side=side,
            quantity=0,
            sellable_quantity=0,
            average_cost=0,
            market_value=0,
            unrealized_pnl=0,
            currency=currency,
        )
        try:
            # 多列唯一键同样可能被并发首笔成交撞上, 冲突后回读胜出的 snapshot 行.
            with self._session.begin_nested():
                self._session.add(position)
                self._session.flush()
            return position
        except IntegrityError:
            existing = self.get_position(account_id, instrument, market, side, currency)
            if existing is None:
                raise
            return existing

    def get_order(self, order_id: str) -> PaperOrderModel | None:
        return self._session.get(PaperOrderModel, order_id)

    def get_order_by_client_order_id(self, account_id: str, client_order_id: str) -> PaperOrderModel | None:
        statement = select(PaperOrderModel).where(
            PaperOrderModel.account_id == account_id,
            PaperOrderModel.client_order_id == client_order_id,
        )
        return self._session.scalar(statement)

    def get_execution_by_idempotency_key(self, account_id: str, idempotency_key: str) -> PaperExecutionModel | None:
        # 幂等查询限定在账户范围内, 避免不同 paper 账户之间的 source key 互相污染.
        statement = select(PaperExecutionModel).where(
            PaperExecutionModel.account_id == account_id,
            PaperExecutionModel.idempotency_key == idempotency_key,
        )
        return self._session.scalar(statement)

    def get_fx_rate_snapshot(
        self,
        from_currency: str,
        to_currency: str,
        captured_at: datetime,
    ) -> FxRateSnapshotModel | None:
        statement = select(FxRateSnapshotModel).where(
            FxRateSnapshotModel.from_currency == from_currency,
            FxRateSnapshotModel.to_currency == to_currency,
            FxRateSnapshotModel.captured_at == captured_at,
        )
        return self._session.scalar(statement)

    def list_cash_balances(self, account_id: str) -> Sequence[CashBalanceModel]:
        return self._session.scalars(
            select(CashBalanceModel)
            .where(CashBalanceModel.account_id == account_id)
            .order_by(CashBalanceModel.currency.asc())
        ).all()

    def list_positions(self, account_id: str) -> Sequence[PositionModel]:
        return self._session.scalars(
            select(PositionModel)
            .where(PositionModel.account_id == account_id)
            .order_by(PositionModel.instrument.asc(), PositionModel.market.asc(), PositionModel.currency.asc())
        ).all()

    def list_orders(self, account_id: str) -> Sequence[PaperOrderModel]:
        return self._session.scalars(
            select(PaperOrderModel)
            .where(PaperOrderModel.account_id == account_id)
            .order_by(PaperOrderModel.requested_at.asc(), PaperOrderModel.id.asc())
        ).all()

    def list_executions(self, account_id: str) -> Sequence[PaperExecutionModel]:
        return self._session.scalars(
            select(PaperExecutionModel)
            .where(PaperExecutionModel.account_id == account_id)
            .order_by(PaperExecutionModel.executed_at.asc(), PaperExecutionModel.id.asc())
        ).all()

    def list_ledger_entries(self, account_id: str, *, limit: int | None = None) -> Sequence[WalletLedgerEntryModel]:
        statement: Select[tuple[WalletLedgerEntryModel]] = (
            select(WalletLedgerEntryModel)
            .where(WalletLedgerEntryModel.account_id == account_id)
            .order_by(WalletLedgerEntryModel.occurred_at.asc(), WalletLedgerEntryModel.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return self._session.scalars(statement).all()

    def list_fx_rate_snapshots(self) -> Sequence[FxRateSnapshotModel]:
        return self._session.scalars(
            select(FxRateSnapshotModel).order_by(FxRateSnapshotModel.captured_at.asc(), FxRateSnapshotModel.id.asc())
        ).all()
