from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
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
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
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
        self.assertTrue(ledger_entries[0].source_ref.startswith("seed-capital"))

    def test_blank_account_id_falls_back_to_generated_value(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="   ",
                name="Generated Account",
                base_currency="USD",
            )
        )

        self.assertTrue(account.account_id.startswith("acct_"))

    def test_manual_adjustment_fallback_source_ref_uses_entry_type_value(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_manual_ref",
                name="Manual Ref",
                base_currency="USD",
            )
        )

        entry = self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="100",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref=None,
            )
        )

        self.assertTrue(entry.source_ref.startswith("manual:deposit:"))

    def test_blank_manual_source_ref_falls_back_to_generated_value(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_blank_manual_ref",
                name="Blank Manual Ref",
                base_currency="USD",
            )
        )

        entry = self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="100",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                source_ref="   ",
            )
        )

        self.assertTrue(entry.source_ref.startswith("manual:deposit:"))

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
        buy_time = datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)
        sell_time = buy_time + timedelta(minutes=1)
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
                executed_at=buy_time,
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
                executed_at=sell_time,
            )
        )

        balances = self.service.list_cash_balances(account.account_id)
        positions = self.service.list_positions(account.account_id)
        facts = self.service.get_wallet_facts(account.account_id)
        executions = self.service.list_paper_executions(account.account_id)

        self.assertEqual(balances[0].total, Decimal("4739.00000000"))
        self.assertEqual(positions[0].quantity, Decimal("3.00000000"))
        self.assertEqual(positions[0].sellable_quantity, Decimal("3.00000000"))
        self.assertEqual(facts.single_instrument_exposure["MSFT:NASDAQ:USD"], Decimal("360.00000000"))
        self.assertEqual(positions[0].updated_at, executions[1].executed_at)

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

    def test_invalid_decimal_string_is_rejected_with_clear_error(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_invalid_decimal",
                name="Invalid Decimal",
                base_currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "Invalid decimal value: 1,000"):
            self.service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=account.account_id,
                    currency="USD",
                    amount="1,000",
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                )
            )

    def test_cash_adjustment_uses_normalized_timestamp_for_snapshot(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_cash_time_norm",
                name="Cash Time Norm",
                base_currency="USD",
            )
        )
        occurred_at = datetime(2026, 5, 23, 20, 0, tzinfo=timezone(timedelta(hours=8)))

        entry = self.service.record_cash_adjustment(
            RecordCashAdjustmentCommand(
                account_id=account.account_id,
                currency="USD",
                amount="100",
                entry_type=WalletLedgerEntryType.DEPOSIT,
                occurred_at=occurred_at,
            )
        )
        balances = self.service.list_cash_balances(account.account_id)
        expected_utc = datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(entry.occurred_at.replace(tzinfo=timezone.utc), expected_utc)
        self.assertEqual(balances[0].updated_at.replace(tzinfo=timezone.utc), expected_utc)

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

    def test_order_type_price_constraints_are_enforced(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_order_type_guard",
                name="Order Type Guard",
                base_currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "LIMIT orders require a positive limit_price"):
            self.service.record_paper_order(
                RecordPaperOrderCommand(
                    account_id=account.account_id,
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity="1",
                    currency="USD",
                )
            )

        with self.assertRaisesRegex(ValueError, "MARKET orders must not include limit_price"):
            self.service.record_paper_order(
                RecordPaperOrderCommand(
                    account_id=account.account_id,
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="1",
                    currency="USD",
                    limit_price="123",
                )
            )

    def test_duplicate_client_order_id_is_rejected_with_clear_error(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_duplicate_client_order",
                name="Duplicate Client Order",
                base_currency="USD",
            )
        )
        self.service.record_paper_order(
            RecordPaperOrderCommand(
                account_id=account.account_id,
                order_id="ord_dup_1",
                client_order_id="client_dup_1",
                instrument="AAPL",
                market="NASDAQ",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity="1",
                currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "Duplicate paper order client_order_id for account: client_dup_1"):
            self.service.record_paper_order(
                RecordPaperOrderCommand(
                    account_id=account.account_id,
                    order_id="ord_dup_2",
                    client_order_id="client_dup_1",
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="1",
                    currency="USD",
                )
            )

    def test_blank_order_id_and_client_order_id_fall_back_to_generated_values(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_blank_order_ids",
                name="Blank Order Ids",
                base_currency="USD",
            )
        )

        order = self.service.record_paper_order(
            RecordPaperOrderCommand(
                account_id=account.account_id,
                order_id="   ",
                client_order_id="   ",
                instrument="AAPL",
                market="NASDAQ",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity="1",
                currency="USD",
            )
        )

        self.assertTrue(order.order_id.startswith("ord_"))
        self.assertEqual(order.client_order_id, order.order_id)

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

    def test_execution_reuses_existing_record_after_idempotency_conflict(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_conflict",
                name="Conflict Guard",
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
        first = self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                execution_id="exe_conflict_1",
                idempotency_key="conflict-key",
                instrument="META",
                market="NASDAQ",
                side=OrderSide.BUY,
                quantity="1",
                price="100",
                currency="USD",
            )
        )
        second = self.service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id=account.account_id,
                execution_id="exe_conflict_2",
                idempotency_key="conflict-key",
                instrument="META",
                market="NASDAQ",
                side=OrderSide.BUY,
                quantity="1",
                price="100",
                currency="USD",
            )
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.execution.execution_id, second.execution.execution_id)

    def test_blank_execution_idempotency_key_is_rejected(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_blank_idempotency_key",
                name="Blank Idempotency Key",
                base_currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "Execution idempotency_key must not be empty"):
            self.service.ingest_paper_execution(
                RecordPaperExecutionCommand(
                    account_id=account.account_id,
                    idempotency_key="   ",
                    instrument="META",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity="1",
                    price="100",
                    currency="USD",
                )
            )

    def test_ledger_entries_limit_must_be_positive(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_ledger_limit",
                name="Ledger Limit",
                base_currency="USD",
            )
        )

        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            self.service.list_ledger_entries(account.account_id, limit=0)

        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            self.service.list_ledger_entries(account.account_id, limit=-1)

    def test_duplicate_fx_snapshot_is_rejected_with_clear_error(self) -> None:
        captured_at = datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)

        self.service.record_fx_rate_snapshot(
            RecordFxRateSnapshotCommand(
                from_currency="HKD",
                to_currency="USD",
                rate="0.12820513",
                source="manual:test",
                captured_at=captured_at,
            )
        )

        with self.assertRaisesRegex(ValueError, "FX snapshot already exists for HKD/USD at 2026-05-23T12:00:00\\+00:00"):
            self.service.record_fx_rate_snapshot(
                RecordFxRateSnapshotCommand(
                    from_currency="HKD",
                    to_currency="USD",
                    rate="0.12820513",
                    source="manual:test",
                    captured_at=captured_at,
                )
            )

    def test_blank_fx_snapshot_id_falls_back_to_generated_value(self) -> None:
        snapshot = self.service.record_fx_rate_snapshot(
            RecordFxRateSnapshotCommand(
                snapshot_id="   ",
                from_currency="HKD",
                to_currency="USD",
                rate="0.12820513",
                source="manual:test",
                captured_at=datetime(2026, 5, 23, 13, 0, tzinfo=timezone.utc),
            )
        )

        self.assertTrue(snapshot.snapshot_id.startswith("fx_"))

    def test_naive_timestamp_is_rejected_with_clear_error(self) -> None:
        account = self.service.create_trading_account(
            CreateTradingAccountCommand(
                account_id="acct_naive_time",
                name="Naive Time",
                base_currency="USD",
            )
        )
        naive_time = datetime(2026, 5, 23, 12, 0, 0)

        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=account.account_id,
                    currency="USD",
                    amount="100",
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                    occurred_at=naive_time,
                )
            )

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
