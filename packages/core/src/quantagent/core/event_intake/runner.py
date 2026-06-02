from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from quantagent.core.event_intake.context import ContentCompleteness, EnrichmentStatus, IndustryEventContextV1
from quantagent.core.event_intake.decision import (
    EVENT_INTAKE_DECISION_SCHEMA_VERSION,
    DiscardReason,
    EventIntakeDecisionV1,
    EventIntakeValidationError,
    build_discard_decision,
    build_review_decision,
)
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


@dataclass(frozen=True)
class StructuredModelInvocation:
    output: JsonObject
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", freeze_json_mapping(self.output, stage="provider_output"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="provider_metadata"))


class StructuredModelInvoker(Protocol):
    async def invoke(
        self,
        *,
        context: IndustryEventContextV1,
        output_schema: str,
    ) -> StructuredModelInvocation: ...


@dataclass(frozen=True)
class EventIntakeRunResult:
    context: IndustryEventContextV1
    decision: EventIntakeDecisionV1
    provider_invocation_count: int
    invocation_metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "invocation_metadata", freeze_json_mapping(self.invocation_metadata, stage="publish"))


class SingleCallEventIntakeRunner:
    def __init__(
        self,
        *,
        invoker: StructuredModelInvoker,
        supported_languages: Sequence[str] = ("en", "zh", "zh-cn", "zh-tw", "ja", "ko", "unknown", ""),
    ) -> None:
        self._invoker = invoker
        self._supported_languages = frozenset(item.lower() for item in supported_languages)

    async def run(self, context: IndustryEventContextV1) -> EventIntakeRunResult:
        context_mapping = context.to_mapping()
        trace = context_mapping["trace"]
        if not isinstance(trace, Mapping):
            raise EventIntakeValidationError("context trace must be an object.")

        deterministic_decision = self._deterministic_precheck(context=context, trace=trace)
        if deterministic_decision is not None:
            return EventIntakeRunResult(
                context=context,
                decision=deterministic_decision,
                provider_invocation_count=0,
                invocation_metadata={"status": "skipped_precheck"},
            )

        try:
            # 单次调用边界：runner 只调用 provider port 一次，不提供工具、二次抓取或多轮 loop 的入口。
            invocation = await self._invoker.invoke(
                context=context,
                output_schema=EVENT_INTAKE_DECISION_SCHEMA_VERSION,
            )
        except Exception as exc:
            decision = build_review_decision(
                trace=trace,
                reason_summary="Structured model provider was unavailable for AI intake.",
                failure_code="PROVIDER_UNAVAILABLE",
                content_completeness=context.article.content_completeness,
                enrichment_status=context.source.enrichment_status,
                safe_error_summary=exc.__class__.__name__,
            )
            return EventIntakeRunResult(
                context=context,
                decision=decision,
                provider_invocation_count=1,
                invocation_metadata={"status": "provider_failed", "error_type": exc.__class__.__name__},
            )

        try:
            decision = EventIntakeDecisionV1.from_mapping(
                invocation.output,
                trace=trace,
                context_content_completeness=context.article.content_completeness,
                context_enrichment_status=context.source.enrichment_status,
                review_confidence_threshold=context.routing_policy.review_confidence_threshold,
            )
        except EventIntakeValidationError as exc:
            decision = build_review_decision(
                trace=trace,
                reason_summary="Structured model output failed EventIntakeDecisionV1 validation.",
                failure_code=exc.reason_code,
                content_completeness=context.article.content_completeness,
                enrichment_status=context.source.enrichment_status,
                safe_error_summary=str(exc),
            )
            return EventIntakeRunResult(
                context=context,
                decision=decision,
                provider_invocation_count=1,
                invocation_metadata={
                    "status": "schema_validation_failed",
                    "error_code": exc.reason_code,
                    "provider_metadata": dict(invocation.metadata),
                },
            )

        return EventIntakeRunResult(
            context=context,
            decision=decision,
            provider_invocation_count=1,
            invocation_metadata={"status": "succeeded", "provider_metadata": dict(invocation.metadata)},
        )

    def _deterministic_precheck(
        self,
        *,
        context: IndustryEventContextV1,
        trace: Mapping[str, object],
    ) -> EventIntakeDecisionV1 | None:
        language = (context.source.language or "unknown").lower()
        if language not in self._supported_languages:
            return build_discard_decision(
                trace=trace,
                reason=DiscardReason.UNSUPPORTED_LANGUAGE,
                reason_summary="Article language is unsupported by V1 intake policy.",
                content_completeness=context.article.content_completeness,
                enrichment_status=context.source.enrichment_status,
            )
        has_any_content = any(
            (
                context.article.title,
                context.article.rss_summary,
                context.article.body_excerpt,
                context.source.url,
            )
        )
        if not has_any_content:
            return build_discard_decision(
                trace=trace,
                reason=DiscardReason.MALFORMED,
                reason_summary="Article item has no usable title, URL, summary, or body snapshot.",
                content_completeness=ContentCompleteness.UNKNOWN,
                enrichment_status=context.source.enrichment_status or EnrichmentStatus.UNKNOWN,
            )
        return None


