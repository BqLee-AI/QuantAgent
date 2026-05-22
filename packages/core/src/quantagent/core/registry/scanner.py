from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from quantagent.core.registry.models import (
    PluginError,
    PluginManifest,
    PluginRecord,
    PluginSource,
    PluginStatus,
    PluginType,
)


REQUIRED_MANIFEST_FIELDS = frozenset(
    {
        "id",
        "name",
        "type",
        "version",
        "entrypoint",
        "capabilities",
        "config_schema",
    }
)

PLUGIN_TYPE_ALIASES = {
    "executor": PluginType.TRADE_EXECUTOR,
}


class RegistryScanner:
    """Scan plugin manifests without importing or executing plugin entrypoints."""

    def __init__(
        self,
        *,
        official_root: Path | str = Path("plugins"),
        runtime_root: Path | str = Path("runtime/plugins"),
    ) -> None:
        self.official_root = Path(official_root)
        self.runtime_root = Path(runtime_root)

    def scan(self) -> list[PluginRecord]:
        """扫描所有插件来源，并在最后统一检查跨来源重复 ID。"""
        # V1 只建立登记视图：官方插件和 runtime 插件走同一套 manifest 校验。
        records = [
            *self._scan_root(self.official_root, PluginSource.OFFICIAL),
            *self._scan_root(self.runtime_root, PluginSource.RUNTIME),
        ]
        return self._mark_duplicate_ids(records)

    def _scan_root(self, root: Path, source: PluginSource) -> list[PluginRecord]:
        """扫描单个插件根目录，返回该来源下所有 manifest 的记录。"""
        if not root.exists():
            # runtime/plugins 在本地新环境里经常不存在；缺失目录等价于空来源。
            return []
        if not root.is_dir():
            return [
                self._error_record(
                    source=source,
                    plugin_dir=root,
                    code="PLUGIN_ROOT_NOT_DIRECTORY",
                    message="Plugin root is not a directory.",
                    stage="discover",
                )
            ]

        records: list[PluginRecord] = []
        for manifest_path in sorted(root.rglob("plugin.yaml")):
            records.append(self._load_manifest(manifest_path, source))
        return records

    def _load_manifest(self, manifest_path: Path, source: PluginSource) -> PluginRecord:
        """读取并校验一个 plugin.yaml，始终返回一条可诊断记录。"""
        plugin_dir = manifest_path.parent
        try:
            with manifest_path.open("r", encoding="utf-8") as manifest_file:
                manifest_data = yaml.safe_load(manifest_file)
        except yaml.YAMLError as exc:
            # 单个坏 manifest 不应让整个 Registry 查询 500，错误落在对应记录上。
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_YAML_INVALID",
                message="Plugin manifest is not valid YAML.",
                stage="parse",
                details={"error": exc.__class__.__name__},
            )
        except OSError as exc:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_READ_FAILED",
                message="Plugin manifest could not be read.",
                stage="read",
                details={"error": exc.__class__.__name__},
                status=PluginStatus.FAILED,
            )

        if not isinstance(manifest_data, dict):
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_INVALID",
                message="Plugin manifest must be a mapping.",
                stage="validate",
            )

        manifest_id = _optional_string(manifest_data.get("id"))
        missing_fields = sorted(field for field in REQUIRED_MANIFEST_FIELDS if not _has_value(manifest_data.get(field)))
        if missing_fields:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_MANIFEST_REQUIRED_FIELD_MISSING",
                message="Plugin manifest is missing required fields.",
                stage="validate",
                details={"fields": missing_fields},
            )

        raw_type = _optional_string(manifest_data.get("type"))
        plugin_type = _normalize_plugin_type(raw_type)
        if plugin_type is None:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_TYPE_UNKNOWN",
                message="Plugin type is not supported by Registry V1.",
                stage="validate",
                details={
                    "type": raw_type,
                    "supported_types": [item.value for item in PluginType],
                },
            )

        capabilities = manifest_data.get("capabilities")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(isinstance(item, str) and item.strip() for item in capabilities)
        ):
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_CAPABILITIES_INVALID",
                message="Plugin capabilities must be a non-empty list of strings.",
                stage="validate",
            )

        config_schema = _optional_string(manifest_data.get("config_schema"))
        config_schema_path = _resolve_inside_plugin_dir(plugin_dir, config_schema)
        if config_schema_path is None:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_CONFIG_SCHEMA_OUTSIDE_PLUGIN",
                message="Plugin config schema must be inside the plugin directory.",
                stage="validate",
            )
        if not config_schema_path.is_file():
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_CONFIG_SCHEMA_NOT_FOUND",
                message="Plugin config schema file does not exist.",
                stage="validate",
                details={"config_schema": config_schema},
            )

        manifest = PluginManifest(
            id=str(manifest_id),
            name=str(_optional_string(manifest_data.get("name"))),
            type=plugin_type,
            version=str(_optional_string(manifest_data.get("version"))),
            entrypoint=str(_optional_string(manifest_data.get("entrypoint"))),
            capabilities=tuple(item.strip() for item in capabilities),
            config_schema=str(config_schema),
            description=_optional_string(manifest_data.get("description")),
            permissions=_string_tuple(manifest_data.get("permissions")),
            dependencies=manifest_data.get("dependencies") if isinstance(manifest_data.get("dependencies"), dict) else {},
        )
        return PluginRecord(
            id=manifest.id,
            source=source,
            path=plugin_dir,
            status=PluginStatus.VALID,
            manifest=manifest,
            config_schema_path=config_schema_path,
        )

    def _mark_duplicate_ids(self, records: Iterable[PluginRecord]) -> list[PluginRecord]:
        """把重复 plugin id 的合法记录降级为 invalid，V1 不做版本选择。"""
        record_list = list(records)
        by_id: dict[str, list[PluginRecord]] = defaultdict(list)
        for record in record_list:
            if record.manifest is not None:
                by_id[record.manifest.id].append(record)

        duplicate_ids = {plugin_id for plugin_id, items in by_id.items() if len(items) > 1}
        if not duplicate_ids:
            return record_list

        marked: list[PluginRecord] = []
        for record in record_list:
            if record.manifest is None or record.manifest.id not in duplicate_ids:
                marked.append(record)
                continue
            marked.append(
                PluginRecord(
                    id=record.id,
                    source=record.source,
                    path=record.path,
                    status=PluginStatus.INVALID,
                    manifest=record.manifest,
                    config_schema_path=record.config_schema_path,
                    last_error=PluginError(
                        code="PLUGIN_ID_DUPLICATE",
                        message="Plugin id is declared by multiple manifests.",
                        stage="validate",
                        details={"plugin_id": record.manifest.id},
                    ),
                )
            )
        return marked

    def _error_record(
        self,
        *,
        source: PluginSource,
        plugin_dir: Path,
        code: str,
        message: str,
        stage: str,
        plugin_id: str | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        status: PluginStatus = PluginStatus.INVALID,
    ) -> PluginRecord:
        """构造脱敏错误记录，避免把底层异常或本机路径细节直接外泄。"""
        return PluginRecord(
            id=plugin_id or _synthetic_plugin_id(source, plugin_dir),
            source=source,
            path=plugin_dir,
            status=status,
            last_error=PluginError(
                code=code,
                message=message,
                stage=stage,
                details=details or {},
                retryable=retryable,
            ),
        )


