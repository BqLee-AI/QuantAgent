from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from fastapi import Request

from quantagent.api.config.settings import Settings
from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError, UnauthorizedError
from quantagent.api.services import plugin_registry as plugin_registry_service
from quantagent.core.registry import PluginRecord, PluginRegistry, PluginStatus
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import NotificationReceiveResult, PluginRuntimeError
from quantagent.plugin_sdk.io import to_json_value


class DiscordReceiveResult(Protocol):
    accepted: bool
    code: str
    message: str
    response: Mapping[str, Any] | None
    item: object | None


@dataclass(frozen=True)
class DiscordInteractionHttpResult:
    status_code: int
    content: Mapping[str, Any]


class DiscordInteractionIngressService:
    """API 私有编排层：只连接 HTTP 配置、Registry 和 runtime invoke，不托管插件生命周期。"""

    def __init__(self, *, settings: Settings, registry: PluginRegistry, runtime: PluginRuntimeService | None = None) -> None:
        self._settings = settings
        self._registry = registry
        self._runtime = runtime or PluginRuntimeService()

    async def receive_interaction(self, *, headers: Mapping[str, str], body: bytes) -> DiscordInteractionHttpResult:
        if not self._settings.DISCORD_INTERACTIONS_ENABLED:
            raise NotFoundError("Discord interactions endpoint is not enabled")

        public_key = self._settings.DISCORD_INTERACTIONS_PUBLIC_KEY
        if not public_key:
            raise ServiceUnavailableError("Discord interactions public key is not configured")

        record = self._require_receive_plugin(self._settings.DISCORD_INTERACTIONS_PLUGIN_ID)
        invocation = await self._runtime.invoke(
            record,
            capability="notification.receive",
            request_id="discord-interactions-ingress",
            config=_build_plugin_config(self._settings, public_key=public_key),
            input={
                "headers": _discord_signature_headers(headers),
                "body": body.decode("utf-8", errors="strict"),
            },
        )
        if invocation.error is not None or invocation.result is None:
            raise ServiceUnavailableError("Configured Discord plugin could not be invoked")
        try:
            result = _validate_receive_result(
                NotificationReceiveResult.from_mapping(invocation.result.output)
            )
        except PluginRuntimeError as exc:
            # 插件 DTO 校验失败属于运行时适配边界问题，对外统一收敛为服务不可用，避免异常穿透 HTTP 层。
            raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload") from exc
        if not result.accepted:
            return _map_plugin_failure(result)

        return DiscordInteractionHttpResult(status_code=200, content=_validated_response_content(result))

    def _require_receive_plugin(self, plugin_id: str) -> PluginRecord:
        record = self._registry.get_plugin(plugin_id)
        if record is None:
            raise ServiceUnavailableError("Configured Discord plugin was not found")
        if record.status != PluginStatus.VALID:
            raise ServiceUnavailableError("Configured Discord plugin is not valid")
        if record.manifest is None:
            raise ServiceUnavailableError("Configured Discord plugin is not valid")
        if "notification.receive" not in record.manifest.capabilities:
            raise ServiceUnavailableError("Configured Discord plugin does not expose notification.receive capability")
        return record


def get_discord_interaction_ingress_service(request: Request) -> DiscordInteractionIngressService:
    service = getattr(request.app.state, "discord_interaction_ingress_service", None)
    if service is None:
        service = DiscordInteractionIngressService(
            settings=request.app.state.settings,
            registry=plugin_registry_service.get_plugin_registry(request),
            runtime=PluginRuntimeService(),
        )
        request.app.state.discord_interaction_ingress_service = service
    return service


def _build_plugin_config(settings: Settings, *, public_key: str) -> dict[str, object]:
    return {
        "public_key": public_key,
        "response_text": settings.DISCORD_INTERACTIONS_RESPONSE_TEXT,
        "timestamp_tolerance_seconds": settings.DISCORD_INTERACTIONS_TIMESTAMP_TOLERANCE_SECONDS,
        "guild_allowlist": list(settings.DISCORD_INTERACTIONS_GUILD_ALLOWLIST),
        "channel_allowlist": list(settings.DISCORD_INTERACTIONS_CHANNEL_ALLOWLIST),
    }


def _discord_signature_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        "X-Signature-Ed25519": headers.get("X-Signature-Ed25519", ""),
        "X-Signature-Timestamp": headers.get("X-Signature-Timestamp", ""),
    }


def _map_plugin_failure(result: DiscordReceiveResult) -> DiscordInteractionHttpResult:
    if result.code in {"SIGNATURE_MISSING", "SIGNATURE_INVALID", "TIMESTAMP_INVALID"}:
        raise UnauthorizedError("Discord signature validation failed")
    if result.code == "UNSUPPORTED_EVENT_TYPE":
        return DiscordInteractionHttpResult(
            status_code=400,
            content={"error": result.code, "message": result.message},
        )
    raise BadRequestError(result.message, details={"code": result.code})


def _validate_receive_result(result: object) -> DiscordReceiveResult:
    if not isinstance(getattr(result, "accepted", None), bool):
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    if not isinstance(getattr(result, "code", None), str) or not getattr(result, "code").strip():
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    if not isinstance(getattr(result, "message", None), str) or not getattr(result, "message").strip():
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")

    response = getattr(result, "response", None)
    if response is not None and not isinstance(response, Mapping):
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    if getattr(result, "accepted") and response is None:
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    item = getattr(result, "item", None)
    # PING 只需要返回 Discord 协议响应；真正进入业务链路的 interaction 才要求 dto。
    if getattr(result, "accepted") and getattr(result, "code") != "PING" and item is None:
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    return result  # type: ignore[return-value]


def _validated_response_content(result: DiscordReceiveResult) -> Mapping[str, Any]:
    response = result.response
    if response is None:
        raise ServiceUnavailableError("Configured Discord plugin returned an invalid result payload")
    return to_json_value(response)
