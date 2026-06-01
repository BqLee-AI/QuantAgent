from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quantagent.core.registry.models import PluginRecord, PluginScanSummary, PluginStatus
from quantagent.core.registry.scanner import RegistryScanner


class PluginRegistry:
    def __init__(self, scanner: RegistryScanner) -> None:
        self.scanner = scanner
        self._records: list[PluginRecord] | None = None
        self._records_by_id: dict[str, PluginRecord] = {}

    def list_plugins(self) -> list[PluginRecord]:
        if self._records is None:
            self.rescan()
        return list(self._records or [])

    def get_plugin(self, plugin_id: str) -> PluginRecord | None:
        self.list_plugins()
        return self._records_by_id.get(plugin_id)

    def read_config_schema(self, plugin_id: str) -> dict[str, Any] | None:
        record = self.get_plugin(plugin_id)
        if record is None or record.status != PluginStatus.VALID or record.config_schema_path is None:
            return None
        try:
            with record.config_schema_path.open("r", encoding="utf-8") as schema_file:
                schema_data = json.load(schema_file)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return schema_data if isinstance(schema_data, dict) else None

    def rescan(self) -> PluginScanSummary:
        self._records = self.scanner.scan()
        self._records_by_id = {}
        for record in self._records:
            self._records_by_id.setdefault(record.id, record)
        return summarize_plugin_records(self._records)


def build_plugin_registry(
    *,
    official_root: Path | str = Path("plugins"),
    runtime_root: Path | str = Path("runtime/plugins"),
) -> PluginRegistry:
    return PluginRegistry(
        RegistryScanner(
            official_root=official_root,
            runtime_root=runtime_root,
        )
    )


def summarize_plugin_records(records: list[PluginRecord]) -> PluginScanSummary:
    status_counts = Counter(record.status for record in records)
    source_counts = Counter(record.source.value for record in records)
    return PluginScanSummary(
        total=len(records),
        valid=status_counts[PluginStatus.VALID],
        invalid=status_counts[PluginStatus.INVALID],
        failed=status_counts[PluginStatus.FAILED],
        sources=dict(sorted(source_counts.items())),
    )
