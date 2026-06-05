from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Protocol

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalAuditRecord,
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

    def get_approval_request_for_update(self, approval_id: str) -> ApprovalRequest | None: ...

    def get_approval_request_by_action_id(self, action_request_id: str) -> ApprovalRequest | None: ...

    def save_input(self, user_input: ApprovalInput) -> ApprovalInput: ...

    def get_input(self, input_id: str, *, approval_id: str | None = None) -> ApprovalInput | None: ...

    def list_inputs(self, approval_id: str) -> tuple[ApprovalInput, ...]: ...

    def save_evaluation(self, evaluation: ApprovalEvaluation) -> None: ...

    def get_evaluation_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalEvaluation | None: ...

    def list_evaluations(self, approval_id: str) -> tuple[ApprovalEvaluation, ...]: ...

    def save_decision(self, decision: ApprovalDecision) -> None: ...

    def link_decision_to_input(self, input_id: str, approval_id: str) -> None: ...

    def get_decision_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalDecision | None: ...

    def latest_decision(self, approval_id: str) -> ApprovalDecision | None: ...

    def list_latest_decisions(self, approval_ids: tuple[str, ...]) -> dict[str, ApprovalDecision]: ...

    def list_decisions(self, approval_id: str) -> tuple[ApprovalDecision, ...]: ...

    def save_audit_record(self, record: ApprovalAuditRecord) -> None: ...

    def list_audit_records(self, approval_id: str) -> tuple[ApprovalAuditRecord, ...]: ...

    def count_approval_requests(
        self,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        required_confirmation_level: str | None = None,
        expires_before: object | None = None,
    ) -> int: ...


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._actions: dict[str, ActionRequest] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._approval_by_action: dict[str, str] = {}
        self._inputs: dict[tuple[str, str], ApprovalInput] = {}
        self._inputs_by_approval: dict[str, list[str]] = defaultdict(list)
        self._evaluations_by_input: dict[tuple[str, str], ApprovalEvaluation] = {}
        self._evaluations_by_approval: dict[str, list[ApprovalEvaluation]] = defaultdict(list)
        self._decisions_by_approval: dict[str, list[ApprovalDecision]] = defaultdict(list)
        self._decision_by_input: dict[tuple[str, str], ApprovalDecision] = {}
        self._audit_by_approval: dict[str, list[ApprovalAuditRecord]] = defaultdict(list)

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

    def get_approval_request_for_update(self, approval_id: str) -> ApprovalRequest | None:
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
            key = (user_input.approval_id, user_input.id)
            existing = self._inputs.get(key)
            if existing is not None:
                return existing
            self._inputs[key] = user_input
            self._inputs_by_approval[user_input.approval_id].append(user_input.id)
            return user_input

    def get_input(self, input_id: str, *, approval_id: str | None = None) -> ApprovalInput | None:
        with self._lock:
            if approval_id is not None:
                return self._inputs.get((approval_id, input_id))
            for (candidate_approval_id, candidate_input_id), user_input in self._inputs.items():
                if candidate_input_id == input_id:
                    return user_input
            return None

    def list_inputs(self, approval_id: str) -> tuple[ApprovalInput, ...]:
        with self._lock:
            return tuple(self._inputs[(approval_id, input_id)] for input_id in self._inputs_by_approval.get(approval_id, ()))

    def save_evaluation(self, evaluation: ApprovalEvaluation) -> None:
        with self._lock:
            key = (evaluation.approval_id, evaluation.input_id)
            if key in self._evaluations_by_input:
                return
            self._evaluations_by_input[key] = evaluation
            self._evaluations_by_approval[evaluation.approval_id].append(evaluation)

    def get_evaluation_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalEvaluation | None:
        with self._lock:
            if approval_id is not None:
                return self._evaluations_by_input.get((approval_id, input_id))
            for (candidate_approval_id, candidate_input_id), evaluation in self._evaluations_by_input.items():
                if candidate_input_id == input_id:
                    return evaluation
            return None

    def list_evaluations(self, approval_id: str) -> tuple[ApprovalEvaluation, ...]:
        with self._lock:
            return tuple(self._evaluations_by_approval.get(approval_id, ()))

    def save_decision(self, decision: ApprovalDecision) -> None:
        with self._lock:
            self._decisions_by_approval[decision.approval_id].append(decision)

    def link_decision_to_input(self, input_id: str, approval_id: str) -> None:
        with self._lock:
            decision = self.latest_decision(approval_id)
            if decision is not None:
                self._decision_by_input.setdefault((approval_id, input_id), decision)

    def get_decision_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalDecision | None:
        with self._lock:
            if approval_id is not None:
                return self._decision_by_input.get((approval_id, input_id))
            for (candidate_approval_id, candidate_input_id), decision in self._decision_by_input.items():
                if candidate_input_id == input_id:
                    return decision
            return None

    def latest_decision(self, approval_id: str) -> ApprovalDecision | None:
        with self._lock:
            decisions = self._decisions_by_approval.get(approval_id, ())
            if not decisions:
                return None
            return decisions[-1]

    def list_latest_decisions(self, approval_ids: tuple[str, ...]) -> dict[str, ApprovalDecision]:
        with self._lock:
            latest: dict[str, ApprovalDecision] = {}
            for approval_id in approval_ids:
                decisions = self._decisions_by_approval.get(approval_id, ())
                if decisions:
                    latest[approval_id] = decisions[-1]
            return latest

    def list_decisions(self, approval_id: str) -> tuple[ApprovalDecision, ...]:
        with self._lock:
            return tuple(self._decisions_by_approval.get(approval_id, ()))

    def save_audit_record(self, record: ApprovalAuditRecord) -> None:
        with self._lock:
            self._audit_by_approval[record.approval_id].append(record)

    def list_audit_records(self, approval_id: str) -> tuple[ApprovalAuditRecord, ...]:
        with self._lock:
            return tuple(self._audit_by_approval.get(approval_id, ()))

    def count_approval_requests(
        self,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        required_confirmation_level: str | None = None,
        expires_before: object | None = None,
    ) -> int:
        with self._lock:
            approvals = self._approvals.values()
            count = 0
            for approval in approvals:
                if status is not None and approval.status.value != status:
                    continue
                if risk_level is not None and approval.risk_level != risk_level:
                    continue
                if (
                    required_confirmation_level is not None
                    and approval.required_confirmation_level.value != required_confirmation_level
                ):
                    continue
                if expires_before is not None:
                    if approval.expires_at is None:
                        continue
                    if approval.expires_at > expires_before.isoformat():
                        continue
                count += 1
            return count
