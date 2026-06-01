from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from quantagent.api.auth.audit import ActorAuditContext
from quantagent.api.http.middleware import get_request_id
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.scheduling import SchedulingQueryService, SourceBindingActionService


def get_scheduling_query_service(session: Session) -> SchedulingQueryService:
    return SchedulingQueryService(
        binding_repository=SourceBindingRepository(session),
        run_repository=SchedulerRunRepository(session),
    )


def get_source_binding_action_service(session: Session) -> SourceBindingActionService:
    return SourceBindingActionService(
        binding_repository=SourceBindingRepository(session),
        run_repository=SchedulerRunRepository(session),
    )


def build_scheduling_actor_metadata(context: ActorAuditContext) -> dict[str, str]:
    return {
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "request_id": context.request_id,
        "request_path": context.request_path,
        "request_method": context.request_method,
    }


def request_id_from_request(request: Request) -> str:
    return get_request_id(request)
