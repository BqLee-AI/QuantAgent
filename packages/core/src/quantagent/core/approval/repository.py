from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Protocol

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalDecision,
    ApprovalEvaluation,
    ApprovalInput,
    ApprovalRequest,
)


class ApprovalRepository(Protocol):
    def save_action_request(self, action: ActionRequest) -> None: ...

    def get_action_request(self, action_request_id: str) -> ActionRequest | None: ...

    def save_approval_request(self, approval: ApprovalRequest) -> None: ...

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None: ...

    def get_approval_request_by_action_id(self, action_request_id: str) -> ApprovalRequest | None: ...

    def save_input(self, user_input: ApprovalInput) -> ApprovalInput: ...

    def get_input(self, input_id: str) -> ApprovalInput | None: ...

    def list_inputs(self, approval_id: str) -> tuple[ApprovalInput, ...]: ...

    def save_evaluation(self, evaluation: ApprovalEvaluation) -> None: ...

    def get_evaluation_by_input_id(self, input_id: str) -> ApprovalEvaluation | None: ...

    def list_evaluations(self, approval_id: str) -> tuple[ApprovalEvaluation, ...]: ...

    def save_decision(self, decision: ApprovalDecision) -> None: ...

    def link_decision_to_input(self, input_id: str, decision: ApprovalDecision) -> None: ...

    def get_decision_by_input_id(self, input_id: str) -> ApprovalDecision | None: ...

    def latest_decision(self, approval_id: str) -> ApprovalDecision | None: ...

    def list_decisions(self, approval_id: str) -> tuple[ApprovalDecision, ...]: ...


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._actions: dict[str, ActionRequest] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._approval_by_action: dict[str, str] = {}
        self._inputs: dict[str, ApprovalInput] = {}
        self._inputs_by_approval: dict[str, list[str]] = defaultdict(list)
        self._evaluations_by_input: dict[str, ApprovalEvaluation] = {}
        self._evaluations_by_approval: dict[str, list[ApprovalEvaluation]] = defaultdict(list)
        self._decisions_by_approval: dict[str, list[ApprovalDecision]] = defaultdict(list)
        self._decision_by_input: dict[str, ApprovalDecision] = {}

    def save_action_request(self, action: ActionRequest) -> None:
        with self._lock:
            self._actions[action.id] = action

    def get_action_request(self, action_request_id: str) -> ActionRequest | None:
        with self._lock:
            return self._actions.get(action_request_id)

    def save_approval_request(self, approval: ApprovalRequest) -> None:
        with self._lock:
            self._approvals[approval.id] = approval
            self._approval_by_action[approval.action_request_id] = approval.id

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._approvals.get(approval_id)

    def get_approval_request_by_action_id(self, action_request_id: str) -> ApprovalRequest | None:
        with self._lock:
            approval_id = self._approval_by_action.get(action_request_id)
            if approval_id is None:
                return None
            return self._approvals.get(approval_id)

    def save_input(self, user_input: ApprovalInput) -> ApprovalInput:
        with self._lock:
            existing = self._inputs.get(user_input.id)
            if existing is not None:
                return existing
            self._inputs[user_input.id] = user_input
            self._inputs_by_approval[user_input.approval_id].append(user_input.id)
            return user_input

    def get_input(self, input_id: str) -> ApprovalInput | None:
        with self._lock:
            return self._inputs.get(input_id)

    def list_inputs(self, approval_id: str) -> tuple[ApprovalInput, ...]:
        with self._lock:
            return tuple(self._inputs[input_id] for input_id in self._inputs_by_approval.get(approval_id, ()))

    def save_evaluation(self, evaluation: ApprovalEvaluation) -> None:
        with self._lock:
            if evaluation.input_id in self._evaluations_by_input:
                return
            self._evaluations_by_input[evaluation.input_id] = evaluation
            self._evaluations_by_approval[evaluation.approval_id].append(evaluation)

    def get_evaluation_by_input_id(self, input_id: str) -> ApprovalEvaluation | None:
        with self._lock:
            return self._evaluations_by_input.get(input_id)

    def list_evaluations(self, approval_id: str) -> tuple[ApprovalEvaluation, ...]:
        with self._lock:
            return tuple(self._evaluations_by_approval.get(approval_id, ()))

    def save_decision(self, decision: ApprovalDecision) -> None:
        with self._lock:
            self._decisions_by_approval[decision.approval_id].append(decision)

    def link_decision_to_input(self, input_id: str, decision: ApprovalDecision) -> None:
        with self._lock:
            self._decision_by_input.setdefault(input_id, decision)

    def get_decision_by_input_id(self, input_id: str) -> ApprovalDecision | None:
        with self._lock:
            return self._decision_by_input.get(input_id)

    def latest_decision(self, approval_id: str) -> ApprovalDecision | None:
        with self._lock:
            decisions = self._decisions_by_approval.get(approval_id, ())
            if not decisions:
                return None
            return decisions[-1]

    def list_decisions(self, approval_id: str) -> tuple[ApprovalDecision, ...]:
        with self._lock:
            return tuple(self._decisions_by_approval.get(approval_id, ()))
