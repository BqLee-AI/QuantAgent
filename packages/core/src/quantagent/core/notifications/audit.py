from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from quantagent.core.notifications.models import NotificationIngressAuditEntry


class NotificationIngressAuditSink(Protocol):
    def append(self, entry: NotificationIngressAuditEntry) -> NotificationIngressAuditEntry: ...

    def list(self) -> Sequence[NotificationIngressAuditEntry]: ...


class InMemoryNotificationIngressAuditSink:
    def __init__(self) -> None:
        self._entries: list[NotificationIngressAuditEntry] = []

    def append(self, entry: NotificationIngressAuditEntry) -> NotificationIngressAuditEntry:
        self._entries.append(entry)
        return entry

    def list(self) -> Sequence[NotificationIngressAuditEntry]:
        return tuple(self._entries)
