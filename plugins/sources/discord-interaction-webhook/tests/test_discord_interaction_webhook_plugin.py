from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey


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
        self.signing_key = SigningKey.generate()
        self.public_key = self.signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        self.config = {
            "public_key": self.public_key,
            "response_text": "Interaction received.",
            "guild_allowlist": ["guild-1"],
            "channel_allowlist": ["channel-1"],
        }
        self.body = FIXTURE_PATH.read_bytes()
        self.timestamp = str(int(time.time()))
        self.headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(self.body),
        }

    def _sign(self, body: bytes) -> str:
        signed = self.signing_key.sign(self.timestamp.encode("utf-8") + body)
        return signed.signature.hex()

    def test_receive_request_returns_pong_for_valid_ping(self) -> None:
        body = json.dumps({"type": 1}).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(body),
        }

        result = self.plugin.receive_request(self.config, headers, body)

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "PING")
        self.assertEqual(result.response, {"type": 1})

    def test_receive_request_returns_dto_and_response_for_valid_signed_interaction(self) -> None:
        result = self.plugin.receive_request(self.config, self.headers, self.body)

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "RECEIVED")
        self.assertIsNotNone(result.dto)
        self.assertEqual(
            result.response,
            {
                "type": 4,
                "data": {
                    "content": "Interaction received.",
                    "flags": 64,
                },
            },
        )
        assert result.dto is not None
        self.assertEqual(result.dto.interaction_id, "1234567890")
        self.assertEqual(result.dto.source_id, "discord.interaction:app-1")
        self.assertEqual(result.dto.text, "hello from discord")
        self.assertEqual(result.dto.guild_id, "guild-1")
        self.assertEqual(result.dto.channel_id, "channel-1")
        self.assertEqual(result.dto.author_id, "user-1")
        self.assertEqual(
            result.dto.payload_summary,
            {
                "type": 2,
                "command_name": "notify",
                "option_names": ["text"],
            },
        )

    def test_receive_request_rejects_invalid_signature(self) -> None:
        result = self.plugin.receive_request(
            self.config,
            {**self.headers, "X-Signature-Ed25519": "00"},
            self.body,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "SIGNATURE_INVALID")

    def test_receive_request_rejects_invalid_timestamp_header(self) -> None:
        result = self.plugin.receive_request(
            self.config,
            {**self.headers, "X-Signature-Timestamp": "not-a-timestamp"},
            self.body,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "TIMESTAMP_INVALID")

    def test_receive_request_rejects_stale_timestamp(self) -> None:
        stale_timestamp = "1"
        headers = {
            "X-Signature-Timestamp": stale_timestamp,
            "X-Signature-Ed25519": self.signing_key.sign(stale_timestamp.encode("utf-8") + self.body).signature.hex(),
        }
        result = self.plugin.receive_request(
            self.config,
            headers,
            self.body,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "TIMESTAMP_INVALID")

    def test_receive_request_rejects_missing_public_key_config(self) -> None:
        result = self.plugin.receive_request({}, self.headers, self.body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "MISSING_CONFIG")

    def test_receive_request_rejects_missing_signature_headers(self) -> None:
        result = self.plugin.receive_request(self.config, {}, self.body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "SIGNATURE_MISSING")

    def test_receive_request_rejects_invalid_json_payload(self) -> None:
        invalid_body = b"{"
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(invalid_body),
        }

        result = self.plugin.receive_request(self.config, headers, invalid_body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PAYLOAD_INVALID")

    def test_receive_request_rejects_unsupported_payload_type(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["type"] = 3
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(custom_body),
        }

        result = self.plugin.receive_request(self.config, headers, custom_body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNSUPPORTED_EVENT_TYPE")

    def test_receive_request_rejects_allowlist_mismatch(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["guild_id"] = "guild-2"
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(custom_body),
        }

        result = self.plugin.receive_request(self.config, headers, custom_body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "GUILD_NOT_ALLOWED")

    def test_receive_request_rejects_channel_allowlist_mismatch(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["channel_id"] = "channel-2"
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(custom_body),
        }

        result = self.plugin.receive_request(self.config, headers, custom_body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CHANNEL_NOT_ALLOWED")

    def test_receive_request_rejects_payload_without_supported_text_option(self) -> None:
        payload = json.loads(self.body.decode("utf-8"))
        payload["data"]["options"] = [{"name": "ignored", "value": "hello from discord"}]
        custom_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(custom_body),
        }

        result = self.plugin.receive_request(self.config, headers, custom_body)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PAYLOAD_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
