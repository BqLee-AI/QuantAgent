from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from quantagent.core.event_read_model.models import (
    EventDashboardSnapshot,
    EventDetailView,
    EventListPage,
    EventListQuery,
    EventRecord,
    EventSummaryBuckets,
    EventTimeRange,
)
from quantagent.core.event_read_model.repository import EventReadModelRepository


class EventReadModelNotFoundError(Exception):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Event not found: {event_id}")
        self.event_id = event_id


@dataclass
class EventReadModelService:
    repository: EventReadModelRepository
    now_factory: Callable[[], datetime] = lambda: datetime.now(UTC)

    def list_events(self, query: EventListQuery) -> EventListPage:
        normalized = self._normalize_query(query)
        return self.repository.list_events(normalized)

    def get_event_detail(self, event_id: str) -> EventDetailView:
        detail = self.repository.get_event_detail(event_id)
        if detail is None:
            raise EventReadModelNotFoundError(event_id)
        return detail

    def get_dashboard_snapshot(
        self,
        *,
        featured_limit: int = 5,
        time_range: EventTimeRange = EventTimeRange.LAST_24H,
    ) -> EventDashboardSnapshot:
        query = self._normalize_query(EventListQuery(time_range=time_range, limit=20))
        featured_events = self.repository.list_featured_events(limit=featured_limit)
        metrics = self.repository.get_summary_buckets(query)
        return EventDashboardSnapshot(
            featured_events=featured_events,
            entry_metrics=metrics,
            generated_at=self.now_factory(),
        )

    def _normalize_query(self, query: EventListQuery) -> EventListQuery:
        captured_from = query.captured_from or query.time_range.resolve_start(now=self.now_factory())
        return EventListQuery(
            time_range=query.time_range,
            industries=query.industries,
            credibility=query.credibility,
            analysis_status=query.analysis_status,
            source_type=query.source_type,
            sort=query.sort,
            cursor=query.cursor,
            limit=query.limit,
            captured_from=captured_from,
        )
