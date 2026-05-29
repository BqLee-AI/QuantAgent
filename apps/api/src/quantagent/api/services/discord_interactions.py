from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from fastapi import Request

from quantagent.api.config.settings import Settings
from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError, UnauthorizedError
from quantagent.api.services import plugin_registry as plugin_registry_service
from quantagent.core.plugins import PluginEntrypointLoadError, load_plugin_entrypoint
from quantagent.core.registry import (
    PluginRegistry,
    PluginStatus,
    PluginType,
)


class DiscordSourcePlugin(Protocol):
    def receive_request(
        self,
        config: Mapping[str, Any],
        headers: Mapping[str, str],
        body: bytes,
    ) -> object: ...


class DiscordReceiveResult(Protocol):
    ok: bool
    code: str
    message: str
    response: Mapping[str, Any] | None


@dataclass(frozen=True)
class DiscordInteractionHttpResult:
    status_code: int
    content: Mapping[str, Any]


class DiscordInteractionIngressService:
    """API 私有编排层：只连接 HTTP 配置、Registry 和插件 entrypoint，不托管插件生命周期。"""

    def __init__(self, *, settings: Settings, registry: PluginRegistry) -> None:
        self._settings = settings
        self._registry = registry

    def receive_interaction(self, *, headers: Mapping[str, str], body: bytes) -> DiscordInteractionHttpResult:
        if not self._settings.DISCORD_INTERACTIONS_ENABLED:
            raise NotFoundError("Discord interactions endpoint is not enabled")

        public_key = self._settings.DISCORD_INTERACTIONS_PUBLIC_KEY
        if not public_key:
            raise ServiceUnavailableError("Discord interactions public key is not configured")

        plugin = self._load_source_plugin(self._settings.DISCORD_INTERACTIONS_PLUGIN_ID)
        result = _validate_receive_result(
            plugin.receive_request(
                _build_plugin_config(self._settings, public_key=public_key),
                _discord_signature_headers(headers),
                body,
            )
        )
        if not result.ok:
            return _map_plugin_failure(result)

        return DiscordInteractionHttpResult(status_code=200, content=_validated_response_content(result))

    def _load_source_plugin(self, plugin_id: str) -> DiscordSourcePlugin:
        record = self._registry.get_plugin(plugin_id)
        if record is None:
            raise ServiceUnavailableError("Configured Discord source plugin was not found")
        if record.status != PluginStatus.VALID:
            raise ServiceUnavailableError("Configured Discord source plugin is not valid")
        if record.manifest is None or record.manifest.type != PluginType.SOURCE:
            raise ServiceUnavailableError("Configured Discord plugin must be a valid source plugin")
        try:
            plugin = load_plugin_entrypoint(record)
        except PluginEntrypointLoadError as exc:
            raise ServiceUnavailableError("Configured Discord source plugin could not be loaded") from exc
        return _validate_source_plugin(plugin)


def get_discord_interaction_ingress_service(request: Request) -> DiscordInteractionIngressService:
    return DiscordInteractionIngressService(
        settings=request.app.state.settings,
        registry=plugin_registry_service.get_plugin_registry(request),
    )


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


def _validate_source_plugin(plugin: object) -> DiscordSourcePlugin:
    receive_request = getattr(plugin, "receive_request", None)
    if not callable(receive_request):
        raise ServiceUnavailableError("Configured Discord source plugin does not expose a receive_request handler")
    return plugin  # type: ignore[return-value]


def _validate_receive_result(result: object) -> DiscordReceiveResult:
    if not isinstance(getattr(result, "ok", None), bool):
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")
    if not isinstance(getattr(result, "code", None), str) or not getattr(result, "code").strip():
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")
    if not isinstance(getattr(result, "message", None), str) or not getattr(result, "message").strip():
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")

    response = getattr(result, "response", None)
    if response is not None and not isinstance(response, Mapping):
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")
    if getattr(result, "ok") and response is None:
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")
    return result  # type: ignore[return-value]


def _validated_response_content(result: DiscordReceiveResult) -> Mapping[str, Any]:
    response = result.response
    if response is None:
        raise ServiceUnavailableError("Configured Discord source plugin returned an invalid result payload")
    return response
