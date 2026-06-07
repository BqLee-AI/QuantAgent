from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
from urllib.parse import urlsplit

from fastapi import Request
from sqlalchemy import Select, and_, desc, func, or_, select
from sqlalchemy.orm import Session

from quantagent.api.schemas.runtime_audit import (
    RuntimeAuditAgentStageResponse,
    RuntimeAuditNewsItemResponse,
    RuntimeAuditNewsListResponse,
    RuntimeAuditNewsRefResponse,
    RuntimeAuditNewsTimelineStepResponse,
    RuntimeAuditNewsTraceResponse,
)
from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.models.scheduler_run import SchedulerRunORM
from quantagent.core.db.repositories.event_intake_repository import EventIntakeRoutedEventRepository
from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.events.codec import REDACTED, sanitize_mapping
from quantagent.plugin_sdk.io import to_json_value

_AUDIT_READ_MODEL_SENSITIVE_KEYWORDS = frozenset({"prompt", "raw_response"})


class RuntimeAuditNewsQueryService:
    def __init__(self, *, session: Session, request: Request) -> None:
        self._session = session
        self._request = request

    def list_news(
        self,
        *,
        keyword: str | None,
        binding_id: str | None,
        source_plugin_id: str | None,
        status: str | None,
        current_stage: str | None,
        trace_id: str | None,
        request_id: str | None,
        time_from: datetime | None,
        time_to: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> RuntimeAuditNewsListResponse:
        normalized = _NormalizedFilters(
            keyword=_clean(keyword),
            binding_id=_clean(binding_id),
            source_plugin_id=_clean(source_plugin_id),
            status=_clean(status),
            current_stage=_clean(current_stage),
            trace_id=_clean(trace_id),
            request_id=_clean(request_id),
            time_from=time_from,
            time_to=time_to,
            cursor=_decode_cursor(cursor),
            limit=min(max(limit, 1), 100),
        )
        items, next_cursor = self._list_raw_events(normalized)
        captures_by_event = self._list_captures(items)
        scheduler_runs = self._list_scheduler_runs(captures_by_event)
        routed_events = EventIntakeRoutedEventRepository(self._session).list_latest_by_raw_event_ids(
            [item.raw_event_id for item in items]
        )
        response_items = [
            _to_news_item(
                item,
                captures_by_event.get(item.raw_event_id, []),
                scheduler_runs,
                routed_events.get(item.raw_event_id),
            )
            for item in items
        ]
        response_items = [
            item
            for item in response_items
            if _matches_computed_filters(item, status=normalized.status, current_stage=normalized.current_stage)
        ]
        response_items.sort(key=_news_activity_sort_key, reverse=True)
        return RuntimeAuditNewsListResponse(
            items=response_items,
            next_cursor=next_cursor,
            generated_at=datetime.now(UTC),
        )

    def _list_raw_events(self, filters: _NormalizedFilters) -> tuple[list[RawEventORM], str | None]:
        effective_time = func.coalesce(RawEventORM.published_at, RawEventORM.last_captured_at)
        statement: Select[tuple[RawEventORM]] = select(RawEventORM)
        if filters.keyword:
            like_value = f"%{filters.keyword.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(RawEventORM.title).like(like_value),
                    func.lower(RawEventORM.canonical_url).like(like_value),
                    func.lower(RawEventORM.content).like(like_value),
                )
            )
        if filters.binding_id:
            statement = statement.where(
                or_(
                    RawEventORM.first_binding_id == filters.binding_id,
                    _capture_exists(
                        RawEventCaptureORM.source_binding_id == filters.binding_id,
                    ),
                )
            )
        if filters.source_plugin_id:
            statement = statement.where(RawEventORM.source_plugin_id == filters.source_plugin_id)
        if filters.trace_id:
            statement = statement.where(
                or_(
                    _json_string(RawEventORM.metadata_json, "trace_id") == filters.trace_id,
                    _capture_exists(_json_string(RawEventCaptureORM.metadata_json, "trace_id") == filters.trace_id),
                    _first_run_exists(_json_string(SchedulerRunORM.metadata_json, "trace_id") == filters.trace_id),
                    _capture_run_exists(_json_string(SchedulerRunORM.metadata_json, "trace_id") == filters.trace_id),
                )
            )
        if filters.request_id:
            statement = statement.where(
                or_(
                    _json_string(RawEventORM.metadata_json, "request_id") == filters.request_id,
                    _capture_exists(RawEventCaptureORM.request_id == filters.request_id),
                    _first_run_exists(SchedulerRunORM.request_id == filters.request_id),
                    _capture_run_exists(SchedulerRunORM.request_id == filters.request_id),
                )
            )
        if filters.time_from:
            statement = statement.where(effective_time >= filters.time_from)
        if filters.time_to:
            statement = statement.where(effective_time <= filters.time_to)
        if filters.cursor:
            cursor_time, cursor_captured_at, cursor_id = _parse_cursor(filters.cursor)
            statement = statement.where(
                or_(
                    effective_time < cursor_time,
                    and_(
                        effective_time == cursor_time,
                        or_(
                            RawEventORM.last_captured_at < cursor_captured_at,
                            and_(
                                RawEventORM.last_captured_at == cursor_captured_at,
                                RawEventORM.raw_event_id < cursor_id,
                            ),
                        ),
                    ),
                )
            )
        statement = statement.order_by(desc(effective_time), desc(RawEventORM.last_captured_at), desc(RawEventORM.raw_event_id)).limit(
            filters.limit + 1
        )
        items = list(self._session.scalars(statement).all())
        next_cursor = None
        if len(items) > filters.limit:
            last = items[filters.limit - 1]
            next_cursor = _encode_cursor(
                {
                    "effective_time": (last.published_at or last.last_captured_at).astimezone(UTC).isoformat(),
                    "last_captured_at": last.last_captured_at.astimezone(UTC).isoformat(),
                    "raw_event_id": last.raw_event_id,
                }
            )
            items = items[: filters.limit]
        return items, next_cursor

    def _list_captures(self, items: list[RawEventORM]) -> dict[str, list[RawEventCaptureORM]]:
        raw_event_ids = [item.raw_event_id for item in items]
        if not raw_event_ids:
            return {}
        statement = (
            select(RawEventCaptureORM)
            .where(RawEventCaptureORM.raw_event_id.in_(raw_event_ids))
            .order_by(RawEventCaptureORM.captured_at.asc(), RawEventCaptureORM.capture_id.asc())
        )
        grouped: dict[str, list[RawEventCaptureORM]] = defaultdict(list)
        for capture in self._session.scalars(statement).all():
            grouped[capture.raw_event_id].append(capture)
        return grouped

    def _list_scheduler_runs(
        self,
        captures_by_event: dict[str, list[RawEventCaptureORM]],
    ) -> dict[str, SchedulerRunORM]:
        run_ids = sorted(
            {
                capture.scheduler_run_id
                for captures in captures_by_event.values()
                for capture in captures
                if capture.scheduler_run_id
            }
        )
        if not run_ids:
            return {}
        statement = select(SchedulerRunORM).where(SchedulerRunORM.run_id.in_(run_ids))
        return {item.run_id: item for item in self._session.scalars(statement).all()}


