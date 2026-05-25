from __future__ import annotations

from dataclasses import dataclass
import json
import socket
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request


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


class DiscordWebhookNotificationPlugin:
    """Standalone experimental sender for Discord webhook notifications."""

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
                "User-Agent": "QuantAgent-DiscordWebhook/0.1",
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


def _resolve_secret(secret_ref: str, secrets: Mapping[str, str] | None) -> str | None:
    if secrets is None:
        return None
    value = secrets.get(secret_ref)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _resolve_timeout(config: Mapping[str, Any], timeout_override: float | None) -> float:
    if timeout_override is not None:
        return max(timeout_override, 0.1)
    raw_timeout = config.get("timeout_seconds", 5)
    try:
        return max(float(raw_timeout), 0.1)
    except (TypeError, ValueError):
        return 5.0


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


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _excerpt(value: str, limit: int = 120) -> str | None:
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= limit:
        return trimmed
    return f"{trimmed[:limit]}..."


plugin = DiscordWebhookNotificationPlugin()
