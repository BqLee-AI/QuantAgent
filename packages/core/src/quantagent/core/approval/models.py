from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping, to_json_value


class ApprovalMode(StrEnum):
    NO_APPROVAL_NOTIFY_ONLY = "no_approval_notify_only"
    EXECUTE_THEN_NOTIFY = "execute_then_notify"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_WITH_TIMEOUT = "approval_with_timeout"
    MANUAL_ONLY = "manual_only"
    BLOCKED = "blocked"


class ConfirmationLevel(StrEnum):
    INFORMATIONAL = "informational"
    SOFT_CONFIRM = "soft_confirm"
    STRONG_CONFIRM = "strong_confirm"
    LINK_CONFIRM = "link_confirm"
    MANUAL_ONLY = "manual_only"


class ExpirationAction(StrEnum):
    EXPIRE_REJECT = "expire_reject"
    EXPIRE_APPROVE = "expire_approve"
    EXPIRE_NOTIFY_ONLY = "expire_notify_only"
    EXPIRE_REANALYSIS = "expire_reanalysis"
    ESCALATE = "escalate"


class ApprovalRequestStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    BLOCKED = "blocked"


class ApprovalIntent(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REANALYSIS = "request_reanalysis"
    UNCLEAR = "unclear"
    ESCALATE = "escalate"


class ApprovalDecisionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REANALYSIS_REQUESTED = "reanalysis_requested"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    BLOCKED = "blocked"
    POLICY_BLOCKED = "policy_blocked"
    POLICY_GATE_FAILED = "policy_gate_failed"
    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION_FAILED = "execution_failed"
    IGNORED = "ignored"


class PolicyGateStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    ALLOWED = "allowed"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ExecutionStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    MOCK_REQUESTED = "mock_requested"
    DRY_RUN_REQUESTED = "dry_run_requested"
    REQUEST_FAILED = "request_failed"


TERMINAL_REQUEST_STATUSES: frozenset[ApprovalRequestStatus] = frozenset(
    {
        ApprovalRequestStatus.COMPLETED,
        ApprovalRequestStatus.EXPIRED,
        ApprovalRequestStatus.ESCALATED,
        ApprovalRequestStatus.BLOCKED,
    }
)

WEAK_CONFIRMATION_CHANNELS: frozenset[str] = frozenset(
    {
        "approval_link",
        "qq",
        "wechat",
        "telegram",
        "discord",
        "email",
        "im",
    }
)

TEXT_CHANNELS: frozenset[str] = WEAK_CONFIRMATION_CHANNELS | frozenset({"sms"})


@dataclass(frozen=True)
class ActionRequest:
    id: str
    action_type: str
    action_side: str
    target_type: str
    target_id: str
    instrument: str | None = None
    market: str | None = None
    amount: float | int | None = None
    leverage: float | int | None = None
    confidence_score: float | None = None
    risk_flags: tuple[str, ...] = field(default_factory=tuple)
    urgency: str = "normal"
    proposed_payload: JsonObject = field(default_factory=dict)
    strategy_policy: JsonObject = field(default_factory=dict)
    user_policy: JsonObject = field(default_factory=dict)
    ai_policy_hint: JsonObject = field(default_factory=dict)
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "action_type", "action_side", "target_type", "target_id", "urgency"):
            _require_non_empty(field_name, getattr(self, field_name))
        if self.confidence_score is not None and not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1 when provided.")
        object.__setattr__(self, "risk_flags", _freeze_string_tuple("risk_flags", self.risk_flags))
        object.__setattr__(self, "proposed_payload", freeze_json_mapping(self.proposed_payload, stage="approval_action"))
        object.__setattr__(self, "strategy_policy", freeze_json_mapping(self.strategy_policy, stage="approval_action"))
        object.__setattr__(self, "user_policy", freeze_json_mapping(self.user_policy, stage="approval_action"))
        object.__setattr__(self, "ai_policy_hint", freeze_json_mapping(self.ai_policy_hint, stage="approval_action"))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ActionRequest:
        return cls(
            id=_required_string(payload, "id"),
            action_type=_required_string(payload, "action_type"),
            action_side=_required_string(payload, "action_side"),
            target_type=_required_string(payload, "target_type"),
            target_id=_required_string(payload, "target_id"),
            instrument=_optional_string(payload.get("instrument")),
            market=_optional_string(payload.get("market")),
            amount=_optional_number(payload.get("amount"), "amount"),
            leverage=_optional_number(payload.get("leverage"), "leverage"),
            confidence_score=_optional_float(payload.get("confidence_score"), "confidence_score"),
            risk_flags=_optional_string_tuple(payload.get("risk_flags")),
            urgency=_optional_string(payload.get("urgency")) or "normal",
            proposed_payload=_optional_mapping(payload.get("proposed_payload")),
            strategy_policy=_optional_mapping(payload.get("strategy_policy")),
            user_policy=_optional_mapping(payload.get("user_policy")),
            ai_policy_hint=_optional_mapping(payload.get("ai_policy_hint")),
            correlation_id=_optional_string(payload.get("correlation_id")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "action_side": self.action_side,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "instrument": self.instrument,
            "market": self.market,
            "amount": self.amount,
            "leverage": self.leverage,
            "confidence_score": self.confidence_score,
            "risk_flags": list(self.risk_flags),
            "urgency": self.urgency,
            "proposed_payload": to_json_value(self.proposed_payload),
            "strategy_policy": to_json_value(self.strategy_policy),
            "user_policy": to_json_value(self.user_policy),
            "ai_policy_hint": to_json_value(self.ai_policy_hint),
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class ResolvedApprovalPolicy:
    mode: ApprovalMode
    required_confirmation_level: ConfirmationLevel
    expires_at: str | None = None
    expiration_action: ExpirationAction = ExpirationAction.EXPIRE_REJECT
    allowed_channels: tuple[str, ...] = field(default_factory=tuple)
    reason_summary: str = ""
    policy_source: str = "system_default"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ApprovalMode(self.mode))
        object.__setattr__(
            self,
            "required_confirmation_level",
            ConfirmationLevel(self.required_confirmation_level),
        )
        object.__setattr__(self, "expiration_action", ExpirationAction(self.expiration_action))
        object.__setattr__(self, "allowed_channels", _freeze_string_tuple("allowed_channels", self.allowed_channels))
        _require_non_empty("reason_summary", self.reason_summary)
        _require_non_empty("policy_source", self.policy_source)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "required_confirmation_level": self.required_confirmation_level.value,
            "expires_at": self.expires_at,
            "expiration_action": self.expiration_action.value,
            "allowed_channels": list(self.allowed_channels),
            "reason_summary": self.reason_summary,
            "policy_source": self.policy_source,
        }


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    action_request_id: str
    target_type: str
    target_id: str
    action_type: str
    action_side: str
    risk_level: str
    urgency: str
    summary: str
    proposed_payload: JsonObject = field(default_factory=dict)
    required_confirmation_level: ConfirmationLevel = ConfirmationLevel.SOFT_CONFIRM
    expires_at: str | None = None
    expiration_action: ExpirationAction = ExpirationAction.EXPIRE_REJECT
    policy_source: str = "system_default"
    status: ApprovalRequestStatus = ApprovalRequestStatus.PENDING
    allowed_channels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for field_name in (
            "id",
            "action_request_id",
            "target_type",
            "target_id",
            "action_type",
            "action_side",
            "risk_level",
            "urgency",
            "summary",
            "policy_source",
        ):
            _require_non_empty(field_name, getattr(self, field_name))
        object.__setattr__(self, "required_confirmation_level", ConfirmationLevel(self.required_confirmation_level))
        object.__setattr__(self, "expiration_action", ExpirationAction(self.expiration_action))
        object.__setattr__(self, "status", ApprovalRequestStatus(self.status))
        object.__setattr__(self, "allowed_channels", _freeze_string_tuple("allowed_channels", self.allowed_channels))
        object.__setattr__(self, "proposed_payload", freeze_json_mapping(self.proposed_payload, stage="approval_request"))

    def with_status(self, status: ApprovalRequestStatus) -> ApprovalRequest:
        return ApprovalRequest(
            id=self.id,
            action_request_id=self.action_request_id,
            target_type=self.target_type,
            target_id=self.target_id,
            action_type=self.action_type,
            action_side=self.action_side,
            risk_level=self.risk_level,
            urgency=self.urgency,
            summary=self.summary,
            proposed_payload=self.proposed_payload,
            required_confirmation_level=self.required_confirmation_level,
            expires_at=self.expires_at,
            expiration_action=self.expiration_action,
            policy_source=self.policy_source,
            status=status,
            allowed_channels=self.allowed_channels,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_request_id": self.action_request_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "action_type": self.action_type,
            "action_side": self.action_side,
            "risk_level": self.risk_level,
            "urgency": self.urgency,
            "summary": self.summary,
            "proposed_payload": to_json_value(self.proposed_payload),
            "required_confirmation_level": self.required_confirmation_level.value,
            "expires_at": self.expires_at,
            "expiration_action": self.expiration_action.value,
            "policy_source": self.policy_source,
            "status": self.status.value,
            "allowed_channels": list(self.allowed_channels),
        }


