from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from quantagent.core.events import EventEnvelope
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping

EVENT_INTAKE_CONTEXT_SCHEMA_VERSION = "industry_event_context.v1"


class ContentCompleteness(StrEnum):
    FULL = "full"
    RSS_SUMMARY_ONLY = "rss_summary_only"
    EXCERPTED = "excerpted"
    UNKNOWN = "unknown"


class EnrichmentStatus(StrEnum):
    NOT_NEEDED = "not_needed"
    SUCCEEDED = "succeeded"
    FAILED_DEGRADED = "failed_degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EventIntakeBudget:
    max_input_chars: int = 256_000
    max_body_chars: int = 220_000
    max_output_items: int = 1

    def __post_init__(self) -> None:
        if self.max_input_chars <= 0:
            raise ValueError("max_input_chars must be greater than zero.")
        if self.max_body_chars <= 0:
            raise ValueError("max_body_chars must be greater than zero.")
        if self.max_body_chars > self.max_input_chars:
            raise ValueError("max_body_chars must not exceed max_input_chars.")
        if self.max_output_items <= 0:
            raise ValueError("max_output_items must be greater than zero.")

    def to_mapping(self) -> dict[str, object]:
        return {
            "max_input_chars": self.max_input_chars,
            "max_body_chars": self.max_body_chars,
            "max_output_items": self.max_output_items,
        }


DEFAULT_EVENT_INTAKE_BUDGET = EventIntakeBudget()


@dataclass(frozen=True)
class TraceSnapshotV1:
    message_id: str
    source_message_id: str | None
    analysis_request_id: str
    binding_id: str | None
    owner_type: str | None
    owner_id: str | None
    item_index: int
    raw_event_id: str | None = None
    source_event_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "message_id": self.message_id,
            "source_message_id": self.source_message_id,
            "analysis_request_id": self.analysis_request_id,
            "binding_id": self.binding_id,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "item_index": self.item_index,
            "raw_event_id": self.raw_event_id,
            "source_event_id": self.source_event_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }


@dataclass(frozen=True)
class SourceSnapshotV1:
    plugin_id: str | None
    binding_id: str | None
    url: str | None
    title: str | None
    published_at: str | None = None
    author: str | None = None
    language: str | None = None
    feed_name: str | None = None
    source_name: str | None = None
    source_tier: str | None = None
    enrichment_status: EnrichmentStatus = EnrichmentStatus.UNKNOWN
    degraded_reason: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "binding_id": self.binding_id,
            "feed_name": self.feed_name,
            "source_name": self.source_name,
            "source_tier": self.source_tier,
            "url": self.url,
            "title": self.title,
            "published_at": self.published_at,
            "author": self.author,
            "language": self.language,
            "enrichment_status": self.enrichment_status.value,
            "degraded_reason": self.degraded_reason,
        }


@dataclass(frozen=True)
class ArticleSnapshotV1:
    title: str | None
    rss_summary: str | None
    body_excerpt: str | None
    body_content_available: bool
    content_length_chars: int | None
    excerpt_start: int | None
    excerpt_end: int | None
    content_completeness: ContentCompleteness

    def to_mapping(self) -> dict[str, object]:
        return {
            "title": self.title,
            "rss_summary": self.rss_summary,
            "body_excerpt": self.body_excerpt,
            "body_content_available": self.body_content_available,
            "content_length_chars": self.content_length_chars,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "content_completeness": self.content_completeness.value,
        }


@dataclass(frozen=True)
class IndustryCandidateV1:
    industry_id: str
    display_name: str
    direct_scope_terms: tuple[str, ...] = field(default_factory=tuple)
    indirect_scope_terms: tuple[str, ...] = field(default_factory=tuple)
    entity_hints: tuple[str, ...] = field(default_factory=tuple)
    exclusion_terms: tuple[str, ...] = field(default_factory=tuple)
    route_target: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "industry_id": self.industry_id,
            "display_name": self.display_name,
            "direct_scope_terms": list(self.direct_scope_terms),
            "indirect_scope_terms": list(self.indirect_scope_terms),
            "entity_hints": list(self.entity_hints),
            "exclusion_terms": list(self.exclusion_terms),
            "route_target": self.route_target or f"industry:{self.industry_id}",
        }