def _json_string(column: object, key: str) -> object:
    return column[key].as_string()  # type: ignore[index, no-any-return]


def _capture_exists(*conditions: object) -> object:
    return (
        select(1)
        .select_from(RawEventCaptureORM)
        .where(
            RawEventCaptureORM.raw_event_id == RawEventORM.raw_event_id,
            *conditions,
        )
        .exists()
    )


def _first_run_exists(*conditions: object) -> object:
    return (
        select(1)
        .select_from(SchedulerRunORM)
        .where(
            SchedulerRunORM.run_id == RawEventORM.first_run_id,
            *conditions,
        )
        .exists()
    )


def _capture_run_exists(*conditions: object) -> object:
    return (
        select(1)
        .select_from(RawEventCaptureORM)
        .join(SchedulerRunORM, SchedulerRunORM.run_id == RawEventCaptureORM.scheduler_run_id)
        .where(
            RawEventCaptureORM.raw_event_id == RawEventORM.raw_event_id,
            *conditions,
        )
        .exists()
    )


class _NormalizedFilters:
    def __init__(
        self,
        *,
        keyword: str | None,
        binding_id: str | None,
        source_plugin_id: str | None,
        status: str | None,
        current_stage: str | None,
        trace_id: str | None,
        request_id: str | None,
        time_from: datetime | None,
        time_to: datetime | None,
        cursor: dict[str, str] | None,
        limit: int,
    ) -> None:
        self.keyword = keyword
        self.binding_id = binding_id
        self.source_plugin_id = source_plugin_id
        self.status = status
        self.current_stage = current_stage
        self.trace_id = trace_id
        self.request_id = request_id
        self.time_from = time_from
        self.time_to = time_to
        self.cursor = cursor
        self.limit = limit


