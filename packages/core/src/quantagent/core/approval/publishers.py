from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from quantagent.core.approval.models import ApprovalDecision, ApprovalRequest
from quantagent.core.events import EventEnvelope, EventBusPublisher, sanitize_mapping


def default_event_id_factory() -> str:
    return f"evt_{uuid4().hex}"


@dataclass
class ApprovalEventPublisher:
    publisher: EventBusPublisher
    producer: str = "approval-orchestration"
    id_factory: object | None = None

    async def publish_approval_requested(self, approval: ApprovalRequest, *, correlation_id: str | None) -> EventEnvelope:
        return await self._publish(
            topic="approval.requested",
            payload=_approval_requested_payload(approval),
            correlation_id=correlation_id,
            causation_id=approval.action_request_id,
            headers={"approval_id": approval.id, "action_request_id": approval.action_request_id},
        )

    async def publish_notification_requested(
        self,
        approval: ApprovalRequest,
        *,
        correlation_id: str | None,
        reason_summary: str,
    ) -> EventEnvelope:
        # 脱敏边界：通知事件只携带人工判断所需摘要，不携带完整 prompt、secret 或私有策略。
        payload = sanitize_mapping(
            {
                "approval_id": approval.id,
                "action_request_id": approval.action_request_id,
                "summary": approval.summary,
                "risk_direction": approval.action_side,
                "required_confirmation_level": approval.required_confirmation_level.value,
                "expires_at": approval.expires_at,
                "expiration_action": approval.expiration_action.value,
                "allowed_channels": list(approval.allowed_channels),
                "safe_context": {
                    "target_type": approval.target_type,
                    "target_id": approval.target_id,
                    "action_type": approval.action_type,
                    "urgency": approval.urgency,
                    "risk_level": approval.risk_level,
                },
                "reason_summary": reason_summary,
            }
        )
        return await self._publish(
            topic="notification.requested",
            payload=payload,
            correlation_id=correlation_id,
            causation_id=approval.id,
            headers={"approval_id": approval.id, "action_request_id": approval.action_request_id},
        )

    async def publish_approval_completed(self, decision: ApprovalDecision) -> EventEnvelope:
        return await self._publish(
            topic="approval.completed",
            payload=decision.to_mapping(),
            correlation_id=decision.correlation_id,
            causation_id=decision.approval_id,
            headers={"approval_id": decision.approval_id, "action_request_id": decision.action_request_id},
        )

    async def _publish(
        self,
        *,
        topic: str,
        payload: object,
        correlation_id: str | None,
        causation_id: str | None,
        headers: dict[str, object],
    ) -> EventEnvelope:
        factory = self.id_factory if callable(self.id_factory) else default_event_id_factory
        envelope = EventEnvelope(
            id=factory(),
            topic=topic,
            payload=sanitize_mapping(payload if isinstance(payload, Mapping) else {}),
            producer=self.producer,
            created_at=datetime.now(UTC).isoformat(),
            correlation_id=correlation_id,
            causation_id=causation_id,
            headers=sanitize_mapping(headers),
        )
        return await self.publisher.publish(envelope)


def _approval_requested_payload(approval: ApprovalRequest) -> dict[str, object]:
    # 脱敏边界：approval.requested 是状态变化摘要，不携带可直接执行的 proposed_payload 原文。
    return {
        "approval_id": approval.id,
        "action_request_id": approval.action_request_id,
        "summary": approval.summary,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "action_type": approval.action_type,
        "action_side": approval.action_side,
        "risk_level": approval.risk_level,
        "urgency": approval.urgency,
        "required_confirmation_level": approval.required_confirmation_level.value,
        "expires_at": approval.expires_at,
        "expiration_action": approval.expiration_action.value,
        "allowed_channels": list(approval.allowed_channels),
        "policy_source": approval.policy_source,
        "status": approval.status.value,
        "safe_context": {
            "target_type": approval.target_type,
            "target_id": approval.target_id,
            "action_type": approval.action_type,
            "urgency": approval.urgency,
            "risk_level": approval.risk_level,
        },
    }
