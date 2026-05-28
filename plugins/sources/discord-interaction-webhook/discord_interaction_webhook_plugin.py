from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Mapping

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


SIGNATURE_HEADER = "x-signature-ed25519"
TIMESTAMP_HEADER = "x-signature-timestamp"
PING_TYPE = 1
APPLICATION_COMMAND_TYPE = 2
PONG_RESPONSE = {"type": 1}
CHANNEL_MESSAGE_WITH_SOURCE = 4
EPHEMERAL_FLAG = 64


@dataclass(frozen=True)
class DiscordInteractionDto:
    interaction_id: str
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
    response: Mapping[str, Any] | None = None
    dto: DiscordInteractionDto | None = None
    retryable: bool = False


class DiscordInteractionWebhookSourcePlugin:
    """Discord interaction webhook source plugin with official request verification."""

    def receive_request(
        self,
        config: Mapping[str, Any],
        headers: Mapping[str, str],
        body: bytes,
        *,
        secrets: Mapping[str, str] | None = None,
    ) -> ReceiveResult:
        public_key = _resolve_public_key(config, secrets)
        if public_key is None:
            return ReceiveResult(
                ok=False,
                code="MISSING_CONFIG",
                message="Missing Discord interactions public key configuration.",
            )

        signature = _get_header(headers, SIGNATURE_HEADER)
        timestamp = _get_header(headers, TIMESTAMP_HEADER)
        if signature is None or timestamp is None:
            return ReceiveResult(
                ok=False,
                code="SIGNATURE_MISSING",
                message="Missing required Discord signature headers.",
            )

        timestamp_seconds = _parse_timestamp(timestamp)
        if timestamp_seconds is None:
            return ReceiveResult(
                ok=False,
                code="TIMESTAMP_INVALID",
                message="Discord signature timestamp is invalid.",
            )

        if not is_timestamp_fresh(
            timestamp_seconds,
            tolerance_seconds=_resolve_timestamp_tolerance(config),
        ):
            return ReceiveResult(
                ok=False,
                code="TIMESTAMP_INVALID",
                message="Discord signature timestamp is outside the accepted tolerance window.",
            )

        if not verify_discord_request(body, timestamp, signature, public_key):
            return ReceiveResult(
                ok=False,
                code="SIGNATURE_INVALID",
                message="Discord request signature validation failed.",
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

        payload_type = payload.get("type")
        if payload_type == PING_TYPE:
            return ReceiveResult(
                ok=True,
                code="PING",
                message="Discord interaction ping acknowledged.",
                response=PONG_RESPONSE,
            )

        if payload_type != APPLICATION_COMMAND_TYPE:
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
            interaction_id=_required_identifier(payload.get("id"), fallback="unknown-interaction"),
            source_id=f"discord.interaction:{_required_identifier(payload.get('application_id'), fallback='unknown-app')}",
            text=text,
            guild_id=guild_id,
            channel_id=channel_id,
            author_id=_extract_author_id(payload),
            payload_summary={
                "type": payload_type,
                "command_name": _optional_str(_mapping(payload.get("data")).get("name")),
                "option_names": _extract_option_names(payload),
            },
        )

        response_text = _optional_str(config.get("response_text")) or "QuantAgent received your Discord interaction."
        response = {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "content": response_text,
                "flags": EPHEMERAL_FLAG,
            },
        }
        return ReceiveResult(
            ok=True,
            code="RECEIVED",
            message="Discord interaction webhook payload received.",
            response=response,
            dto=dto,
        )


def verify_discord_request(body: bytes, timestamp: str, signature: str, public_key: str) -> bool:
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        verify_key.verify(timestamp.encode("utf-8") + body, bytes.fromhex(signature))
    except (BadSignatureError, ValueError):
        return False
    return True


def is_timestamp_fresh(
    timestamp_seconds: int,
    *,
    tolerance_seconds: int,
    current_time_seconds: int | None = None,
) -> bool:
    now = int(current_time_seconds if current_time_seconds is not None else time.time())
    return abs(now - timestamp_seconds) <= tolerance_seconds


def _resolve_public_key(config: Mapping[str, Any], secrets: Mapping[str, str] | None) -> str | None:
    public_key = _optional_str(config.get("public_key"))
    if public_key is not None:
        return public_key
    public_key_ref = _optional_str(config.get("public_key_ref"))
    if public_key_ref is None or secrets is None:
        return None
    value = secrets.get(public_key_ref)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_timestamp_tolerance(config: Mapping[str, Any]) -> int:
    raw_value = config.get("timestamp_tolerance_seconds", 300)
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 300


def _parse_timestamp(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            stripped = value.strip()
            return stripped or None
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
