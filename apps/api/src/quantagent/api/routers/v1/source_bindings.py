from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import (
    CurrentActor,
    SOURCE_BINDING_CONTROL_CAPABILITY,
    SOURCE_BINDING_READ_CAPABILITY,
    build_actor_audit_context,
    require_capability,
    require_csrf,
)
from quantagent.api.db import get_db_session
from quantagent.api.http.errors import AppError, BadRequestError, NotFoundError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.observability import events
from quantagent.api.observability.logging import log_audit_event
from quantagent.api.schemas.source_bindings import (
    EffectiveConfigSummaryResponse,
    SchedulerRunDetailResponse,
    SchedulerRunListResponse,
    SchedulerRunSummaryResponse,
    SourceBindingDetailResponse,
    SourceBindingListResponse,
    SourceBindingRunNowAcceptedResponse,
    SourceBindingRunRefResponse,
    SourceBindingStateActionAcceptedResponse,
    SourceBindingSummaryResponse,
)
from quantagent.api.services.source_binding_api import (
    get_scheduling_query_service,
    get_source_binding_action_service,
)
from quantagent.core.scheduling import (
    SchedulingActionNotFoundError,
    SchedulingActionStateError,
    SchedulingQueryNotFoundError,
    SchedulingQueryService,
    SchedulerRunQuery,
    SchedulerRunSummaryView,
    SourceBindingActionService,
    SourceBindingQuery,
    SourceBindingSummaryView,
)


router = APIRouter(prefix="/source-bindings", tags=["source-bindings"])
runs_router = APIRouter(prefix="/scheduler-runs", tags=["scheduler-runs"])


@router.get("", response_model=ApiResponse[SourceBindingListResponse], dependencies=[Depends(require_capability(SOURCE_BINDING_READ_CAPABILITY))])
def list_source_bindings(
    owner_type: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    source_plugin_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SourceBindingListResponse]:
    service = get_scheduling_query_service(session)
    try:
        page = service.list_bindings(
            SourceBindingQuery(
                owner_type=owner_type,
                owner_id=owner_id,
                source_plugin_id=source_plugin_id,
                status=_parse_binding_status(status),
                cursor=cursor,
                limit=limit,
            )
        )
    except ValueError as exc:
        raise BadRequestError("Invalid source binding query", details={"reason": str(exc)}) from exc
    return ApiResponse.success(
        SourceBindingListResponse(
            items=[_binding_summary_response(item) for item in page.items if isinstance(item, SourceBindingSummaryView)],
            next_cursor=page.next_cursor,
        )
    )


@router.get("/{binding_id}", response_model=ApiResponse[SourceBindingDetailResponse], dependencies=[Depends(require_capability(SOURCE_BINDING_READ_CAPABILITY))])
def get_source_binding(
    binding_id: str,
    session: Session = Depends(get_db_session),
) -> ApiResponse[SourceBindingDetailResponse]:
    service = get_scheduling_query_service(session)
    try:
        detail = service.get_binding_detail(binding_id)
    except SchedulingQueryNotFoundError as exc:
        raise NotFoundError("Source binding not found", details={"binding_id": exc.resource_id}) from exc
    return ApiResponse.success(_binding_detail_response(detail))


@router.get(
    "/{binding_id}/scheduler-runs",
    response_model=ApiResponse[SchedulerRunListResponse],
    dependencies=[Depends(require_capability(SOURCE_BINDING_READ_CAPABILITY))],
)
def list_source_binding_runs(
    binding_id: str,
    status: str | None = Query(default=None),
    trigger_mode: str | None = Query(default=None),
    started_after: datetime | None = Query(default=None),
    started_before: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SchedulerRunListResponse]:
    service = get_scheduling_query_service(session)
    try:
        page = service.list_binding_runs(
            binding_id,
            SchedulerRunQuery(
                binding_id=binding_id,
                status=_parse_run_status(status),
                trigger_mode=_parse_trigger_mode(trigger_mode),
                started_after=started_after,
                started_before=started_before,
                cursor=cursor,
                limit=limit,
            ),
        )
    except SchedulingQueryNotFoundError as exc:
        raise NotFoundError("Source binding not found", details={"binding_id": exc.resource_id}) from exc
    except ValueError as exc:
        raise BadRequestError("Invalid scheduler run query", details={"reason": str(exc)}) from exc
    return ApiResponse.success(
        SchedulerRunListResponse(
            items=[_run_summary_response(item) for item in page.items if isinstance(item, SchedulerRunSummaryView)],
            next_cursor=page.next_cursor,
        )
    )


@router.post(
    "/{binding_id}/actions/pause",
    response_model=ApiResponse[SourceBindingStateActionAcceptedResponse],
    dependencies=[Depends(require_capability(SOURCE_BINDING_CONTROL_CAPABILITY))],
)
def pause_source_binding(
    binding_id: str,
    request: Request,
    actor: CurrentActor = Depends(require_csrf),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SourceBindingStateActionAcceptedResponse]:
    return _handle_binding_state_action(
        action="pause",
        binding_id=binding_id,
        request=request,
        actor=actor,
        session=session,
    )


