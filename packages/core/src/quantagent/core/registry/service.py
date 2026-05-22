from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quantagent.core.registry.models import PluginRecord, PluginScanSummary, PluginStatus
from quantagent.core.registry.scanner import RegistryScanner


class PluginRegistry:
    """Registry V1 query facade over manifest scanning results."""

    def __init__(self, scanner: RegistryScanner) -> None:
        self.scanner = scanner
        self._records: list[PluginRecord] | None = None
        self._records_by_id: dict[str, PluginRecord] = {}

    def list_plugins(self) -> list[PluginRecord]:
        """返回当前 Registry 视图，首次调用时自动扫描。"""
        if self._records is None:
            # 首次读取时惰性扫描，避免 import API/app 时就访问文件系统。
            self.rescan()
        return list(self._records or [])

    def get_plugin(self, plugin_id: str) -> PluginRecord | None:
        """按插件 ID 查询单条记录，找不到时返回 None 交给 API 映射错误。"""
        self.list_plugins()
        return self._records_by_id.get(plugin_id)

    def read_config_schema(self, plugin_id: str) -> dict[str, Any] | None:
        """读取插件声明的 JSON Schema；插件非法或 schema 不可用时返回 None。"""
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
        """刷新 Registry 视图，并返回本次扫描摘要。"""
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
    """按官方插件目录和 runtime 插件目录创建默认 Registry。"""
    return PluginRegistry(
        RegistryScanner(
            official_root=official_root,
            runtime_root=runtime_root,
        )
    )


def summarize_plugin_records(records: list[PluginRecord]) -> PluginScanSummary:
    """把扫描记录聚合成 API rescan 可返回的简短摘要。"""
    status_counts = Counter(record.status for record in records)
    source_counts = Counter(record.source.value for record in records)
    return PluginScanSummary(
        total=len(records),
        valid=status_counts[PluginStatus.VALID],
        invalid=status_counts[PluginStatus.INVALID],
        failed=status_counts[PluginStatus.FAILED],
        sources=dict(sorted(source_counts.items())),
    )
