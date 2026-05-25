from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "discord_webhook_plugin.py"
    module_name = "discord_webhook_plugin"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class DiscordWebhookPluginTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = MODULE.DiscordWebhookNotificationPlugin()
        self.config = {
            "webhook_secret_ref": "discord.webhooks.primary",
            "timeout_seconds": 5,
        }
        self.secrets = {
            "discord.webhooks.primary": "https://discord.example.invalid/api/webhooks/test",
        }

    def test_send_text_builds_minimal_payload_and_reports_success(self) -> None:
        captured_request = {}

        def fake_transport(request):
            captured_request["url"] = request.url
            captured_request["body"] = request.body
            captured_request["timeout"] = request.timeout_seconds
            return MODULE.DiscordWebhookResponse(status_code=204)

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "SENT")
        self.assertEqual(captured_request["url"], self.secrets["discord.webhooks.primary"])
        self.assertEqual(json.loads(captured_request["body"]), {"content": "hello discord"})
        self.assertEqual(captured_request["timeout"], 5.0)

    def test_send_text_returns_missing_config_for_absent_secret_reference(self) -> None:
        result = self.plugin.send_text({}, "hello discord", secrets=self.secrets)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "MISSING_CONFIG")

    def test_send_text_returns_upstream_error_without_leaking_webhook(self) -> None:
        def fake_transport(_request):
            return MODULE.DiscordWebhookResponse(status_code=502, body="discord upstream unavailable")

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UPSTREAM_ERROR")
        self.assertEqual(result.http_status, 502)
        self.assertNotIn("discord.example.invalid", result.message)
        self.assertEqual(result.response_excerpt, "discord upstream unavailable")

    def test_send_text_returns_timeout_as_retryable_failure(self) -> None:
        def fake_transport(_request):
            raise TimeoutError("boom")

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "NETWORK_TIMEOUT")
        self.assertTrue(result.retryable)

    def test_send_text_returns_network_error_for_transport_failure(self) -> None:
        def fake_transport(_request):
            raise OSError("network down")

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "NETWORK_ERROR")
        self.assertTrue(result.retryable)


if __name__ == "__main__":
    unittest.main()