@router.post(
    "/{binding_id}/actions/resume",
    response_model=ApiResponse[SourceBindingStateActionAcceptedResponse],
    dependencies=[Depends(require_capability(SOURCE_BINDING_CONTROL_CAPABILITY))],
)
def resume_source_binding(
    binding_id: str,
    request: Request,
    actor: CurrentActor = Depends(require_csrf),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SourceBindingStateActionAcceptedResponse]:
    return _handle_binding_state_action(
        action="resume",
        binding_id=binding_id,
        request=request,
        actor=actor,
        session=session,
    )


@router.post(
    "/{binding_id}/actions/run-now",
    response_model=ApiResponse[SourceBindingRunNowAcceptedResponse],
    dependencies=[Depends(require_capability(SOURCE_BINDING_CONTROL_CAPABILITY))],
)
def run_now_source_binding(
    binding_id: str,
    request: Request,
    actor: CurrentActor = Depends(require_csrf),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SourceBindingRunNowAcceptedResponse]:
    service = get_source_binding_action_service(session)
    context = build_actor_audit_context(request, actor)
    try:
        accepted = service.request_run_now(
            binding_id=binding_id,
            actor_id=context.actor_id,
            actor_type=context.actor_type,
            request_id=context.request_id,
        )
    except SchedulingActionNotFoundError as exc:
        raise NotFoundError("Source binding not found", details={"binding_id": exc.resource_id}) from exc
    except SchedulingActionStateError as exc:
        raise AppError(
            "Source binding state invalid",
            status_code=409,
            error_code=40910,
            error_key="SOURCE_BINDING_STATE_INVALID",
            details={"binding_id": exc.binding_id, "action": exc.action},
        ) from exc
    session.commit()
    _log_binding_action(context, accepted.audit_ref, action="run-now", target_id=binding_id, result="accepted")
    return ApiResponse.success(_run_now_response(accepted))


@runs_router.get("", response_model=ApiResponse[SchedulerRunListResponse], dependencies=[Depends(require_capability(SOURCE_BINDING_READ_CAPABILITY))])
def list_scheduler_runs(
    binding_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    trigger_mode: str | None = Query(default=None),
    started_after: datetime | None = Query(default=None),
    started_before: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
) -> ApiResponse[SchedulerRunListResponse]:
    service = get_scheduling_query_service(session)
    try:
        page = service.list_runs(
            SchedulerRunQuery(
                binding_id=binding_id,
                status=_parse_run_status(status),
                trigger_mode=_parse_trigger_mode(trigger_mode),
                started_after=started_after,
                started_before=started_before,
                cursor=cursor,
                limit=limit,
            )
        )
    except ValueError as exc:
        raise BadRequestError("Invalid scheduler run query", details={"reason": str(exc)}) from exc
    return ApiResponse.success(
        SchedulerRunListResponse(
            items=[_run_summary_response(item) for item in page.items if isinstance(item, SchedulerRunSummaryView)],
            next_cursor=page.next_cursor,
        )
    )


@runs_router.get("/{run_id}", response_model=ApiResponse[SchedulerRunDetailResponse], dependencies=[Depends(require_capability(SOURCE_BINDING_READ_CAPABILITY))])
def get_scheduler_run(
    run_id: str,
    session: Session = Depends(get_db_session),
) -> ApiResponse[SchedulerRunDetailResponse]:
    service = get_scheduling_query_service(session)
    try:
        detail = service.get_run_detail(run_id)
    except SchedulingQueryNotFoundError as exc:
        raise NotFoundError("Scheduler run not found", details={"run_id": exc.resource_id}) from exc
    return ApiResponse.success(_run_detail_response(detail))


def _handle_binding_state_action(
    *,
    action: str,
    binding_id: str,
    request: Request,
    actor: CurrentActor,
    session: Session,
) -> ApiResponse[SourceBindingStateActionAcceptedResponse]:
    service = get_source_binding_action_service(session)
    context = build_actor_audit_context(request, actor)
    try:
        if action == "pause":
            accepted = service.pause_binding(binding_id=binding_id, actor_id=context.actor_id, request_id=context.request_id)
        elif action == "resume":
            accepted = service.resume_binding(binding_id=binding_id, actor_id=context.actor_id, request_id=context.request_id)
        else:
            raise ValueError(f"unknown action: {action}")
    except SchedulingActionNotFoundError as exc:
        raise NotFoundError("Source binding not found", details={"binding_id": exc.resource_id}) from exc
    except SchedulingActionStateError as exc:
        raise AppError(
            "Source binding state invalid",
            status_code=409,
            error_code=40910,
            error_key="SOURCE_BINDING_STATE_INVALID",
            details={"binding_id": exc.binding_id, "action": exc.action},
        ) from exc
    session.commit()
    _log_binding_action(context, accepted.audit_ref, action=action, target_id=binding_id, result="accepted")
    return ApiResponse.success(_binding_action_response(accepted))