@dataclass(frozen=True)
class RoutingPolicyV1:
    allowed_decisions: tuple[str, ...] = ("discard", "route", "review")
    minimum_route_confidence: float = 0.72
    review_confidence_threshold: float = 0.58
    spam_definitions: tuple[str, ...] = (
        "SEO keyword stuffing without verifiable industry facts",
        "promotional stock touting or affiliate spam",
        "duplicated low-information snippet",
    )
    low_information_definitions: tuple[str, ...] = (
        "title-only item with no usable fact",
        "generic market commentary without named entity, product, metric, or date",
    )
    no_trade_advice: bool = True
    tool_calls_allowed: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            "allowed_decisions": list(self.allowed_decisions),
            "minimum_route_confidence": self.minimum_route_confidence,
            "review_confidence_threshold": self.review_confidence_threshold,
            "spam_definitions": list(self.spam_definitions),
            "low_information_definitions": list(self.low_information_definitions),
            "no_trade_advice": self.no_trade_advice,
            "tool_calls_allowed": self.tool_calls_allowed,
        }


@dataclass(frozen=True)
class IndustryEventContextV1:
    trace: TraceSnapshotV1
    source: SourceSnapshotV1
    article: ArticleSnapshotV1
    industry_candidates: tuple[IndustryCandidateV1, ...]
    routing_policy: RoutingPolicyV1 = field(default_factory=RoutingPolicyV1)
    budget: EventIntakeBudget = DEFAULT_EVENT_INTAKE_BUDGET
    schema_version: str = EVENT_INTAKE_CONTEXT_SCHEMA_VERSION

    def to_mapping(self) -> JsonObject:
        # 安全边界：只把 bounded snapshot 交给模型，不把 RawEvent、provider client 或完整 runtime object 倒进去。
        return freeze_json_mapping(
            {
                "schema_version": self.schema_version,
                "trace": self.trace.to_mapping(),
                "source": self.source.to_mapping(),
                "article": self.article.to_mapping(),
                "industry_candidates": [candidate.to_mapping() for candidate in self.industry_candidates],
                "routing_policy": self.routing_policy.to_mapping(),
                "budget": self.budget.to_mapping(),
            },
            stage="model_input",
        )