def _to_news_item(
    raw_event: RawEventORM,
    captures: list[RawEventCaptureORM],
    scheduler_runs: dict[str, SchedulerRunORM],
    routed_event: EventIntakeRoutedEventORM | None,
) -> RuntimeAuditNewsItemResponse:
    first_capture = captures[0] if captures else None
    run = _first_scheduler_run(captures, scheduler_runs)
    binding_id = raw_event.first_binding_id or (first_capture.source_binding_id if first_capture else None)
    run_id = raw_event.first_run_id or (first_capture.scheduler_run_id if first_capture else None)
    trace = RuntimeAuditNewsTraceResponse(
        raw_event_id=raw_event.raw_event_id,
        binding_id=binding_id,
        run_id=run_id,
        request_id=_first_string(
            raw_event.metadata_json.get("request_id") if isinstance(raw_event.metadata_json, dict) else None,
            first_capture.request_id if first_capture else None,
            run.request_id if run else None,
        ),
        trace_id=_first_string(
            _metadata_string(raw_event.metadata_json, "trace_id"),
            _metadata_string(first_capture.metadata_json, "trace_id") if first_capture else None,
            _metadata_string(run.metadata_json, "trace_id") if run else None,
        ),
        correlation_id=_first_string(
            _metadata_string(raw_event.metadata_json, "correlation_id"),
            _metadata_string(first_capture.metadata_json, "correlation_id") if first_capture else None,
            _metadata_string(run.metadata_json, "correlation_id") if run else None,
        ),
    )
    timeline = _build_timeline(raw_event=raw_event, captures=captures, run=run, trace=trace, routed_event=routed_event)
    status = "routed" if routed_event else ("linked" if run else "captured")
    current_stage = "route_decided" if routed_event else ("scheduler_linked" if run else "persisted")
    focus_stage = "route_decided" if routed_event else "ai_intake_unavailable"
    return RuntimeAuditNewsItemResponse(
        raw_event_id=raw_event.raw_event_id,
        title=raw_event.title,
        canonical_url=raw_event.canonical_url,
        url_host=_url_host(raw_event.canonical_url),
        source_plugin_id=raw_event.source_plugin_id,
        source_name=_source_name(raw_event),
        author=raw_event.author,
        published_at=raw_event.published_at,
        first_captured_at=raw_event.first_captured_at,
        last_captured_at=raw_event.last_captured_at,
        content_preview=_content_preview(raw_event.content),
        status=status,
        current_stage=current_stage,
        focus_stage=focus_stage,
        trace=trace,
        timeline=timeline,
        agent_stages=_build_agent_stages(raw_event=raw_event, trace=trace, routed_event=routed_event),
        safe_details=_safe_details(raw_event=raw_event, captures=captures, run=run),
    )


