from __future__ import annotations

from dataclasses import dataclass

from quantagent.core.approval.models import ActionRequest, ApprovalInput
from quantagent.core.approval.service import ApprovalOrchestrationService, ApprovalServiceResult
from quantagent.core.events import EventEnvelope


@dataclass
class ActionRequestedHandler:
    service: ApprovalOrchestrationService

    async def handle(self, envelope: EventEnvelope) -> None:
        action = ActionRequest.from_mapping(dict(envelope.payload))
        await self.service.submit_action(action)


@dataclass
class ApprovalInputReceivedHandler:
    service: ApprovalOrchestrationService
    last_result: ApprovalServiceResult | None = None

    async def handle(self, envelope: EventEnvelope) -> None:
        user_input = ApprovalInput.from_mapping(dict(envelope.payload))
        self.last_result = await self.service.submit_input(user_input)
