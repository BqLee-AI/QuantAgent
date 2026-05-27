from __future__ import annotations

import socket
import unittest
from urllib import error as urllib_error
from unittest.mock import patch

from . import alpaca_wallet_api_e2e_support
from .alpaca_wallet_api_e2e_support import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaPaperRequestError,
    AlpacaHttpResponse,
    UrllibAlpacaTransport,
    fetch_read_only_snapshot,
    map_alpaca_order,
)


class FakeTransport:
    def __init__(self, responses: list[AlpacaHttpResponse]) -> None:
        self._responses = list(responses)

    def request(self, *_args, **_kwargs) -> AlpacaHttpResponse:
        if not self._responses:
            raise AssertionError("Expected fake transport response.")
        return self._responses.pop(0)


class StubSnapshotClient:
    def get_account(self):
        return {
            "id": "acct_redacted",
            "account_number": "acct_redacted",
            "currency": "USD",
            "cash": "1000.00",
            "buying_power": "2000.00",
            "status": "ACTIVE",
        }

    def get_positions(self):
        return [
            {
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "currency": "USD",
                "qty": "2.5",
                "avg_entry_price": "150.125",
            }
        ]

    def get_orders(self):
        return [
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
        ]


class AlpacaWalletApiE2ESupportTestCase(unittest.TestCase):
    def test_get_positions_requires_list_of_mappings(self) -> None:
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url="https://paper-api.alpaca.markets",
                api_key_id="key",
                api_secret_key="secret",
                smoke_enabled=True,
            ),
            transport=FakeTransport([AlpacaHttpResponse(status_code=200, payload="not-a-list")]),
        )

        with self.assertRaisesRegex(ValueError, "positions response must be a list of mappings"):
            client.get_positions()

    def test_get_orders_requires_list_of_mappings(self) -> None:
        client = AlpacaPaperClient(
            AlpacaPaperConfig(
                base_url="https://paper-api.alpaca.markets",
                api_key_id="key",
                api_secret_key="secret",
                smoke_enabled=True,
            ),
            transport=FakeTransport([AlpacaHttpResponse(status_code=200, payload=["not-a-mapping"])]),
        )

        with self.assertRaisesRegex(ValueError, "orders response must be a list of mappings"):
            client.get_orders()

    def test_map_alpaca_order_rejects_missing_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "Alpaca timestamp is required"):
            map_alpaca_order(
                {
                    "id": "order_redacted_1",
                    "client_order_id": "client_redacted_1",
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "side": "buy",
                    "type": "market",
                    "qty": "2.5",
                    "currency": "USD",
                }
            )

    def test_fetch_read_only_snapshot_maps_position_contexts(self) -> None:
        snapshot = fetch_read_only_snapshot(StubSnapshotClient())

        self.assertEqual(len(snapshot.fixture.position_contexts), 1)
        position = snapshot.fixture.position_contexts[0]
        self.assertEqual(position.instrument, "AAPL")
        self.assertEqual(position.market, "NASDAQ")
        self.assertEqual(str(position.quantity), "2.5")

    def test_transport_maps_urlerror_timeout_to_timeout_category(self) -> None:
        transport = UrllibAlpacaTransport()
        request_timeout = urllib_error.URLError(socket.timeout("timed out"))

        with patch.object(alpaca_wallet_api_e2e_support, "urlopen", side_effect=request_timeout):
            with self.assertRaises(AlpacaPaperRequestError) as context:
                transport.request(
                    "GET",
                    "https://paper-api.alpaca.markets/v2/account",
                    headers={},
                    timeout_seconds=1.0,
                )

        self.assertEqual(context.exception.broker_error.category, "timeout")


if __name__ == "__main__":
    unittest.main()
