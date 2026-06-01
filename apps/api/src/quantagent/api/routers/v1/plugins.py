from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request

from quantagent.api.auth import CurrentActor, require_csrf
from quantagent.api.http.errors import BadRequestError, NotFoundError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.plugins import (
    PluginErrorResponse,
    PluginManifestResponse,
    PluginRecordResponse,
    PluginRescanResponse,
    PluginScanSummaryResponse,
    SourceBindingManifestResponse,
)
from quantagent.api.services.plugin_registry import find_repo_root, get_plugin_registry
from quantagent.core.registry import (
    PluginError,
    PluginManifest,
    PluginRecord,
    PluginRegistry,
    PluginScanSummary,
)


router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=ApiResponse[list[PluginRecordResponse]])
def list_plugins(request: Request) -> ApiResponse[list[PluginRecordResponse]]:
    """返回当前 Registry 视图中的插件列表。"""
    registry = get_plugin_registry(request)
    records = registry.list_plugins()
    return ApiResponse.success([_record_response(record) for record in records])


@router.get("/{plugin_id}", response_model=ApiResponse[PluginRecordResponse])
def get_plugin(plugin_id: str, request: Request) -> ApiResponse[PluginRecordResponse]:
    """按插件 ID 返回单条插件记录。"""
    record = _require_plugin(get_plugin_registry(request), plugin_id)
    return ApiResponse.success(_record_response(record))


@router.get("/{plugin_id}/config-schema", response_model=ApiResponse[dict[str, Any]])
def get_plugin_config_schema(plugin_id: str, request: Request) -> ApiResponse[dict[str, Any]]:
    """返回插件 manifest 引用的配置 JSON Schema。"""
    registry = get_plugin_registry(request)
    record = _require_plugin(registry, plugin_id)
    if record.config_schema_path is None:
        raise BadRequestError(
            "Plugin config schema is not available",
            details={"plugin": _record_error_details(record)},
        )

    schema = registry.read_config_schema(plugin_id)
    if schema is None:
        raise BadRequestError(
            "Plugin config schema is not available",
            details={"plugin": _record_error_details(record)},
        )
    return ApiResponse.success(schema)


@router.post("/actions/rescan", response_model=ApiResponse[PluginRescanResponse])
def rescan_plugins(
    request: Request,
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[PluginRescanResponse]:
    """重新扫描插件目录；作为写动作，需要登录态和 CSRF。"""
    registry = get_plugin_registry(request)
    summary = registry.rescan()
    records = registry.list_plugins()
    return ApiResponse.success(
        PluginRescanResponse(
            summary=_summary_response(summary),
            plugins=[_record_response(record) for record in records],
        )
    )


def _require_plugin(registry: PluginRegistry, plugin_id: str) -> PluginRecord:
    """查询插件并把 core 的 None 结果映射成 API 层 404。"""
    record = registry.get_plugin(plugin_id)
    if record is None:
        raise NotFoundError("Plugin not found", details={"plugin_id": plugin_id})
    return record


def _record_response(record: PluginRecord) -> PluginRecordResponse:
    """把 core PluginRecord 转成 API 响应 DTO。"""
    # API DTO 是传输层契约，避免把 core dataclass 或本地绝对路径直接暴露出去。
    return PluginRecordResponse(
        id=record.id,
        source=record.source.value,
        path=_display_path(record.path),
        status=record.status.value,
        manifest=_manifest_response(record.manifest) if record.manifest is not None else None,
        last_error=_error_response(record.last_error) if record.last_error is not None else None,
    )


def _manifest_response(manifest: PluginManifest) -> PluginManifestResponse:
    return PluginManifestResponse(
        id=manifest.id,
        name=manifest.name,
        type=manifest.type.value,
        version=manifest.version,
        entrypoint=manifest.entrypoint,
        capabilities=list(manifest.capabilities),
        config_schema=manifest.config_schema,
        description=manifest.description,
        permissions=list(manifest.permissions),
        dependencies=dict(manifest.dependencies),
        source_bindings=[
            SourceBindingManifestResponse(
                source_plugin_id=item.source_plugin_id,
                required=item.required,
                config_template=item.config_template,
            )
            for item in manifest.source_bindings
        ],
    )


def _error_response(error: PluginError) -> PluginErrorResponse:
    return PluginErrorResponse(
        code=error.code,
        message=error.message,
        stage=error.stage,
        details=dict(error.details),
        retryable=error.retryable,
    )


def _summary_response(summary: PluginScanSummary) -> PluginScanSummaryResponse:
    return PluginScanSummaryResponse(
        total=summary.total,
        valid=summary.valid,
        invalid=summary.invalid,
        failed=summary.failed,
        sources=dict(summary.sources),
    )


def _record_error_details(record: PluginRecord) -> dict[str, Any]:
    details: dict[str, Any] = {
        "id": record.id,
        "status": record.status.value,
    }
    if record.last_error is not None:
        details["last_error"] = {
            "code": record.last_error.code,
            "stage": record.last_error.stage,
            "retryable": record.last_error.retryable,
        }
    return details


def _display_path(path: Path) -> str:
    repo_root = find_repo_root()
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except (OSError, RuntimeError, ValueError):
        return path.name
