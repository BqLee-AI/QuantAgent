from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN

from fastapi.testclient import TestClient

from quantagent.api.config.settings import Settings
from quantagent.api.main import create_app
from quantagent.core.db import Base
from quantagent.core.wallet import (
    CreateTradingAccountCommand,
    OrderSide,
    OrderType,
    RecordCashAdjustmentCommand,
    RecordPaperExecutionCommand,
    RecordPaperOrderCommand,
    WalletLedgerEntryType,
    WalletService,
)
from .alpaca_wallet_api_e2e_support import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaReadOnlySnapshot,
    fetch_read_only_snapshot,
    get_wallet_api_external_smoke_skip_reason,
    load_alpaca_paper_config,
    map_alpaca_account,
    map_alpaca_fill_activity,
    map_alpaca_order,
)


class AlpacaWalletApiE2ETestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_file.close()
        self.addCleanup(lambda: os.unlink(self.database_file.name))

        self.settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{self.database_file.name}")
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        engine = self.client.app.state.db_engine
        if engine is None:
            raise AssertionError("Expected database engine to be initialized for wallet API E2E tests.")
        Base.metadata.create_all(engine)

        self._login()
        self.wallet_service = WalletService(self.client.app.state.db_session_factory)

    def test_offline_e2e_replays_redacted_alpaca_shape_through_wallet_api(self) -> None:
        account = map_alpaca_account(
            {
                "id": "acct_redacted",
                "account_number": "acct_redacted",
                "currency": "usd",
                "cash": "1000.25",
                "buying_power": "4000.50",
                "status": "ACTIVE",
            }
        )
        order = map_alpaca_order(
            {
                "id": "order_redacted_1",
                "client_order_id": "client_redacted_1",
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "side": "buy",
                "type": "market",
                "qty": "2.5",
                "currency": "USD",
                "submitted_at": "2026-05-26T06:00:00Z",
            }
        )
        execution = map_alpaca_fill_activity(
            {
                "id": "activity_redacted_1",
                "order_id": "order_redacted_1",
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "side": "buy",
                "qty": "2.5",
                "price": "150.125",
                "fee": "1.25",
                "currency": "USD",
                "transaction_time": "2026-05-26T06:01:00Z",
            },
            account_id="acct_redacted",
        )

        self.wallet_service.create_trading_account(
            CreateTradingAccountCommand(
                account_id=account.fixture.account.account_id,
                name="Alpaca Redacted Wallet",
                base_currency=account.fixture.account.base_currency,
            )
        )
        for balance in account.fixture.cash_balances:
            self.wallet_service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id="acct_redacted",
                    currency=balance.currency,
                    amount=balance.total,
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                    source_ref=balance.source_key or "alpaca:e2e:cash:seed",
                    occurred_at=datetime(2026, 5, 26, 5, 59, tzinfo=UTC),
                )
            )

        self.wallet_service.record_paper_order(
            RecordPaperOrderCommand(
                account_id="acct_redacted",
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
        first_ingest = self.wallet_service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id="acct_redacted",
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
        second_ingest = self.wallet_service.ingest_paper_execution(
            RecordPaperExecutionCommand(
                account_id="acct_redacted",
                execution_id="activity_redacted_duplicate",
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

        account_response = self.client.get("/api/v1/wallet/accounts/acct_redacted")
        cash_response = self.client.get("/api/v1/wallet/accounts/acct_redacted/cash-balances")
        positions_response = self.client.get("/api/v1/wallet/accounts/acct_redacted/positions")
        ledger_response = self.client.get("/api/v1/wallet/accounts/acct_redacted/ledger-entries")
        orders_response = self.client.get("/api/v1/wallet/accounts/acct_redacted/paper-orders")
        executions_response = self.client.get("/api/v1/wallet/accounts/acct_redacted/paper-executions")

        self.assertTrue(first_ingest.created)
        self.assertFalse(second_ingest.created)
        self.assertEqual(account_response.status_code, 200)
        self.assertEqual(cash_response.status_code, 200)
        self.assertEqual(positions_response.status_code, 200)
        self.assertEqual(ledger_response.status_code, 200)
        self.assertEqual(orders_response.status_code, 200)
        self.assertEqual(executions_response.status_code, 200)

        account_body = account_response.json()
        cash_body = cash_response.json()
        positions_body = positions_response.json()
        ledger_body = ledger_response.json()
        orders_body = orders_response.json()
        executions_body = executions_response.json()

        self.assertEqual(account_body["data"]["account_id"], "acct_redacted")
        self.assertEqual(account_body["data"]["mode"], "paper")
        self.assertEqual(cash_body["data"][0]["currency"], "USD")
        self.assertEqual(Decimal(cash_body["data"][0]["total"]), Decimal("623.68750000"))
        self.assertEqual(Decimal(cash_body["data"][0]["available"]), Decimal("623.68750000"))
        self.assertEqual(positions_body["data"][0]["instrument"], "AAPL")
        self.assertEqual(positions_body["data"][0]["market"], "NASDAQ")
        self.assertEqual(Decimal(positions_body["data"][0]["quantity"]), Decimal("2.50000000"))
        self.assertEqual(Decimal(positions_body["data"][0]["average_cost"]), Decimal("150.62500000"))
        self.assertEqual(Decimal(positions_body["data"][0]["market_value"]), Decimal("375.31250000"))
        self.assertEqual(Decimal(positions_body["data"][0]["unrealized_pnl"]), Decimal("-1.25000000"))
        self.assertEqual(ledger_body["data"][0]["entry_type"], "deposit")
        self.assertCountEqual(
            [entry["entry_type"] for entry in ledger_body["data"][1:]],
            ["trade", "fee"],
        )
        self.assertEqual(ledger_body["data"][1]["source_ref"], "acct_redacted:alpaca:activity:activity_redacted_1")
        self.assertEqual(ledger_body["data"][2]["source_ref"], "acct_redacted:alpaca:activity:activity_redacted_1")
        self.assertEqual(orders_body["data"][0]["order_id"], "order_redacted_1")
        self.assertEqual(orders_body["data"][0]["client_order_id"], "client_redacted_1")
        self.assertEqual(orders_body["data"][0]["status"], "filled")
        self.assertEqual(len(executions_body["data"]), 1)
        self.assertEqual(executions_body["data"][0]["execution_id"], "activity_redacted_1")
        self.assertEqual(
            executions_body["data"][0]["idempotency_key"],
            "acct_redacted:alpaca:activity:activity_redacted_1",
        )

        combined_text = str(
            [
                account_body,
                cash_body,
                positions_body,
                ledger_body,
                orders_body,
                executions_body,
            ]
        )
        self.assertNotIn("APCA_API_SECRET_KEY", combined_text)
        self.assertNotIn(self.settings.AUTH_SESSION_SECRET or "", combined_text)

    def test_external_smoke_reads_paper_snapshot_and_replays_redacted_wallet_state(self) -> None:
        config = load_alpaca_paper_config(os.environ)
        reason = self._get_external_smoke_skip_reason(config)
        if reason is not None:
            self.skipTest(reason)

        snapshot = fetch_read_only_snapshot(AlpacaPaperClient(config))
        expected = self._seed_redacted_wallet_from_snapshot(snapshot)

        account_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted")
        cash_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted/cash-balances")
        positions_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted/positions")
        ledger_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted/ledger-entries")
        orders_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted/paper-orders")
        executions_response = self.client.get("/api/v1/wallet/accounts/acct_alpaca_e2e_redacted/paper-executions")

        self.assertEqual(account_response.status_code, 200)
        self.assertEqual(cash_response.status_code, 200)
        self.assertEqual(positions_response.status_code, 200)
        self.assertEqual(ledger_response.status_code, 200)
        self.assertEqual(orders_response.status_code, 200)
        self.assertEqual(executions_response.status_code, 200)

        account_body = account_response.json()
        cash_body = cash_response.json()
        positions_body = positions_response.json()
        ledger_body = ledger_response.json()
        orders_body = orders_response.json()
        executions_body = executions_response.json()

        self.assertEqual(account_body["data"]["account_id"], "acct_alpaca_e2e_redacted")
        self.assertEqual(account_body["data"]["mode"], "paper")
        self.assertTrue(cash_body["data"])
        self.assertEqual(len(orders_body["data"]), expected["order_count"])
        self.assertEqual(len(executions_body["data"]), expected["execution_count"])
        self.assertEqual(len(positions_body["data"]), expected["position_count"])
        self.assertGreaterEqual(len(ledger_body["data"]), 1)

        combined_text = str(
            [
                account_body,
                cash_body,
                positions_body,
                ledger_body,
                orders_body,
                executions_body,
            ]
        )
        self.assertNotIn(config.api_key_id or "", combined_text)
        self.assertNotIn(config.api_secret_key or "", combined_text)
        if snapshot.fixture.account.account_id != "acct_alpaca_e2e_redacted":
            self.assertNotIn(snapshot.fixture.account.account_id, combined_text)
        for order in snapshot.orders:
            if order.broker_order_id is not None:
                self.assertNotIn(order.broker_order_id, combined_text)
            if order.client_order_id is not None:
                self.assertNotIn(order.client_order_id, combined_text)

    def _seed_redacted_wallet_from_snapshot(self, snapshot: AlpacaReadOnlySnapshot) -> dict[str, int]:
        account_id = "acct_alpaca_e2e_redacted"
        self.wallet_service.create_trading_account(
            CreateTradingAccountCommand(
                account_id=account_id,
                name="Alpaca Paper Redacted Wallet",
                base_currency=snapshot.fixture.account.base_currency,
            )
        )
        for index, balance in enumerate(snapshot.fixture.cash_balances, start=1):
            self.wallet_service.record_cash_adjustment(
                RecordCashAdjustmentCommand(
                    account_id=account_id,
                    currency=balance.currency,
                    amount=balance.total,
                    entry_type=WalletLedgerEntryType.DEPOSIT,
                    source_ref=f"alpaca:e2e:cash:redacted:{index}",
                )
            )

        order_count = 0
        for index, order in enumerate(snapshot.orders, start=1):
            self.wallet_service.record_paper_order(
                RecordPaperOrderCommand(
                    account_id=account_id,
                    order_id=f"order_redacted_{index}",
                    client_order_id=f"client_redacted_{index}",
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
            order_count += 1

        execution_count = 0
        position_count = 0
        if snapshot.fixture.position_contexts:
            position = snapshot.fixture.position_contexts[0]
            price = Decimal(str(position.average_cost or "1"))
            affordable_quantity = self._derive_affordable_quantity(
                snapshot=snapshot,
                currency=position.currency,
                price=price,
                desired_quantity=Decimal(str(position.quantity)),
            )
            if affordable_quantity > 0:
                order_count += 1
                execution_order = self.wallet_service.record_paper_order(
                    RecordPaperOrderCommand(
                        account_id=account_id,
                        order_id="order_redacted_exec_1",
                        client_order_id="client_redacted_exec_1",
                        instrument=position.instrument,
                        market=position.market,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=affordable_quantity,
                        currency=position.currency,
                        requested_at=datetime.now(UTC),
                    )
                )
                self.wallet_service.ingest_paper_execution(
                    RecordPaperExecutionCommand(
                        account_id=account_id,
                        execution_id="activity_redacted_1",
                        order_id=execution_order.order_id,
                        idempotency_key=f"{account_id}:alpaca:activity:activity_redacted_1",
                        instrument=position.instrument,
                        market=position.market,
                        side=OrderSide.BUY,
                        quantity=affordable_quantity,
                        price=price,
                        currency=position.currency,
                        fee_amount=Decimal("0"),
                        fee_currency=position.currency,
                        executed_at=datetime.now(UTC),
                    )
                )
                execution_count = 1
                position_count = 1

        return {
            "order_count": order_count,
            "execution_count": execution_count,
            "position_count": position_count,
        }

    def _derive_affordable_quantity(
        self,
        *,
        snapshot: AlpacaReadOnlySnapshot,
        currency: str,
        price: Decimal,
        desired_quantity: Decimal,
    ) -> Decimal:
        if price <= 0:
            return Decimal("0")
        matching_balance = next(
            (Decimal(str(item.total)) for item in snapshot.fixture.cash_balances if item.currency == currency),
            Decimal("0"),
        )
        if matching_balance <= 0:
            return Decimal("0")
        affordable_quantity = (matching_balance / price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        while affordable_quantity > 0 and (affordable_quantity * price) > matching_balance:
            affordable_quantity -= Decimal("0.00000001")
        return min(desired_quantity, affordable_quantity)

    def _get_external_smoke_skip_reason(self, config: AlpacaPaperConfig) -> str | None:
        return get_wallet_api_external_smoke_skip_reason(config, os.environ)

    def _login(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"password": self.settings.AUTH_ADMIN_PASSWORD})
        self.assertEqual(response.status_code, 200)

    def _settings(self, **overrides: object) -> Settings:
        baseline = {
            "_env_file": None,
            "APP_ENV": "development",
            "DATABASE_URL": None,
            "RUNTIME_DIR": "runtime",
            "LOG_LEVEL": "INFO",
            "API_V1_PREFIX": "/api/v1",
            "API_HOST": "127.0.0.1",
            "API_PORT": 8000,
            "AUTH_ENABLED": True,
            "AUTH_ADMIN_PASSWORD": "test-admin-password",
            "AUTH_SESSION_SECRET": "test-session-secret",
        }
        baseline.update(overrides)
        return Settings(**baseline)


if __name__ == "__main__":
    unittest.main()
