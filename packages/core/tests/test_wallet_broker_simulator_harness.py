from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from quantagent.core.wallet import OrderSide, OrderType

from wallet_broker_simulator_harness import (
    BrokerSimulatorAccount,
    BrokerSimulatorCashBalance,
    BrokerSimulatorErrorInput,
    BrokerSimulatorExecutionInput,
    BrokerSimulatorFixture,
    BrokerSimulatorHarness,
    BrokerSimulatorOrderInput,
    BrokerSimulatorPositionContext,
)


class BrokerSimulatorHarnessTestCase(unittest.TestCase):
    def test_full_fill_contract_keeps_cash_position_execution_and_ledger_consistent(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_full_fill", name="Broker Full Fill"),
            cash_balances=(BrokerSimulatorCashBalance(currency="USD", total="10000"),),
            position_contexts=(
                BrokerSimulatorPositionContext(
                    instrument="AAPL",
                    market="NASDAQ",
                    currency="USD",
                    quantity="10",
                    average_cost="150.25000000",
                ),
            ),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            order = harness.place_order(
                BrokerSimulatorOrderInput(
                    broker_order_id="broker-ord-aapl-1",
                    client_order_id="client-aapl-1",
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="10",
                    currency="USD",
                )
            )
            result = harness.ingest_execution(
                BrokerSimulatorExecutionInput(
                    external_execution_id="broker-exec-aapl-1",
                    source_key="acct_broker_full_fill:exec:aapl:1",
                    broker_order_id=order.order_id,
                    instrument="AAPL",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity="10",
                    price="150.125",
                    currency="USD",
                    fee_amount="1.25",
                    executed_at=datetime(2026, 5, 26, 2, 0, tzinfo=timezone.utc),
                )
            )

            balances = harness.list_cash_balances()
            positions = harness.list_positions()
            ledger_entries = harness.list_ledger_entries()
            executions = harness.list_paper_executions()
            facts = harness.get_wallet_facts()
            harness.assert_position_contexts_match(fixture.position_contexts)

        self.assertTrue(result.created)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0].idempotency_key, "acct_broker_full_fill:exec:aapl:1")
        self.assertEqual(balances[0].currency, "USD")
        self.assertEqual(balances[0].total, Decimal("8497.50000000"))
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].quantity, Decimal("10.00000000"))
        self.assertEqual(positions[0].sellable_quantity, Decimal("10.00000000"))
        self.assertEqual(positions[0].average_cost, Decimal("150.25000000"))
        self.assertEqual(len(ledger_entries), 3)
        self.assertEqual({entry.entry_type.value for entry in ledger_entries}, {"deposit", "trade", "fee"})
        execution_entries = [entry for entry in ledger_entries if entry.entry_type.value in {"trade", "fee"}]
        self.assertEqual({entry.source_ref for entry in execution_entries}, {"acct_broker_full_fill:exec:aapl:1"})
        self.assertEqual(facts.position_quantities["AAPL:NASDAQ:USD"], Decimal("10.00000000"))
        self.assertEqual(
            Decimal(str(fixture.position_contexts[0].average_cost)),
            positions[0].average_cost,
        )

    def test_duplicate_execution_reuses_account_scoped_source_key_without_double_booking(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_duplicate", name="Broker Duplicate"),
            cash_balances=(BrokerSimulatorCashBalance(currency="USD", total="10000"),),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            order = harness.place_order(
                BrokerSimulatorOrderInput(
                    broker_order_id="broker-ord-msft-1",
                    client_order_id="client-msft-1",
                    instrument="MSFT",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="5",
                    currency="USD",
                )
            )
            first = harness.ingest_execution(
                BrokerSimulatorExecutionInput(
                    external_execution_id="broker-exec-msft-1",
                    source_key="acct_broker_duplicate:exec:msft:1",
                    broker_order_id=order.order_id,
                    instrument="MSFT",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity="5",
                    price="100",
                    currency="USD",
                    fee_amount="1.25",
                )
            )
            second = harness.ingest_execution(
                BrokerSimulatorExecutionInput(
                    external_execution_id="broker-exec-msft-duplicate",
                    source_key="acct_broker_duplicate:exec:msft:1",
                    broker_order_id=order.order_id,
                    instrument="MSFT",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    quantity="5",
                    price="100",
                    currency="USD",
                    fee_amount="1.25",
                )
            )

            balances = harness.list_cash_balances()
            positions = harness.list_positions()
            ledger_entries = harness.list_ledger_entries()
            executions = harness.list_paper_executions()

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.execution.execution_id, second.execution.execution_id)
        self.assertEqual(len(executions), 1)
        self.assertEqual(balances[0].total, Decimal("9498.75000000"))
        self.assertEqual(positions[0].quantity, Decimal("5.00000000"))
        self.assertEqual(len(ledger_entries), 3)

    def test_broker_rejection_shape_is_a_noop_for_wallet_ingestion(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_reject", name="Broker Reject"),
            cash_balances=(BrokerSimulatorCashBalance(currency="USD", total="1000"),),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            rejection = harness.report_broker_error(
                BrokerSimulatorErrorInput(
                    code="BROKER_ORDER_REJECTED",
                    message="broker simulator rejected the paper order",
                    broker_status="rejected",
                    related_order_id="broker-ord-rejected-1",
                    related_source_key="acct_broker_reject:exec:1",
                )
            )

            balances = harness.list_cash_balances()
            positions = harness.list_positions()
            ledger_entries = harness.list_ledger_entries()
            executions = harness.list_paper_executions()

        self.assertFalse(rejection.ingested)
        self.assertEqual(rejection.code, "BROKER_ORDER_REJECTED")
        self.assertEqual(len(executions), 0)
        self.assertEqual(len(positions), 0)
        self.assertEqual(balances[0].total, Decimal("1000.00000000"))
        self.assertEqual(len(ledger_entries), 1)

    def test_insufficient_cash_error_does_not_leave_partial_wallet_state(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_insufficient_cash", name="Broker Insufficient Cash"),
            cash_balances=(BrokerSimulatorCashBalance(currency="USD", total="100"),),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            order = harness.place_order(
                BrokerSimulatorOrderInput(
                    broker_order_id="broker-ord-nvda-1",
                    client_order_id="client-nvda-1",
                    instrument="NVDA",
                    market="NASDAQ",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="2",
                    currency="USD",
                )
            )

            with self.assertRaisesRegex(ValueError, "Cash balance cannot become negative"):
                harness.ingest_execution(
                    BrokerSimulatorExecutionInput(
                        external_execution_id="broker-exec-nvda-1",
                        source_key="acct_broker_insufficient_cash:exec:nvda:1",
                        broker_order_id=order.order_id,
                        instrument="NVDA",
                        market="NASDAQ",
                        side=OrderSide.BUY,
                        quantity="2",
                        price="100",
                        currency="USD",
                    )
                )

            balances = harness.list_cash_balances()
            positions = harness.list_positions()
            ledger_entries = harness.list_ledger_entries()
            executions = harness.list_paper_executions()
            orders = harness.list_paper_orders()

        self.assertEqual(len(executions), 0)
        self.assertEqual(len(positions), 0)
        self.assertEqual(len(ledger_entries), 1)
        self.assertEqual(balances[0].total, Decimal("100.00000000"))
        self.assertEqual(orders[0].status.value, "open")

    def test_fee_and_multi_currency_fields_preserve_decimal_semantics(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_fx", name="Broker FX", base_currency="USD"),
            cash_balances=(
                BrokerSimulatorCashBalance(currency="HKD", total="10000"),
                BrokerSimulatorCashBalance(currency="USD", total="1000"),
            ),
            position_contexts=(
                BrokerSimulatorPositionContext(
                    instrument="0700",
                    market="HKEX",
                    currency="HKD",
                    quantity="100",
                    average_cost="50.12500000",
                ),
            ),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            order = harness.place_order(
                BrokerSimulatorOrderInput(
                    broker_order_id="broker-ord-0700-1",
                    client_order_id="client-0700-1",
                    instrument="0700",
                    market="HKEX",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity="100",
                    currency="HKD",
                )
            )
            result = harness.ingest_execution(
                BrokerSimulatorExecutionInput(
                    external_execution_id="broker-exec-0700-1",
                    source_key="acct_broker_fx:exec:0700:1",
                    broker_order_id=order.order_id,
                    instrument="0700",
                    market="HKEX",
                    side=OrderSide.BUY,
                    quantity="100",
                    price="50.125",
                    currency="HKD",
                    fee_amount="1.25",
                    fee_currency="USD",
                    executed_at=datetime(2026, 5, 26, 3, 0, tzinfo=timezone.utc),
                )
            )

            balances = {balance.currency: balance for balance in harness.list_cash_balances()}
            positions = harness.list_positions()
            ledger_entries = harness.list_ledger_entries()
            harness.assert_position_contexts_match(fixture.position_contexts)

        self.assertTrue(result.created)
        self.assertEqual(balances["HKD"].total, Decimal("4987.50000000"))
        self.assertEqual(balances["USD"].total, Decimal("998.75000000"))
        self.assertEqual(positions[0].quantity, Decimal("100.00000000"))
        self.assertEqual(positions[0].average_cost, Decimal("50.12500000"))
        self.assertEqual(
            {(entry.entry_type.value, entry.currency, entry.amount) for entry in ledger_entries},
            {
                ("deposit", "HKD", Decimal("10000.00000000")),
                ("deposit", "USD", Decimal("1000.00000000")),
                ("trade", "HKD", Decimal("-5012.50000000")),
                ("fee", "USD", Decimal("-1.25000000")),
            },
        )

    def test_partial_fill_extension_is_explicitly_deferred(self) -> None:
        fixture = BrokerSimulatorFixture(
            account=BrokerSimulatorAccount(account_id="acct_broker_partial_fill", name="Broker Partial Fill"),
            cash_balances=(BrokerSimulatorCashBalance(currency="USD", total="1000"),),
        )

        with BrokerSimulatorHarness(fixture) as harness:
            with self.assertRaisesRegex(NotImplementedError, "Partial fill is deferred in broker simulator harness V1"):
                harness.ingest_partial_fill(
                    BrokerSimulatorExecutionInput(
                        external_execution_id="broker-exec-tsla-1",
                        source_key="acct_broker_partial_fill:exec:tsla:1",
                        instrument="TSLA",
                        market="NASDAQ",
                        side=OrderSide.BUY,
                        quantity="5",
                        price="100",
                        currency="USD",
                    ),
                    filled_quantity="2",
                )


if __name__ == "__main__":
    unittest.main()