class IndustryEventContextBuilder:
    def __init__(
        self,
        *,
        budget: EventIntakeBudget = DEFAULT_EVENT_INTAKE_BUDGET,
        routing_policy: RoutingPolicyV1 | None = None,
        industry_candidates: Sequence[IndustryCandidateV1] | None = None,
    ) -> None:
        self._budget = budget
        self._routing_policy = routing_policy or RoutingPolicyV1()
        self._industry_candidates = tuple(industry_candidates or ())

    def build_contexts(self, envelope: EventEnvelope) -> tuple[IndustryEventContextV1, ...]:
        payload = dict(envelope.payload)
        items = payload.get("items")
        if not isinstance(items, tuple | list):
            return (self._build_malformed_context(envelope=envelope, payload=payload, item_index=0),)

        contexts: list[IndustryEventContextV1] = []
        for item_index, raw_item in enumerate(items):
            if not isinstance(raw_item, Mapping):
                contexts.append(
                    self._build_malformed_context(
                        envelope=envelope,
                        payload=payload,
                        item_index=item_index,
                    )
                )
                continue
            contexts.append(self._build_context(envelope=envelope, payload=payload, item=dict(raw_item), item_index=item_index))
        if not contexts:
            return (self._build_malformed_context(envelope=envelope, payload=payload, item_index=0),)
        return tuple(contexts)

    def _build_context(
        self,
        *,
        envelope: EventEnvelope,
        payload: Mapping[str, Any],
        item: Mapping[str, Any],
        item_index: int,
    ) -> IndustryEventContextV1:
        source_metadata = _mapping_or_empty(item.get("source_metadata"))
        owner_id = _optional_string(payload.get("owner_id"))
        binding_id = _first_string(payload.get("binding_id"), envelope.headers.get("binding_id"))
        enrichment_status = _parse_enrichment_status(item.get("enrichment_status"))
        degraded_reason = _first_string(
            item.get("enrichment_error_code"),
            source_metadata.get("degraded_reason"),
            source_metadata.get("enrichment_error_code"),
        )
        if _boolish(payload.get("degraded")) and degraded_reason is None:
            degraded_reason = "UPSTREAM_DEGRADED"

        content = _optional_string(item.get("summary_or_content"))
        article = _build_article_snapshot(
            title=_optional_string(item.get("title")),
            content=content,
            enrichment_status=enrichment_status,
            degraded_reason=degraded_reason,
            source_metadata=source_metadata,
            budget=self._budget,
        )

        source = SourceSnapshotV1(
            plugin_id=_first_string(payload.get("plugin_id"), envelope.headers.get("plugin_id")),
            binding_id=binding_id,
            url=_optional_string(item.get("url")),
            title=_optional_string(item.get("title")),
            published_at=_first_string(source_metadata.get("published_at"), source_metadata.get("published")),
            author=_optional_string(source_metadata.get("author")),
            language=_first_string(source_metadata.get("language"), source_metadata.get("lang")),
            feed_name=_first_string(source_metadata.get("feed_name"), source_metadata.get("feed_title")),
            source_name=_first_string(source_metadata.get("source_name"), source_metadata.get("source")),
            source_tier=_optional_string(source_metadata.get("source_tier")),
            enrichment_status=enrichment_status,
            degraded_reason=degraded_reason,
        )

        trace = TraceSnapshotV1(
            message_id=envelope.id,
            source_message_id=_first_string(payload.get("source_message_id"), envelope.causation_id),
            analysis_request_id=envelope.id,
            binding_id=binding_id,
            owner_type=_optional_string(payload.get("owner_type")),
            owner_id=owner_id,
            item_index=item_index,
            raw_event_id=_first_string(source_metadata.get("raw_event_id"), payload.get("raw_event_id")),
            source_event_id=_first_string(source_metadata.get("source_event_id"), source_metadata.get("external_id")),
            request_id=_first_string(payload.get("request_id"), envelope.headers.get("request_id")),
            correlation_id=_first_string(envelope.correlation_id, payload.get("correlation_id")),
            causation_id=_first_string(envelope.causation_id, payload.get("causation_id")),
        )

        return IndustryEventContextV1(
            trace=trace,
            source=source,
            article=article,
            industry_candidates=self._resolve_industry_candidates(owner_id),
            routing_policy=self._routing_policy,
            budget=self._budget,
        )

    def _resolve_industry_candidates(self, owner_id: str | None) -> tuple[IndustryCandidateV1, ...]:
        if self._industry_candidates:
            return self._industry_candidates
        if owner_id == "semiconductor":
            return (default_semiconductor_candidate(),)
        if owner_id:
            return (
                IndustryCandidateV1(
                    industry_id=owner_id,
                    display_name=owner_id,
                    route_target=f"industry:{owner_id}",
                ),
            )
        return ()

    def _build_malformed_context(
        self,
        *,
        envelope: EventEnvelope,
        payload: Mapping[str, Any],
        item_index: int,
    ) -> IndustryEventContextV1:
        owner_id = _optional_string(payload.get("owner_id"))
        binding_id = _first_string(payload.get("binding_id"), envelope.headers.get("binding_id"))
        trace = TraceSnapshotV1(
            message_id=envelope.id,
            source_message_id=_first_string(payload.get("source_message_id"), envelope.causation_id),
            analysis_request_id=envelope.id,
            binding_id=binding_id,
            owner_type=_optional_string(payload.get("owner_type")),
            owner_id=owner_id,
            item_index=item_index,
            raw_event_id=_optional_string(payload.get("raw_event_id")),
            source_event_id=_optional_string(payload.get("source_event_id")),
            request_id=_first_string(payload.get("request_id"), envelope.headers.get("request_id")),
            correlation_id=_first_string(envelope.correlation_id, payload.get("correlation_id")),
            causation_id=_first_string(envelope.causation_id, payload.get("causation_id")),
        )
        source = SourceSnapshotV1(
            plugin_id=_first_string(payload.get("plugin_id"), envelope.headers.get("plugin_id")),
            binding_id=binding_id,
            url=None,
            title=None,
            enrichment_status=EnrichmentStatus.UNKNOWN,
            degraded_reason="ANALYSIS_REQUEST_PAYLOAD_MALFORMED",
        )
        article = ArticleSnapshotV1(
            title=None,
            rss_summary=None,
            body_excerpt=None,
            body_content_available=False,
            content_length_chars=None,
            excerpt_start=None,
            excerpt_end=None,
            content_completeness=ContentCompleteness.UNKNOWN,
        )
        return IndustryEventContextV1(
            trace=trace,
            source=source,
            article=article,
            industry_candidates=self._resolve_industry_candidates(owner_id),
            routing_policy=self._routing_policy,
            budget=self._budget,
        )


