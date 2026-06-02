from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quantagent.core.event_intake import (
    EventIntakeRoutedPublisher,
    EnrichmentStatus,
    ContentCompleteness,
    IndustryEventContextBuilder,
    SingleCallEventIntakeRunner,
)
from quantagent.core.event_intake.decision import build_discard_decision, DiscardReason
from quantagent.core.events import EventEnvelope


class AnalysisRequestIntakeAuditSink(Protocol):
    def record(self, entry: dict[str, object]) -> None: ...


@dataclass
class InMemoryAnalysisRequestIntakeAuditSink:
    entries: list[dict[str, object]]

    def __init__(self) -> None:
        self.entries = []

    def record(self, entry: dict[str, object]) -> None:
        self.entries.append(entry)


@dataclass
class IndustryAnalysisRequestHandler:
    context_builder: IndustryEventContextBuilder
    runner: SingleCallEventIntakeRunner
    routed_publisher: EventIntakeRoutedPublisher
    audit_sink: AnalysisRequestIntakeAuditSink

    async def handle(self, envelope: EventEnvelope) -> None:
        contexts = self.context_builder.build_contexts(envelope)
        for context in contexts:
            result = await self.runner.run(context)
            published = await self.routed_publisher.publish(result)
            self.audit_sink.record(
                {
                    "analysis_request_id": context.trace.analysis_request_id,
                    "source_message_id": context.trace.source_message_id,
                    "binding_id": context.trace.binding_id,
                    "owner_id": context.trace.owner_id,
                    "item_index": context.trace.item_index,
                    "decision": result.decision.decision.value,
                    "discard_reason": result.decision.discard_reason.value,
                    "event_routed_message_id": published.id,
                    "provider_invocation_count": result.provider_invocation_count,
                }
            )
        if not contexts:
            decision = build_discard_decision(
                trace={
                    "message_id": envelope.id,
                    "source_message_id": envelope.causation_id,
                    "analysis_request_id": envelope.id,
                    "binding_id": envelope.headers.get("binding_id"),
                    "owner_type": envelope.payload.get("owner_type"),
                    "owner_id": envelope.payload.get("owner_id"),
                    "item_index": 0,
                    "request_id": envelope.headers.get("request_id"),
                    "correlation_id": envelope.correlation_id,
                    "causation_id": envelope.causation_id,
                },
                reason=DiscardReason.MALFORMED,
                reason_summary="Analysis request payload did not contain any valid item.",
                content_completeness=ContentCompleteness.UNKNOWN,
                enrichment_status=EnrichmentStatus.UNKNOWN,
            )
            from quantagent.core.event_intake.runner import EventIntakeRunResult
            from quantagent.core.event_intake.context import IndustryEventContextV1, TraceSnapshotV1, SourceSnapshotV1, ArticleSnapshotV1

            fallback_context = IndustryEventContextV1(
                trace=TraceSnapshotV1(
                    message_id=envelope.id,
                    source_message_id=envelope.causation_id,
                    analysis_request_id=envelope.id,
                    binding_id=envelope.headers.get("binding_id"),
                    owner_type=envelope.payload.get("owner_type"),
                    owner_id=envelope.payload.get("owner_id"),
                    item_index=0,
                    request_id=envelope.headers.get("request_id"),
                    correlation_id=envelope.correlation_id,
                    causation_id=envelope.causation_id,
                ),
                source=SourceSnapshotV1(
                    plugin_id=envelope.payload.get("plugin_id"),
                    binding_id=envelope.headers.get("binding_id"),
                    url=None,
                    title=None,
                    enrichment_status=EnrichmentStatus.UNKNOWN,
                    degraded_reason="ANALYSIS_REQUEST_PAYLOAD_MALFORMED",
                ),
                article=ArticleSnapshotV1(
                    title=None,
                    rss_summary=None,
                    body_excerpt=None,
                    body_content_available=False,
                    content_length_chars=None,
                    excerpt_start=None,
                    excerpt_end=None,
                    content_completeness=ContentCompleteness.UNKNOWN,
                ),
                industry_candidates=(),
            )
            published = await self.routed_publisher.publish(
                EventIntakeRunResult(
                    context=fallback_context,
                    decision=decision,
                    provider_invocation_count=0,
                    invocation_metadata={"status": "malformed_analysis_request"},
                )
            )
            self.audit_sink.record(
                {
                    "analysis_request_id": envelope.id,
                    "source_message_id": envelope.causation_id,
                    "binding_id": envelope.headers.get("binding_id"),
                    "owner_id": envelope.payload.get("owner_id"),
                    "item_index": 0,
                    "decision": decision.decision.value,
                    "discard_reason": decision.discard_reason.value,
                    "event_routed_message_id": published.id,
                    "provider_invocation_count": 0,
                }
            )
