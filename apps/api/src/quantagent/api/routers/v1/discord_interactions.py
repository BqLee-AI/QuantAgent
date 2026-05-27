from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError, UnauthorizedError
from quantagent.core.plugins import PluginEntrypointLoadError, load_plugin_entrypoint
from quantagent.core.registry import (
    PluginRegistry,
    PluginStatus,
    build_plugin_registry,
)


router = APIRouter(prefix="/integrations/discord", tags=["integrations"])


@router.post("/interactions")
async def receive_discord_interaction(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    if not settings.DISCORD_INTERACTIONS_ENABLED:
        raise NotFoundError("Discord interactions endpoint is not enabled")

    public_key = settings.DISCORD_INTERACTIONS_PUBLIC_KEY
    if not public_key:
        raise ServiceUnavailableError("Discord interactions public key is not configured")

    body = await request.body()
    headers = {
        "X-Signature-Ed25519": request.headers.get("X-Signature-Ed25519", ""),
        "X-Signature-Timestamp": request.headers.get("X-Signature-Timestamp", ""),
    }
    plugin = _load_source_plugin(request, settings.DISCORD_INTERACTIONS_PLUGIN_ID)
    config = {
        "public_key": public_key,
        "response_text": settings.DISCORD_INTERACTIONS_RESPONSE_TEXT,
    }

    result = plugin.receive_request(config, headers, body)
    if not result.ok:
        if result.code in {"SIGNATURE_MISSING", "SIGNATURE_INVALID", "TIMESTAMP_INVALID"}:
            raise UnauthorizedError("Discord signature validation failed")
        if result.code == "UNSUPPORTED_EVENT_TYPE":
            return JSONResponse(status_code=400, content={"error": result.code, "message": result.message})
        raise BadRequestError(result.message, details={"code": result.code})

    return JSONResponse(status_code=200, content=result.response)


def _load_source_plugin(request: Request, plugin_id: str) -> object:
    registry = _get_plugin_registry(request)
    record = registry.get_plugin(plugin_id)
    if record is None:
        raise ServiceUnavailableError("Configured Discord source plugin was not found")
    if record.status != PluginStatus.VALID:
        raise ServiceUnavailableError("Configured Discord source plugin is not valid")
    try:
        return load_plugin_entrypoint(record)
    except PluginEntrypointLoadError as exc:
        raise ServiceUnavailableError("Configured Discord source plugin could not be loaded") from exc


def _get_plugin_registry(request: Request) -> PluginRegistry:
    registry = getattr(request.app.state, "plugin_registry", None)
    if registry is None:
        settings = request.app.state.settings
        repo_root = _find_repo_root()
        runtime_dir = Path(settings.RUNTIME_DIR)
        if not runtime_dir.is_absolute():
            runtime_dir = repo_root / runtime_dir
        registry = build_plugin_registry(
            official_root=repo_root / "plugins",
            runtime_root=runtime_dir / "plugins",
        )
        request.app.state.plugin_registry = registry
    return registry


@lru_cache(maxsize=1)
def _find_repo_root() -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "plugins").exists() or (candidate / "runtime").exists():
            return candidate
    return Path.cwd()
