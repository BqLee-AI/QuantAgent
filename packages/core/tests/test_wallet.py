from __future__ import annotations

import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db import Base
from quantagent.core.wallet import (
    AccountMode,
    CreateTradingAccountCommand,
    OrderSide,
    OrderType,
    RecordCashAdjustmentCommand,
    RecordFxRateSnapshotCommand,
    RecordPaperExecutionCommand,
    RecordPaperOrderCommand,
    WalletLedgerEntryType,
    WalletService,
)


class WalletServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.service = WalletService(self.session_factory)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_create_paper_account_and_manual_adjustment_update_cash_and_ledger(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_paper_usd",
                name="Paper USD",
                base_currency="USD",
            )
        )
        entry = self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="10000.00",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="seed-capital",
                note="initial funding",
            )
        )

        balances = self.service.list_cash_balances(account.account_id)
        ledger_entries = self.service.list_ledger_entries(account.account_id)
        facts = self.service.get_wallet_facts(account.account_id)

        self.assertEqual(account.mode, AccountMode.PAPER)
        self.assertEqual(entry.entry_type, WalletLedgerEntryType.DEPOSIT)
        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0].currency, "USD")
        self.assertEqual(balances[0].total, Decimal("10000.00000000"))
        self.assertEqual(balances[0].available, Decimal("10000.00000000"))
        self.assertEqual(len(ledger_entries), 1)
        self.assertEqual(ledger_entries[0].metadata["note"], "initial funding")
        self.assertEqual(facts.available_cash["USD"], Decimal("10000.00000000"))
        self.assertTrue(facts.paper_execution_allowed)

    def test_paper_execution_is_idempotent_and_updates_order_cash_position_and_ledger(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_exec",
                name="Exec",
                base_currency="USD",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="10000",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="capital",
            )
        )
        order = self.service.record_paper_order(
            RecordPaperOrderCommand(
                account_id=account.account_id,
                order_id="ord_aapl_1",
                client_order_id="client_ord_aapl_1",
                instrument="AAPL",
                market="NASDAQ",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity="10",
                currency="USD",
            )
        )

        first = self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                execution_id="exe_aapl_1",
                order_id=order.order_id,
                idempotency_key="sim:exec:aapl:1",
                instrument="AAPL",
                market="NASDAQ",
                side=OrderSide.BUY,
                quantity="10",
                price="150",
                currency="USD",
                fee_amount="1.25",
            )
        )
        second = self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                execution_id="exe_aapl_duplicated",
                order_id=order.order_id,
                idempotency_key="sim:exec:aapl:1",
                instrument="AAPL",
                market="NASDAQ",
                side=OrderSide.BUY,
                quantity="10",
                price="150",
                currency="USD",
                fee_amount="1.25",
            )
        )

        balances = self.service.list_cash_balances(account.account_id)
        positions = self.service.list_positions(account.account_id)
        ledger_entries = self.service.list_ledger_entries(account.account_id)
        orders = self.service.list_paper_orders(account.account_id)
        executions = self.service.list_paper_executions(account.account_id)
        facts = self.service.get_wallet_facts(account.account_id)

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(len(executions), 1)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].status.value, "filled")
        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0].total, Decimal("8498.75000000"))
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].quantity, Decimal("10.00000000"))
        self.assertEqual(positions[0].sellable_quantity, Decimal("10.00000000"))
        self.assertEqual(positions[0].average_cost, Decimal("150.12500000"))
        self.assertEqual(len(ledger_entries), 3)
        self.assertEqual({entry.entry_type.value for entry in ledger_entries}, {"deposit", "trade", "fee"})
        trade_entry = next(entry for entry in ledger_entries if entry.entry_type.value == "trade")
        fee_entry = next(entry for entry in ledger_entries if entry.entry_type.value == "fee")
        self.assertEqual(trade_entry.amount, Decimal("-1500.00000000"))
        self.assertEqual(fee_entry.amount, Decimal("-1.25000000"))
        self.assertEqual(facts.position_quantities["AAPL:NASDAQ:USD"], Decimal("10.00000000"))
        self.assertEqual(facts.sellable_positions["AAPL:NASDAQ:USD"], Decimal("10.00000000"))

    def test_sell_execution_reduces_position_and_increases_cash(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_sell",
                name="Sell Flow",
                base_currency="USD",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="5000",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="capital",
            )
        )
        self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                idempotency_key="buy-msft-1",
                instrument="MSFT",
                market="NASDAQ",
                side=OrderSide.BUY,
                quantity="5",
                price="100",
                currency="USD",
            )
        )
        self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                idempotency_key="sell-msft-1",
                instrument="MSFT",
                market="NASDAQ",
                side=OrderSide.SELL,
                quantity="2",
                price="120",
                currency="USD",
                fee_amount="1",
            )
        )

        balances = self.service.list_cash_balances(account.account_id)
        positions = self.service.list_positions(account.account_id)
        facts = self.service.get_wallet_facts(account.account_id)

        self.assertEqual(balances[0].total, Decimal("4739.00000000"))
        self.assertEqual(positions[0].quantity, Decimal("3.00000000"))
        self.assertEqual(positions[0].sellable_quantity, Decimal("3.00000000"))
        self.assertEqual(facts.single_instrument_exposure["MSFT:NASDAQ:USD"], Decimal("360.00000000"))
        self.assertEqual(positions[0].updated_at, self.service.list_paper_executions(account.account_id)[1].executed_at)

    def test_fx_rate_snapshots_preserve_original_currency_records(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_fx",
                name="FX",
                base_currency="USD",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="1000",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="usd-capital",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="HKD",
                amount="7800",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="hkd-capital",
            )
        )
        fx_snapshot = self.service.record_fx_rate_snapshot(
            RecordFxRateSnapshotCommand(
                from_currency="HKD",
                to_currency="USD",
                rate="0.12820513",
                source="manual:test",
            )
        )

        balances = self.service.list_cash_balances(account.account_id)
        fx_snapshots = self.service.list_fx_rate_snapshots()
        currencies = {balance.currency for balance in balances}

        self.assertEqual(currencies, {"USD", "HKD"})
        self.assertEqual(fx_snapshot.from_currency, "HKD")
        self.assertEqual(fx_snapshot.rate, Decimal("0.12820513"))
        self.assertEqual(len(fx_snapshots), 1)

    def test_cash_adjustment_rejects_wrong_sign_for_deposit_and_withdrawal(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_sign_guard",
                name="Sign Guard",
                base_currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "Deposit amount must be positive"):
            self.service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=account.account_id,
                    currency="USD",
                    amount="-10",
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                )
            )

        with self.assertRaisesRegex(ValueError, "Withdrawal amount must be negative"):
            self.service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=account.account_id,
                    currency="USD",
                    amount="10",
                    entry_type=WalletLedgerEntryType.WITHDRAWAL,
                )
            )

    def test_execution_must_match_referenced_order(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_order_guard",
                name="Order Guard",
                base_currency="USD",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="1000",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="capital",
            )
        )
        order = self.service.record_paper_order(
            RecordPaperOrderCommand(
                account_id=account.account_id,
                order_id="ord_limit_1",
                client_order_id="client_limit_1",
                instrument="NVDA",
                market="NASDAQ",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity="2",
                limit_price="100",
                currency="usd",
            )
        )

        with self.assertRaisesRegex(ValueError, "does not match the referenced paper order"):
            self.service.ingest_paper_execution(
                RecordPaperExecutionCommand(
                    account_id=account.account_id,
                    order_id=order.order_id,
                    idempotency_key="bad-order-side",
                    instrument="NVDA",
                    market="NASDAQ",
                    side=OrderSide.SELL,
                    quantity="2",
                    price="100",
                    currency="USD",
                )
            )

        with self.assertRaisesRegex(ValueError, "must not exceed the order limit_price"):
            self.service.ingest_paper_execution(
                RecordPaperExecutionCommand(
                    account_id=account.account_id,
                    order_id=order.order_id,
                    idempotency_key="bad-order-price",
                    instrument="NVDA",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity="2",
                    price="101",
                    currency="USD",
                )
            )

    def test_currency_is_normalized_to_uppercase(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_currency_norm",
                name="Currency Norm",
                base_currency="usd",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="usd",
                amount="100",
                entry_type=WalletLedgerEntryType.DEPOSIT,
            )
        )

        balances = self.service.list_cash_balances(account.account_id)

        self.assertEqual(account.base_currency, "USD")
        self.assertEqual(balances[0].currency, "USD")

    def test_non_paper_account_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "only supports paper accounts"):
            self.service.create_trading_account(
                CreateTradingAccountCommand(
                    account_id="acct_live",
                    name="Live",
                    base_currency="USD",
                    mode="live",  # type: ignore[arg-type]
                )
            )

    def test_sell_more_than_current_position_is_rejected_without_partial_state(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_guard",
                name="Guard",
                base_currency="USD",
            )
        )
        self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="1000",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="capital",
            )
        )

        with self.assertRaisesRegex(ValueError, "exceeds current sellable position"):
            self.service.ingest_paper_execution(
                RecordPaperExecutionCommand(
                    account_id=account.account_id,
                    idempotency_key="bad-sell",
                    instrument="TSLA",
                    market="NASDAQ",
                    side=OrderSide.SELL,
                    quantity="1",
                    price="200",
                    currency="USD",
                )
            )

        self.assertEqual(len(self.service.list_paper_executions(account.account_id)), 0)
        self.assertEqual(len(self.service.list_ledger_entries(account.account_id)), 1)


if __name__ == "__main__":
    unittest.main()
