from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
from urllib.parse import urlsplit

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from quantagent.api.http.errors import NotFoundError
from quantagent.api.schemas.events import (
    EventAgentStageResponse,
    EventDetailResponse,
    EventListItemResponse,
    EventListResponse,
    EventRefResponse,
    EventRouterOutputResponse,
    EventTimelineStepResponse,
    EventTraceResponse,
)
from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.repositories.event_intake_repository import EventIntakeRoutedEventRepository
from quantagent.core.events.codec import sanitize_mapping
from quantagent.plugin_sdk.io import to_json_value


DEFAULT_EVENT_DECISIONS = frozenset({"route", "review"})
SECRET_KEYS = frozenset(
    {
        "api_key",
        "api_token",
        "authorization",
        "body_excerpt",
        "chain_of_thought",
        "content",
        "cookie",
        "password",
        "prompt",
        "provider_raw_response",
        "provider_raw_request",
        "raw_payload",
        "raw_prompt",
        "raw_response",
        "reasoning_prompt",
        "secret",
        "token",
    }
)
SECRET_KEY_FRAGMENTS = frozenset(
    {
        "api_key",
        "api_token",
        "authorization",
        "chain_of_thought",
        "cookie",
        "password",
        "prompt",
        "provider_raw",
        "raw_payload",
        "reasoning",
        "secret",
        "token",
    }
)


