from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from quantagent.core.wallet import OrderSide, OrderType

from alpaca_paper_adapter_spike import (
    ALPACA_PAPER_BASE_URL,
    APCA_API_KEY_ID_ENV,
    APCA_API_SECRET_KEY_ENV,
    QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV,
    QUANTAGENT_ALPACA_PAPER_SMOKE_ENV,
    AlpacaHttpResponse,
    AlpacaOrderSmokeRequest,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaPaperRequestError,
    build_order_smoke_request,
    fetch_read_only_snapshot,
    get_order_smoke_skip_reason,
    get_read_only_smoke_skip_reason,
    load_alpaca_paper_config,
    map_alpaca_account,
    map_alpaca_error,
    map_alpaca_fill_activity,
    map_alpaca_order,
    map_alpaca_position,
    sanitize_for_logs,
    validate_paper_base_url,
)
from wallet_broker_simulator_harness import BrokerSimulatorHarness


class MockTransport:
    def __init__(self, responses=None, exceptions=None) -> None:
        self.responses = list(responses or [])
        self.exceptions = list(exceptions or [])
        self.requests: list[dict[str, object]] = []

    def request(self, method, url, *, headers, params=None, json_body=None, timeout_seconds):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "params": dict(params or {}),
                "json_body": dict(json_body or {}),
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.exceptions:
            raise self.exceptions.pop(0)
        if not self.responses:
            raise AssertionError("No mock response configured.")
        return self.responses.pop(0)


