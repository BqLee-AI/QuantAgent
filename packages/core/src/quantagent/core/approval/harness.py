from __future__ import annotations

from dataclasses import dataclass, field

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalInput,
    ApprovalRequest,
    ExecutionStatus,
    HumanAuthorizationMessage,
)
from quantagent.core.approval.notification_handoff import ApprovalNotificationHandoffAdapter
from quantagent.core.approval.ports import ActionExecutionResult, PolicyGateResult
from quantagent.core.events import EventBusPublisher, EventEnvelope, sanitize_mapping
from quantagent.core.notifications.models import NotificationApprovalHandoffRequest, NotificationApprovalHandoffResult


@dataclass
class FakeAIActionProducer:
    publisher: EventBusPublisher

    async def publish_action(self, action: ActionRequest) -> EventEnvelope:
        envelope = EventEnvelope(
            id=f"evt_{action.id}",
            topic="action.requested",
            payload=action.to_mapping(),
            producer="fake-ai-decision",
            created_at="2026-06-01T00:00:00+00:00",
            correlation_id=action.correlation_id or action.id,
        )
        return await self.publisher.publish(envelope)


@dataclass
class HumanAuthorizationMessageBuilder:
    def build(self, envelope: EventEnvelope) -> HumanAuthorizationMessage:
        payload = dict(envelope.payload)
        # 脱敏边界: 授权消息只能使用 notification.requested 中已脱敏摘要。
        safe_context = sanitize_mapping(dict(payload.get("safe_context") or {}))
        return HumanAuthorizationMessage(
            approval_id=str(payload["approval_id"]),
            action_request_id=str(payload["action_request_id"]),
            summary=str(payload["summary"]),
            risk_direction=str(payload["risk_direction"]),
            required_confirmation_level=str(payload["required_confirmation_level"]),
            expires_at=payload.get("expires_at") if isinstance(payload.get("expires_at"), str) else None,
            expiration_action=str(payload["expiration_action"]),
            allowed_channels=tuple(str(item) for item in payload.get("allowed_channels", ())),
            safe_context=safe_context,
        )


@dataclass
class FakeNotificationConsumer:
    builder: HumanAuthorizationMessageBuilder = field(default_factory=HumanAuthorizationMessageBuilder)
    messages: list[HumanAuthorizationMessage] = field(default_factory=list)

    async def handle(self, envelope: EventEnvelope) -> None:
        self.messages.append(self.builder.build(envelope))

    @property
    def latest_message(self) -> HumanAuthorizationMessage | None:
        if not self.messages:
            return None
        return self.messages[-1]


@dataclass
class FakeHumanInputProducer:
    publisher: EventBusPublisher

    async def publish_input(self, user_input: ApprovalInput) -> EventEnvelope:
        envelope = EventEnvelope(
            id=f"evt_{user_input.id}",
            topic="approval.input_received",
            payload=user_input.to_mapping(),
            producer="fake-human-input",
            created_at=user_input.received_at,
            correlation_id=user_input.approval_id,
            causation_id=user_input.id,
        )
        return await self.publisher.publish(envelope)


@dataclass
class FakeNotificationHandoffProducer:
    adapter: ApprovalNotificationHandoffAdapter

    async def handoff(
        self,
        *,
        approval_id: str,
        text: str,
        intent: str | None = None,
        fact_id: str = "notif_fact_1",
        interaction_id: str = "interaction-1",
        author_id: str = "user-1",
    ) -> NotificationApprovalHandoffResult:
        payload_summary: dict[str, object] = {"approval_id": approval_id}
        if intent is not None:
            payload_summary["intent"] = intent
        return await self.adapter.handoff(
            NotificationApprovalHandoffRequest(
                handoff_id=f"handoff-{fact_id}",
                fact_id=fact_id,
                plugin_id="quantagent.official.notification.fake",
                transport="discord",
                request_id=f"req-{fact_id}",
                correlation_id=f"corr-{fact_id}",
                interaction_id=interaction_id,
                source_id="channel-1",
                text=text,
                payload_summary=payload_summary,
                metadata={"approval_input_id": f"input-{fact_id}"},
                received_at="2026-06-01T00:00:02+00:00",
                author_id=author_id,
            )
        )


@dataclass
class FakePolicyGate:
    allowed: bool = True
    fail: bool = False
    reason_summary: str = "fake policy gate allowed"
    calls: list[tuple[ActionRequest, ApprovalRequest]] = field(default_factory=list)

    async def evaluate(self, *, action: ActionRequest, approval: ApprovalRequest) -> PolicyGateResult:
        self.calls.append((action, approval))
        if self.fail:
            raise RuntimeError("fake policy gate failure")
        return PolicyGateResult(allowed=self.allowed, reason_summary=self.reason_summary)


@dataclass
class FakeActionExecutor:
    execution_status: ExecutionStatus = ExecutionStatus.DRY_RUN_REQUESTED
    fail: bool = False
    calls: list[tuple[ActionRequest, ApprovalRequest]] = field(default_factory=list)

    async def execute(self, *, action: ActionRequest, approval: ApprovalRequest) -> ActionExecutionResult:
        self.calls.append((action, approval))
        if self.fail:
            raise RuntimeError("fake executor failure")
        return ActionExecutionResult(
            execution_status=self.execution_status,
            reason_summary="fake executor recorded request; no real broker execution happened.",
        )