def _build_timeline(
    *,
    raw_event: RawEventORM,
    captures: list[RawEventCaptureORM],
    run: SchedulerRunORM | None,
    trace: RuntimeAuditNewsTraceResponse,
    routed_event: EventIntakeRoutedEventORM | None,
) -> list[RuntimeAuditNewsTimelineStepResponse]:
    refs = [RuntimeAuditNewsRefResponse(kind="raw_event", id=raw_event.raw_event_id, label="RawEvent")]
    timeline = [
        RuntimeAuditNewsTimelineStepResponse(
            step_id="captured",
            label="采集",
            status="success",
            occurred_at=raw_event.first_captured_at,
            summary="新闻已由 source plugin 捕获。",
            refs=refs,
        ),
        RuntimeAuditNewsTimelineStepResponse(
            step_id="persisted",
            label="RawEvent 入库",
            status="success",
            occurred_at=raw_event.created_at,
            summary="采集事实已作为 RawEvent 保存；列表未返回完整正文或 raw payload。",
            refs=refs,
        ),
    ]
    if run:
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="scheduler_linked",
                label="调度关联",
                status="success" if run.status == "succeeded" else "warning",
                occurred_at=run.started_at or run.created_at,
                summary=f"关联 scheduler run，状态为 {run.status}。",
                refs=[RuntimeAuditNewsRefResponse(kind="scheduler_run", id=run.run_id, label="SchedulerRun")],
            )
        )
    elif captures:
        capture = captures[0]
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="scheduler_linked",
                label="调度关联",
                status="pending",
                occurred_at=capture.captured_at,
                summary="已有 capture ledger，但没有可关联的 scheduler run。",
                refs=[RuntimeAuditNewsRefResponse(kind="raw_event_capture", id=capture.capture_id, label="RawEventCapture")],
            )
        )
    if routed_event is not None:
        routed_refs = [
            RuntimeAuditNewsRefResponse(kind="event_routed", id=routed_event.event_id, label="event.routed"),
            RuntimeAuditNewsRefResponse(kind="raw_event", id=trace.raw_event_id, label="Source fact"),
        ]
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="ai_intake_routed",
                label="AI intake",
                status="success" if routed_event.status == "success" else "warning",
                occurred_at=routed_event.created_at,
                summary=f"Router Agent 已完成结构化 intake，decision={routed_event.decision}。",
                refs=routed_refs,
            )
        )
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="route_decided",
                label="路由结果",
                status="success" if routed_event.status == "success" else "warning",
                occurred_at=routed_event.created_at,
                summary=_route_decision_summary(routed_event),
                refs=routed_refs,
            )
        )
    else:
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="ai_intake_unavailable",
                label="AI intake",
                status="unavailable",
                occurred_at=None,
                summary="V1 尚无持久化 AI intake / route decision read model；不展示伪造的 route、review 或 discard。",
                refs=[RuntimeAuditNewsRefResponse(kind="raw_event", id=trace.raw_event_id, label="Source fact")],
            )
        )
        timeline.append(
            RuntimeAuditNewsTimelineStepResponse(
                step_id="route_unavailable",
                label="路由结果",
                status="unavailable",
                occurred_at=None,
                summary="event.routed 当前没有稳定落库结果，Runtime audit 仅显示真实已持久化事实。",
                refs=[],
            )
        )
    return timeline


def _build_agent_stages(
    *,
    raw_event: RawEventORM,
    trace: RuntimeAuditNewsTraceResponse,
    routed_event: EventIntakeRoutedEventORM | None,
) -> list[RuntimeAuditAgentStageResponse]:
    raw_event_ref = RuntimeAuditNewsRefResponse(kind="raw_event", id=raw_event.raw_event_id, label="RawEvent")
    binding_refs = (
        [RuntimeAuditNewsRefResponse(kind="source_binding", id=trace.binding_id, label="SourceBinding")]
        if trace.binding_id
        else []
    )

    if routed_event is not None:
        router_stage = RuntimeAuditAgentStageResponse(
            stage_id="router_agent",
            agent_name="Router Agent",
            agent_type="router_agent",
            status="success" if routed_event.status == "success" else "failed",
            summary=routed_event.summary or _route_decision_summary(routed_event),
            key_fields=_json_safe_mapping(routed_event.key_fields),
            # 中文注释：Router output 允许展示结构化摘要，但必须先脱敏，避免未来新增字段把 secret / prompt / raw response 直接带到前端。
            output_json=_safe_output_json(routed_event.output_json),
            refs=[
                raw_event_ref,
                RuntimeAuditNewsRefResponse(kind="event_routed", id=routed_event.event_id, label="event.routed"),
                *binding_refs,
            ],
            unavailable_reason=None,
        )
    else:
        # 安全边界：没有 Router 输出落库时，read model 只能暴露可审计缺口，不能从 fixture 或自然语言推断决策。
        router_stage = RuntimeAuditAgentStageResponse(
            stage_id="router_agent",
            agent_name="Router Agent",
            agent_type="router_agent",
            status="unavailable",
            summary="暂无持久化 Router Agent 结构化输出。",
            key_fields={
                "raw_event_id": raw_event.raw_event_id,
                "title": raw_event.title,
                "output_persistence": "unavailable",
                "expected_schema": "event_intake_decision.v1",
            },
            output_json=None,
            refs=[raw_event_ref, *binding_refs],
            unavailable_reason="当前数据库尚未提供 Router Agent output_json / route decision read model。",
        )
    return [
        router_stage,
        RuntimeAuditAgentStageResponse(
            stage_id="industry_main_agent",
            agent_name="行业 MainAgent",
            agent_type="industry_main_agent",
            status="unavailable",
            summary="暂无持久化行业分析输出；后续会以 Chat/Markdown/ToolCall 流形式接入。",
            key_fields={
                "raw_event_id": raw_event.raw_event_id,
                "planned_view": "chat_markdown_toolcall_stream",
            },
            output_json=None,
            refs=[raw_event_ref],
            unavailable_reason="V1 尚未落库行业 MainAgent 消费记录。",
        ),
    ]


