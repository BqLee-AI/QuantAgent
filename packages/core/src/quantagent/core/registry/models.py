from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any


class PluginType(StrEnum):
    SOURCE = "source"
    INDUSTRY = "industry"
    STRATEGY = "strategy"
    NOTIFICATION = "notification"
    BROKER = "broker"


class PluginStatus(StrEnum):
    DISCOVERED = "discovered"
    VALID = "valid"
    INVALID = "invalid"
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"


class PluginSource(StrEnum):
    OFFICIAL = "official"
    RUNTIME = "runtime"


@dataclass(frozen=True)
class SourceBindingManifest:
    source_plugin_id: str
    required: bool
    config_template: str


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    type: PluginType
    version: str
    entrypoint: str
    capabilities: tuple[str, ...]
    config_schema: str
    description: str | None = None
    permissions: tuple[str, ...] = ()
    dependencies: Mapping[str, Any] = field(default_factory=dict)
    source_bindings: tuple[SourceBindingManifest, ...] = ()

    def __post_init__(self) -> None:
        # Frozen dataclasses only freeze the top-level attribute; wrap mappings so
        # callers cannot mutate cached registry records through nested dicts.
        object.__setattr__(self, "dependencies", MappingProxyType(dict(self.dependencies)))
        object.__setattr__(self, "source_bindings", tuple(self.source_bindings))


@dataclass(frozen=True)
class PluginError:
    code: str
    message: str
    stage: str
    details: Mapping[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True)
class PluginRecord:
    id: str
    source: PluginSource
    path: Path
    status: PluginStatus
    manifest: PluginManifest | None = None
    config_schema_path: Path | None = None
    last_error: PluginError | None = None


@dataclass(frozen=True)
class PluginScanSummary:
    total: int
    valid: int
    invalid: int
    failed: int
    sources: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", MappingProxyType(dict(self.sources)))
