from __future__ import annotations

from quantagent.core.events import EventEnvelope
from quantagent.core.worker_routing.models import CapturedSourceEventInput


def decode_captured_source_event(envelope: EventEnvelope) -> CapturedSourceEventInput:
    payload = dict(envelope.payload)
    headers = dict(envelope.headers)
    binding_id = _read_optional_string(payload, headers, "binding_id")
    request_id = _read_optional_string(headers, payload, "request_id")
    plugin_id = _read_optional_string(payload, headers, "plugin_id")
    item_count = _read_item_count(payload, headers)
    return CapturedSourceEventInput(
        message_id=envelope.id,
        topic=envelope.topic,
        binding_id=binding_id,
        request_id=request_id,
        plugin_id=plugin_id,
        item_count=item_count,
        correlation_id=envelope.correlation_id,
        causation_id=envelope.causation_id,
        payload=payload,
        headers=headers,
    )


def _read_optional_string(primary: dict[str, object], secondary: dict[str, object], key: str) -> str | None:
    value = primary.get(key, secondary.get(key))
    if isinstance(value, str) and value.strip():
        return value
    return None


def _read_item_count(payload: dict[str, object], headers: dict[str, object]) -> int:
    header_count = headers.get("item_count")
    if isinstance(header_count, int) and header_count >= 0:
        return header_count
    items = payload.get("items")
    if isinstance(items, tuple | list):
        return len(items)
    return 0
