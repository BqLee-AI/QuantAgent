from __future__ import annotations

import importlib.util
import asyncio
import json
import logging
from pathlib import Path
import sys
import time
import unittest

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey
from quantagent.plugin_sdk import NotificationReceiveResult, PluginInvokeRequest, RuntimeContext


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "discord_plugin.py"
    module_name = "discord_plugin"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class DiscordPluginSendTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = MODULE.DiscordPlugin()
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
            "  hello discord  ",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "SENT")
        self.assertEqual(captured_request["url"], self.secrets["discord.webhooks.primary"])
        self.assertEqual(json.loads(captured_request["body"]), {"content": "hello discord"})
        self.assertEqual(captured_request["timeout"], 5.0)

    def test_send_text_returns_secret_not_resolved_when_secret_value_is_missing(self) -> None:
        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets={},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "SECRET_NOT_RESOLVED")
        self.assertEqual(result.webhook_secret_ref, "discord.webhooks.primary")

    def test_send_text_returns_missing_config_for_absent_secret_reference(self) -> None:
        result = self.plugin.send_text({}, "hello discord", secrets=self.secrets)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "MISSING_CONFIG")

    def test_send_text_rejects_blank_message_without_transport_call(self) -> None:
        transport_called = False

        def fake_transport(_request):
            nonlocal transport_called
            transport_called = True
            return MODULE.DiscordWebhookResponse(status_code=204)

        result = self.plugin.send_text(
            self.config,
            "   ",
            secrets=self.secrets,
            transport=fake_transport,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_MESSAGE")
        self.assertFalse(transport_called)

    def test_send_text_rejects_non_https_webhook_without_transport_call(self) -> None:
        transport_called = False

        def fake_transport(_request):
            nonlocal transport_called
            transport_called = True
            return MODULE.DiscordWebhookResponse(status_code=204)

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets={"discord.webhooks.primary": "http://discord.example.invalid/api/webhooks/test"},
            transport=fake_transport,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_WEBHOOK_URL")
        self.assertEqual(result.webhook_secret_ref, "discord.webhooks.primary")
        self.assertNotIn("discord.example.invalid", result.message)
        self.assertFalse(transport_called)

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

    def test_send_text_clamps_timeout_override_to_minimum_value(self) -> None:
        captured_request = {}

        def fake_transport(request):
            captured_request["timeout"] = request.timeout_seconds
            return MODULE.DiscordWebhookResponse(status_code=204)

        result = self.plugin.send_text(
            self.config,
            "hello discord",
            secrets=self.secrets,
            transport=fake_transport,
            timeout_seconds=0,
        )

        self.assertTrue(result.ok)
        self.assertEqual(captured_request["timeout"], 0.1)


class DiscordPluginReceiveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = MODULE.DiscordPlugin()
        self.signing_key = SigningKey.generate()
        self.public_key = self.signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        self.config = {
            "public_key": self.public_key,
            "response_text": "Interaction received.",
            "guild_allowlist": ["guild-1"],
            "channel_allowlist": ["channel-1"],
        }
        self.body = json.dumps(
            {
                "id": "1234567890",
                "application_id": "app-1",
                "type": 2,
                "guild_id": "guild-1",
                "channel_id": "channel-1",
                "member": {"user": {"id": "user-1"}},
                "data": {
                    "name": "notify",
                    "options": [{"name": "text", "type": 3, "value": "hello from discord"}],
                },
            }
        ).encode("utf-8")
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

        self.assertTrue(result.accepted)
        self.assertEqual(result.code, "PING")
        self.assertEqual(result.response, {"type": 1})

    def test_receive_request_returns_item_and_response_for_valid_signed_interaction(self) -> None:
        result = self.plugin.receive_request(self.config, self.headers, self.body)

        self.assertTrue(result.accepted)
        self.assertEqual(result.code, "RECEIVED")
        self.assertIsNotNone(result.item)
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
        assert result.item is not None
        self.assertEqual(result.item.interaction_id, "1234567890")
        self.assertEqual(result.item.source_id, "discord.interaction:app-1")
        self.assertEqual(result.item.text, "hello from discord")
        self.assertEqual(result.item.guild_id, "guild-1")
        self.assertEqual(result.item.channel_id, "channel-1")
        self.assertEqual(result.item.author_id, "user-1")
        self.assertEqual(
            result.item.payload_summary,
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

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "SIGNATURE_INVALID")

    def test_receive_request_rejects_invalid_timestamp_header(self) -> None:
        result = self.plugin.receive_request(
            self.config,
            {**self.headers, "X-Signature-Timestamp": "not-a-timestamp"},
            self.body,
        )

        self.assertFalse(result.accepted)
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

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "TIMESTAMP_INVALID")

    def test_receive_request_rejects_missing_public_key_config(self) -> None:
        result = self.plugin.receive_request({}, self.headers, self.body)

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "MISSING_CONFIG")

    def test_receive_request_rejects_missing_signature_headers(self) -> None:
        result = self.plugin.receive_request(self.config, {}, self.body)

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "SIGNATURE_MISSING")

    def test_receive_request_rejects_invalid_json_payload(self) -> None:
        invalid_body = b"{"
        headers = {
            "X-Signature-Timestamp": self.timestamp,
            "X-Signature-Ed25519": self._sign(invalid_body),
        }

        result = self.plugin.receive_request(self.config, headers, invalid_body)

        self.assertFalse(result.accepted)
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

        self.assertFalse(result.accepted)
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

        self.assertFalse(result.accepted)
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

        self.assertFalse(result.accepted)
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

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "PAYLOAD_UNSUPPORTED")


