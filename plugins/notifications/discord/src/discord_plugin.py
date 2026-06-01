from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from quantagent.plugin_sdk import (
    BasePlugin,
    NotificationReceiveInput,
    NotificationReceiveItem,
    NotificationReceiveResult,
    NotificationSendInput,
    NotificationSendResult,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
)


SIGNATURE_HEADER = "x-signature-ed25519"
TIMESTAMP_HEADER = "x-signature-timestamp"
PING_TYPE = 1
APPLICATION_COMMAND_TYPE = 2
PONG_RESPONSE = {"type": 1}
CHANNEL_MESSAGE_WITH_SOURCE = 4
EPHEMERAL_FLAG = 64

Transport = Callable[["DiscordWebhookRequest"], "DiscordWebhookResponse"]


@dataclass(frozen=True)
class DiscordWebhookRequest:
    url: str
    body: bytes
    headers: Mapping[str, str]
    timeout_seconds: float


@dataclass(frozen=True)
class DiscordWebhookResponse:
    status_code: int
    body: str = ""


@dataclass(frozen=True)
class SendResult:
    ok: bool
    code: str
    message: str
    retryable: bool = False
    http_status: int | None = None
    webhook_secret_ref: str | None = None
    response_excerpt: str | None = None


class DiscordPlugin(BasePlugin):
    """Unified experimental Discord plugin for low-risk send and receive flows."""

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        if request.capability == "notification.send":
            return self._invoke_send(request)
        if request.capability == "notification.receive":
            return self._invoke_receive(request)
        raise PluginRuntimeError(
            code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
            message="Discord plugin only implements notification.send and notification.receive.",
            stage="invoke",
            details={"capability": request.capability},
        )

    def _invoke_send(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        payload = NotificationSendInput.from_mapping(request.input)
        config = _merge_effective_config(self.context.config, payload.metadata.get("config_override"))
        result = self.send_text(
            config,
            payload.text,
            secrets=_resolve_runtime_secrets(self.context.config),
        )
        output = NotificationSendResult(
            accepted=result.ok,
            retryable=result.retryable,
            metadata={
                "code": result.code,
                "message": result.message,
                "http_status": result.http_status,
                "webhook_secret_ref": result.webhook_secret_ref,
                "response_excerpt": result.response_excerpt,
            },
        )
        return PluginInvokeResult(output=output.to_mapping())

    def _invoke_receive(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        payload = NotificationReceiveInput.from_mapping(request.input)
        config = _merge_effective_config(self.context.config, payload.config_override)
        headers = _mapping(payload.headers)
        body_text = payload.body_text
        if body_text is None:
            raise PluginRuntimeError(
                code="PLUGIN_INVALID_INPUT",
                message="notification.receive body_text must be a utf-8 string.",
                stage="invoke",
                details={"field": "body_text"},
            )
        result = self.receive_request(
            config,
            headers,
            body_text.encode("utf-8"),
            secrets=_resolve_runtime_secrets(self.context.config),
        )
        output = NotificationReceiveResult(
            accepted=result.accepted,
            code=result.code,
            message=result.message,
            response_status_code=result.response_status_code,
            response=result.response,
            item=result.item,
            retryable=result.retryable,
            metadata=result.metadata,
        )
        return PluginInvokeResult(output=output.to_mapping())

    def build_payload(self, text: str) -> dict[str, str]:
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Notification text must be a non-empty string.")
        return {"content": normalized_text}

    def send_text(
        self,
        config: Mapping[str, Any],
        text: str,
        *,
        secrets: Mapping[str, str] | None = None,
        transport: Transport | None = None,
        timeout_seconds: float | None = None,
    ) -> SendResult:
        webhook_secret_ref = _optional_str(config.get("webhook_secret_ref"))
        if webhook_secret_ref is None:
            return SendResult(
                ok=False,
                code="MISSING_CONFIG",
                message="Missing required config field: webhook_secret_ref.",
            )

        webhook_url = _resolve_secret(webhook_secret_ref, secrets)
        if webhook_url is None:
            return SendResult(
                ok=False,
                code="SECRET_NOT_RESOLVED",
                message="Webhook secret reference could not be resolved.",
                webhook_secret_ref=webhook_secret_ref,
            )

        if not _is_allowed_webhook_url(webhook_url):
            return SendResult(
                ok=False,
                code="INVALID_WEBHOOK_URL",
                message="Discord webhook URL must use https scheme.",
                webhook_secret_ref=webhook_secret_ref,
            )

        try:
            payload = self.build_payload(text)
        except ValueError as exc:
            return SendResult(
                ok=False,
                code="INVALID_MESSAGE",
                message=str(exc),
                webhook_secret_ref=webhook_secret_ref,
            )

        request = DiscordWebhookRequest(
            url=webhook_url,
            body=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "QuantAgent-Discord/0.1",
            },
            timeout_seconds=_resolve_timeout(config, timeout_seconds),
        )

        transport_impl = transport or _default_transport
        try:
            response = transport_impl(request)
        except TimeoutError:
            return SendResult(
                ok=False,
                code="NETWORK_TIMEOUT",
                message="Discord webhook request timed out.",
                retryable=True,
                webhook_secret_ref=webhook_secret_ref,
            )
        except OSError as exc:
            return SendResult(
                ok=False,
                code="NETWORK_ERROR",
                message=f"Discord webhook request failed: {exc.__class__.__name__}.",
                retryable=True,
                webhook_secret_ref=webhook_secret_ref,
            )

        if 200 <= response.status_code < 300:
            return SendResult(
                ok=True,
                code="SENT",
                message="Discord webhook notification sent.",
                http_status=response.status_code,
                webhook_secret_ref=webhook_secret_ref,
            )

        return SendResult(
            ok=False,
            code="UPSTREAM_ERROR",
            message="Discord webhook rejected the notification request.",
            http_status=response.status_code,
            webhook_secret_ref=webhook_secret_ref,
            response_excerpt=_excerpt(response.body),
        )

    def receive_request(
        self,
        config: Mapping[str, Any],
        headers: Mapping[str, str],
        body: bytes,
        *,
        secrets: Mapping[str, str] | None = None,
    ) -> NotificationReceiveResult:
        public_key = _resolve_public_key(config, secrets)
        if public_key is None:
            return NotificationReceiveResult(
                accepted=False,
                code="MISSING_CONFIG",
                message="Missing Discord interactions public key configuration.",
                response_status_code=503,
                response={"error": "MISSING_CONFIG", "message": "Missing Discord interactions public key configuration."},
            )

        signature = _get_header(headers, SIGNATURE_HEADER)
        timestamp = _get_header(headers, TIMESTAMP_HEADER)
        if signature is None or timestamp is None:
            return NotificationReceiveResult(
                accepted=False,
                code="SIGNATURE_MISSING",
                message="Missing required Discord signature headers.",
                response_status_code=401,
                response={"error": "SIGNATURE_MISSING", "message": "Missing required Discord signature headers."},
            )

        timestamp_seconds = _parse_timestamp(timestamp)
        if timestamp_seconds is None:
            return NotificationReceiveResult(
                accepted=False,
                code="TIMESTAMP_INVALID",
                message="Discord signature timestamp is invalid.",
                response_status_code=401,
                response={"error": "TIMESTAMP_INVALID", "message": "Discord signature timestamp is invalid."},
            )

        if not is_timestamp_fresh(
            timestamp_seconds,
            tolerance_seconds=_resolve_timestamp_tolerance(config),
        ):
            return NotificationReceiveResult(
                accepted=False,
                code="TIMESTAMP_INVALID",
                message="Discord signature timestamp is outside the accepted tolerance window.",
                response_status_code=401,
                response={
                    "error": "TIMESTAMP_INVALID",
                    "message": "Discord signature timestamp is outside the accepted tolerance window.",
                },
            )

        if not verify_discord_request(body, timestamp, signature, public_key):
            return NotificationReceiveResult(
                accepted=False,
                code="SIGNATURE_INVALID",
                message="Discord request signature validation failed.",
                response_status_code=401,
                response={"error": "SIGNATURE_INVALID", "message": "Discord request signature validation failed."},
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return NotificationReceiveResult(
                accepted=False,
                code="PAYLOAD_INVALID",
                message="Request body is not valid JSON.",
                response_status_code=400,
                response={"error": "PAYLOAD_INVALID", "message": "Request body is not valid JSON."},
            )

        if not isinstance(payload, dict):
            return NotificationReceiveResult(
                accepted=False,
                code="PAYLOAD_INVALID",
                message="Request payload must be a JSON object.",
                response_status_code=400,
                response={"error": "PAYLOAD_INVALID", "message": "Request payload must be a JSON object."},
            )

        payload_type = payload.get("type")
        if payload_type == PING_TYPE:
            return NotificationReceiveResult(
                accepted=True,
                code="PING",
                message="Discord interaction ping acknowledged.",
                response_status_code=200,
                response=PONG_RESPONSE,
            )

        if payload_type != APPLICATION_COMMAND_TYPE:
            return NotificationReceiveResult(
                accepted=False,
                code="UNSUPPORTED_EVENT_TYPE",
                message="Only application command interactions are supported in v1.",
                response_status_code=400,
                response={"error": "UNSUPPORTED_EVENT_TYPE", "message": "Only application command interactions are supported in v1."},
            )

        guild_id = _optional_str(payload.get("guild_id"))
        guild_allowlist = _normalized_allowlist(config.get("guild_allowlist"))
        if guild_allowlist and guild_id not in guild_allowlist:
            return NotificationReceiveResult(
                accepted=False,
                code="GUILD_NOT_ALLOWED",
                message="Interaction guild is not allowed by this plugin config.",
                response_status_code=400,
                response={"error": "GUILD_NOT_ALLOWED", "message": "Interaction guild is not allowed by this plugin config."},
            )

        channel_id = _optional_str(payload.get("channel_id"))
        channel_allowlist = _normalized_allowlist(config.get("channel_allowlist"))
        if channel_allowlist and channel_id not in channel_allowlist:
            return NotificationReceiveResult(
                accepted=False,
                code="CHANNEL_NOT_ALLOWED",
                message="Interaction channel is not allowed by this plugin config.",
                response_status_code=400,
                response={"error": "CHANNEL_NOT_ALLOWED", "message": "Interaction channel is not allowed by this plugin config."},
            )

        text = _extract_text(payload)
        if text is None:
            return NotificationReceiveResult(
                accepted=False,
                code="PAYLOAD_UNSUPPORTED",
                message="Interaction payload does not include a supported text option.",
                response_status_code=400,
                response={
                    "error": "PAYLOAD_UNSUPPORTED",
                    "message": "Interaction payload does not include a supported text option.",
                },
            )

        item = NotificationReceiveItem(
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
            metadata={"plugin_id": self.context.plugin_id if self._context is not None else "quantagent.official.notification.discord"},
        )

        response_text = _optional_str(config.get("response_text")) or "QuantAgent received your Discord interaction."
        response = {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "content": response_text,
                "flags": EPHEMERAL_FLAG,
            },
        }
        return NotificationReceiveResult(
            accepted=True,
            code="RECEIVED",
            message="Discord interaction webhook payload received.",
            response_status_code=200,
            response=response,
            item=item,
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


def _resolve_secret(secret_ref: str, secrets: Mapping[str, str] | None) -> str | None:
    if secrets is None:
        return None
    value = secrets.get(secret_ref)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _is_allowed_webhook_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _resolve_public_key(config: Mapping[str, Any], secrets: Mapping[str, str] | None) -> str | None:
    public_key = _optional_str(config.get("public_key"))
    if public_key is not None:
        return public_key
    public_key_ref = _optional_str(config.get("public_key_ref"))
    if public_key_ref is None:
        return None
    return _resolve_secret(public_key_ref, secrets)


def _resolve_timeout(config: Mapping[str, Any], timeout_override: float | None) -> float:
    if timeout_override is not None:
        return max(timeout_override, 0.1)
    raw_timeout = config.get("timeout_seconds", 5)
    try:
        return max(float(raw_timeout), 0.1)
    except (TypeError, ValueError):
        return 5.0


def _resolve_timestamp_tolerance(config: Mapping[str, Any]) -> int:
    raw_value = config.get("timestamp_tolerance_seconds", 300)
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 300


def _default_transport(request: DiscordWebhookRequest) -> DiscordWebhookResponse:
    http_request = urllib.request.Request(
        request.url,
        data=request.body,
        headers=dict(request.headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=request.timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return DiscordWebhookResponse(status_code=response.status, body=response_body)
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        return DiscordWebhookResponse(status_code=exc.code, body=response_body)
    except socket.timeout as exc:
        raise TimeoutError("Timed out while sending Discord webhook request.") from exc


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
    if isinstance(value, Mapping):
        return value
    return {}


def _excerpt(value: str, limit: int = 120) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= limit:
        return trimmed
    return f"{trimmed[:limit]}..."


plugin = DiscordPlugin


def _merge_effective_config(context_config: Mapping[str, Any], override: Any) -> dict[str, Any]:
    if isinstance(override, Mapping):
        return {**context_config, **override}
    return dict(context_config)


def _resolve_runtime_secrets(config: Mapping[str, Any]) -> Mapping[str, str] | None:
    secrets = config.get("__secrets__")
    if isinstance(secrets, Mapping):
        return {str(key): str(value) for key, value in secrets.items()}
    return None