def _normalize_plugin_type(raw_type: str | None) -> PluginType | None:
    """将 manifest 中的 type 转成 canonical PluginType。"""
    if raw_type is None:
        return None
    normalized = raw_type.strip()
    if normalized in PLUGIN_TYPE_ALIASES:
        return PLUGIN_TYPE_ALIASES[normalized]
    try:
        return PluginType(normalized)
    except ValueError:
        return None


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and not value:
        return False
    return True


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _resolve_inside_plugin_dir(plugin_dir: Path, configured_path: str | None) -> Path | None:
    """解析 config_schema 路径，并拒绝指向插件目录外的文件。"""
    if configured_path is None:
        return None
    candidate = Path(configured_path)
    if candidate.is_absolute():
        return None
    resolved_plugin_dir = plugin_dir.resolve()
    resolved_schema_path = (plugin_dir / candidate).resolve()
    try:
        # 防止 manifest 通过 ../ 引用插件目录外的本地文件或 secret。
        resolved_schema_path.relative_to(resolved_plugin_dir)
    except ValueError:
        return None
    return resolved_schema_path


def _synthetic_plugin_id(source: PluginSource, plugin_dir: Path) -> str:
    safe_name = "-".join(part for part in plugin_dir.parts[-3:] if part)
    return f"invalid:{source.value}:{safe_name or 'plugin'}"
