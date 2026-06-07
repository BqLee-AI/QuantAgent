from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.db.repositories.event_intake_repository import EventIntakeRoutedEventRepository
from quantagent.core.event_intake.runner import EventIntakeRunResult
from quantagent.core.events.envelope import EventEnvelope
from quantagent.plugin_sdk.io import freeze_json_mapping, to_json_value


class EventIntakeRoutedEventStore(Protocol):
    def record(self, *, envelope: EventEnvelope, result: EventIntakeRunResult) -> EventIntakeRoutedEventORM: ...


@dataclass
class SqlAlchemyEventIntakeRoutedEventStore:
    repository: EventIntakeRoutedEventRepository

    def record(self, *, envelope: EventEnvelope, result: EventIntakeRunResult) -> EventIntakeRoutedEventORM:
        payload = dict(envelope.payload)
        trace = dict(result.decision.trace)
        context = result.context
        output_json = to_json_value(freeze_json_mapping(payload, stage="persist"))
        key_fields = to_json_value(freeze_json_mapping(_key_fields(payload), stage="persist"))
        routed_event = EventIntakeRoutedEventORM(
            event_id=envelope.id,
            schema_version=str(payload.get("schema_version") or ""),
            raw_event_id=_optional_string(trace.get("raw_event_id")),
            source_message_id=_optional_string(trace.get("source_message_id")),
            analysis_request_id=_optional_string(trace.get("analysis_request_id")) or envelope.id,
            binding_id=_optional_string(trace.get("binding_id")),
            owner_type=_optional_string(trace.get("owner_type")),
            owner_id=_optional_string(trace.get("owner_id")),
            request_id=_optional_string(trace.get("request_id")),
            correlation_id=envelope.correlation_id,
            decision=result.decision.decision.value,
            discard_reason=result.decision.discard_reason.value,
            status=_status_for_decision(result),
            summary=_summary(payload),
            output_json=output_json,
            key_fields=key_fields,
            source_snapshot=to_json_value(freeze_json_mapping(context.source.to_mapping(), stage="persist")),
            article_snapshot=to_json_value(freeze_json_mapping(context.article.to_mapping(), stage="persist")),
            provider_invocation_count=result.provider_invocation_count,
            invocation_metadata=to_json_value(freeze_json_mapping(result.invocation_metadata, stage="persist")),
            created_at=datetime.now(UTC),
        )
        saved, _created = self.repository.create_once(routed_event)
        return saved


def _key_fields(payload: dict[str, object]) -> dict[str, object]:
    structured_news = payload.get("structured_news")
    routing = payload.get("routing")
    quality = payload.get("quality")
    relevance = payload.get("industry_relevance")
    audit = payload.get("audit")

    first_relevance = relevance[0] if isinstance(relevance, list | tuple) and relevance else None
    tags = _mapping_value(structured_news, "tags")
    return {
        "decision": payload.get("decision"),
        "discard_reason": payload.get("discard_reason"),
        "title": _mapping_value(structured_news, "canonical_title"),
        "short_summary": _mapping_value(structured_news, "short_summary"),
        "event_type": _mapping_value(structured_news, "event_type"),
        "event_type_label": _mapping_value(structured_news, "event_type_label"),
        "tags": tags if isinstance(tags, list | tuple) else [],
        "target_industries": _mapping_value(routing, "target_industries"),
        "target_topics": _mapping_value(routing, "target_topics"),
        "priority": _mapping_value(routing, "priority"),
        "requires_deep_analysis": _mapping_value(routing, "requires_deep_analysis"),
        "requires_human_review": _mapping_value(routing, "requires_human_review"),
        "next_step_hint": _mapping_value(routing, "next_step_hint"),
        "routing_reason_summary": _mapping_value(routing, "reason_summary"),
        "confidence": _mapping_value(quality, "confidence"),
        "is_spam": _mapping_value(quality, "is_spam"),
        "quality_reason_summary": _mapping_value(quality, "reason_summary"),
        "relationship": _mapping_value(first_relevance, "relationship"),
        "relevance": _relevance_summary(first_relevance),
        "schema_validation_status": _mapping_value(audit, "schema_validation_status"),
    }


def _summary(payload: dict[str, object]) -> str | None:
    structured_summary = _mapping_value(payload.get("structured_news"), "short_summary")
    if isinstance(structured_summary, str) and structured_summary.strip():
        return structured_summary.strip()
    audit_summary = _mapping_value(payload.get("audit"), "reason_summary")
    if isinstance(audit_summary, str) and audit_summary.strip():
        return audit_summary.strip()
    return None


def _status_for_decision(result: EventIntakeRunResult) -> str:
    if result.provider_invocation_count == 0 and result.invocation_metadata.get("status") == "skipped_precheck":
        return "success"
    status = result.invocation_metadata.get("status")
    if isinstance(status, str) and status in {"provider_failed", "schema_validation_failed", "malformed_analysis_request"}:
        return "failed"
    return "success"


def _mapping_value(value: object, key: str) -> object:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _relevance_summary(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    industry_id = value.get("industry_id")
    relationship = value.get("relationship")
    score = value.get("relevance_score")
    parts = [str(item) for item in (industry_id, relationship, score) if item is not None]
    return " / ".join(parts) if parts else None


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
