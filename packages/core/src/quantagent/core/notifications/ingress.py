from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quantagent.core.registry import PluginRecord, PluginRegistry, PluginStatus
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import NotificationReceiveInput, NotificationReceiveResult, PluginRuntimeError


@dataclass(frozen=True)
class NotificationIngressInvocationResult:
    accepted: bool
    plugin_id: str
    receive_result: NotificationReceiveResult


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
    ) -> None:
        self._registry = registry
        self._runtime = runtime or PluginRuntimeService()

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
        return NotificationIngressInvocationResult(
            accepted=receive_result.accepted,
            plugin_id=plugin_id,
            receive_result=receive_result,
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
