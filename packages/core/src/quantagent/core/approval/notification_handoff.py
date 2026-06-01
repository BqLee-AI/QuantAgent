from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from quantagent.core.approval.models import ApprovalInput
from quantagent.core.approval.service import ApprovalOrchestrationService
from quantagent.core.events import EventBusPublisher, EventEnvelope, sanitize_mapping
from quantagent.core.notifications.models import NotificationApprovalHandoffRequest, NotificationApprovalHandoffResult


APPROVAL_ID_PATTERN = re.compile(r"(?i)\bapproval[_ -]?id\s*[:=]\s*([A-Za-z0-9_.:-]+)")


@dataclass
class ApprovalNotificationHandoffAdapter:
    service: ApprovalOrchestrationService | None = None
    publisher: EventBusPublisher | None = None
    producer: str = "approval-notification-handoff"

    async def handoff(self, request: NotificationApprovalHandoffRequest) -> NotificationApprovalHandoffResult:
        try:
            approval_input = self._to_approval_input(request)
        except ValueError as exc:
            return NotificationApprovalHandoffResult(
                status="failed",
                message=str(exc),
                metadata={"fact_id": request.fact_id, "handoff_id": request.handoff_id},
            )

        if self.publisher is not None:
            await self._publish_input(request, approval_input)
            return NotificationApprovalHandoffResult(
                status="queued",
                message="Notification receive fact was mapped to approval.input_received.",
                metadata={
                    "fact_id": request.fact_id,
                    "handoff_id": request.handoff_id,
                    "approval_id": approval_input.approval_id,
                    "input_id": approval_input.id,
                },
            )

        if self.service is None:
            return NotificationApprovalHandoffResult(
                status="failed",
                message="Approval handoff adapter requires a service or publisher.",
                metadata={
                    "fact_id": request.fact_id,
                    "handoff_id": request.handoff_id,
                    "approval_id": approval_input.approval_id,
                    "input_id": approval_input.id,
                },
            )

        # 移交边界：notification ingress 只提供事实，approve/reject 判断仍由 approval service 完成。
        result = await self.service.submit_input(approval_input)
        decision = result.decision
        return NotificationApprovalHandoffResult(
            status="completed" if decision is not None else "queued",
            message=decision.reason_summary if decision is not None else "Approval input was queued.",
            metadata={
                "fact_id": request.fact_id,
                "handoff_id": request.handoff_id,
                "approval_id": approval_input.approval_id,
                "input_id": approval_input.id,
                "decision_status": decision.status.value if decision is not None else None,
                "execution_status": decision.execution_status.value if decision is not None else None,
            },
        )

    def _to_approval_input(self, request: NotificationApprovalHandoffRequest) -> ApprovalInput:
        approval_id = _approval_id_from_request(request)
        if approval_id is None:
            raise ValueError("Approval id could not be resolved from notification handoff request.")
        return ApprovalInput(
            id=_input_id_from_request(request),
            approval_id=approval_id,
            channel=request.transport,
            actor_ref=_actor_ref_from_request(request),
            raw_text=request.text,
            structured_payload=_structured_payload_from_request(request),
            received_at=request.received_at,
        )

    async def _publish_input(
        self,
        request: NotificationApprovalHandoffRequest,
        approval_input: ApprovalInput,
    ) -> EventEnvelope:
        assert self.publisher is not None
        envelope = EventEnvelope(
            id=f"evt_{approval_input.id}",
            topic="approval.input_received",
            payload=approval_input.to_mapping(),
            producer=self.producer,
            created_at=datetime.now(UTC).isoformat(),
            correlation_id=request.correlation_id,
            causation_id=request.fact_id,
            headers=sanitize_mapping(
                {
                    "approval_id": approval_input.approval_id,
                    "input_id": approval_input.id,
                    "fact_id": request.fact_id,
                    "handoff_id": request.handoff_id,
                }
            ),
        )
        return await self.publisher.publish(envelope)


def _approval_id_from_request(request: NotificationApprovalHandoffRequest) -> str | None:
    candidates: list[Any] = [
        request.payload_summary.get("approval_id"),
        request.metadata.get("approval_id"),
        request.metadata.get("approvalId"),
    ]
    candidates.extend(_nested_values(request.payload_summary, "approval_id"))
    candidates.extend(_nested_values(request.metadata, "approval_id"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    match = APPROVAL_ID_PATTERN.search(request.text)
    if match:
        return match.group(1)
    return None


def _input_id_from_request(request: NotificationApprovalHandoffRequest) -> str:
    raw = request.metadata.get("approval_input_id") or request.payload_summary.get("approval_input_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    # 幂等边界：同一 notification receive fact 重试时必须落到同一个 ApprovalInput.id。
    return f"approval_input_{request.fact_id}_{request.interaction_id}"


def _actor_ref_from_request(request: NotificationApprovalHandoffRequest) -> str:
    if request.author_id:
        return f"{request.transport}:{request.author_id}"
    return f"{request.transport}:{request.source_id}"


def _structured_payload_from_request(request: NotificationApprovalHandoffRequest) -> dict[str, object]:
    # 安全边界：外部通知插件不能通过 metadata/payload 直接写入 approve/reject 意图。
    return {
        "notification_fact_id": request.fact_id,
        "notification_handoff_id": request.handoff_id,
    }


def _nested_values(mapping: Mapping[str, Any], field_name: str) -> list[Any]:
    values: list[Any] = []
    for value in mapping.values():
        if isinstance(value, Mapping):
            if field_name in value:
                values.append(value[field_name])
            values.extend(_nested_values(value, field_name))
    return values
