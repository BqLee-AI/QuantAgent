from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quantagent.core.approval.models import ActionRequest, ApprovalRequest, ExecutionStatus
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping, to_json_value


@dataclass(frozen=True)
class PolicyGateResult:
    allowed: bool
    reason_summary: str
    metadata: JsonObject | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise ValueError("allowed must be a boolean.")
        if not isinstance(self.reason_summary, str) or not self.reason_summary.strip():
            raise ValueError("reason_summary must be a non-empty string.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata or {}, stage="policy_gate"))

    def to_mapping(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason_summary": self.reason_summary,
            "metadata": to_json_value(self.metadata or {}),
        }


@dataclass(frozen=True)
class ActionExecutionResult:
    execution_status: ExecutionStatus
    reason_summary: str
    metadata: JsonObject | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "execution_status", ExecutionStatus(self.execution_status))
        except ValueError as exc:
            allowed = ", ".join(status.value for status in ExecutionStatus)
            raise ValueError(f"execution_status must be one of: {allowed}.") from exc
        if not isinstance(self.reason_summary, str) or not self.reason_summary.strip():
            raise ValueError("reason_summary must be a non-empty string.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata or {}, stage="action_execution"))

    def to_mapping(self) -> dict[str, object]:
        return {
            "execution_status": self.execution_status.value,
            "reason_summary": self.reason_summary,
            "metadata": to_json_value(self.metadata or {}),
        }


class PolicyGate(Protocol):
    async def evaluate(self, *, action: ActionRequest, approval: ApprovalRequest) -> PolicyGateResult: ...


class ActionExecutor(Protocol):
    async def execute(self, *, action: ActionRequest, approval: ApprovalRequest) -> ActionExecutionResult: ...