def _route_decision_summary(routed_event: EventIntakeRoutedEventORM) -> str:
    decision = routed_event.decision
    if decision == "route":
        targets = routed_event.key_fields.get("target_industries") if isinstance(routed_event.key_fields, dict) else None
        return f"Router Agent 已路由到 {targets or '下游行业分析'}。"
    if decision == "review":
        return "Router Agent 标记为需要人工或后续 review。"
    if decision == "discard":
        return f"Router Agent 已丢弃，原因为 {routed_event.discard_reason or 'unknown'}。"
    return f"Router Agent 已输出 decision={decision}。"


def _matches_computed_filters(
    item: RuntimeAuditNewsItemResponse,
    *,
    status: str | None,
    current_stage: str | None,
) -> bool:
    if status and item.status != status:
        return False
    if current_stage and item.current_stage != current_stage and item.focus_stage != current_stage:
        return False
    return True


def _news_activity_sort_key(item: RuntimeAuditNewsItemResponse) -> datetime:
    # 列表服务“新闻审计流”，最新 Router 输出也应浮到顶部，而不是只按 RSS 捕获时间排序。
    latest_agent_time = max(
        (step.occurred_at for step in item.timeline if step.step_id in {"ai_intake_routed", "route_decided"} and step.occurred_at),
        default=None,
    )
    return latest_agent_time or item.last_captured_at


def _first_scheduler_run(
    captures: list[RawEventCaptureORM],
    scheduler_runs: dict[str, SchedulerRunORM],
) -> SchedulerRunORM | None:
    for capture in captures:
        if capture.scheduler_run_id and capture.scheduler_run_id in scheduler_runs:
            return scheduler_runs[capture.scheduler_run_id]
    return None


def _safe_details(
    *,
    raw_event: RawEventORM,
    captures: list[RawEventCaptureORM],
    run: SchedulerRunORM | None,
) -> dict[str, object]:
    metadata = raw_event.metadata_json if isinstance(raw_event.metadata_json, dict) else {}
    allowed_metadata_keys = ("feed", "source", "provider", "payload_truncated")
    details: dict[str, object] = {
        "dedupe_strategy": raw_event.dedupe_strategy,
        "duplicate_capture_count": raw_event.duplicate_capture_count,
        "metadata": {key: metadata[key] for key in allowed_metadata_keys if key in metadata},
        "capture_count": len(captures),
    }
    if run:
        details["scheduler"] = {
            "status": run.status,
            "trigger_type": run.trigger_mode,
            "captured_count": run.captured_count,
            "duration_ms": run.duration_ms,
        }
    return _json_safe_mapping(details)


def _safe_output_json(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return _json_safe_mapping(sanitize_mapping(value))


def _json_safe_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    normalized = {
        str(key): REDACTED if _is_audit_read_model_sensitive_key(str(key)) else _json_safe_value(item)
        for key, item in value.items()
    }
    json_value = to_json_value(normalized)
    return json_value if isinstance(json_value, dict) else {}


def _json_safe_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe_value(item) for item in value]
    return value


def _is_audit_read_model_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(keyword in normalized for keyword in _AUDIT_READ_MODEL_SENSITIVE_KEYWORDS)


def _content_preview(content: str | None) -> str | None:
    if not content or not content.strip():
        return None
    return content[:280].rstrip()


def _source_name(raw_event: RawEventORM) -> str | None:
    metadata = raw_event.metadata_json if isinstance(raw_event.metadata_json, dict) else {}
    for key in ("source", "feed", "provider"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return raw_event.source_plugin_id


def _url_host(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return parsed.netloc or None


def _metadata_string(metadata: object, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _encode_cursor(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str | None) -> dict[str, str] | None:
    if cursor is None:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeEncodeError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    normalized = {str(key): str(value) for key, value in payload.items()}
    if not {"effective_time", "last_captured_at", "raw_event_id"}.issubset(normalized):
        return None
    return normalized


def _parse_cursor(cursor: dict[str, str]) -> tuple[datetime, datetime, str]:
    return (
        datetime.fromisoformat(cursor["effective_time"]),
        datetime.fromisoformat(cursor["last_captured_at"]),
        cursor["raw_event_id"],
    )