def default_semiconductor_candidate() -> IndustryCandidateV1:
    return IndustryCandidateV1(
        industry_id="semiconductor",
        display_name="Semiconductor / Memory",
        direct_scope_terms=(
            "semiconductor",
            "memory",
            "DRAM",
            "NAND",
            "HBM",
            "foundry",
            "advanced packaging",
            "wafer capacity",
            "lithography",
            "chip equipment",
        ),
        indirect_scope_terms=(
            "AI server demand",
            "hyperscaler AI capex",
            "memory bandwidth bottleneck",
            "GPU supply chain",
            "data center buildout",
            "packaging capacity",
        ),
        entity_hints=("TSMC", "Samsung", "SK hynix", "Micron", "ASML", "NVIDIA", "Broadcom", "AMD"),
        exclusion_terms=(
            "generic consumer gadget review",
            "unrelated stock promotion",
            "SEO keyword stuffing without semiconductor facts",
        ),
        route_target="industry:semiconductor",
    )


def _build_article_snapshot(
    *,
    title: str | None,
    content: str | None,
    enrichment_status: EnrichmentStatus,
    degraded_reason: str | None,
    source_metadata: Mapping[str, Any],
    budget: EventIntakeBudget,
) -> ArticleSnapshotV1:
    rss_summary = _first_string(
        source_metadata.get("rss_summary"),
        source_metadata.get("summary"),
        source_metadata.get("description"),
    )
    if enrichment_status == EnrichmentStatus.FAILED_DEGRADED or degraded_reason is not None:
        return ArticleSnapshotV1(
            title=title,
            rss_summary=content or rss_summary,
            body_excerpt=None,
            body_content_available=False,
            content_length_chars=len(content) if content is not None else None,
            excerpt_start=None,
            excerpt_end=None,
            content_completeness=ContentCompleteness.RSS_SUMMARY_ONLY,
        )
    if content is None:
        return ArticleSnapshotV1(
            title=title,
            rss_summary=rss_summary,
            body_excerpt=None,
            body_content_available=False,
            content_length_chars=None,
            excerpt_start=None,
            excerpt_end=None,
            content_completeness=ContentCompleteness.UNKNOWN,
        )

    content_length = len(content)
    if content_length > budget.max_body_chars:
        excerpt = content[: budget.max_body_chars]
        return ArticleSnapshotV1(
            title=title,
            rss_summary=rss_summary,
            body_excerpt=excerpt,
            body_content_available=True,
            content_length_chars=content_length,
            excerpt_start=0,
            excerpt_end=len(excerpt),
            content_completeness=ContentCompleteness.EXCERPTED,
        )
    return ArticleSnapshotV1(
        title=title,
        rss_summary=rss_summary,
        body_excerpt=content,
        body_content_available=True,
        content_length_chars=content_length,
        excerpt_start=0,
        excerpt_end=content_length,
        content_completeness=ContentCompleteness.FULL,
    )


def _parse_enrichment_status(value: object) -> EnrichmentStatus:
    if isinstance(value, str):
        normalized = value.strip()
        for status in EnrichmentStatus:
            if status.value == normalized:
                return status
    return EnrichmentStatus.UNKNOWN


def _mapping_or_empty(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_string(*values: object) -> str | None:
    for value in values:
        text = _optional_string(value)
        if text is not None:
            return text
    return None


def _boolish(value: object) -> bool:
    return value is True
