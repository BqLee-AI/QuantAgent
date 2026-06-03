from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quantagent.core.events import EventEnvelope, sanitize_mapping
from quantagent.core.notifications.message import build_discord_approval_notification_text
from quantagent.core.notifications.models import NotificationDispatchRequest, NotificationDispatchResult
from quantagent.core.notifications.publishers import NotificationEventPublisher
from quantagent.core.notifications.sender import NotificationDispatchService


@dataclass
class NotificationRequestedHandler:
    dispatch_service: NotificationDispatchService
    event_publisher: NotificationEventPublisher
    plugin_id: str
    channel: str = "discord"

    async def handle(self, envelope: EventEnvelope) -> None:
        result = await self._dispatch_from_envelope(envelope)
        await self.event_publisher.publish_notification_completed(result)

    async def _dispatch_from_envelope(self, envelope: EventEnvelope) -> NotificationDispatchResult:
        if not isinstance(envelope.payload, Mapping):
            request = self._failed_request(envelope)
            return _failed_result(request, code="NOTIFICATION_PAYLOAD_INVALID", message="notification.requested payload must be a mapping.")
        try:
            request = self._request_from_payload(envelope)
        except ValueError as exc:
            request = self._failed_request(envelope)
            return _failed_result(request, code="NOTIFICATION_PAYLOAD_INVALID", message=str(exc))
        return await self.dispatch_service.dispatch(request)

    def _request_from_payload(self, envelope: EventEnvelope) -> NotificationDispatchRequest:
        payload = dict(envelope.payload)
        approval_id = _required_text(payload, "approval_id")
        action_request_id = _required_text(payload, "action_request_id")
        text = build_discord_approval_notification_text(payload)
        request_id = _notification_request_id(envelope, approval_id=approval_id)
        return NotificationDispatchRequest(
            request_id=request_id,
            plugin_id=self.plugin_id,
            correlation_id=envelope.correlation_id or request_id,
            causation_id=envelope.causation_id or approval_id,
            approval_id=approval_id,
            action_request_id=action_request_id,
            channel=self.channel,
            text=text,
            metadata=sanitize_mapping(
                {
                    "approval_id": approval_id,
                    "action_request_id": action_request_id,
                    "notification_event_id": envelope.id,
                    "source_topic": envelope.topic,
                }
            ),
        )

    def _failed_request(self, envelope: EventEnvelope) -> NotificationDispatchRequest:
        payload = envelope.payload if isinstance(envelope.payload, Mapping) else {}
        approval_id = _optional_text(payload.get("approval_id")) or "unknown_approval"
        action_request_id = _optional_text(payload.get("action_request_id")) or "unknown_action"
        request_id = _notification_request_id(envelope, approval_id=approval_id)
        return NotificationDispatchRequest(
            request_id=request_id,
            plugin_id=self.plugin_id,
            correlation_id=envelope.correlation_id or request_id,
            causation_id=envelope.causation_id or approval_id,
            approval_id=approval_id,
            action_request_id=action_request_id,
            channel=self.channel,
            text=f"approval_id: {approval_id}",
            metadata=sanitize_mapping({"notification_event_id": envelope.id, "source_topic": envelope.topic}),
        )


def _failed_result(request: NotificationDispatchRequest, *, code: str, message: str) -> NotificationDispatchResult:
    return NotificationDispatchResult(
        request_id=request.request_id,
        plugin_id=request.plugin_id,
        accepted=False,
        retryable=False,
        code=code,
        message=message,
        correlation_id=request.correlation_id,
        causation_id=request.causation_id,
        approval_id=request.approval_id,
        action_request_id=request.action_request_id,
        channel=request.channel,
        metadata=request.metadata,
    )


def _notification_request_id(envelope: EventEnvelope, *, approval_id: str) -> str:
    return f"notification_request_{approval_id}_{envelope.id}"


def _required_text(payload: Mapping[str, object], field_name: str) -> str:
    value = _optional_text(payload.get(field_name))
    if value is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
