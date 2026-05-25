from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Mapping


SIGNATURE_HEADER = "x-quantagent-signature"
TIMESTAMP_HEADER = "x-signature-timestamp"


@dataclass(frozen=True)
class DiscordInteractionDto:
    message_id: str
    source_id: str
    text: str
    payload_summary: Mapping[str, Any]
    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None


@dataclass(frozen=True)
class ReceiveResult:
    ok: bool
    code: str
    message: str
    dto: DiscordInteractionDto | None = None
    retryable: bool = False


class DiscordInteractionWebhookSourcePlugin:
    """Standalone experimental receiver for Discord-style interaction webhooks."""

    def receive_request(
        self,
        config: Mapping[str, Any],
        headers: Mapping[str, str],
        body: bytes,
        *,
        secrets: Mapping[str, str] | None = None,
        now: int | None = None,
    ) -> ReceiveResult:
        signing_secret_ref = _optional_str(config.get("signing_secret_ref"))
        if signing_secret_ref is None:
            return ReceiveResult(
                ok=False,
                code="MISSING_CONFIG",
                message="Missing required config field: signing_secret_ref.",
            )

        signing_secret = _resolve_secret(signing_secret_ref, secrets)
        if signing_secret is None:
            return ReceiveResult(
                ok=False,
                code="SECRET_NOT_RESOLVED",
                message="Signing secret reference could not be resolved.",
            )

        signature = _get_header(headers, SIGNATURE_HEADER)
        timestamp_text = _get_header(headers, TIMESTAMP_HEADER)
        if signature is None or timestamp_text is None:
            return ReceiveResult(
                ok=False,
                code="SIGNATURE_MISSING",
                message="Missing required signature headers.",
            )

        try:
            timestamp_value = int(timestamp_text)
        except ValueError:
            return ReceiveResult(
                ok=False,
                code="TIMESTAMP_INVALID",
                message="Request timestamp header is not a valid integer.",
            )

        current_time = now if now is not None else int(time.time())
        tolerance = _resolve_tolerance(config)
        if abs(current_time - timestamp_value) > tolerance:
            return ReceiveResult(
                ok=False,
                code="SIGNATURE_STALE",
                message="Request timestamp is outside the allowed verification window.",
            )

        expected_signature = sign_request_body(body, timestamp_value, signing_secret)
        if not hmac.compare_digest(signature, expected_signature):
            return ReceiveResult(
                ok=False,
                code="SIGNATURE_INVALID",
                message="Request signature validation failed.",
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ReceiveResult(
                ok=False,
                code="PAYLOAD_INVALID",
                message="Request body is not valid JSON.",
            )

        if not isinstance(payload, dict):
            return ReceiveResult(
                ok=False,
                code="PAYLOAD_INVALID",
                message="Request payload must be a JSON object.",
            )

        if payload.get("type") != 2:
            return ReceiveResult(
                ok=False,
                code="UNSUPPORTED_EVENT_TYPE",
                message="Only application command interactions are supported in v1.",
            )

        guild_id = _optional_str(payload.get("guild_id"))
        guild_allowlist = _normalized_allowlist(config.get("guild_allowlist"))
        if guild_allowlist and guild_id not in guild_allowlist:
            return ReceiveResult(
                ok=False,
                code="GUILD_NOT_ALLOWED",
                message="Interaction guild is not allowed by this plugin config.",
            )

        channel_id = _optional_str(payload.get("channel_id"))
        channel_allowlist = _normalized_allowlist(config.get("channel_allowlist"))
        if channel_allowlist and channel_id not in channel_allowlist:
            return ReceiveResult(
                ok=False,
                code="CHANNEL_NOT_ALLOWED",
                message="Interaction channel is not allowed by this plugin config.",
            )

        text = _extract_text(payload)
        if text is None:
            return ReceiveResult(
                ok=False,
                code="PAYLOAD_UNSUPPORTED",
                message="Interaction payload does not include a supported text option.",
            )

        dto = DiscordInteractionDto(
            message_id=_required_identifier(payload.get("id"), fallback="unknown-interaction"),
            source_id=f"discord.interaction:{_required_identifier(payload.get('application_id'), fallback='unknown-app')}",
            text=text,
            guild_id=guild_id,
            channel_id=channel_id,
            author_id=_extract_author_id(payload),
            payload_summary={
                "type": payload.get("type"),
                "command_name": _optional_str(_mapping(payload.get("data")).get("name")),
                "option_names": _extract_option_names(payload),
            },
        )
        return ReceiveResult(
            ok=True,
            code="RECEIVED",
            message="Discord interaction webhook payload received.",
            dto=dto,
        )


def sign_request_body(body: bytes, timestamp: int, signing_secret: str) -> str:
    payload = str(timestamp).encode("utf-8") + b"." + body
    return hmac.new(signing_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _resolve_secret(secret_ref: str, secrets: Mapping[str, str] | None) -> str | None:
    if secrets is None:
        return None
    value = secrets.get(secret_ref)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _resolve_tolerance(config: Mapping[str, Any]) -> int:
    raw_value = config.get("timestamp_tolerance_seconds", 300)
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 300


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value.strip()
    return None


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalized_allowlist(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item.strip() for item in value if isinstance(item, str) and item.strip()}


def _extract_text(payload: Mapping[str, Any]) -> str | None:
    data = _mapping(payload.get("data"))
    for option in data.get("options", []):
        if not isinstance(option, dict):
            continue
        name = _optional_str(option.get("name"))
        value = option.get("value")
        if name in {"text", "message", "content", "prompt"} and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_author_id(payload: Mapping[str, Any]) -> str | None:
    member = _mapping(payload.get("member"))
    if member:
        return _optional_str(_mapping(member.get("user")).get("id"))
    return _optional_str(_mapping(payload.get("user")).get("id"))


def _extract_option_names(payload: Mapping[str, Any]) -> list[str]:
    data = _mapping(payload.get("data"))
    names: list[str] = []
    for option in data.get("options", []):
        if isinstance(option, dict):
            name = _optional_str(option.get("name"))
            if name is not None:
                names.append(name)
    return names


def _required_identifier(value: Any, *, fallback: str) -> str:
    identifier = _optional_str(str(value)) if value is not None else None
    return identifier or fallback


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


plugin = DiscordInteractionWebhookSourcePlugin()
