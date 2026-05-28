from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from quantagent.core.scheduling.models import PluginRunRecord


class PluginRunRepository(Protocol):
    def create(self, record: PluginRunRecord) -> PluginRunRecord: ...

    def update(self, record: PluginRunRecord) -> PluginRunRecord: ...

    def get(self, run_id: str) -> PluginRunRecord | None: ...

    def list(self, *, plugin_id: str | None = None) -> Sequence[PluginRunRecord]: ...


class InMemoryPluginRunRepository:
    def __init__(self) -> None:
        self._records_by_id: dict[str, PluginRunRecord] = {}
        self._ordered_run_ids: list[str] = []
        self._history: dict[str, list[PluginRunRecord]] = {}

    def create(self, record: PluginRunRecord) -> PluginRunRecord:
        if record.run_id in self._records_by_id:
            raise ValueError(f"Run record already exists: {record.run_id}")
        self._records_by_id[record.run_id] = record
        self._ordered_run_ids.append(record.run_id)
        self._history[record.run_id] = [record]
        return record

    def update(self, record: PluginRunRecord) -> PluginRunRecord:
        if record.run_id not in self._records_by_id:
            raise ValueError(f"Unknown run record: {record.run_id}")
        self._records_by_id[record.run_id] = record
        self._history.setdefault(record.run_id, []).append(record)
        return record

    def get(self, run_id: str) -> PluginRunRecord | None:
        return self._records_by_id.get(run_id)

    def list(self, *, plugin_id: str | None = None) -> Sequence[PluginRunRecord]:
        records = [self._records_by_id[run_id] for run_id in self._ordered_run_ids]
        if plugin_id is None:
            return records
        return [record for record in records if record.plugin_id == plugin_id]

    def get_history(self, run_id: str) -> Sequence[PluginRunRecord]:
        return tuple(self._history.get(run_id, ()))
