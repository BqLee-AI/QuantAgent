from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from quantagent.core.notifications.models import NotificationReceiveFact


class NotificationReceiveFactRepository(Protocol):
    def create(self, fact: NotificationReceiveFact) -> NotificationReceiveFact: ...

    def get(self, fact_id: str) -> NotificationReceiveFact | None: ...

    def list(self, *, plugin_id: str | None = None) -> Sequence[NotificationReceiveFact]: ...


class InMemoryNotificationReceiveFactRepository:
    def __init__(self) -> None:
        self._facts_by_id: dict[str, NotificationReceiveFact] = {}
        self._ordered_fact_ids: list[str] = []

    def create(self, fact: NotificationReceiveFact) -> NotificationReceiveFact:
        if fact.fact_id in self._facts_by_id:
            raise ValueError(f"Notification receive fact already exists: {fact.fact_id}")
        self._facts_by_id[fact.fact_id] = fact
        self._ordered_fact_ids.append(fact.fact_id)
        return fact

    def get(self, fact_id: str) -> NotificationReceiveFact | None:
        return self._facts_by_id.get(fact_id)

    def list(self, *, plugin_id: str | None = None) -> Sequence[NotificationReceiveFact]:
        facts = [self._facts_by_id[fact_id] for fact_id in self._ordered_fact_ids]
        if plugin_id is None:
            return facts
        return [fact for fact in facts if fact.plugin_id == plugin_id]
