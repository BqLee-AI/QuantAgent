from __future__ import annotations

import unittest

from alpaca_paper_adapter_spike import (
    AlpacaPaperClient,
    build_order_smoke_request,
    fetch_read_only_snapshot,
    get_order_smoke_skip_reason,
    get_read_only_smoke_skip_reason,
    load_alpaca_paper_config,
)


class AlpacaPaperAdapterSmokeTestCase(unittest.TestCase):
    def test_read_only_smoke_skip_path_without_credentials(self) -> None:
        config = load_alpaca_paper_config({})
        reason = get_read_only_smoke_skip_reason(config)

        self.assertIsNotNone(reason)
        self.assertIn("QUANTAGENT_ALPACA_PAPER_SMOKE", reason or "")

    def test_order_smoke_skip_path_without_order_flag(self) -> None:
        config = load_alpaca_paper_config(
            {
                "QUANTAGENT_ALPACA_PAPER_SMOKE": "1",
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            }
        )
        reason = get_order_smoke_skip_reason(config, build_order_smoke_request())

        self.assertIsNotNone(reason)
        self.assertIn("QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE", reason or "")

    def test_read_only_smoke_against_paper_api(self) -> None:
        config = load_alpaca_paper_config(__import__("os").environ)
        reason = get_read_only_smoke_skip_reason(config)
        if reason is not None:
            self.skipTest(reason)

        snapshot = fetch_read_only_snapshot(AlpacaPaperClient(config))

        self.assertTrue(snapshot.fixture.account.account_id)
        self.assertTrue(snapshot.fixture.cash_balances)
        self.assertGreaterEqual(len(snapshot.orders), 0)

    def test_order_submit_smoke_against_paper_api(self) -> None:
        config = load_alpaca_paper_config(__import__("os").environ)
        request = build_order_smoke_request()
        reason = get_order_smoke_skip_reason(config, request)
        if reason is not None:
            self.skipTest(reason)

        client = AlpacaPaperClient(config)
        submitted = client.submit_order(request)
        client_order_id = submitted["client_order_id"]
        queried = client.get_order_by_client_order_id(client_order_id)

        self.assertEqual(queried["client_order_id"], client_order_id)
        self.assertTrue(queried["status"])


if __name__ == "__main__":
    unittest.main()
