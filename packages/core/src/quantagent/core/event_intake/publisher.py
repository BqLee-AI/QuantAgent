from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from quantagent.core.event_intake.runner import EventIntakeRunResult
from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.ports import EventBusPublisher
from quantagent.plugin_sdk.io import freeze_json_mapping


class EventIntakeEventIdFactory(Protocol):
    def __call__(self) -> str: ...


@dataclass
class EventIntakeRoutedPublisher:
    publisher: EventBusPublisher
    id_factory: EventIntakeEventIdFactory | None = None

    async def publish(self, result: EventIntakeRunResult) -> EventEnvelope:
        context = result.context
        decision_payload = dict(result.decision.to_mapping())
        trace = dict(result.decision.trace)
        envelope = EventEnvelope(
            id=(self.id_factory or _default_event_id_factory)(),
            topic="event.routed",
            payload=freeze_json_mapping(
                {
                    **decision_payload,
                    "source": {
                        "plugin_id": context.source.plugin_id,
                        "binding_id": context.source.binding_id,
                        "url": context.source.url,
                        "title": context.source.title,
                        "published_at": context.source.published_at,
                        "source_name": context.source.source_name,
                        "enrichment_status": context.source.enrichment_status.value,
                        "degraded_reason": context.source.degraded_reason,
                    },
                    "article": {
                        # 路由事件只暴露内容状态和长度，不把正文/excerpt 再次广播出去。
                        "content_completeness": context.article.content_completeness.value,
                        "body_content_available": context.article.body_content_available,
                        "content_length_chars": context.article.content_length_chars,
                        "excerpt_start": context.article.excerpt_start,
                        "excerpt_end": context.article.excerpt_end,
                    },
                    "audit": {
                        **dict(decision_payload["audit"]),
                        "provider_invocation_count": result.provider_invocation_count,
                        "invocation_metadata": dict(result.invocation_metadata),
                    },
                },
                stage="publish",
            ),
            producer="ai-event-intake",
            created_at=datetime.now(UTC).isoformat(),
            correlation_id=_optional_string(trace.get("correlation_id")) or _optional_string(trace.get("request_id")),
            causation_id=_optional_string(trace.get("message_id")),
            headers=freeze_json_mapping(
                {
                    "schema_version": result.decision.schema_version,
                    "decision": result.decision.decision.value,
                    "discard_reason": result.decision.discard_reason.value,
                    "binding_id": context.trace.binding_id,
                    "owner_type": context.trace.owner_type,
                    "owner_id": context.trace.owner_id,
                    "request_id": context.trace.request_id,
                    "source_message_id": context.trace.source_message_id,
                    "analysis_request_id": context.trace.analysis_request_id,
                    "item_index": context.trace.item_index,
                    "content_completeness": context.article.content_completeness.value,
                    "enrichment_status": context.source.enrichment_status.value,
                },
                stage="publish",
            ),
            retry_count=0,
        )
        return await self.publisher.publish(envelope)


def _default_event_id_factory() -> str:
    return f"evt_{uuid4().hex}"


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
