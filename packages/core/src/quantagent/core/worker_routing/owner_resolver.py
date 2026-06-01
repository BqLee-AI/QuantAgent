from __future__ import annotations

from quantagent.core.scheduling import SourceBindingRecord, SourceBindingStatus
from quantagent.core.worker_routing.models import IndustryEntrypointRef


class OwnerRoutingResolutionError(Exception):
    def __init__(self, *, reason_code: str, owner_type: str, owner_id: str, binding_id: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.owner_type = owner_type
        self.owner_id = owner_id
        self.binding_id = binding_id


class SourceBindingOwnerResolver:
    def resolve(self, binding: SourceBindingRecord) -> IndustryEntrypointRef:
        if binding.status != SourceBindingStatus.ACTIVE:
            raise OwnerRoutingResolutionError(
                reason_code="SOURCE_BINDING_NOT_ACTIVE",
                owner_type=binding.owner_type,
                owner_id=binding.owner_id,
                binding_id=binding.binding_id,
            )
        if binding.owner_type != "industry":
            raise OwnerRoutingResolutionError(
                reason_code="CAPTURED_EVENT_OWNER_UNSUPPORTED",
                owner_type=binding.owner_type,
                owner_id=binding.owner_id,
                binding_id=binding.binding_id,
            )
        return IndustryEntrypointRef(
            owner_type=binding.owner_type,
            owner_id=binding.owner_id,
            binding_id=binding.binding_id,
        )
