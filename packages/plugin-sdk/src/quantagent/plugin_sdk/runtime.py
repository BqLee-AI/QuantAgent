from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable


def _freeze_mapping(value: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True)
class RuntimeContext:
    plugin_id: str
    plugin_version: str
    request_id: str
    logger: logging.Logger
    config: Mapping[str, Any] = field(default_factory=dict)
    runtime_mode: str = "local"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _freeze_mapping(self.config))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class PluginInvokeRequest:
    capability: str
    request_id: str
    input: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "input", _freeze_mapping(self.input))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class PluginInvokeResult:
    output: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", _freeze_mapping(self.output))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class HealthCheckResult:
    status: str = "ok"
    message: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _freeze_mapping(self.details))


@dataclass(frozen=True)
class PluginRuntimeError(Exception):
    code: str
    message: str
    stage: str
    retryable: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _freeze_mapping(self.details))
        Exception.__init__(self, self.message)


@runtime_checkable
class RuntimePlugin(Protocol):
    async def load(self, context: RuntimeContext) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def health_check(self) -> HealthCheckResult: ...

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult: ...


class BasePlugin:
    def __init__(self) -> None:
        self._context: RuntimeContext | None = None

    @property
    def context(self) -> RuntimeContext:
        if self._context is None:
            raise PluginRuntimeError(
                code="PLUGIN_CONTEXT_NOT_LOADED",
                message="Plugin context is not loaded.",
                stage="load",
            )
        return self._context

    @property
    def logger(self) -> logging.Logger:
        return self.context.logger

    async def load(self, context: RuntimeContext) -> None:
        self._context = context

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult()

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        raise PluginRuntimeError(
            code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
            message="Plugin capability is not implemented.",
            stage="invoke",
            details={"capability": request.capability},
        )
