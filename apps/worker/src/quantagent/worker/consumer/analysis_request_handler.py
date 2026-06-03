from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from quantagent.core.event_intake import (
    EventIntakeRoutedEventStore,
    EventIntakeRoutedPublisher,
    EnrichmentStatus,
    ContentCompleteness,
    IndustryEventContextBuilder,
    SingleCallEventIntakeRunner,
)
from quantagent.core.event_intake.decision import build_discard_decision, DiscardReason
from quantagent.core.events import EventEnvelope

logger = logging.getLogger(__name__)


class AnalysisRequestIntakeAuditSink(Protocol):
    def record(self, entry: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class AnalysisRequestProcessingScope:
    runner: SingleCallEventIntakeRunner
    routed_event_store: EventIntakeRoutedEventStore | None = None
    commit: Callable[[], None] | None = None
    rollback: Callable[[], None] | None = None
    close: Callable[[], None] | None = None


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
    routed_event_store: EventIntakeRoutedEventStore | None = None
    commit: Callable[[], None] | None = None
    rollback: Callable[[], None] | None = None
    article_concurrency: int = 10
    processing_scope_factory: Callable[[], AnalysisRequestProcessingScope] | None = None

    async def handle(self, envelope: EventEnvelope) -> None:
        contexts = self.context_builder.build_contexts(envelope)
        concurrency = max(1, self.article_concurrency)
        logger.info(
            "Worker AI intake started: analysis_request_id=%s binding_id=%s owner=%s:%s context_count=%s concurrency=%s",
            envelope.id,
            envelope.headers.get("binding_id"),
            envelope.payload.get("owner_type"),
            envelope.payload.get("owner_id"),
            len(contexts),
            concurrency,
            extra={
                "analysis_request_id": envelope.id,
                "binding_id": envelope.headers.get("binding_id"),
                "owner_type": envelope.payload.get("owner_type"),
                "owner_id": envelope.payload.get("owner_id"),
                "context_count": len(contexts),
                "article_concurrency": concurrency,
            },
        )
        if contexts:
            semaphore = asyncio.Semaphore(concurrency)

            async def process_bounded(context) -> None:
                # 每篇文章独立处理，生产入口会给每个 scope 独立 DB session，避免并发模型调用共享 session。
                async with semaphore:
                    await self._process_context(envelope=envelope, context=context)

            await asyncio.gather(*(process_bounded(context) for context in contexts))
            logger.info(
                "Worker AI intake batch completed: analysis_request_id=%s context_count=%s concurrency=%s",
                envelope.id,
                len(contexts),
                concurrency,
                extra={
                    "analysis_request_id": envelope.id,
                    "context_count": len(contexts),
                    "article_concurrency": concurrency,
                },
            )
            return
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
            fallback_result = EventIntakeRunResult(
                context=fallback_context,
                decision=decision,
                provider_invocation_count=0,
                invocation_metadata={"status": "malformed_analysis_request"},
            )
            published = await self.routed_publisher.publish(fallback_result)
            self._record_routed_event(
                envelope=published,
                result=fallback_result,
                routed_event_store=self.routed_event_store,
                commit=self.commit,
                rollback=self.rollback,
            )
            logger.warning(
                "Worker AI intake malformed request routed to discard: analysis_request_id=%s event_routed_message_id=%s",
                envelope.id,
                published.id,
                extra={
                    "analysis_request_id": envelope.id,
                    "event_routed_message_id": published.id,
                    "decision": decision.decision.value,
                    "discard_reason": decision.discard_reason.value,
                },
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

    async def _process_context(self, *, envelope: EventEnvelope, context) -> None:
        scope = self._create_processing_scope()
        try:
            result = await scope.runner.run(context)
            published = await self.routed_publisher.publish(result)
            self._record_routed_event(
                envelope=published,
                result=result,
                routed_event_store=scope.routed_event_store,
                commit=scope.commit,
                rollback=scope.rollback,
            )
            logger.info(
                (
                    "Worker AI intake routed: analysis_request_id=%s source_message_id=%s binding_id=%s "
                    "item_index=%s decision=%s discard_reason=%s provider_calls=%s event_routed_message_id=%s"
                ),
                context.trace.analysis_request_id,
                context.trace.source_message_id,
                context.trace.binding_id,
                context.trace.item_index,
                result.decision.decision.value,
                result.decision.discard_reason.value,
                result.provider_invocation_count,
                published.id,
                extra={
                    "analysis_request_id": context.trace.analysis_request_id,
                    "source_message_id": context.trace.source_message_id,
                    "binding_id": context.trace.binding_id,
                    "item_index": context.trace.item_index,
                    "decision": result.decision.decision.value,
                    "discard_reason": result.decision.discard_reason.value,
                    "provider_invocation_count": result.provider_invocation_count,
                    "event_routed_message_id": published.id,
                },
            )
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
        finally:
            if scope.close is not None:
                scope.close()

    def _create_processing_scope(self) -> AnalysisRequestProcessingScope:
        if self.processing_scope_factory is not None:
            return self.processing_scope_factory()
        return AnalysisRequestProcessingScope(
            runner=self.runner,
            routed_event_store=self.routed_event_store,
            commit=self.commit,
            rollback=self.rollback,
        )

    def _record_routed_event(
        self,
        *,
        envelope: EventEnvelope,
        result,
        routed_event_store: EventIntakeRoutedEventStore | None,
        commit: Callable[[], None] | None,
        rollback: Callable[[], None] | None,
    ) -> None:
        if routed_event_store is None:
            return
        try:
            routed_event_store.record(envelope=envelope, result=result)
            if commit is not None:
                commit()
            logger.info(
                "Worker persisted event.routed read model: message_id=%s binding_id=%s decision=%s",
                envelope.id,
                envelope.headers.get("binding_id"),
                envelope.headers.get("decision"),
                extra={
                    "message_id": envelope.id,
                    "binding_id": envelope.headers.get("binding_id"),
                    "decision": envelope.headers.get("decision"),
                },
            )
        except Exception:
            if rollback is not None:
                rollback()
            logger.exception(
                "Worker failed to persist event.routed read model: message_id=%s binding_id=%s",
                envelope.id,
                envelope.headers.get("binding_id"),
                extra={"message_id": envelope.id, "binding_id": envelope.headers.get("binding_id")},
            )
            raise