class EventReadModelQueryService:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._repository = EventIntakeRoutedEventRepository(session)

    def list_events(
        self,
        *,
        keyword: str | None,
        decision: str | None,
        include_discard: bool,
        binding_id: str | None,
        source_plugin_id: str | None,
        industry_id: str | None,
        target_topic: str | None,
        priority: str | None,
        relationship: str | None,
        status: str | None,
        trace_id: str | None,
        request_id: str | None,
        sort: str,
        time_from: datetime | None,
        time_to: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> EventListResponse:
        decisions = _decision_filter(decision, include_discard=include_discard)
        normalized_sort = _sort_value(sort)
        decoded_cursor = _decode_cursor(cursor)
        cursor_sort_at, cursor_id = _parse_cursor(decoded_cursor)
        raw_items = self._repository.list_for_events_read_model(
            decisions=decisions,
            binding_id=_clean(binding_id),
            source_plugin_id=_clean(source_plugin_id),
            industry_id=_clean(industry_id),
            keyword=_clean(keyword),
            target_topic=_clean(target_topic),
            priority=_clean(priority),
            relationship=_clean(relationship),
            status=_clean(status),
            trace_id=_clean(trace_id),
            request_id=_clean(request_id),
            sort=normalized_sort,
            time_from=time_from,
            time_to=time_to,
            cursor_sort_at=cursor_sort_at,
            cursor_id=cursor_id,
            limit=limit,
        )
        page_limit = min(max(limit, 1), 100)
        raw_events = self._raw_events_for(raw_items)
        next_cursor = None
        if len(raw_items) > page_limit:
            last = raw_items[page_limit - 1]
            next_cursor = _encode_cursor(
                {"sort_at": _cursor_sort_at(last, raw_events.get(last.raw_event_id or ""), normalized_sort), "id": str(last.id)}
            )
            raw_items = raw_items[:page_limit]
        response_items = [_to_list_item(item, raw_events.get(item.raw_event_id or "")) for item in raw_items]
        return EventListResponse(items=response_items, next_cursor=next_cursor, generated_at=datetime.now(UTC))

    def get_event_detail(self, raw_event_id: str) -> EventDetailResponse:
        routed_event = self._repository.get_latest_by_raw_event_id(raw_event_id)
        if routed_event is None:
            raise NotFoundError("Event not found", details={"reason": "ROUTED_EVENT_NOT_FOUND"})
        raw_event = self._raw_events_for([routed_event]).get(raw_event_id)
        list_item = _to_list_item(routed_event, raw_event)
        return EventDetailResponse(
            **list_item.model_dump(),
            safe_details=_safe_details(routed_event, raw_event),
            agent_stages=[
                list_item.router_stage_summary,
                EventAgentStageResponse(
                    stage_id="industry_main_agent",
                    agent_name="行业 MainAgent",
                    agent_type="industry_main_agent",
                    status="unavailable",
                    summary="当前还没有持久化的行业 MainAgent 输出。",
                    key_fields={},
                    refs=list_item.router_stage_summary.refs,
                    unavailable_reason="MainAgent read model 尚未接入，本页只展示 Router Agent 阶段。",
                    has_output_json=False,
                ),
            ],
        )

    def get_router_output(self, *, raw_event_id: str, routed_event_id: str | None) -> EventRouterOutputResponse:
        routed_event = (
            self._repository.get_by_event_id(routed_event_id)
            if routed_event_id
            else self._repository.get_latest_by_raw_event_id(raw_event_id)
        )
        if routed_event is None or routed_event.raw_event_id != raw_event_id:
            raise NotFoundError("Router output not found", details={"reason": "ROUTED_EVENT_NOT_FOUND"})
        raw_event = self._raw_events_for([routed_event]).get(raw_event_id)
        item = _to_list_item(routed_event, raw_event)
        return EventRouterOutputResponse(
            raw_event_id=raw_event_id,
            routed_event_id=routed_event.event_id,
            schema_version=routed_event.schema_version,
            agent_stage=item.router_stage_summary,
            output_json=_sanitize_json(routed_event.output_json),
            trace=item.trace,
        )

    def _raw_events_for(self, routed_events: Sequence[EventIntakeRoutedEventORM]) -> dict[str, RawEventORM]:
        raw_event_ids = sorted({item.raw_event_id for item in routed_events if item.raw_event_id})
        if not raw_event_ids:
            return {}
        statement: Select[tuple[RawEventORM]] = select(RawEventORM).where(RawEventORM.raw_event_id.in_(raw_event_ids))
        return {item.raw_event_id: item for item in self._session.scalars(statement).all()}


def _to_list_item(routed_event: EventIntakeRoutedEventORM, raw_event: RawEventORM | None) -> EventListItemResponse:
    output = _mapping(routed_event.output_json)
    structured_news = _mapping(output.get("structured_news"))
    routing = _mapping(output.get("routing"))
    quality = _mapping(output.get("quality"))
    relevance_items = output.get("industry_relevance") or output.get("relevance") or ()
    first_relevance = _first_mapping(relevance_items)
    source_snapshot = _mapping(routed_event.source_snapshot)
    key_fields = _sanitize_json(routed_event.key_fields)
    title = _string_value(structured_news, "canonical_title") or (raw_event.title if raw_event else None) or _string_value(source_snapshot, "title")
    url = (raw_event.canonical_url if raw_event else None) or _string_value(source_snapshot, "url")
    trace = _trace(routed_event)
    refs = _refs(routed_event)
    summary = routed_event.summary or _string_value(structured_news, "short_summary") or _string_value(_mapping(output.get("audit")), "reason_summary")
    router_stage = EventAgentStageResponse(
        stage_id="router_agent",
        routed_event_id=routed_event.event_id,
        agent_name="Router Agent",
        agent_type="router_agent",
        status="failed" if routed_event.status == "failed" else "success",
        summary=summary or "Router Agent 已完成处理。",
        key_fields=key_fields,
        refs=refs,
        unavailable_reason=None,
        has_output_json=True,
    )
    return EventListItemResponse(
        raw_event_id=routed_event.raw_event_id or "",
        routed_event_id=routed_event.event_id,
        schema_version=routed_event.schema_version,
        title=title,
        url=url,
        url_host=_url_host(url),
        source_name=(raw_event.metadata_json.get("source") if raw_event and isinstance(raw_event.metadata_json, Mapping) else None)
        or _string_value(source_snapshot, "source_name"),
        source_plugin_id=(raw_event.source_plugin_id if raw_event else None) or _string_value(source_snapshot, "plugin_id"),
        published_at=raw_event.published_at if raw_event else _parse_datetime(_string_value(source_snapshot, "published_at")),
        routed_at=routed_event.created_at,
        decision=_decision_literal(routed_event.decision),
        discard_reason=routed_event.discard_reason,
        status="failed" if routed_event.status == "failed" else "success",
        summary=summary,
        event_type=_string_value(structured_news, "event_type"),
        tags=_string_list(structured_news.get("tags")),
        priority=_string_value(routing, "priority") or _string_value(routed_event.key_fields, "priority"),
        relationship_summary=_relationship_summary(first_relevance, routed_event.key_fields),
        target_industries=_string_list(routing.get("target_industries") or routed_event.key_fields.get("target_industries")),
        target_topics=_string_list(routing.get("target_topics") or routed_event.key_fields.get("target_topics")),
        quality=_sanitize_json(quality),
        trace=trace,
        timeline=_timeline(routed_event, refs),
        router_stage_summary=router_stage,
    )


def _timeline(routed_event: EventIntakeRoutedEventORM, refs: list[EventRefResponse]) -> list[EventTimelineStepResponse]:
    status = "failed" if routed_event.status == "failed" else "success"
    return [
        EventTimelineStepResponse(
            step_id="router_intake",
            label="Router Agent 处理",
            status=status,
            occurred_at=routed_event.created_at,
            summary=f"Router Agent 已输出 {routed_event.decision} 决策。",
            refs=refs,
        ),
        EventTimelineStepResponse(
            step_id="event_ready",
            label="事件已形成",
            status=status,
            occurred_at=routed_event.created_at,
            summary="该新闻已具备 Router routed read model，可进入 /events 业务审计。",
            refs=refs,
        ),
    ]


def _safe_details(routed_event: EventIntakeRoutedEventORM, raw_event: RawEventORM | None) -> dict[str, object]:
    return _sanitize_json(
        {
            "schema_version": routed_event.schema_version,
            "provider_invocation_count": routed_event.provider_invocation_count,
            "invocation_metadata": routed_event.invocation_metadata,
            "source_snapshot": routed_event.source_snapshot,
            "article_snapshot": _safe_article_snapshot(routed_event.article_snapshot),
            "raw_event": {
                "dedupe_strategy": raw_event.dedupe_strategy if raw_event else None,
                "duplicate_capture_count": raw_event.duplicate_capture_count if raw_event else None,
                "first_binding_id": raw_event.first_binding_id if raw_event else None,
                "first_run_id": raw_event.first_run_id if raw_event else None,
            },
        }
    )


def _decision_filter(decision: str | None, *, include_discard: bool) -> frozenset[str]:
    normalized = _clean(decision)
    if normalized in {None, "", "default"}:
        return frozenset({"route", "review", "discard"} if include_discard else DEFAULT_EVENT_DECISIONS)
    if normalized == "all":
        return frozenset({"route", "review", "discard"})
    if normalized in {"route", "review", "discard"}:
        return frozenset({normalized})
    return DEFAULT_EVENT_DECISIONS


def _sort_value(value: str | None) -> str:
    normalized = _clean(value)
    if normalized == "published_at_desc":
        return "published_at_desc"
    return "routed_at_desc"


def _cursor_sort_at(routed_event: EventIntakeRoutedEventORM, raw_event: RawEventORM | None, sort: str) -> str:
    if sort == "published_at_desc":
        sort_at = raw_event.published_at if raw_event and raw_event.published_at else routed_event.created_at
    else:
        sort_at = routed_event.created_at
    return sort_at.astimezone(UTC).isoformat()


def _trace(routed_event: EventIntakeRoutedEventORM) -> EventTraceResponse:
    return EventTraceResponse(
        raw_event_id=routed_event.raw_event_id or "",
        routed_event_id=routed_event.event_id,
        binding_id=routed_event.binding_id,
        request_id=routed_event.request_id,
        correlation_id=routed_event.correlation_id,
        analysis_request_id=routed_event.analysis_request_id,
        source_message_id=routed_event.source_message_id,
    )


def _refs(routed_event: EventIntakeRoutedEventORM) -> list[EventRefResponse]:
    refs = [
        EventRefResponse(kind="event.routed", id=routed_event.event_id, label="Router routed event"),
        EventRefResponse(kind="analysis_request", id=routed_event.analysis_request_id, label="Analysis request"),
    ]
    if routed_event.raw_event_id:
        refs.append(EventRefResponse(kind="raw_event", id=routed_event.raw_event_id, label="RawEvent"))
    return refs


def _decision_literal(value: str):
    return value if value in {"route", "review", "discard"} else "review"


def _relationship_summary(first_relevance: Mapping[str, object] | None, key_fields: Mapping[str, object]) -> str | None:
    if first_relevance is None:
        value = key_fields.get("relevance")
        return value if isinstance(value, str) else None
    parts = [
        _optional_string(first_relevance.get("industry_id")),
        _optional_string(first_relevance.get("relationship")),
        str(first_relevance.get("relevance_score")) if first_relevance.get("relevance_score") is not None else None,
    ]
    return " / ".join(part for part in parts if part)


def _safe_article_snapshot(value: object) -> dict[str, object]:
    snapshot = _mapping(value)
    safe_keys = {
        "body_content_available",
        "content_completeness",
        "content_length_chars",
        "excerpt_end",
        "excerpt_start",
        "language",
        "title",
    }
    safe = {key: snapshot[key] for key in safe_keys if key in snapshot}
    preview = _optional_string(snapshot.get("preview"))
    if preview:
        # 审计详情只允许有限预览；RSS summary 可能就是全文，不能作为安全摘要透出。
        safe["preview"] = preview[:500]
    return _sanitize_json(safe)


def _first_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, list | tuple) and value and isinstance(value[0], Mapping):
        return value[0]
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_value(value: object, key: str) -> str | None:
    if not isinstance(value, Mapping):
        return None
    return _optional_string(value.get(key))


