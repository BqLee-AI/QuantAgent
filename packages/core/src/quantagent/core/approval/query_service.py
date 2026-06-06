from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from quantagent.core.approval.models import (
    TERMINAL_REQUEST_STATUSES,
    ActionRequest,
    ApprovalAuditRecord,
    ApprovalDecision,
    ApprovalEvaluation,
    ApprovalInput,
    ApprovalRequest,
)
from quantagent.core.approval.repository import ApprovalRepository
from quantagent.plugin_sdk.io import JsonObject, to_json_value

_MASKED = "[masked]"
_SENSITIVE_KEYWORDS = (
    "account",
    "api_key",
    "authorization",
    "broker_credential",
    "credential",
    "password",
    "private_policy",
    "prompt",
    "secret",
    "token",
)
_UNSET = object()


@dataclass(frozen=True)
class ApprovalListQuery:
    status: str | None = None
    risk_level: str | None = None
    required_confirmation_level: str | None = None
    expires_before: datetime | None = None
    cursor: str | None = None
    limit: int = 50
    sort: str = "-updated_at"


@dataclass(frozen=True)
class ApprovalPage:
    items: tuple[ApprovalSummaryView, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class ApprovalSummaryCounts:
    total: int


@dataclass(frozen=True)
class ApprovalDecisionSummaryView:
    status: str
    intent: str | None
    reason_summary: str
    policy_gate_status: str
    execution_status: str


@dataclass(frozen=True)
class ApprovalSummaryView:
    id: str
    status: str
    target_type: str
    target_id: str
    action_type: str
    action_side: str
    risk_level: str
    urgency: str
    summary: str
    required_confirmation_level: str
    expires_at: str | None
    expiration_action: str
    created_at: str | None
    updated_at: str | None
    latest_decision_summary: ApprovalDecisionSummaryView | None
    allowed_actions: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalDetailView:
    summary: ApprovalSummaryView
    action_request_summary: JsonObject
    allowed_channels: tuple[str, ...]
    policy_source: str
    inputs: tuple[dict[str, object | None], ...] = field(default_factory=tuple)
    evaluations: tuple[dict[str, object | None], ...] = field(default_factory=tuple)
    decisions: tuple[dict[str, object | None], ...] = field(default_factory=tuple)
    audit_refs: tuple[dict[str, object | None], ...] = field(default_factory=tuple)


class ApprovalQueryNotFoundError(Exception):
    def __init__(self, approval_id: str) -> None:
        super().__init__(f"Approval not found: {approval_id}")
        self.approval_id = approval_id


class ApprovalQueryService:
    def __init__(self, repository: ApprovalRepository) -> None:
        self._repository = repository

    def list_approvals(self, query: ApprovalListQuery) -> ApprovalPage:
        list_method = getattr(self._repository, "list_approval_requests", None)
        if callable(list_method):
            approvals, next_cursor_payload = list_method(
                status=query.status,
                risk_level=query.risk_level,
                required_confirmation_level=query.required_confirmation_level,
                expires_before=query.expires_before,
                cursor=_decode_cursor(query.cursor),
                sort=query.sort,
                limit=query.limit,
            )
        else:
            approvals = []
            next_cursor_payload = None
        latest_decisions = self._repository.list_latest_decisions(tuple(approval.id for approval in approvals))
        return ApprovalPage(
            items=tuple(
                self._summary(approval, latest_decision=latest_decisions.get(approval.id))
                for approval in approvals
            ),
            next_cursor=_encode_cursor(next_cursor_payload),
        )

    def get_detail(self, approval_id: str) -> ApprovalDetailView:
        approval = self._repository.get_approval_request(approval_id)
        if approval is None:
            raise ApprovalQueryNotFoundError(approval_id)
        action = self._repository.get_action_request(approval.action_request_id)
        return ApprovalDetailView(
            summary=self._summary(approval),
            action_request_summary=_action_summary(action),
            allowed_channels=approval.allowed_channels,
            policy_source=approval.policy_source,
            inputs=tuple(_input_view(item) for item in self._repository.list_inputs(approval.id)),
            evaluations=tuple(_evaluation_view(item) for item in self._repository.list_evaluations(approval.id)),
            decisions=tuple(_decision_view(item) for item in self._repository.list_decisions(approval.id)),
            audit_refs=tuple(_audit_ref(item) for item in self._repository.list_audit_records(approval.id)),
        )

    def count_approvals(
        self,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        required_confirmation_level: str | None = None,
        expires_before: datetime | None = None,
    ) -> ApprovalSummaryCounts:
        return ApprovalSummaryCounts(
            total=self._repository.count_approval_requests(
                status=status,
                risk_level=risk_level,
                required_confirmation_level=required_confirmation_level,
                expires_before=expires_before,
            )
        )

    def _summary(
        self,
        approval: ApprovalRequest,
        *,
        latest_decision: ApprovalDecision | None | object = _UNSET,
    ) -> ApprovalSummaryView:
        if latest_decision is _UNSET:
            latest_decision = self._repository.latest_decision(approval.id)
        return ApprovalSummaryView(
            id=approval.id,
            status=approval.status.value,
            target_type=approval.target_type,
            target_id=approval.target_id,
            action_type=approval.action_type,
            action_side=approval.action_side,
            risk_level=approval.risk_level,
            urgency=approval.urgency,
            summary=approval.summary,
            required_confirmation_level=approval.required_confirmation_level.value,
            expires_at=approval.expires_at,
            expiration_action=approval.expiration_action.value,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
            latest_decision_summary=_decision_summary(latest_decision),
            allowed_actions=_allowed_actions(approval),
        )


def _allowed_actions(approval: ApprovalRequest) -> tuple[str, ...]:
    if approval.status in TERMINAL_REQUEST_STATUSES:
        return ()
    return ("approve", "reject", "request-reanalysis")


def _decision_summary(decision: ApprovalDecision | None) -> ApprovalDecisionSummaryView | None:
    if decision is None:
        return None
    return ApprovalDecisionSummaryView(
        status=decision.status.value,
        intent=decision.intent.value if decision.intent else None,
        reason_summary=decision.reason_summary,
        policy_gate_status=decision.policy_gate_status.value,
        execution_status=decision.execution_status.value,
    )


def _action_summary(action: ActionRequest | None) -> JsonObject:
    if action is None:
        return {"state": "missing"}
    return {
        "id": action.id,
        "action_type": action.action_type,
        "action_side": action.action_side,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "instrument": action.instrument,
        "market": action.market,
        "amount": action.amount,
        "leverage": action.leverage,
        "confidence_score": action.confidence_score,
        "risk_flags": list(action.risk_flags),
        "urgency": action.urgency,
        "proposed_payload_summary": _redact_json_mapping(action.proposed_payload),
        "correlation_id": action.correlation_id,
    }


def _input_view(item: ApprovalInput) -> dict[str, object | None]:
    return {
        "id": item.id,
        "approval_id": item.approval_id,
        "channel": item.channel,
        "actor_ref": item.actor_ref,
        "raw_text_summary": item.raw_text,
        "structured_payload": _redact_json_mapping(item.structured_payload),
        "received_at": item.received_at,
    }


def _evaluation_view(item: ApprovalEvaluation) -> dict[str, object | None]:
    return {
        "approval_id": item.approval_id,
        "input_id": item.input_id,
        "evaluator_type": item.evaluator_type,
        "interpreted_intent": item.interpreted_intent.value,
        "confidence": item.confidence,
        "extracted_changes": _redact_json_mapping(item.extracted_changes),
        "requires_stronger_confirmation": item.requires_stronger_confirmation,
        "reason_summary": item.reason_summary,
    }


def _decision_view(item: ApprovalDecision) -> dict[str, object | None]:
    return {
        "approval_id": item.approval_id,
        "action_request_id": item.action_request_id,
        "status": item.status.value,
        "intent": item.intent.value if item.intent else None,
        "policy_gate_status": item.policy_gate_status.value,
        "execution_status": item.execution_status.value,
        "reason_summary": item.reason_summary,
        "correlation_id": item.correlation_id,
        "request_id": item.request_id,
    }


def _audit_ref(item: ApprovalAuditRecord) -> dict[str, object | None]:
    return {
        "record_id": item.record_id,
        "action": item.action,
        "resource_id": item.resource_id,
        "before_status": item.before_status.value if item.before_status else None,
        "after_status": item.after_status.value if item.after_status else None,
        "request_id": item.request_id,
        "channel": item.channel,
        "reason_summary": item.reason_summary,
        "record_refs": _redact_json_mapping(item.record_refs),
        "created_at": item.created_at,
    }


def _redact_json_mapping(payload: JsonObject) -> JsonObject:
    value = _redact_json_value(to_json_value(payload))
    return value if isinstance(value, dict) else {}


def _redact_json_value(value: object, *, key: str | None = None) -> object:
    if key is not None and _is_sensitive_key(key):
        return _MASKED
    if isinstance(value, Mapping):
        return {str(item_key): _redact_json_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def _decode_cursor(cursor: str | None) -> dict[str, str] | None:
    if cursor is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("approval cursor is invalid") from exc
    if not isinstance(payload, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in payload.items()):
        raise ValueError("approval cursor is invalid")
    return payload


def _encode_cursor(cursor: dict[str, str] | None) -> str | None:
    if cursor is None:
        return None
    payload = json.dumps(cursor, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")
