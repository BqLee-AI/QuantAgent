from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from quantagent.core.db.models.sources import SourceFetchRun, SourceFetchRunStatus
from quantagent.core.db.repositories.raw_events import RawEventRepository
from quantagent.core.events.dto import StoredRawEvent
from quantagent.core.sources.protocols import PullSourcePlugin, RuntimeContext, SourceBindingConfig


@dataclass(frozen=True)
class SourceFetchResult:
    status: str
    fetched_count: int
    stored_count: int
    duplicate_count: int
    error_summary: str | None = None
    stored_events: tuple[StoredRawEvent, ...] = field(default_factory=tuple)


class SourceFetchService:
    def __init__(self, session: Session):
        self._session = session
        self._raw_events = RawEventRepository(session)

    def trigger_fetch(
        self,
        *,
        plugin: PullSourcePlugin,
        binding: SourceBindingConfig,
        cursor: str | None = None,
    ) -> SourceFetchResult:
        started_at = _utc_now()
        run = SourceFetchRun(
            source_binding_id=binding.id,
            source_plugin_id=binding.source_plugin_id,
            status=SourceFetchRunStatus.running,
            started_at=started_at,
        )
        self._session.add(run)
        self._session.flush()

        timer = perf_counter()
        plugin_started = False
        try:
            plugin.load(RuntimeContext(plugin_id=binding.source_plugin_id))
            plugin.start()
            plugin_started = True
            drafts = plugin.fetch(cursor, binding.effective_config)
            stored: list[StoredRawEvent] = []
            duplicates = 0
            for draft in drafts:
                result = self._raw_events.store_if_new(draft)
                if result.is_duplicate:
                    duplicates += 1
                elif result.event is not None:
                    stored.append(result.event)

            run.status = SourceFetchRunStatus.succeeded
            run.fetched_count = len(drafts)
            run.stored_count = len(stored)
            run.duplicate_count = duplicates
            return SourceFetchResult(
                status=run.status.value,
                fetched_count=run.fetched_count,
                stored_count=run.stored_count,
                duplicate_count=run.duplicate_count,
                stored_events=tuple(stored),
            )
        except Exception as exc:
            run.status = SourceFetchRunStatus.failed
            run.error_summary = f"{type(exc).__name__}: {exc}"
            return SourceFetchResult(
                status=run.status.value,
                fetched_count=run.fetched_count,
                stored_count=run.stored_count,
                duplicate_count=run.duplicate_count,
                error_summary=run.error_summary,
            )
        finally:
            if plugin_started:
                try:
                    plugin.stop()
                except Exception:
                    if run.status != SourceFetchRunStatus.failed:
                        run.status = SourceFetchRunStatus.failed
                        run.error_summary = "Plugin stop failed after fetch."
            run.finished_at = _utc_now()
            run.duration_ms = int((perf_counter() - timer) * 1000)
            self._session.flush()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
