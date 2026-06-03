from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from quantagent.core.events import (
    DEFAULT_EVENT_SCHEMA_VERSION,
    EventBusCodec,
    EventBusError,
    EventBusSettings,
    EventEnvelope,
    EventTopicPolicy,
    error_to_summary,
)
from quantagent.core.config.settings import Settings


class EventBusContractTestCase(unittest.TestCase):
    def test_envelope_requires_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be a non-empty string"):
            EventEnvelope(
                id="",
                topic="source.event.captured",
                producer="source-ingestion",
                created_at="2026-05-30T00:00:00Z",
            )

    def test_envelope_payload_is_frozen_and_json_safe(self) -> None:
        envelope = EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={"items": [{"symbol": "AAPL"}]},
            producer="source-ingestion",
            created_at="2026-05-30T00:00:00Z",
            headers={"trace_id": "trace-1"},
        )

        self.assertEqual(envelope.schema_version, DEFAULT_EVENT_SCHEMA_VERSION)
        self.assertEqual(envelope.payload["items"][0]["symbol"], "AAPL")
        with self.assertRaises(TypeError):
            envelope.payload["new"] = "value"  # type: ignore[index]

    def test_topic_policy_accepts_default_topics(self) -> None:
        policy = EventTopicPolicy()
        self.assertEqual(policy.validate("runtime.failed"), "runtime.failed")

    def test_topic_policy_rejects_unknown_topic(self) -> None:
        policy = EventTopicPolicy()
        with self.assertRaises(EventBusError) as raised:
            policy.validate("runtime.unknown")
        self.assertEqual(raised.exception.code, "EVENT_TOPIC_UNREGISTERED")

    def test_codec_round_trip_preserves_envelope(self) -> None:
        codec = EventBusCodec()
        envelope = EventEnvelope(
            id="evt-1",
            topic="event.routed",
            payload={"event_id": "e-1", "symbols": ["AAPL", "MSFT"]},
            producer="worker-router",
            created_at="2026-05-30T00:00:00Z",
            correlation_id="corr-1",
            causation_id="cause-1",
            headers={"request_id": "req-1"},
            retry_count=1,
        )

        decoded = codec.decode(codec.encode(envelope))
        self.assertEqual(decoded.id, envelope.id)
        self.assertEqual(decoded.topic, envelope.topic)
        self.assertEqual(tuple(decoded.payload["symbols"]), ("AAPL", "MSFT"))
        self.assertEqual(decoded.retry_count, 1)

    def test_event_routed_accepts_event_intake_decision_payload(self) -> None:
        envelope = EventEnvelope(
            id="evt-routed-1",
            topic="event.routed",
            payload={
                "schema_version": "event_intake_decision.v1",
                "trace": {
                    "message_id": "evt-analysis-1",
                    "source_message_id": "evt-source-1",
                    "binding_id": "binding-semi",
                    "owner_id": "semiconductor",
                },
                "decision": "route",
                "discard_reason": "not_discarded",
                "routing": {
                    "target_industries": ("semiconductor",),
                    "target_topics": ("memory",),
                    "requires_deep_analysis": True,
                    "requires_human_review": False,
                },
                "quality": {
                    "content_completeness": "full",
                    "enrichment_status": "succeeded",
                    "confidence": 0.88,
                },
                "audit": {"reason_summary": "direct HBM relevance"},
            },
            producer="ai-event-intake",
            created_at="2026-06-02T00:00:00Z",
            correlation_id="corr-1",
            causation_id="evt-analysis-1",
            headers={
                "schema_version": "event_intake_decision.v1",
                "decision": "route",
                "binding_id": "binding-semi",
                "owner_id": "semiconductor",
            },
        )

        decoded = EventBusCodec().decode(EventBusCodec().encode(envelope))

        self.assertEqual(decoded.topic, "event.routed")
        self.assertEqual(decoded.payload["schema_version"], "event_intake_decision.v1")
        self.assertEqual(decoded.payload["decision"], "route")
        self.assertEqual(decoded.headers["schema_version"], "event_intake_decision.v1")

    def test_codec_rejects_invalid_message(self) -> None:
        codec = EventBusCodec()
        with self.assertRaises(EventBusError) as raised:
            codec.decode(b'{"topic":"missing required fields"}')
        self.assertEqual(raised.exception.code, "EVENT_CODEC_FIELD_MISSING")

    def test_error_summary_redacts_sensitive_details(self) -> None:
        summary = error_to_summary(
            EventBusError(
                code="EVENT_PUBLISH_FAILED",
                message="token=abc123 leaked from /Users/private/app.env",
                stage="publish",
                details={"api_key": "secret", "safe": "visible"},
            )
        )

        self.assertNotIn("abc123", summary["message"])
        self.assertEqual(summary["details"]["api_key"], "[REDACTED]")
        self.assertEqual(summary["details"]["safe"], "visible")

    def test_event_bus_settings_defaults_to_kafka(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            app_settings = Settings(_env_file=None)
            event_settings = EventBusSettings.from_settings(app_settings)

            self.assertEqual(event_settings.backend, "kafka")
            self.assertEqual(event_settings.kafka_bootstrap_servers, "127.0.0.1:19092")

    def test_event_bus_settings_require_bootstrap_servers_for_kafka(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            app_settings = Settings(_env_file=None, EVENT_BUS_BACKEND="kafka", EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=None)

            with self.assertRaises(EventBusError) as raised:
                EventBusSettings.from_settings(app_settings)
            self.assertEqual(raised.exception.code, "EVENT_BUS_KAFKA_CONFIG_MISSING")

    def test_event_bus_settings_reject_whitespace_bootstrap_servers(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            app_settings = Settings(
                _env_file=None,
                EVENT_BUS_BACKEND="kafka",
                EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS="   ",
            )

            with self.assertRaises(EventBusError) as raised:
                EventBusSettings.from_settings(app_settings)
            self.assertEqual(raised.exception.code, "EVENT_BUS_KAFKA_CONFIG_MISSING")


if __name__ == "__main__":
    unittest.main()