class ReviewOnlyStructuredModelInvoker:
    async def invoke(
        self,
        *,
        context: IndustryEventContextV1,
        output_schema: str,
    ) -> StructuredModelInvocation:
        return StructuredModelInvocation(
            output={
                "schema_version": output_schema,
                "decision": "review",
                "discard_reason": "not_discarded",
                "quality": {
                    "is_spam": False,
                    "noise_flags": ("provider_not_configured",),
                    "content_completeness": context.article.content_completeness.value,
                    "enrichment_status": context.source.enrichment_status.value,
                    "confidence": 0.0,
                },
                "industry_relevance": (),
                "structured_news": {
                    "canonical_title": context.article.title,
                    "short_summary": "AI intake provider is not configured; keep the item in review.",
                    "bullet_summary": (),
                    "event_type": "provider_not_configured",
                    "entities": (),
                    "companies": (),
                    "tickers": (),
                    "technologies": (),
                    "products": (),
                    "locations": (),
                    "numbers": (),
                    "time_horizon": None,
                    "source_facts": (),
                    "uncertainties": ("provider_not_configured",),
                },
                "routing": {
                    "target_industries": (),
                    "target_topics": (),
                    "priority": "low",
                    "requires_deep_analysis": False,
                    "requires_human_review": True,
                    "dedupe_key_hint": context.source.url,
                },
                "audit": {
                    "reason_summary": "No structured model provider is configured for worker AI intake.",
                    "evidence_field_refs": ("trace", "source.url", "article.title"),
                    "schema_validation_status": "valid",
                    "failure_code": "PROVIDER_NOT_CONFIGURED",
                    "safe_error_summary": None,
                },
            },
            metadata={"status": "provider_not_configured", "model": "review-only"},
        )


class FakeStructuredModelInvoker:
    def __init__(
        self,
        outputs: Sequence[Mapping[str, object]] | Callable[[IndustryEventContextV1], Mapping[str, object]],
    ) -> None:
        self._outputs = outputs
        self.invocations: list[IndustryEventContextV1] = []

    @property
    def invocation_count(self) -> int:
        return len(self.invocations)

    async def invoke(
        self,
        *,
        context: IndustryEventContextV1,
        output_schema: str,
    ) -> StructuredModelInvocation:
        self.invocations.append(context)
        if callable(self._outputs):
            output = self._outputs(context)
        else:
            index = min(len(self.invocations) - 1, len(self._outputs) - 1)
            output = self._outputs[index]
        return StructuredModelInvocation(
            output=output,
            metadata={"fake_invocation_index": len(self.invocations) - 1, "output_schema": output_schema},
        )
