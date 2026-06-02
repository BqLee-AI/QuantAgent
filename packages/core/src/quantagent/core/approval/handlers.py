from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quantagent.core.approval.models import ActionRequest, ApprovalInput
from quantagent.core.approval.service import ApprovalOrchestrationService
from quantagent.core.events import EventEnvelope


@dataclass
class ActionRequestedHandler:
    service: ApprovalOrchestrationService

    async def handle(self, envelope: EventEnvelope) -> None:
        if not isinstance(envelope.payload, Mapping):
            raise ValueError("Event payload for topic action.requested must be a mapping.")
        action = ActionRequest.from_mapping(dict(envelope.payload))
        await self.service.submit_action(action)


@dataclass
class ApprovalInputReceivedHandler:
    service: ApprovalOrchestrationService

    async def handle(self, envelope: EventEnvelope) -> None:
        if not isinstance(envelope.payload, Mapping):
            raise ValueError("Event payload for topic approval.input_received must be a mapping.")
        user_input = ApprovalInput.from_mapping(dict(envelope.payload))
        await self.service.submit_input(user_input)
