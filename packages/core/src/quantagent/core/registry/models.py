from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PluginType(StrEnum):
    SOURCE = "source"
    INDUSTRY = "industry"
    STRATEGY = "strategy"
    NOTIFICATION = "notification"
    TRADE_EXECUTOR = "trade_executor"


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
    dependencies: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginError:
    code: str
    message: str
    stage: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False


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
    sources: dict[str, int]