class DiscordPluginRuntimeContractTestCase(unittest.TestCase):
    def test_runtime_invoke_send_returns_notification_result_mapping(self) -> None:
        plugin = MODULE.DiscordPlugin()
        asyncio.run(
            plugin.load(
                RuntimeContext(
                    plugin_id="quantagent.official.notification.discord",
                    plugin_version="0.1.0",
                    request_id="req-runtime-send",
                    logger=logging.getLogger("test"),
                    config={
                        "webhook_secret_ref": "discord.webhooks.primary",
                        "__secrets__": {
                            "discord.webhooks.primary": "https://discord.example.invalid/api/webhooks/test"
                        },
                    },
                )
            )
        )

        captured = {}

        def fake_transport(request):
            captured["url"] = request.url
            return MODULE.DiscordWebhookResponse(status_code=204)

        original_transport = MODULE._default_transport
        MODULE._default_transport = fake_transport
        try:
            result = asyncio.run(
                plugin.invoke(
                    PluginInvokeRequest(
                        capability="notification.send",
                        request_id="req-runtime-send",
                        input={"channel": "discord", "text": "hello runtime"},
                    )
                )
            )
        finally:
            MODULE._default_transport = original_transport

        self.assertTrue(result.output["accepted"])
        self.assertEqual(result.output["metadata"]["code"], "SENT")
        self.assertEqual(captured["url"], "https://discord.example.invalid/api/webhooks/test")

    def test_runtime_invoke_receive_returns_structured_mapping(self) -> None:
        plugin = MODULE.DiscordPlugin()
        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
        body = json.dumps({"type": 1}).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

        asyncio.run(
            plugin.load(
                RuntimeContext(
                    plugin_id="quantagent.official.notification.discord",
                    plugin_version="0.1.0",
                    request_id="req-runtime-receive",
                    logger=logging.getLogger("test"),
                    config={"public_key": public_key},
                )
            )
        )

        result = asyncio.run(
            plugin.invoke(
                PluginInvokeRequest(
                    capability="notification.receive",
                    request_id="req-runtime-receive",
                    input={
                        "headers": {
                            "X-Signature-Timestamp": timestamp,
                            "X-Signature-Ed25519": signature,
                        },
                        "body": body.decode("utf-8"),
                    },
                )
            )
        )

        output = NotificationReceiveResult.from_mapping(result.output)
        self.assertTrue(output.accepted)
        self.assertEqual(output.code, "PING")
        self.assertEqual(output.response, {"type": 1})


if __name__ == "__main__":
    unittest.main()