def _string_list(value: object) -> list[str]:
    if isinstance(value, list | tuple):
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, Mapping):
                label = _optional_string(item.get("label")) or _optional_string(item.get("code"))
                if label:
                    result.append(label)
        return result
    return []


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clean(value: str | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _url_host(url: str | None) -> str | None:
    if not url:
        return None
    host = urlsplit(url).netloc
    return host or None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _sanitize_json(value: object) -> dict[str, object]:
    sanitized = _sanitize_value(value)
    return to_json_value(sanitize_mapping(sanitized if isinstance(sanitized, Mapping) else {}))


def _sanitize_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_secret_key(str(key)) else _sanitize_value(child)
            for key, child in value.items()
        }
    if isinstance(value, list | tuple):
        return [_sanitize_value(item) for item in value]
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    if normalized in SECRET_KEYS:
        return True
    return any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS)


def _decode_cursor(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _encode_cursor(value: Mapping[str, str]) -> str:
    raw = json.dumps(dict(value), separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _parse_cursor(value: Mapping[str, str] | None) -> tuple[datetime | None, int | None]:
    if not value:
        return None, None
    created_at = value.get("sort_at") or value.get("created_at")
    row_id = value.get("id")
    if not isinstance(created_at, str) or not isinstance(row_id, str):
        return None, None
    try:
        return datetime.fromisoformat(created_at), int(row_id)
    except ValueError:
        return None, None
