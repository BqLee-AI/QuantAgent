from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quantagent.core.events import sanitize_mapping
from quantagent.core.events.codec import sanitize_string
from quantagent.core.notifications.models import NotificationDispatchRequest, NotificationDispatchResult
from quantagent.core.registry import PluginRecord, PluginRegistry, PluginStatus, PluginType
from quantagent.core.runtime import PluginRuntimeInvocation, PluginRuntimeService
from quantagent.plugin_sdk import NotificationSendInput, NotificationSendResult, PluginRuntimeError
from quantagent.plugin_sdk.io import to_json_value


class NotificationDispatchService:
    def __init__(
        self,
        *,
        registry: PluginRegistry,
        runtime: PluginRuntimeService | None = None,
        enabled: bool = True,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._runtime = runtime or PluginRuntimeService()
        self._enabled = enabled
        self._config = dict(config or {})

    async def dispatch(self, request: NotificationDispatchRequest) -> NotificationDispatchResult:
        if not self._enabled:
            return self._failed(request, code="NOTIFICATION_DISPATCH_DISABLED", message="Notification dispatch is disabled.")

        record = self._require_send_plugin(request.plugin_id)
        if record is None:
            return self._failed(
                request,
                code="PLUGIN_UNAVAILABLE",
                message="Configured notification plugin is unavailable.",
            )

        send_input = NotificationSendInput(
            channel=request.channel,
            text=request.text,
            metadata=request.metadata,
        )
        invocation = await self._runtime.invoke(
            record,
            capability="notification.send",
            request_id=request.request_id,
            config=self._config,
            input=send_input.to_mapping(),
            metadata={
                "channel": request.channel,
                "approval_id": request.approval_id,
                "action_request_id": request.action_request_id,
            },
        )
        if invocation.error is not None or invocation.result is None:
            return self._runtime_failed(request, invocation)

        try:
            send_result = NotificationSendResult.from_mapping(invocation.result.output)
        except PluginRuntimeError:
            return self._failed(
                request,
                code="PLUGIN_RESULT_INVALID",
                message="Configured notification plugin returned an invalid result payload.",
                retryable=True,
            )
        return self._from_send_result(request, send_result)

    def _require_send_plugin(self, plugin_id: str) -> PluginRecord | None:
        record = self._registry.get_plugin(plugin_id)
        if record is None or record.status != PluginStatus.VALID or record.manifest is None:
            return None
        if record.manifest.type != PluginType.NOTIFICATION:
            return None
        if "notification.send" not in record.manifest.capabilities:
            return None
        return record

    def _from_send_result(
        self,
        request: NotificationDispatchRequest,
        send_result: NotificationSendResult,
    ) -> NotificationDispatchResult:
        metadata = dict(to_json_value(send_result.metadata))
        code = _metadata_text(metadata, "code") or ("SENT" if send_result.accepted else "SEND_REJECTED")
        message = _metadata_text(metadata, "message") or (
            "Notification send was accepted by the plugin."
            if send_result.accepted
            else "Notification send was rejected by the plugin."
        )
        return NotificationDispatchResult(
            request_id=request.request_id,
            plugin_id=request.plugin_id,
            accepted=send_result.accepted,
            retryable=send_result.retryable,
            code=sanitize_string(code),
            message=sanitize_string(message),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            approval_id=request.approval_id,
            action_request_id=request.action_request_id,
            channel=request.channel,
            metadata=sanitize_mapping(
                {
                    "provider_message_id": send_result.provider_message_id,
                    "plugin_metadata": metadata,
                }
            ),
        )

    def _runtime_failed(
        self,
        request: NotificationDispatchRequest,
        invocation: PluginRuntimeInvocation,
    ) -> NotificationDispatchResult:
        error = invocation.error
        if error is None:
            return self._failed(request, code="PLUGIN_INVOKE_FAILED", message="Configured notification plugin could not be invoked.", retryable=True)
        return self._failed(
            request,
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            metadata={
                "stage": error.stage,
                "details": dict(error.details),
            },
        )

    def _failed(
        self,
        request: NotificationDispatchRequest,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> NotificationDispatchResult:
        return NotificationDispatchResult(
            request_id=request.request_id,
            plugin_id=request.plugin_id,
            accepted=False,
            retryable=retryable,
            code=sanitize_string(code),
            message=sanitize_string(message),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            approval_id=request.approval_id,
            action_request_id=request.action_request_id,
            channel=request.channel,
            metadata=sanitize_mapping(metadata or {}),
        )


def _metadata_text(metadata: Mapping[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
