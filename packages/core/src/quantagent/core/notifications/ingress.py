from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from quantagent.core.notifications.audit import InMemoryNotificationIngressAuditSink, NotificationIngressAuditSink
from quantagent.core.notifications.handoff import NoopNotificationApprovalHandoff, NotificationApprovalHandoffPort
from quantagent.core.notifications.models import (
    NotificationApprovalHandoffRequest,
    NotificationApprovalHandoffResult,
    NotificationIngressAuditEntry,
    NotificationReceiveFact,
)
from quantagent.core.notifications.repository import InMemoryNotificationReceiveFactRepository, NotificationReceiveFactRepository
from quantagent.core.registry import PluginRecord, PluginRegistry, PluginStatus
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import NotificationReceiveInput, NotificationReceiveItem, NotificationReceiveResult, PluginRuntimeError
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


@dataclass(frozen=True)
class NotificationIngressInvocationResult:
    accepted: bool
    plugin_id: str
    receive_result: NotificationReceiveResult
    receive_fact: NotificationReceiveFact | None = None
    approval_handoff: NotificationApprovalHandoffResult | None = None


class NotificationIngressError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class NotificationIngressServiceUnavailableError(NotificationIngressError):
    pass


class NotificationIngressService:
    """平台侧 notification ingress 编排层。"""

    def __init__(
        self,
        *,
        registry: PluginRegistry,
        runtime: PluginRuntimeService | None = None,
        repository: NotificationReceiveFactRepository | None = None,
        audit_sink: NotificationIngressAuditSink | None = None,
        approval_handoff: NotificationApprovalHandoffPort | None = None,
    ) -> None:
        self._registry = registry
        self._runtime = runtime or PluginRuntimeService()
        self._repository = repository or InMemoryNotificationReceiveFactRepository()
        self._audit_sink = audit_sink or InMemoryNotificationIngressAuditSink()
        self._approval_handoff = approval_handoff or NoopNotificationApprovalHandoff()

    async def receive(
        self,
        *,
        plugin_id: str,
        request_id: str,
        config: Mapping[str, Any],
        receive_input: NotificationReceiveInput,
    ) -> NotificationIngressInvocationResult:
        record = self._require_receive_plugin(plugin_id)
        invocation = await self._runtime.invoke(
            record,
            capability="notification.receive",
            request_id=request_id,
            config=config,
            input=receive_input.to_mapping(),
            metadata={"transport": receive_input.transport},
        )
        if invocation.error is not None or invocation.result is None:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin could not be invoked",
                code="PLUGIN_INVOKE_FAILED",
            )

        try:
            receive_result = self._validate_receive_result(
                NotificationReceiveResult.from_mapping(invocation.result.output)
            )
        except PluginRuntimeError as exc:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin returned an invalid result payload",
                code="PLUGIN_RESULT_INVALID",
            ) from exc

        receive_fact = None
        approval_handoff_result = None
        if receive_result.accepted and receive_result.item is not None:
            receive_fact = self._record_receive_fact(
                plugin_id=plugin_id,
                request_id=request_id,
                receive_input=receive_input,
                item=receive_result.item,
                receive_result=receive_result,
            )
            approval_handoff_result = await self._handoff_for_approval_with_audit(
                receive_fact=receive_fact,
                receive_result=receive_result,
            )
        return NotificationIngressInvocationResult(
            accepted=receive_result.accepted,
            plugin_id=plugin_id,
            receive_result=receive_result,
            receive_fact=receive_fact,
            approval_handoff=approval_handoff_result,
        )

    def _require_receive_plugin(self, plugin_id: str) -> PluginRecord:
        record = self._registry.get_plugin(plugin_id)
        if record is None:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin was not found",
                code="PLUGIN_NOT_FOUND",
            )
        if record.status != PluginStatus.VALID:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin is not valid",
                code="PLUGIN_INVALID",
            )
        if record.manifest is None:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin is not valid",
                code="PLUGIN_INVALID",
            )
        if "notification.receive" not in record.manifest.capabilities:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin does not expose notification.receive capability",
                code="PLUGIN_CAPABILITY_UNAVAILABLE",
            )
        return record

    def _validate_receive_result(self, result: object) -> NotificationReceiveResult:
        if not isinstance(result, NotificationReceiveResult):
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin returned an invalid result payload",
                code="PLUGIN_RESULT_INVALID",
            )
        response = result.response
        if response is not None and not isinstance(response, Mapping):
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin returned an invalid result payload",
                code="PLUGIN_RESULT_INVALID",
            )
        if result.accepted and response is None:
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin returned an invalid result payload",
                code="PLUGIN_RESULT_INVALID",
            )
        if result.response is not None and result.response_status_code is not None and not (100 <= result.response_status_code <= 599):
            raise NotificationIngressServiceUnavailableError(
                "Configured notification plugin returned an invalid result payload",
                code="PLUGIN_RESULT_INVALID",
            )
        return result

    def _record_receive_fact(
        self,
        *,
        plugin_id: str,
        request_id: str,
        receive_input: NotificationReceiveInput,
        item: NotificationReceiveItem,
        receive_result: NotificationReceiveResult,
    ) -> NotificationReceiveFact:
        now = datetime.now(UTC).isoformat()
        correlation_id = self._resolve_correlation_id(receive_input=receive_input, item=item, request_id=request_id)
        fact = NotificationReceiveFact(
            fact_id=f"notif_fact_{uuid4().hex}",
            plugin_id=plugin_id,
            transport=receive_input.transport,
            request_id=request_id,
            correlation_id=correlation_id,
            interaction_id=item.interaction_id,
            source_id=item.source_id,
            text=item.text,
            payload_summary=item.payload_summary,
            metadata=self._build_fact_metadata(receive_input=receive_input, item=item, receive_result=receive_result),
            received_at=now,
            guild_id=item.guild_id,
            channel_id=item.channel_id,
            author_id=item.author_id,
        )
        self._repository.create(fact)
        self._append_audit_entry(
            event_type="notification.receive.recorded",
            plugin_id=plugin_id,
            request_id=request_id,
            correlation_id=correlation_id,
            recorded_at=now,
            details={
                "fact_id": fact.fact_id,
                "transport": fact.transport,
                "interaction_id": fact.interaction_id,
                "source_id": fact.source_id,
                "plugin_code": receive_result.code,
                "accepted": receive_result.accepted,
            },
        )
        return fact

    async def _handoff_for_approval_with_audit(
        self,
        *,
        receive_fact: NotificationReceiveFact,
        receive_result: NotificationReceiveResult,
    ) -> NotificationApprovalHandoffResult:
        handoff_request = self._build_handoff_request(receive_fact=receive_fact, receive_result=receive_result)
        try:
            result = await self._approval_handoff.handoff(handoff_request)
        except Exception as exc:
            failure = NotificationApprovalHandoffResult(
                status="failed",
                message="Notification receive fact was recorded, but approval handoff failed.",
                metadata={
                    "error_type": exc.__class__.__name__,
                    "fact_id": receive_fact.fact_id,
                },
            )
            self._append_audit_entry(
                event_type="notification.receive.approval_handoff_failed",
                plugin_id=receive_fact.plugin_id,
                request_id=receive_fact.request_id,
                correlation_id=receive_fact.correlation_id,
                recorded_at=datetime.now(UTC).isoformat(),
                details={
                    "fact_id": receive_fact.fact_id,
                    "handoff_status": failure.status,
                    "error_type": exc.__class__.__name__,
                },
            )
            return failure
        self._append_audit_entry(
            event_type="notification.receive.approval_handoff",
            plugin_id=receive_fact.plugin_id,
            request_id=receive_fact.request_id,
            correlation_id=receive_fact.correlation_id,
            recorded_at=datetime.now(UTC).isoformat(),
            details={
                "fact_id": receive_fact.fact_id,
                "handoff_status": result.status,
                "handoff_message": result.message,
            },
        )
        return result

    def _build_handoff_request(
        self,
        *,
        receive_fact: NotificationReceiveFact,
        receive_result: NotificationReceiveResult,
    ) -> NotificationApprovalHandoffRequest:
        return NotificationApprovalHandoffRequest(
            handoff_id=f"notif_handoff_{uuid4().hex}",
            fact_id=receive_fact.fact_id,
            plugin_id=receive_fact.plugin_id,
            transport=receive_fact.transport,
            request_id=receive_fact.request_id,
            correlation_id=receive_fact.correlation_id,
            interaction_id=receive_fact.interaction_id,
            source_id=receive_fact.source_id,
            text=receive_fact.text,
            payload_summary=receive_fact.payload_summary,
            metadata=self._build_handoff_metadata(receive_fact=receive_fact, receive_result=receive_result),
            received_at=receive_fact.received_at,
            guild_id=receive_fact.guild_id,
            channel_id=receive_fact.channel_id,
            author_id=receive_fact.author_id,
        )

    def _append_audit_entry(
        self,
        *,
        event_type: str,
        plugin_id: str,
        request_id: str,
        correlation_id: str,
        recorded_at: str,
        details: Mapping[str, object],
    ) -> NotificationIngressAuditEntry:
        entry = NotificationIngressAuditEntry(
            audit_id=f"notif_audit_{uuid4().hex}",
            event_type=event_type,
            plugin_id=plugin_id,
            request_id=request_id,
            correlation_id=correlation_id,
            recorded_at=recorded_at,
            details=freeze_json_mapping(details, stage="invoke"),
        )
        return self._audit_sink.append(entry)

    def _build_fact_metadata(
        self,
        *,
        receive_input: NotificationReceiveInput,
        item: NotificationReceiveItem,
        receive_result: NotificationReceiveResult,
    ) -> JsonObject:
        metadata: dict[str, object] = {
            "request_metadata": dict(receive_input.request_metadata),
            "item_metadata": dict(item.metadata),
            "plugin_metadata": dict(receive_result.metadata),
        }
        return freeze_json_mapping(metadata, stage="invoke")

    def _build_handoff_metadata(
        self,
        *,
        receive_fact: NotificationReceiveFact,
        receive_result: NotificationReceiveResult,
    ) -> JsonObject:
        metadata: dict[str, object] = {
            "fact_id": receive_fact.fact_id,
            "plugin_code": receive_result.code,
            "plugin_message": receive_result.message,
            "request_id": receive_fact.request_id,
        }
        return freeze_json_mapping(metadata, stage="invoke")

    def _resolve_correlation_id(
        self,
        *,
        receive_input: NotificationReceiveInput,
        item: NotificationReceiveItem,
        request_id: str,
    ) -> str:
        raw = receive_input.request_metadata.get("correlation_id")
        if isinstance(raw, str) and raw.strip():
            return raw
        return f"corr_notification_receive:{item.interaction_id}:{request_id}"
