from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from quantagent.core.notifications.models import NotificationApprovalHandoffRequest, NotificationApprovalHandoffResult


class NotificationApprovalHandoffPort(Protocol):
    async def handoff(self, request: NotificationApprovalHandoffRequest) -> NotificationApprovalHandoffResult: ...


class NoopNotificationApprovalHandoff:
    async def handoff(self, request: NotificationApprovalHandoffRequest) -> NotificationApprovalHandoffResult:
        return NotificationApprovalHandoffResult(
            status="ignored",
            message="Notification receive fact was recorded, but no approval handoff workflow is configured yet.",
            metadata={"fact_id": request.fact_id},
        )


class InMemoryNotificationApprovalHandoff:
    def __init__(
        self,
        *,
        result: NotificationApprovalHandoffResult | None = None,
    ) -> None:
        self._result = result or NotificationApprovalHandoffResult(
            status="queued",
            message="Notification receive fact queued for approval handoff.",
        )
        self._requests: list[NotificationApprovalHandoffRequest] = []

    async def handoff(self, request: NotificationApprovalHandoffRequest) -> NotificationApprovalHandoffResult:
        self._requests.append(request)
        return self._result

    def list(self) -> Sequence[NotificationApprovalHandoffRequest]:
        return tuple(self._requests)