class AlpacaPaperAdapterSpikeTestCase(unittest.TestCase):
    def test_load_config_defaults_and_redaction(self) -> None:
        config = load_alpaca_paper_config(
            {
                APCA_API_KEY_ID_ENV: "paper-key",
                APCA_API_SECRET_KEY_ENV: "paper-secret",
            }
        )

        self.assertEqual(config.base_url, ALPACA_PAPER_BASE_URL)
        self.assertFalse(config.smoke_enabled)
        self.assertFalse(config.order_smoke_enabled)
        self.assertEqual(config.timeout_seconds, 10.0)
        self.assertEqual(config.redacted()["api_key_id"], "<redacted>")
        self.assertEqual(config.redacted()["api_secret_key"], "<redacted>")
        self.assertEqual(config.redacted()["symbol_whitelist"], ("AAPL", "MSFT", "SPY"))
        self.assertEqual(config.redacted()["max_notional_usd"], "5")
        self.assertEqual(config.redacted()["max_quantity"], "1")

    def test_load_config_reads_process_environment_when_env_is_none(self) -> None:
        with patch.dict(
            os.environ,
            {
                APCA_API_KEY_ID_ENV: "paper-key-from-env",
                APCA_API_SECRET_KEY_ENV: "paper-secret-from-env",
                QUANTAGENT_ALPACA_PAPER_SMOKE_ENV: "1",
                QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV: "1",
            },
            clear=False,
        ):
            config = load_alpaca_paper_config()

        self.assertEqual(config.api_key_id, "paper-key-from-env")
        self.assertEqual(config.api_secret_key, "paper-secret-from-env")
        self.assertTrue(config.smoke_enabled)
        self.assertTrue(config.order_smoke_enabled)

    def test_validate_paper_base_url_rejects_non_paper_targets(self) -> None:
        self.assertEqual(validate_paper_base_url(ALPACA_PAPER_BASE_URL), ALPACA_PAPER_BASE_URL)

        with self.assertRaisesRegex(ValueError, "https"):
            validate_paper_base_url("http://paper-api.alpaca.markets")
        with self.assertRaisesRegex(ValueError, "paper-api.alpaca.markets"):
            validate_paper_base_url("https://api.alpaca.markets")
        with self.assertRaisesRegex(ValueError, "path"):
            validate_paper_base_url("https://paper-api.alpaca.markets/v2")

    def test_smoke_skip_reason_requires_flag_credentials_and_valid_url(self) -> None:
        disabled = load_alpaca_paper_config({})
        self.assertIn(QUANTAGENT_ALPACA_PAPER_SMOKE_ENV, get_read_only_smoke_skip_reason(disabled) or "")

        missing_credentials = load_alpaca_paper_config({QUANTAGENT_ALPACA_PAPER_SMOKE_ENV: "1"})
        self.assertEqual(get_read_only_smoke_skip_reason(missing_credentials), "Alpaca paper credentials are missing.")

        invalid_url = load_alpaca_paper_config(
            {
                QUANTAGENT_ALPACA_PAPER_SMOKE_ENV: "1",
                APCA_API_KEY_ID_ENV: "paper-key",
                APCA_API_SECRET_KEY_ENV: "paper-secret",
                "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
            }
        )
        self.assertIn("paper-api.alpaca.markets", get_read_only_smoke_skip_reason(invalid_url) or "")

    def test_order_smoke_skip_reason_enforces_order_flag_whitelist_and_limits(self) -> None:
        config = load_alpaca_paper_config(
            {
                QUANTAGENT_ALPACA_PAPER_SMOKE_ENV: "1",
                APCA_API_KEY_ID_ENV: "paper-key",
                APCA_API_SECRET_KEY_ENV: "paper-secret",
            }
        )

        self.assertIn(
            QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV,
            get_order_smoke_skip_reason(config, build_order_smoke_request(symbol="SPY")) or "",
        )

        enabled = load_alpaca_paper_config(
            {
                QUANTAGENT_ALPACA_PAPER_SMOKE_ENV: "1",
                QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE_ENV: "1",
                APCA_API_KEY_ID_ENV: "paper-key",
                APCA_API_SECRET_KEY_ENV: "paper-secret",
            }
        )
        self.assertIn(
            "allowlisted",
            get_order_smoke_skip_reason(enabled, build_order_smoke_request(symbol="QQQ")) or "",
        )
        self.assertIn(
            "exceeds 5",
            get_order_smoke_skip_reason(
                enabled,
                build_order_smoke_request(symbol="SPY", notional_usd=Decimal("6")),
            )
            or "",
        )
        self.assertIn(
            "exceeds 1",
            get_order_smoke_skip_reason(
                enabled,
                build_order_smoke_request(symbol="SPY", notional_usd=None, quantity=Decimal("2")),
            )
            or "",
        )
        self.assertIn(
            "greater than 0",
            get_order_smoke_skip_reason(
                enabled,
                build_order_smoke_request(symbol="SPY", notional_usd=Decimal("0")),
            )
            or "",
        )
        self.assertIn(
            "greater than 0",
            get_order_smoke_skip_reason(
                enabled,
                build_order_smoke_request(symbol="SPY", notional_usd=None, quantity=Decimal("-1")),
            )
            or "",
        )

    def test_account_mapping_keeps_cash_and_buying_power_separate(self) -> None:
        mapped = map_alpaca_account(
            {
                "id": "acct_redacted",
                "account_number": "acct_redacted",
                "currency": "usd",
                "cash": "1000.25",
                "buying_power": "4000.50",
                "status": "ACTIVE",
            }
        )

        self.assertEqual(mapped.fixture.account.account_id, "acct_redacted")
        self.assertEqual(mapped.fixture.cash_balances[0].currency, "USD")
        self.assertEqual(mapped.fixture.cash_balances[0].total, Decimal("1000.25"))
        self.assertEqual(mapped.buying_power, Decimal("4000.50"))
        self.assertEqual(mapped.broker_account_context["buying_power"], "4000.50")

    def test_position_and_order_mapping_use_broker_shaped_contract(self) -> None:
        position = map_alpaca_position(
            {
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "currency": "usd",
                "qty": "2.5",
                "avg_entry_price": "150.125",
            }
        )
        order = map_alpaca_order(
            {
                "id": "order_redacted_1",
                "client_order_id": "client_redacted_1",
                "symbol": "AAPL",
                "side": "buy",
                "type": "market",
                "qty": "2.5",
                "currency": "USD",
                "submitted_at": "2026-05-26T06:00:00Z",
            }
        )

        self.assertEqual(position.instrument, "AAPL")
        self.assertEqual(position.market, "NASDAQ")
        self.assertEqual(position.quantity, Decimal("2.5"))
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.order_type, OrderType.MARKET)
        self.assertEqual(order.broker_order_id, "order_redacted_1")
        self.assertEqual(order.client_order_id, "client_redacted_1")
        self.assertEqual(order.requested_at, datetime(2026, 5, 26, 6, 0, tzinfo=timezone.utc))

    def test_client_requires_list_of_mappings_for_positions_orders_and_activities(self) -> None:
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url=ALPACA_PAPER_BASE_URL,
                api_key_id="paper-key",
                api_secret_key="paper-secret",
                smoke_enabled=True,
                order_smoke_enabled=False,
            ),
            transport=MockTransport(
                responses=[
                    AlpacaHttpResponse(200, "not-a-list"),
                    AlpacaHttpResponse(200, ["not-a-mapping"]),
                    AlpacaHttpResponse(200, "still-not-a-list"),
                ]
            ),
        )

        with self.assertRaisesRegex(ValueError, "positions response must be a list of mappings"):
            client.get_positions()
        with self.assertRaisesRegex(ValueError, "orders response must be a list of mappings"):
            client.get_orders()
        with self.assertRaisesRegex(ValueError, "activities response must be a list of mappings"):
            client.get_fill_activities()

    def test_fill_activity_uses_account_scoped_source_key_and_wallet_idempotency(self) -> None:
        snapshot = fetch_read_only_snapshot(
            AlpacaPaperClient(
                AlpacaPaperConfig(
                    base_url=ALPACA_PAPER_BASE_URL,
                    api_key_id="paper-key",
                    api_secret_key="paper-secret",
                    smoke_enabled=True,
                    order_smoke_enabled=False,
                ),
                transport=MockTransport(
                    responses=[
                        AlpacaHttpResponse(
                            200,
                            {
                                "id": "acct_redacted",
                                "account_number": "acct_redacted",
                                "currency": "USD",
                                "cash": "1000",
                                "buying_power": "3000",
                            },
                        ),
                        AlpacaHttpResponse(
                            200,
                            [
                                {
                                    "symbol": "AAPL",
                                    "exchange": "NASDAQ",
                                    "currency": "USD",
                                    "qty": "1",
                                    "avg_entry_price": "100",
                                }
                            ],
                        ),
                        AlpacaHttpResponse(
                            200,
                            [
                                {
                                    "id": "order_redacted_1",
                                    "client_order_id": "client_redacted_1",
                                    "symbol": "AAPL",
                                    "side": "buy",
                                    "type": "market",
                                    "qty": "1",
                                    "currency": "USD",
                                }
                            ],
                        ),
                    ]
                ),
            )
        )
        execution = map_alpaca_fill_activity(
            {
                "activity_type": "FILL",
                "id": "activity_redacted_1",
                "order_id": "order_redacted_1",
                "symbol": "AAPL",
                "side": "buy",
                "qty": "1",
                "price": "100",
                "transaction_time": "2026-05-26T06:01:00Z",
            },
            account_id=snapshot.fixture.account.account_id,
        )

        with BrokerSimulatorHarness(snapshot.fixture) as harness:
            order = harness.place_order(snapshot.orders[0])
            first = harness.ingest_execution(
                execution.__class__(
                    source_key=execution.source_key,
                    instrument=execution.instrument,
                    market=execution.market,
                    side=execution.side,
                    quantity=execution.quantity,
                    price=execution.price,
                    currency=execution.currency,
                    external_execution_id=execution.external_execution_id,
                    broker_order_id=order.order_id,
                    fee_amount=execution.fee_amount,
                    fee_currency=execution.fee_currency,
                    executed_at=execution.executed_at,
                )
            )
            second = harness.ingest_execution(
                execution.__class__(
                    source_key=execution.source_key,
                    instrument=execution.instrument,
                    market=execution.market,
                    side=execution.side,
                    quantity=execution.quantity,
                    price=execution.price,
                    currency=execution.currency,
                    external_execution_id="activity_redacted_1_duplicate",
                    broker_order_id=order.order_id,
                    fee_amount=execution.fee_amount,
                    fee_currency=execution.fee_currency,
                    executed_at=execution.executed_at,
                )
            )

            balances = harness.list_cash_balances()
            positions = harness.list_positions()
            executions = harness.list_paper_executions()

        self.assertEqual(execution.source_key, "acct_redacted:alpaca:activity:activity_redacted_1")
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(len(executions), 1)
        self.assertEqual(balances[0].total, Decimal("900.00000000"))
        self.assertEqual(positions[0].quantity, Decimal("1.00000000"))

    def test_client_uses_controlled_headers_and_read_only_paths(self) -> None:
        transport = MockTransport(
            responses=[
                AlpacaHttpResponse(200, {"id": "acct_redacted", "account_number": "acct_redacted", "cash": "1", "currency": "USD"}),
                AlpacaHttpResponse(200, []),
                AlpacaHttpResponse(200, []),
                AlpacaHttpResponse(200, []),
            ]
        )
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url=ALPACA_PAPER_BASE_URL,
                api_key_id="paper-key",
                api_secret_key="paper-secret",
                smoke_enabled=True,
                order_smoke_enabled=False,
            ),
            transport=transport,
        )

        client.get_account()
        client.get_positions()
        client.get_orders()
        client.get_fill_activities()

        self.assertEqual(transport.requests[0]["url"], "https://paper-api.alpaca.markets/v2/account")
        self.assertEqual(transport.requests[1]["url"], "https://paper-api.alpaca.markets/v2/positions")
        self.assertEqual(transport.requests[2]["url"], "https://paper-api.alpaca.markets/v2/orders")
        self.assertEqual(transport.requests[3]["url"], "https://paper-api.alpaca.markets/v2/account/activities/FILL")
        self.assertEqual(transport.requests[0]["headers"]["APCA-API-KEY-ID"], "paper-key")
        self.assertEqual(transport.requests[0]["headers"]["APCA-API-SECRET-KEY"], "paper-secret")

    def test_broker_error_mapping_is_redacted_and_categorized(self) -> None:
        auth_error = map_alpaca_error(
            status_code=401,
            payload={
                "message": "secret should never be logged",
                "account_id": "acct_redacted",
                "order_id": "order_redacted_1",
                "raw_body": '{"secret":"value"}',
            },
        )
        invalid_symbol = map_alpaca_error(status_code=422, payload={"message": "invalid symbol"})
        insufficient = map_alpaca_error(status_code=403, payload={"message": "insufficient buying power"})
        timeout = map_alpaca_error(exception=TimeoutError("timed out"))

        self.assertEqual(auth_error.category, "authentication_failed")
        self.assertEqual(auth_error.details["payload"]["account_id"], "<redacted>")
        self.assertEqual(auth_error.details["payload"]["order_id"], "<redacted>")
        self.assertEqual(auth_error.details["payload"]["raw_body"], "<redacted-response-body>")
        self.assertEqual(auth_error.details["payload"]["message"], "<redacted-message>")
        self.assertEqual(invalid_symbol.category, "invalid_symbol")
        self.assertEqual(insufficient.category, "insufficient_buying_power")
        self.assertEqual(timeout.category, "timeout")

    def test_client_raises_redacted_request_error(self) -> None:
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url=ALPACA_PAPER_BASE_URL,
                api_key_id="paper-key",
                api_secret_key="paper-secret",
                smoke_enabled=True,
                order_smoke_enabled=False,
            ),
            transport=MockTransport(
                responses=[
                    AlpacaHttpResponse(
                        401,
                        {"message": "bad auth", "account_id": "acct_redacted", "raw_body": "secret"},
                    )
                ]
            ),
        )

        with self.assertRaises(AlpacaPaperRequestError) as ctx:
            client.get_account()

        self.assertEqual(ctx.exception.broker_error.category, "authentication_failed")
        self.assertEqual(ctx.exception.broker_error.details["payload"]["account_id"], "<redacted>")

    def test_order_submit_builds_client_order_id_and_query_path(self) -> None:
        transport = MockTransport(
            responses=[
                AlpacaHttpResponse(200, {"id": "order_redacted_1", "client_order_id": "client_redacted_1", "status": "new"}),
                AlpacaHttpResponse(200, {"id": "order_redacted_1", "client_order_id": "client_redacted_1", "status": "accepted"}),
            ]
        )
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url=ALPACA_PAPER_BASE_URL,
                api_key_id="paper-key",
                api_secret_key="paper-secret",
                smoke_enabled=True,
                order_smoke_enabled=True,
            ),
            transport=transport,
        )

        submitted = client.submit_order(build_order_smoke_request(symbol="SPY", notional_usd=Decimal("1")))
        queried = client.get_order_by_client_order_id("client_redacted_1")

        self.assertEqual(submitted["id"], "order_redacted_1")
        self.assertEqual(queried["status"], "accepted")
        self.assertEqual(transport.requests[0]["url"], "https://paper-api.alpaca.markets/v2/orders")
        self.assertEqual(transport.requests[1]["url"], "https://paper-api.alpaca.markets/v2/orders:by_client_order_id")
        self.assertEqual(transport.requests[1]["params"]["client_order_id"], "client_redacted_1")
        self.assertEqual(transport.requests[0]["json_body"]["symbol"], "SPY")
        self.assertEqual(transport.requests[0]["json_body"]["notional"], "1")
        self.assertIn("client_order_id", transport.requests[0]["json_body"])

    def test_sanitize_for_logs_redacts_identifiers_and_raw_body(self) -> None:
        sanitized = sanitize_for_logs(
            {
                "account_id": "acct_redacted",
                "nested": [{"order_id": "order_redacted_1"}],
                "raw_body": '{"secret":"value"}',
                "message": "provider text",
            }
        )

        self.assertEqual(sanitized["account_id"], "<redacted>")
        self.assertEqual(sanitized["nested"][0]["order_id"], "<redacted>")
        self.assertEqual(sanitized["raw_body"], "<redacted-response-body>")
        self.assertEqual(sanitized["message"], "<redacted-message>")


if __name__ == "__main__":
    unittest.main()
