from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from quantagent.core.events import EventBusPublisher, EventEnvelope, sanitize_mapping
from quantagent.core.notifications.models import NotificationDeliverySummary, NotificationDispatchResult


@dataclass
class NotificationEventPublisher:
    publisher: EventBusPublisher
    producer: str = "notification-dispatch"

    async def publish_notification_completed(self, result: NotificationDispatchResult) -> EventEnvelope:
        summary = NotificationDeliverySummary.from_dispatch_result(result)
        # 事件语义边界：completed 只表示发送尝试结果，不表达用户审批或 broker 执行状态。
        return await self.publisher.publish(
            EventEnvelope(
                id=f"evt_{uuid4().hex}",
                topic="notification.completed",
                payload=sanitize_mapping(summary.to_mapping()),
                producer=self.producer,
                created_at=datetime.now(UTC).isoformat(),
                correlation_id=result.correlation_id,
                causation_id=result.causation_id,
                headers=sanitize_mapping(
                    {
                        "notification_request_id": result.request_id,
                        "approval_id": result.approval_id,
                        "action_request_id": result.action_request_id,
                        "plugin_id": result.plugin_id,
                    }
                ),
            )
        )
