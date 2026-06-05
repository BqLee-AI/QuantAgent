from __future__ import annotations

from typing import Protocol

from quantagent.core.event_read_model.models import (
    EventDashboardSnapshot,
    EventDetailView,
    EventListPage,
    EventListQuery,
    EventMaterializationInput,
    EventMaterializationResult,
    EventRecord,
    EventStateTransitionRecord,
    EventSummaryBuckets,
)


class EventReadModelRepository(Protocol):
    def materialize(self, input_data: EventMaterializationInput) -> EventMaterializationResult: ...

    def get_event(self, event_id: str) -> EventRecord | None: ...

    def get_event_detail(self, event_id: str) -> EventDetailView | None: ...

    def list_events(self, query: EventListQuery) -> EventListPage: ...

    def list_featured_events(self, *, limit: int) -> tuple[EventRecord, ...]: ...

    def get_summary_buckets(self, query: EventListQuery) -> EventSummaryBuckets: ...

    def list_state_transitions(self, event_id: str) -> tuple[EventStateTransitionRecord, ...]: ...