@dataclass(frozen=True)
class ApprovalInput:
    id: str
    approval_id: str
    channel: str
    actor_ref: str
    raw_text: str | None = None
    structured_payload: JsonObject = field(default_factory=dict)
    received_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        for field_name in ("id", "approval_id", "channel", "actor_ref", "received_at"):
            _require_non_empty(field_name, getattr(self, field_name))
        object.__setattr__(
            self,
            "structured_payload",
            freeze_json_mapping(self.structured_payload, stage="approval_input"),
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ApprovalInput:
        return cls(
            id=_required_string(payload, "id"),
            approval_id=_required_string(payload, "approval_id"),
            channel=_required_string(payload, "channel"),
            actor_ref=_required_string(payload, "actor_ref"),
            raw_text=_optional_string(payload.get("raw_text")),
            structured_payload=_optional_mapping(payload.get("structured_payload")),
            received_at=_optional_string(payload.get("received_at")) or datetime.now(UTC).isoformat(),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "approval_id": self.approval_id,
            "channel": self.channel,
            "actor_ref": self.actor_ref,
            "raw_text": self.raw_text,
            "structured_payload": to_json_value(self.structured_payload),
            "received_at": self.received_at,
        }


@dataclass(frozen=True)
class ApprovalEvaluation:
    approval_id: str
    input_id: str
    evaluator_type: str
    interpreted_intent: ApprovalIntent
    confidence: float
    extracted_changes: JsonObject = field(default_factory=dict)
    requires_stronger_confirmation: bool = False
    reason_summary: str = ""

    def __post_init__(self) -> None:
        for field_name in ("approval_id", "input_id", "evaluator_type", "reason_summary"):
            _require_non_empty(field_name, getattr(self, field_name))
        object.__setattr__(self, "interpreted_intent", ApprovalIntent(self.interpreted_intent))
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(
            self,
            "extracted_changes",
            freeze_json_mapping(self.extracted_changes, stage="approval_evaluation"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "input_id": self.input_id,
            "evaluator_type": self.evaluator_type,
            "interpreted_intent": self.interpreted_intent.value,
            "confidence": self.confidence,
            "extracted_changes": to_json_value(self.extracted_changes),
            "requires_stronger_confirmation": self.requires_stronger_confirmation,
            "reason_summary": self.reason_summary,
        }


@dataclass(frozen=True)
class ApprovalDecision:
    approval_id: str
    action_request_id: str
    status: ApprovalDecisionStatus
    intent: ApprovalIntent | None = None
    policy_gate_status: PolicyGateStatus = PolicyGateStatus.NOT_REQUIRED
    execution_status: ExecutionStatus = ExecutionStatus.NOT_REQUESTED
    reason_summary: str = ""
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("approval_id", self.approval_id)
        _require_non_empty("action_request_id", self.action_request_id)
        _require_non_empty("reason_summary", self.reason_summary)
        object.__setattr__(self, "status", ApprovalDecisionStatus(self.status))
        if self.intent is not None:
            object.__setattr__(self, "intent", ApprovalIntent(self.intent))
        object.__setattr__(self, "policy_gate_status", PolicyGateStatus(self.policy_gate_status))
        object.__setattr__(self, "execution_status", ExecutionStatus(self.execution_status))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action_request_id": self.action_request_id,
            "status": self.status.value,
            "intent": self.intent.value if self.intent else None,
            "policy_gate_status": self.policy_gate_status.value,
            "execution_status": self.execution_status.value,
            "reason_summary": self.reason_summary,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class HumanAuthorizationMessage:
    approval_id: str
    action_request_id: str
    summary: str
    risk_direction: str
    required_confirmation_level: ConfirmationLevel
    expires_at: str | None
    expiration_action: ExpirationAction
    allowed_channels: tuple[str, ...] = field(default_factory=tuple)
    safe_context: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("approval_id", "action_request_id", "summary", "risk_direction"):
            _require_non_empty(field_name, getattr(self, field_name))
        object.__setattr__(self, "required_confirmation_level", ConfirmationLevel(self.required_confirmation_level))
        object.__setattr__(self, "expiration_action", ExpirationAction(self.expiration_action))
        object.__setattr__(self, "allowed_channels", _freeze_string_tuple("allowed_channels", self.allowed_channels))
        object.__setattr__(
            self,
            "safe_context",
            freeze_json_mapping(self.safe_context, stage="human_authorization_message"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action_request_id": self.action_request_id,
            "summary": self.summary,
            "risk_direction": self.risk_direction,
            "required_confirmation_level": self.required_confirmation_level.value,
            "expires_at": self.expires_at,
            "expiration_action": self.expiration_action.value,
            "allowed_channels": list(self.allowed_channels),
            "safe_context": to_json_value(self.safe_context),
        }


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    _require_non_empty(field_name, value)
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional string fields must be strings when provided.")
    return value if value.strip() else None


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a number when provided.")
    return float(value)


def _optional_number(value: Any, field_name: str) -> float | int | None:
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a number when provided.")
    return value


def _optional_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("mapping fields must be JSON objects when provided.")
    return value


def _optional_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError("string tuple fields must be arrays when provided.")
    return _freeze_string_tuple("string_tuple", value)


def _freeze_string_tuple(field_name: str, value: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    frozen = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in frozen):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return frozen
