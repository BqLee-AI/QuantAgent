from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "discord_interaction_webhook_plugin.py"
    module_name = "discord_interaction_webhook_plugin"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "interaction_command.json"


class DiscordInteractionWebhookPluginTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = MODULE.DiscordInteractionWebhookSourcePlugin()
        self.config = {
            "signing_secret_ref": "discord.interactions.signing",
            "timestamp_tolerance_seconds": 300,
            "guild_allowlist": ["guild-1"],
            "channel_allowlist": ["channel-1"],
        }
        self.secrets = {
            "discord.interactions.signing": "integration-secret",
        }
        self.body = FIXTURE_PATH.read_bytes()
        self.timestamp = 1_700_000_000
        self.headers = {
            "X-Signature-Timestamp": str(self.timestamp),
            "X-QuantAgent-Signature": MODULE.sign_request_body(
                self.body,
                self.timestamp,
                self.secrets["discord.interactions.signing"],
            ),
        }

    def test_receive_request_returns_dto_for_valid_signed_interaction(self) -> None:
        result = self.plugin.receive_request(
            self.config,
            self.headers,
            self.body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "RECEIVED")
        self.assertIsNotNone(result.dto)
        assert result.dto is not None
        self.assertEqual(result.dto.message_id, "1234567890")
        self.assertEqual(result.dto.source_id, "discord.interaction:app-1")
        self.assertEqual(result.dto.text, "hello from discord")
        self.assertEqual(result.dto.guild_id, "guild-1")
        self.assertEqual(result.dto.channel_id, "channel-1")

    def test_receive_request_rejects_invalid_signature(self) -> None:
        result = self.plugin.receive_request(
            self.config,
            {**self.headers, "X-QuantAgent-Signature": "bad-signature"},
            self.body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "SIGNATURE_INVALID")

    def test_receive_request_rejects_missing_config(self) -> None:
        result = self.plugin.receive_request(
            {},
            self.headers,
            self.body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "MISSING_CONFIG")

    def test_receive_request_rejects_invalid_json_payload(self) -> None:
        invalid_body = b"{"
        headers = {
            "X-Signature-Timestamp": str(self.timestamp),
            "X-QuantAgent-Signature": MODULE.sign_request_body(
                invalid_body,
                self.timestamp,
                self.secrets["discord.interactions.signing"],
            ),
        }

        result = self.plugin.receive_request(
            self.config,
            headers,
            invalid_body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PAYLOAD_INVALID")

    def test_receive_request_rejects_unsupported_payload_type(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["type"] = 5
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": str(self.timestamp),
            "X-QuantAgent-Signature": MODULE.sign_request_body(
                custom_body,
                self.timestamp,
                self.secrets["discord.interactions.signing"],
            ),
        }

        result = self.plugin.receive_request(
            self.config,
            headers,
            custom_body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNSUPPORTED_EVENT_TYPE")

    def test_receive_request_rejects_allowlist_mismatch(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["guild_id"] = "guild-2"
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": str(self.timestamp),
            "X-QuantAgent-Signature": MODULE.sign_request_body(
                custom_body,
                self.timestamp,
                self.secrets["discord.interactions.signing"],
            ),
        }

        result = self.plugin.receive_request(
            self.config,
            headers,
            custom_body,
            secrets=self.secrets,
            now=self.timestamp,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "GUILD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