def _binding_summary_response(item: SourceBindingSummaryView) -> SourceBindingSummaryResponse:
    return SourceBindingSummaryResponse(
        id=item.id,
        source_plugin_id=item.source_plugin_id,
        owner_type=item.owner_type,
        owner_id=item.owner_id,
        status=item.status.value,
        blocked_reason=item.blocked_reason,
        schedule_summary=_json_data(item.schedule_summary),
        last_run_ref=_run_ref_response(item.last_run_ref),
        next_run_at=item.next_run_at,
        health_summary=_json_data(item.health_summary),
        allowed_actions=list(item.allowed_actions),
    )


def _binding_detail_response(item) -> SourceBindingDetailResponse:
    summary = _binding_summary_response(item.summary)
    return SourceBindingDetailResponse(
        **summary.model_dump(),
        effective_config_summary=EffectiveConfigSummaryResponse(
            values=_json_data(item.effective_config_summary.values),
            secret_fields_masked=list(item.effective_config_summary.secret_fields_masked),
            last_validated_at=item.effective_config_summary.last_validated_at,
            config_source_refs=list(item.effective_config_summary.config_source_refs),
        ),
        config_version=item.config_version,
        config_validation_status=item.config_validation_status,
        rate_limit_policy_summary=_json_data(item.rate_limit_policy_summary),
        retry_policy_summary=_json_data(item.retry_policy_summary),
        last_error_summary=_json_data(item.last_error_summary),
        audit_refs=list(item.audit_refs),
        recent_run_refs=[_run_ref_response(run) for run in item.recent_run_refs],
    )


def _run_summary_response(item: SchedulerRunSummaryView) -> SchedulerRunSummaryResponse:
    return SchedulerRunSummaryResponse(
        id=item.id,
        binding_id=item.binding_id,
        source_plugin_id=item.source_plugin_id,
        trigger_mode=item.trigger_mode.value,
        status=item.status.value,
        started_at=item.started_at,
        finished_at=item.finished_at,
        duration_ms=item.duration_ms,
        attempt_index=item.attempt_index,
        captured_count=item.captured_count,
        failure_summary=_json_data(item.failure_summary),
    )


def _run_detail_response(item) -> SchedulerRunDetailResponse:
    summary = _run_summary_response(item.summary)
    return SchedulerRunDetailResponse(
        **summary.model_dump(),
        request_id=item.request_id,
        actor=_json_data(item.actor),
        correlation_id=item.correlation_id,
        binding_snapshot_ref=item.binding_snapshot_ref,
        output_summary=_json_data(item.output_summary),
        error_code=item.error_code,
        error_stage=item.error_stage,
        error_retryable=item.error_retryable,
        audit_ref=item.audit_ref,
    )


def _run_ref_response(item) -> SourceBindingRunRefResponse | None:
    if item is None:
        return None
    return SourceBindingRunRefResponse(
        run_id=item.run_id,
        status=item.status.value,
        started_at=item.started_at,
        finished_at=item.finished_at,
    )


def _binding_action_response(item) -> SourceBindingStateActionAcceptedResponse:
    return SourceBindingStateActionAcceptedResponse(
        binding_id=item.binding_id,
        target_state=item.target_state.value,
        already_in_target_state=item.already_in_target_state,
        accepted_at=item.accepted_at,
        audit_ref=item.audit_ref,
    )


def _run_now_response(item) -> SourceBindingRunNowAcceptedResponse:
    return SourceBindingRunNowAcceptedResponse(
        binding_id=item.binding_id,
        accepted_at=item.accepted_at,
        request_id=item.request_id,
        requested_run_ref=item.requested_run_ref,
        audit_ref=item.audit_ref,
    )


def _parse_binding_status(value: str | None):
    if value is None:
        return None
    from quantagent.core.scheduling import SourceBindingStatus

    try:
        return SourceBindingStatus(value)
    except ValueError as exc:
        raise BadRequestError("Invalid source binding status", details={"status": value}) from exc


def _parse_run_status(value: str | None):
    if value is None:
        return None
    from quantagent.core.scheduling import PluginRunStatus

    try:
        return PluginRunStatus(value)
    except ValueError as exc:
        raise BadRequestError("Invalid scheduler run status", details={"status": value}) from exc


def _parse_trigger_mode(value: str | None):
    if value is None:
        return None
    from quantagent.core.scheduling import PluginTriggerType

    try:
        return PluginTriggerType(value)
    except ValueError as exc:
        raise BadRequestError("Invalid scheduler trigger mode", details={"trigger_mode": value}) from exc


def _log_binding_action(context, audit_ref: str, *, action: str, target_id: str, result: str) -> None:
    log_audit_event(
        event=events.AUDIT_CONTEXT_BOUND,
        action=f"source-binding.{action}",
        actor_id=context.actor_id,
        actor_type=context.actor_type,
        request_id=context.request_id,
        path=context.request_path,
        method=context.request_method,
    )


def _json_data(value):
    if isinstance(value, Mapping):
        return {str(key): _json_data(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_data(item) for item in value]
    return value
