from __future__ import annotations

import logging
from collections.abc import Callable

from quantagent.core.scheduling import SourceBindingRecord, SourceBindingService
from quantagent.core.worker_routing.enrichment_service import WorkerArticleEnrichmentService
from quantagent.core.worker_routing.industry_gateway import IndustryGateway
from quantagent.core.worker_routing.models import (
    AnalysisRequestPayload,
    CapturedSourceEventInput,
    ConsumerDisposition,
    WorkerRouteResult,
    WorkerRouteStatus,
)
from quantagent.core.worker_routing.owner_resolver import OwnerRoutingResolutionError, SourceBindingOwnerResolver

logger = logging.getLogger(__name__)


class WorkerCapturedEventRoutingService:
    def __init__(
        self,
        *,
        binding_service: SourceBindingService,
        owner_resolver: SourceBindingOwnerResolver,
        industry_gateway: IndustryGateway,
        enrichment_service: WorkerArticleEnrichmentService | None = None,
        duplicate_guard: Callable[[str], bool] | None = None,
    ) -> None:
        self._binding_service = binding_service
        self._owner_resolver = owner_resolver
        self._industry_gateway = industry_gateway
        self._enrichment_service = enrichment_service
        guard = duplicate_guard or InMemoryMessageDuplicateGuard()
        self._has_seen = guard if callable(guard) else guard.has_seen
        self._remember = None if callable(guard) else guard.remember

    async def route(self, event: CapturedSourceEventInput) -> WorkerRouteResult:
        if event.binding_id is None:
            result = _route_result(
                event,
                reason_code="CAPTURED_EVENT_BINDING_ID_MISSING",
                status=WorkerRouteStatus.FAILED,
                disposition=ConsumerDisposition.ACK_AND_RECORD_FAILURE,
                retryable=False,
            )
            self._record_if_terminal(result)
            return result
        if self._has_seen(event.message_id):
            return _route_result(
                event,
                reason_code="CAPTURED_EVENT_DUPLICATE",
                status=WorkerRouteStatus.DUPLICATE,
                disposition=ConsumerDisposition.ACK_AND_RECORD_DUPLICATE,
                retryable=False,
            )

        binding = self._get_binding(event.binding_id)
        if binding is None:
            result = _route_result(
                event,
                reason_code="SOURCE_BINDING_NOT_FOUND",
                status=WorkerRouteStatus.FAILED,
                disposition=ConsumerDisposition.ACK_AND_RECORD_FAILURE,
                retryable=False,
            )
            self._record_if_terminal(result)
            return result
        logger.info(
            "Worker resolved source binding: message_id=%s binding_id=%s owner=%s:%s plugin_id=%s",
            event.message_id,
            binding.binding_id,
            binding.owner_type,
            binding.owner_id,
            binding.source_plugin_id,
            extra={
                "message_id": event.message_id,
                "binding_id": binding.binding_id,
                "owner_type": binding.owner_type,
                "owner_id": binding.owner_id,
                "source_plugin_id": binding.source_plugin_id,
            },
        )
        try:
            target = self._owner_resolver.resolve(binding)
        except OwnerRoutingResolutionError as exc:
            status = WorkerRouteStatus.IGNORED if exc.reason_code == "SOURCE_BINDING_NOT_ACTIVE" else WorkerRouteStatus.FAILED
            disposition = (
                ConsumerDisposition.ACK_AND_RECORD_IGNORED
                if exc.reason_code == "SOURCE_BINDING_NOT_ACTIVE"
                else ConsumerDisposition.ACK_AND_RECORD_FAILURE
            )
            result = _route_result(
                event,
                reason_code=exc.reason_code,
                status=status,
                disposition=disposition,
                retryable=False,
                owner_type=exc.owner_type,
                owner_id=exc.owner_id,
            )
            self._record_if_terminal(result)
            return result

        analysis_request = await self._build_analysis_request(target=target, event=event)
        logger.info(
            "Worker analysis request built: message_id=%s binding_id=%s owner=%s:%s item_count=%s degraded=%s",
            event.message_id,
            analysis_request.binding_id,
            analysis_request.owner_type,
            analysis_request.owner_id,
            len(analysis_request.items),
            analysis_request.degraded,
            extra={
                "message_id": event.message_id,
                "binding_id": analysis_request.binding_id,
                "owner_type": analysis_request.owner_type,
                "owner_id": analysis_request.owner_id,
                "item_count": len(analysis_request.items),
                "degraded": analysis_request.degraded,
            },
        )
        gateway_result = await self._industry_gateway.invoke(target=target, event=event, analysis_request=analysis_request)
        if gateway_result.status == "failed":
            return _route_result(
                event,
                reason_code=gateway_result.reason_code or "INDUSTRY_ENTRYPOINT_FAILED",
                status=WorkerRouteStatus.FAILED,
                disposition=ConsumerDisposition.NACK_OR_SCHEDULE_RETRY,
                retryable=True,
                owner_type=target.owner_type,
                owner_id=target.owner_id,
                route_target=gateway_result.target_ref,
                extra_audit={
                    "gateway_error": gateway_result.error_summary,
                    "analysis_request": analysis_request.to_mapping() if analysis_request is not None else {},
                },
            )
        result = _route_result(
            event,
            reason_code=gateway_result.reason_code,
            status=WorkerRouteStatus.ROUTED,
            disposition=ConsumerDisposition.ACK_AND_RECORD_ROUTED,
            retryable=False,
            owner_type=target.owner_type,
            owner_id=target.owner_id,
            route_target=gateway_result.target_ref,
            extra_audit={
                "analysis_request": analysis_request.to_mapping() if analysis_request is not None else {},
            },
        )
        self._record_if_terminal(result)
        return result

    def _get_binding(self, binding_id: str) -> SourceBindingRecord | None:
        return self._binding_service.get_binding(binding_id)

    def _record_if_terminal(self, result: WorkerRouteResult) -> None:
        if result.retryable or self._remember is None:
            return
        self._remember(result.message_id)

    async def _build_analysis_request(
        self,
        *,
        target: object,
        event: CapturedSourceEventInput,
    ) -> AnalysisRequestPayload:
        owner_type = getattr(target, "owner_type")
        owner_id = getattr(target, "owner_id")
        binding_id = getattr(target, "binding_id")
        if self._enrichment_service is None:
            items = ()
        else:
            items = await self._enrichment_service.build_analysis_items(
                owner_id=owner_id,
                event=event,
            )
        degraded = any(item.enrichment_status.value == "failed_degraded" for item in items)
        return AnalysisRequestPayload(
            owner_type=owner_type,
            owner_id=owner_id,
            binding_id=binding_id,
            source_message_id=event.message_id,
            request_id=event.request_id,
            plugin_id=event.plugin_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            degraded=degraded,
            items=items,
        )


