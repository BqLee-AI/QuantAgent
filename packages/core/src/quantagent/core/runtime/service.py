from __future__ import annotations

import importlib
import inspect
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from quantagent.core.registry.models import PluginError, PluginRecord, PluginStatus
from quantagent.plugin_sdk import (
    HealthCheckResult,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    RuntimeContext,
)


@dataclass(frozen=True)
class PluginRuntimeInvocation:
    result: PluginInvokeResult | None = None
    error: PluginError | None = None
    cleanup_error: PluginError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class PluginRuntimeService:
    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        runtime_mode: str = "local",
        import_module: Callable[[str], Any] = importlib.import_module,
    ) -> None:
        self.logger = logger or logging.getLogger("quantagent.core.runtime")
        self.runtime_mode = runtime_mode
        self._import_module = import_module

    async def invoke(
        self,
        record: PluginRecord,
        *,
        capability: str,
        request_id: str,
        config: Mapping[str, Any] | None = None,
        input: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PluginRuntimeInvocation:
        plugin, load_error = await self.load_plugin(
            record,
            request_id=request_id,
            config=config,
            metadata=metadata,
        )
        if load_error is not None:
            return PluginRuntimeInvocation(error=load_error)

        start_error = await self.start_plugin(plugin)
        if start_error is not None:
            cleanup_error = await self.stop_plugin(plugin, plugin_id=record.id)
            return PluginRuntimeInvocation(error=start_error, cleanup_error=cleanup_error)

        invocation = PluginRuntimeInvocation()
        try:
            if not _supports_capability(record, capability):
                invocation = PluginRuntimeInvocation(
                    error=PluginError(
                        code="PLUGIN_CAPABILITY_UNAVAILABLE",
                        message="Plugin capability is not declared by manifest.",
                        stage="invoke",
                        details={"plugin_id": record.id, "capability": capability},
                    )
                )
            else:
                result = await _call_async(
                    plugin.invoke(
                        PluginInvokeRequest(
                            capability=capability,
                            request_id=request_id,
                            input=input or {},
                            metadata=metadata or {},
                        )
                    )
                )
                if not isinstance(result, PluginInvokeResult):
                    invocation = PluginRuntimeInvocation(
                        error=PluginError(
                            code="PLUGIN_INVOKE_RESULT_INVALID",
                            message="Plugin invoke returned an invalid result.",
                            stage="invoke",
                            details={"plugin_id": record.id, "result_type": type(result).__name__},
                        )
                    )
                else:
                    invocation = PluginRuntimeInvocation(result=result)
        except Exception as exc:
            invocation = PluginRuntimeInvocation(error=_to_plugin_error(exc, stage="invoke", plugin_id=record.id))
        finally:
            cleanup_error = await self.stop_plugin(plugin, plugin_id=record.id)
            if cleanup_error is not None:
                invocation = PluginRuntimeInvocation(
                    result=invocation.result,
                    error=invocation.error,
                    cleanup_error=cleanup_error,
                )
        return invocation

    async def load_plugin(
        self,
        record: PluginRecord,
        *,
        request_id: str,
        config: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[Any | None, PluginError | None]:
        validation_error = _validate_record(record)
        if validation_error is not None:
            return None, validation_error

        assert record.manifest is not None
        try:
            plugin = self._load_entrypoint(record.manifest.entrypoint)
            if not _has_runtime_shape(plugin):
                return None, PluginError(
                    code="PLUGIN_RUNTIME_PROTOCOL_INVALID",
                    message="Plugin entrypoint does not satisfy RuntimePlugin protocol.",
                    stage="load",
                    details={"plugin_id": record.id},
                )
            context = RuntimeContext(
                plugin_id=record.manifest.id,
                plugin_version=record.manifest.version,
                request_id=request_id,
                logger=self.logger.getChild(record.manifest.id),
                config=config or {},
                runtime_mode=self.runtime_mode,
                metadata=metadata or {},
            )
            await _call_async(plugin.load(context))
            return plugin, None
        except Exception as exc:
            return None, _to_plugin_error(exc, stage="load", plugin_id=record.id)

    async def start_plugin(self, plugin: Any) -> PluginError | None:
        try:
            await _call_async(plugin.start())
        except Exception as exc:
            return _to_plugin_error(exc, stage="start")
        return None

    async def health_check(self, plugin: Any) -> tuple[HealthCheckResult | None, PluginError | None]:
        try:
            result = await _call_async(plugin.health_check())
        except Exception as exc:
            return None, _to_plugin_error(exc, stage="health_check")
        if not isinstance(result, HealthCheckResult):
            return None, PluginError(
                code="PLUGIN_HEALTH_CHECK_RESULT_INVALID",
                message="Plugin health_check returned an invalid result.",
                stage="health_check",
                details={"result_type": type(result).__name__},
            )
        return result, None

    async def stop_plugin(self, plugin: Any, *, plugin_id: str | None = None) -> PluginError | None:
        try:
            await _call_async(plugin.stop())
        except Exception as exc:
            return _to_plugin_error(exc, stage="stop", plugin_id=plugin_id)
        return None

    def _load_entrypoint(self, entrypoint: str) -> Any:
        module_name, separator, attribute_name = entrypoint.partition(":")
        if not separator or not module_name or not attribute_name:
            raise PluginRuntimeError(
                code="PLUGIN_ENTRYPOINT_INVALID",
                message="Plugin entrypoint must use 'module:attribute' format.",
                stage="load",
            )

        module = self._import_module(module_name)
        entrypoint_object = module
        for attribute in attribute_name.split("."):
            entrypoint_object = getattr(entrypoint_object, attribute)
        if inspect.isclass(entrypoint_object):
            return entrypoint_object()
        if callable(entrypoint_object):
            return entrypoint_object()
        raise PluginRuntimeError(
            code="PLUGIN_ENTRYPOINT_NOT_FACTORY",
            message="Plugin entrypoint must be a plugin class or factory.",
            stage="load",
        )


def _validate_record(record: PluginRecord) -> PluginError | None:
    if record.status != PluginStatus.VALID:
        return PluginError(
            code="PLUGIN_RECORD_NOT_LOADABLE",
            message="Plugin record is not valid for runtime loading.",
            stage="load",
            details={"plugin_id": record.id, "status": record.status.value},
        )
    if record.manifest is None:
        return PluginError(
            code="PLUGIN_MANIFEST_MISSING",
            message="Plugin record does not include a manifest.",
            stage="load",
            details={"plugin_id": record.id},
        )
    return None


def _supports_capability(record: PluginRecord, capability: str) -> bool:
    return record.manifest is not None and capability in record.manifest.capabilities


def _has_runtime_shape(plugin: Any) -> bool:
    return all(
        callable(getattr(plugin, method_name, None))
        for method_name in ("load", "start", "stop", "health_check", "invoke")
    )


async def _call_async(value: Awaitable[Any] | Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _to_plugin_error(exc: Exception, *, stage: str, plugin_id: str | None = None) -> PluginError:
    if isinstance(exc, PluginRuntimeError):
        details = _sanitize_details(exc.details)
        if plugin_id is not None:
            details.setdefault("plugin_id", plugin_id)
        return PluginError(
            code=exc.code,
            message=_sanitize_message(exc.message),
            stage=exc.stage or stage,
            retryable=exc.retryable,
            details=details,
        )

    details: dict[str, Any] = {"error_type": exc.__class__.__name__}
    if plugin_id is not None:
        details["plugin_id"] = plugin_id
    return PluginError(
        code=f"PLUGIN_{stage.upper()}_FAILED",
        message=f"Plugin {stage} failed.",
        stage=stage,
        details=details,
    )


SENSITIVE_KEYWORDS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "password",
        "secret",
        "session",
        "token",
    }
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(token|secret|password|cookie|authorization|api[_-]?key)\s*[:=]\s*[^,\s]+"
)
LOCAL_PATH_PATTERN = re.compile(r"(/(?:home|tmp|var|Users)/[^\s,;]+|[A-Za-z]:\\[^\s,;]+)")
REDACTED = "[REDACTED]"


def _sanitize_message(message: str) -> str:
    return LOCAL_PATH_PATTERN.sub(REDACTED, SENSITIVE_VALUE_PATTERN.sub(REDACTED, message))


def _sanitize_details(details: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize_detail_value(str(key), value) for key, value in details.items()}


def _sanitize_detail_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, str):
        return _sanitize_message(value)
    if isinstance(value, Mapping):
        return _sanitize_details(value)
    if isinstance(value, list | tuple):
        return [_sanitize_detail_value(key, item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower().replace("-", "_")
    return any(keyword in normalized_key for keyword in SENSITIVE_KEYWORDS)
