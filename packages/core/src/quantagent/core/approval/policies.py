from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalMode,
    ConfirmationLevel,
    ExpirationAction,
    ResolvedApprovalPolicy,
)


DEFAULT_ALLOWED_CHANNELS: tuple[str, ...] = ("web", "local_cli", "approval_link")
MANUAL_ONLY_CHANNELS: tuple[str, ...] = ("web", "local_cli")


@dataclass(frozen=True)
class ApprovalPolicyResolver:
    default_timeout_seconds: int = 900

    def resolve(self, action: ActionRequest) -> ResolvedApprovalPolicy:
        policy = _merged_policy(action.strategy_policy, action.ai_policy_hint, action.user_policy)
        requested_mode = _string_value(policy, "mode")
        baseline = self._baseline_mode(action)
        mode = self._resolve_mode(requested_mode, baseline)
        expiration_action = _expiration_action(policy, action, mode)
        confirmation_level = _confirmation_level(policy, action, mode)
        allowed_channels = _allowed_channels(policy, confirmation_level)
        expires_at = _expires_at(policy, self.default_timeout_seconds, mode)

        return ResolvedApprovalPolicy(
            mode=mode,
            required_confirmation_level=confirmation_level,
            expires_at=expires_at,
            expiration_action=expiration_action,
            allowed_channels=allowed_channels,
            reason_summary=self._reason_summary(action, mode),
            policy_source=_policy_source(action, requested_mode),
        )

    def _baseline_mode(self, action: ActionRequest) -> ApprovalMode:
        if "blocked" in action.risk_flags or action.action_type in {"live_execute_order", "live_trade"}:
            return ApprovalMode.BLOCKED
        if action.action_type in {"notify", "monitor"} or action.action_side == "neutral":
            return ApprovalMode.NO_APPROVAL_NOTIFY_ONLY
        if action.action_type in {"reduce_position", "cancel_order"} and action.action_side == "reduce_risk":
            return ApprovalMode.EXECUTE_THEN_NOTIFY
        if action.urgency in {"time_sensitive", "urgent"}:
            return ApprovalMode.APPROVAL_WITH_TIMEOUT
        if action.action_type in {"enable_broker", "execute_order"} and (
            "manual_only" in action.risk_flags or "high_risk" in action.risk_flags
        ):
            return ApprovalMode.MANUAL_ONLY
        return ApprovalMode.APPROVAL_REQUIRED

    def _resolve_mode(self, requested_mode: str | None, baseline: ApprovalMode) -> ApprovalMode:
        if baseline == ApprovalMode.BLOCKED:
            return baseline
        if requested_mode is None:
            return baseline
        candidate = ApprovalMode(requested_mode)
        # 安全边界：AI hint 或策略只能收紧高风险路径，不能把需要审批的动作降级成 notify-only。
        if baseline in {ApprovalMode.APPROVAL_REQUIRED, ApprovalMode.APPROVAL_WITH_TIMEOUT, ApprovalMode.MANUAL_ONLY}:
            if candidate in {ApprovalMode.NO_APPROVAL_NOTIFY_ONLY, ApprovalMode.EXECUTE_THEN_NOTIFY}:
                return baseline
        if baseline == ApprovalMode.MANUAL_ONLY and candidate != ApprovalMode.BLOCKED:
            return ApprovalMode.MANUAL_ONLY
        return candidate

    def _reason_summary(self, action: ActionRequest, mode: ApprovalMode) -> str:
        return (
            f"{action.action_type} on {action.target_type}:{action.target_id} resolved as {mode.value} "
            f"for {action.action_side}/{action.urgency}."
        )


def _merged_policy(*policies: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for policy in policies:
        merged.update(dict(policy))
    return merged


def _string_value(policy: Mapping[str, Any], field_name: str) -> str | None:
    value = policy.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"policy.{field_name} must be a non-empty string when provided.")
    return value


def _expiration_action(
    policy: Mapping[str, Any],
    action: ActionRequest,
    mode: ApprovalMode,
) -> ExpirationAction:
    configured = _string_value(policy, "expiration_action")
    if configured is not None:
        return ExpirationAction(configured)
    if mode == ApprovalMode.NO_APPROVAL_NOTIFY_ONLY:
        return ExpirationAction.EXPIRE_NOTIFY_ONLY
    if action.action_side == "reduce_risk" and action.urgency == "urgent":
        return ExpirationAction.EXPIRE_APPROVE
    if mode == ApprovalMode.EXECUTE_THEN_NOTIFY:
        return ExpirationAction.EXPIRE_NOTIFY_ONLY
    if action.urgency == "time_sensitive":
        return ExpirationAction.EXPIRE_REANALYSIS
    return ExpirationAction.EXPIRE_REJECT


def _confirmation_level(
    policy: Mapping[str, Any],
    action: ActionRequest,
    mode: ApprovalMode,
) -> ConfirmationLevel:
    configured = _string_value(policy, "required_confirmation_level")
    if configured is not None:
        candidate = ConfirmationLevel(configured)
        if mode == ApprovalMode.MANUAL_ONLY:
            return ConfirmationLevel.MANUAL_ONLY
        return candidate
    if mode == ApprovalMode.NO_APPROVAL_NOTIFY_ONLY:
        return ConfirmationLevel.INFORMATIONAL
    if mode == ApprovalMode.MANUAL_ONLY:
        return ConfirmationLevel.MANUAL_ONLY
    if action.action_type in {"execute_order", "enable_broker"}:
        return ConfirmationLevel.LINK_CONFIRM
    if action.action_side == "increase_risk":
        return ConfirmationLevel.STRONG_CONFIRM
    return ConfirmationLevel.SOFT_CONFIRM


def _allowed_channels(policy: Mapping[str, Any], level: ConfirmationLevel) -> tuple[str, ...]:
    configured = policy.get("allowed_channels")
    if configured is not None:
        if not isinstance(configured, list | tuple):
            raise ValueError("policy.allowed_channels must be an array when provided.")
        channels = tuple(str(item) for item in configured if str(item).strip())
    elif level == ConfirmationLevel.MANUAL_ONLY:
        channels = MANUAL_ONLY_CHANNELS
    else:
        channels = DEFAULT_ALLOWED_CHANNELS
    if not channels:
        raise ValueError("policy.allowed_channels must not be empty.")
    return channels


def _expires_at(policy: Mapping[str, Any], default_timeout_seconds: int, mode: ApprovalMode) -> str | None:
    configured = _string_value(policy, "expires_at")
    if configured is not None:
        return configured
    if mode not in {ApprovalMode.APPROVAL_WITH_TIMEOUT, ApprovalMode.MANUAL_ONLY}:
        return None
    return (datetime.now(UTC) + timedelta(seconds=default_timeout_seconds)).isoformat()


def _policy_source(action: ActionRequest, requested_mode: str | None) -> str:
    if requested_mode is not None and action.user_policy:
        return "user_policy"
    if requested_mode is not None and action.strategy_policy:
        return "strategy_policy"
    return "system_default"
