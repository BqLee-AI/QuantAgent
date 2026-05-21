from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    type: str
    version: str
    entrypoint: str
    description: str | None = None
    execution_mode: str | None = None
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    config_schema: str | None = None
    path: Path | None = None


def load_plugin_manifest(path: Path) -> PluginManifest:
    manifest_path = path / "plugin.yaml" if path.is_dir() else path
    data = _parse_simple_yaml(manifest_path.read_text(encoding="utf-8"))
    required = ("id", "name", "type", "version", "entrypoint")
    missing = [field_name for field_name in required if not data.get(field_name)]
    if missing:
        raise ValueError(f"plugin manifest is missing required fields: {', '.join(missing)}")

    return PluginManifest(
        id=str(data["id"]),
        name=str(data["name"]),
        type=str(data["type"]),
        version=str(data["version"]),
        entrypoint=str(data["entrypoint"]),
        description=_optional_str(data.get("description")),
        execution_mode=_optional_str(data.get("execution_mode")),
        capabilities=tuple(str(item) for item in data.get("capabilities", [])),
        config_schema=_optional_str(data.get("config_schema")),
        path=manifest_path.parent,
    )


def discover_plugin_manifests(root: Path, *, plugin_type: str | None = None) -> list[PluginManifest]:
    manifests: list[PluginManifest] = []
    for manifest_path in sorted(root.rglob("plugin.yaml")):
        manifest = load_plugin_manifest(manifest_path)
        if plugin_type is None or manifest.type == plugin_type:
            manifests.append(manifest)
    return manifests


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is None:
                raise ValueError("list item without a key in plugin manifest")
            result.setdefault(current_list_key, []).append(stripped[2:].strip().strip('"').strip("'"))
            continue
        if ":" not in stripped:
            raise ValueError(f"unsupported plugin manifest line: {line}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            result[key] = []
            current_list_key = key
        else:
            result[key] = value.strip('"').strip("'")
            current_list_key = None
    return result