class InMemoryMessageDuplicateGuard:
    def __init__(self) -> None:
        self._seen_message_ids: set[str] = set()

    def has_seen(self, message_id: str) -> bool:
        return message_id in self._seen_message_ids

    def remember(self, message_id: str) -> None:
        self._seen_message_ids.add(message_id)


def _route_result(
    event: CapturedSourceEventInput,
    *,
    reason_code: str | None,
    status: WorkerRouteStatus,
    disposition: ConsumerDisposition,
    retryable: bool,
    owner_type: str | None = None,
    owner_id: str | None = None,
    route_target: str | None = None,
    extra_audit: dict[str, object] | None = None,
) -> WorkerRouteResult:
    audit_payload: dict[str, object] = {
        "message_id": event.message_id,
        "binding_id": event.binding_id,
        "request_id": event.request_id,
        "plugin_id": event.plugin_id,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "route_target": route_target,
        "reason_code": reason_code,
        "item_count": event.item_count,
    }
    if extra_audit:
        audit_payload.update(extra_audit)
    return WorkerRouteResult(
        message_id=event.message_id,
        binding_id=event.binding_id,
        status=status,
        consumer_disposition=disposition,
        retryable=retryable,
        audit_required=True,
        reason_code=reason_code,
        owner_type=owner_type,
        owner_id=owner_id,
        route_target=route_target,
        request_id=event.request_id,
        plugin_id=event.plugin_id,
        audit_payload=audit_payload,
    )
