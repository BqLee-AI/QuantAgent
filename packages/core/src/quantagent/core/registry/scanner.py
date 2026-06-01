from __future__ import annotations

import hashlib
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
REQUIRED_STRING_MANIFEST_FIELDS = frozenset(
    {
        "id",
        "name",
        "type",
        "version",
        "entrypoint",
        "config_schema",
    }
)

PLUGIN_TYPE_ALIASES = {
    "executor": PluginType.BROKER,
    "trade_executor": PluginType.BROKER,
}


class RegistryScanner:
    def __init__(
        self,
        *,
        official_root: Path | str = Path("plugins"),
        runtime_root: Path | str = Path("runtime/plugins"),
    ) -> None:
        self.official_root = Path(official_root)
        self.runtime_root = Path(runtime_root)

    def scan(self) -> list[PluginRecord]:
        records = [
            *self._scan_root(self.official_root, PluginSource.OFFICIAL),
            *self._scan_root(self.runtime_root, PluginSource.RUNTIME),
        ]
        return self._mark_duplicate_ids(records)

    def _scan_root(self, root: Path, source: PluginSource) -> list[PluginRecord]:
        if not root.exists():
            return []
        if not root.is_dir():
            return [
                self._error_record(
                    source=source,
                    plugin_dir=root,
                    code="PLUGIN_ROOT_NOT_DIRECTORY",
                    message="Plugin root is not a directory.",
                    stage="discover",
                    root=root,
                )
            ]

        records: list[PluginRecord] = []
        for manifest_path in sorted(root.rglob("plugin.yaml")):
            if not _is_path_inside_root(manifest_path, root):
                records.append(
                    self._error_record(
                        source=source,
                        plugin_dir=manifest_path.parent,
                        code="PLUGIN_MANIFEST_OUTSIDE_ROOT",
                        message="Plugin manifest must resolve inside the configured plugin root.",
                        stage="discover",
                        root=root,
                    )
                )
                continue
            records.append(self._load_manifest(manifest_path, source, root))
        return records

    def _load_manifest(self, manifest_path: Path, source: PluginSource, root: Path) -> PluginRecord:
        plugin_dir = manifest_path.parent
        try:
            with manifest_path.open("r", encoding="utf-8") as manifest_file:
                manifest_data = yaml.safe_load(manifest_file)
        except yaml.YAMLError as exc:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_YAML_INVALID",
                message="Plugin manifest is not valid YAML.",
                stage="parse",
                details={"error": exc.__class__.__name__},
                root=root,
            )
        except (OSError, UnicodeError) as exc:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_READ_FAILED",
                message="Plugin manifest could not be read.",
                stage="read",
                details={"error": exc.__class__.__name__},
                status=PluginStatus.FAILED,
                root=root,
            )

        if not isinstance(manifest_data, dict):
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                code="PLUGIN_MANIFEST_INVALID",
                message="Plugin manifest must be a mapping.",
                stage="validate",
                root=root,
            )

        manifest_id = _optional_string(manifest_data.get("id"))
        missing_fields = _missing_required_fields(manifest_data)
        if missing_fields:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_MANIFEST_REQUIRED_FIELD_MISSING",
                message="Plugin manifest is missing required fields.",
                stage="validate",
                details={"fields": missing_fields},
                root=root,
            )

        invalid_string_fields = _invalid_required_string_fields(manifest_data)
        if invalid_string_fields:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_MANIFEST_FIELD_INVALID",
                message="Plugin manifest required string fields must be non-empty strings.",
                stage="validate",
                details={"fields": invalid_string_fields},
                root=root,
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
                root=root,
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
                root=root,
            )

        plugin_id = _required_string(manifest_data, "id")
        name = _required_string(manifest_data, "name")
        version = _required_string(manifest_data, "version")
        entrypoint = _required_string(manifest_data, "entrypoint")
        config_schema = _required_string(manifest_data, "config_schema")
        config_schema_path = _resolve_inside_plugin_dir(plugin_dir, config_schema)
        if config_schema_path is None:
            return self._error_record(
                source=source,
                plugin_dir=plugin_dir,
                plugin_id=manifest_id,
                code="PLUGIN_CONFIG_SCHEMA_OUTSIDE_PLUGIN",
                message="Plugin config schema must be inside the plugin directory.",
                stage="validate",
                root=root,
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
                root=root,
            )

        manifest = PluginManifest(
            id=plugin_id,
            name=name,
            type=plugin_type,
            version=version,
            entrypoint=entrypoint,
            capabilities=tuple(item.strip() for item in capabilities),
            config_schema=config_schema,
            description=_optional_string(manifest_data.get("description")),
            permissions=_string_tuple(manifest_data.get("permissions")),
            dependencies=manifest_data.get("dependencies") if isinstance(manifest_data.get("dependencies"), dict) else {},
        )
        return PluginRecord(
            id=manifest.id,
            source=source,
            path=plugin_dir.resolve(),
            status=PluginStatus.VALID,
            manifest=manifest,
            config_schema_path=config_schema_path.resolve(),
        )

    def _mark_duplicate_ids(self, records: Iterable[PluginRecord]) -> list[PluginRecord]:
        record_list = list(records)
        by_id: dict[str, list[PluginRecord]] = defaultdict(list)
        for record in record_list:
            if not _is_synthetic_plugin_id(record.id):
                by_id[record.id].append(record)

        duplicate_ids = {plugin_id for plugin_id, items in by_id.items() if len(items) > 1}
        if not duplicate_ids:
            return record_list

        marked: list[PluginRecord] = []
        for record in record_list:
            if record.id not in duplicate_ids:
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
                        details={"plugin_id": record.id},
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
        root: Path | None = None,
    ) -> PluginRecord:
        return PluginRecord(
            id=plugin_id or _synthetic_plugin_id(source, plugin_dir, root),
            source=source,
            path=plugin_dir.resolve(),
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


def _missing_required_fields(manifest_data: dict[str, Any]) -> list[str]:
    return sorted(field for field in REQUIRED_MANIFEST_FIELDS if not _has_value(manifest_data.get(field)))


def _invalid_required_string_fields(manifest_data: dict[str, Any]) -> list[str]:
    invalid_fields: list[str] = []
    for field in sorted(REQUIRED_STRING_MANIFEST_FIELDS):
        value = manifest_data.get(field)
        if _has_value(value) and not _optional_string(value):
            invalid_fields.append(field)
    return invalid_fields


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _required_string(manifest_data: dict[str, Any], field: str) -> str:
    value = _optional_string(manifest_data.get(field))
    if value is None:
        raise ValueError(f"validated manifest field is missing: {field}")
    return value


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _resolve_inside_plugin_dir(plugin_dir: Path, configured_path: str | None) -> Path | None:
    if configured_path is None:
        return None
    candidate = Path(configured_path)
    if candidate.is_absolute():
        return None
    try:
        resolved_plugin_dir = plugin_dir.resolve()
        resolved_schema_path = (plugin_dir / candidate).resolve()
        resolved_schema_path.relative_to(resolved_plugin_dir)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved_schema_path


def _is_path_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _is_synthetic_plugin_id(plugin_id: str) -> bool:
    return plugin_id.startswith("invalid:")


def _synthetic_plugin_id(source: PluginSource, plugin_dir: Path, root: Path | None) -> str:
    if root is not None:
        try:
            relative_path = plugin_dir.relative_to(root).as_posix()
        except ValueError:
            try:
                relative_path = plugin_dir.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, RuntimeError, ValueError):
                relative_path = plugin_dir.name
    else:
        relative_path = plugin_dir.name
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]
    return f"invalid:{source.value}:{digest}"
