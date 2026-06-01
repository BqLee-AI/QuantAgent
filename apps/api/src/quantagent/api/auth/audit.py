from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from quantagent.api.auth.actor import CurrentActor
from quantagent.api.http.middleware import get_request_id
from quantagent.api.observability import events
from quantagent.api.observability.logging import log_audit_event


@dataclass(frozen=True)
class ActorAuditContext:
    """供后续高风险 handler 复用的审计上下文，只保留 actor 与请求元数据。"""

    actor_id: str
    actor_type: str
    capabilities: tuple[str, ...]
    request_id: str
    request_method: str
    request_path: str


def build_actor_audit_context(request: Request, actor: CurrentActor) -> ActorAuditContext:
    """构造脱敏审计上下文，供后续 Policy Gate 或审计持久化复用。"""
    context = ActorAuditContext(
        actor_id=actor.actor_id,
        actor_type=actor.actor_type,
        capabilities=tuple(sorted(actor.capabilities)),
        request_id=get_request_id(request),
        request_method=request.method,
        request_path=request.url.path,
    )
    # 这里只记录审计上下文建立，不把业务载荷或敏感写请求内容写进日志。
    log_audit_event(
        event=events.AUDIT_CONTEXT_BOUND,
        action="request.audit_context",
        actor_id=context.actor_id,
        actor_type=context.actor_type,
        request_id=context.request_id,
        path=context.request_path,
        method=context.request_method,
    )
    return context
