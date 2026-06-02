from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quantagent.core.events.codec import sanitize_string

_FALLBACK_VALUE = "unknown"


def build_discord_approval_notification_text(payload: Mapping[str, Any]) -> str:
    approval_id = _required_text(payload, "approval_id")
    action_request_id = _optional_text(payload.get("action_request_id"))
    summary = _optional_text(payload.get("summary")) or "Approval requested."
    risk_direction = _optional_text(payload.get("risk_direction")) or _optional_text(payload.get("action_side")) or _FALLBACK_VALUE
    confirmation = _optional_text(payload.get("required_confirmation_level")) or _FALLBACK_VALUE
    expires_at = _optional_text(payload.get("expires_at"))

    lines = [
        "QuantAgent approval requested",
        f"approval_id: {approval_id}",
    ]
    if action_request_id:
        lines.append(f"action_request_id: {action_request_id}")
    lines.extend(
        [
            f"summary: {summary}",
            f"risk: {risk_direction}",
            f"confirmation: {confirmation}",
        ]
    )
    if expires_at:
        lines.append(f"expires_at: {expires_at}")
    lines.extend(
        [
            "",
            "Reply with:",
            f"approval_id: {approval_id} approve",
            f"approval_id: {approval_id} reject",
            f"approval_id: {approval_id} reanalysis",
        ]
    )
    return "\n".join(lines)


def _required_text(payload: Mapping[str, Any], field_name: str) -> str:
    value = _optional_text(payload.get(field_name))
    if value is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    stripped = sanitize_string(value).strip()
    return stripped or None
