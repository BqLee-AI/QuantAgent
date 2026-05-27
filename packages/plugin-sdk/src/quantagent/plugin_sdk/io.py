from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, TypeAlias, runtime_checkable

from quantagent.plugin_sdk.runtime import PluginRuntimeError

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]

DTO_VALIDATION_ERROR_CODE = "PLUGIN_DTO_VALIDATION_FAILED"


def dto_validation_error(
    message: str,
    *,
    field_name: str | None = None,
    stage: str = "invoke",
    details: Mapping[str, JsonValue] | None = None,
) -> PluginRuntimeError:
    # Keep validation errors generic so runtime wrappers can surface structure without leaking payload contents.
    error_details = dict(details or {})
    if field_name is not None:
        error_details.setdefault("field", field_name)
    return PluginRuntimeError(
        code=DTO_VALIDATION_ERROR_CODE,
        message=message,
        stage=stage,
        details=freeze_json_mapping(error_details),
    )


def freeze_json_mapping(value: Mapping[str, Any] | None = None, *, stage: str = "invoke") -> JsonObject:
    normalized = {
        _validate_mapping_key(key, stage=stage): freeze_json_value(item, stage=stage)
        for key, item in (value or {}).items()
    }
    return MappingProxyType(normalized)


def freeze_json_value(value: Any, *, stage: str = "invoke") -> JsonValue:
    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        raise dto_validation_error(
            "Plugin DTO numbers must be finite JSON-safe values.",
            stage=stage,
            details={"value_type": type(value).__name__},
        )
    if isinstance(value, Mapping):
        return freeze_json_mapping(value, stage=stage)
    if isinstance(value, list | tuple):
        return tuple(freeze_json_value(item, stage=stage) for item in value)
    raise dto_validation_error(
        "Plugin DTO values must be JSON-safe scalars, arrays, or objects.",
        stage=stage,
        details={"value_type": type(value).__name__},
    )


def to_json_value(value: JsonValue) -> Any:
    if isinstance(value, Mapping):
        return {key: to_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    return value


@runtime_checkable
class PluginInput(Protocol):
    def to_mapping(self) -> dict[str, Any]: ...


@runtime_checkable
class PluginResult(Protocol):
    def to_mapping(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SourceFetchInput:
    query: str | None = None
    limit: int | None = None
    cursor: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_string("query", self.query)
        _validate_optional_int("limit", self.limit)
        _validate_optional_string("cursor", self.cursor)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "limit": self.limit,
            "cursor": self.cursor,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceFetchInput:
        _validate_object(payload, dto_name="SourceFetchInput", stage=stage)
        return cls(
            query=_get_optional_string(payload, "query", stage=stage),
            limit=_get_optional_int(payload, "limit", stage=stage),
            cursor=_get_optional_string(payload, "cursor", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class SourceItemDraft:
    external_id: str | None = None
    url: str | None = None
    title: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: str | None = None
    captured_at: str | None = None
    raw_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_string("external_id", self.external_id)
        _validate_optional_string("url", self.url)
        _validate_optional_string("title", self.title)
        _validate_optional_string("content", self.content)
        _validate_optional_string("author", self.author)
        _validate_optional_string("published_at", self.published_at)
        _validate_optional_string("captured_at", self.captured_at)
        object.__setattr__(self, "raw_payload", freeze_json_mapping(self.raw_payload))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published_at": self.published_at,
            "captured_at": self.captured_at,
            "raw_payload": to_json_value(self.raw_payload),
            "metadata": to_json_value(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceItemDraft:
        _validate_object(payload, dto_name="SourceItemDraft", stage=stage)
        return cls(
            external_id=_get_optional_string(payload, "external_id", stage=stage),
            url=_get_optional_string(payload, "url", stage=stage),
            title=_get_optional_string(payload, "title", stage=stage),
            content=_get_optional_string(payload, "content", stage=stage),
            author=_get_optional_string(payload, "author", stage=stage),
            published_at=_get_optional_string(payload, "published_at", stage=stage),
            captured_at=_get_optional_string(payload, "captured_at", stage=stage),
            raw_payload=freeze_json_mapping(_get_optional_mapping(payload, "raw_payload", stage=stage), stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class SourceFetchResult:
    items: tuple[SourceItemDraft, ...] = field(default_factory=tuple)
    next_cursor: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", _freeze_items(self.items))
        _validate_optional_string("next_cursor", self.next_cursor)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "items": [item.to_mapping() for item in self.items],
            "next_cursor": self.next_cursor,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceFetchResult:
        _validate_object(payload, dto_name="SourceFetchResult", stage=stage)
        if "items" not in payload:
            raise dto_validation_error(
                "SourceFetchResult.items is required.",
                field_name="items",
                stage=stage,
            )
        items = payload["items"]
        if not isinstance(items, list | tuple):
            raise dto_validation_error(
                "SourceFetchResult.items must be an array of SourceItemDraft objects.",
                field_name="items",
                stage=stage,
                details={"value_type": type(items).__name__},
            )
        return cls(
            items=tuple(
                item
                if isinstance(item, SourceItemDraft)
                else SourceItemDraft.from_mapping(_require_mapping(item, field_name="items", stage=stage), stage=stage)
                for item in items
            ),
            next_cursor=_get_optional_string(payload, "next_cursor", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class NotificationSendInput:
    channel: str
    text: str
    severity: str | None = None
    recipient: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("channel", self.channel)
        _validate_required_string("text", self.text)
        _validate_optional_string("severity", self.severity)
        _validate_optional_string("recipient", self.recipient)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "text": self.text,
            "severity": self.severity,
            "recipient": self.recipient,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> NotificationSendInput:
        _validate_object(payload, dto_name="NotificationSendInput", stage=stage)
        return cls(
            channel=_get_required_string(payload, "channel", stage=stage),
            text=_get_required_string(payload, "text", stage=stage),
            severity=_get_optional_string(payload, "severity", stage=stage),
            recipient=_get_optional_string(payload, "recipient", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class NotificationSendResult:
    accepted: bool
    provider_message_id: str | None = None
    retryable: bool = False
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_bool("accepted", self.accepted)
        _validate_optional_string("provider_message_id", self.provider_message_id)
        _validate_bool("retryable", self.retryable)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "provider_message_id": self.provider_message_id,
            "retryable": self.retryable,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> NotificationSendResult:
        _validate_object(payload, dto_name="NotificationSendResult", stage=stage)
        return cls(
            accepted=_get_required_bool(payload, "accepted", stage=stage),
            provider_message_id=_get_optional_string(payload, "provider_message_id", stage=stage),
            retryable=_get_required_bool(payload, "retryable", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


def _freeze_items(items: tuple[SourceItemDraft, ...] | list[SourceItemDraft]) -> tuple[SourceItemDraft, ...]:
    if not isinstance(items, list | tuple):
        raise dto_validation_error(
            "SourceFetchResult.items must be an array of SourceItemDraft objects.",
            field_name="items",
            details={"value_type": type(items).__name__},
        )
    frozen_items: list[SourceItemDraft] = []
    for item in items:
        if not isinstance(item, SourceItemDraft):
            raise dto_validation_error(
                "SourceFetchResult.items must contain SourceItemDraft instances.",
                field_name="items",
                details={"value_type": type(item).__name__},
            )
        frozen_items.append(item)
    return tuple(frozen_items)


def _validate_object(payload: Mapping[str, Any], *, dto_name: str, stage: str) -> None:
    if not isinstance(payload, Mapping):
        raise dto_validation_error(
            f"{dto_name} payload must be an object mapping.",
            stage=stage,
            details={"value_type": type(payload).__name__},
        )


def _validate_mapping_key(key: Any, *, stage: str) -> str:
    if not isinstance(key, str):
        raise dto_validation_error(
            "Plugin DTO object keys must be strings.",
            stage=stage,
            details={"key_type": type(key).__name__},
        )
    return key


def _validate_required_string(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if not isinstance(value, str):
        raise dto_validation_error(
            f"{field_name} must be a string.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_optional_string(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if value is not None and not isinstance(value, str):
        raise dto_validation_error(
            f"{field_name} must be a string or null.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_optional_int(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise dto_validation_error(
            f"{field_name} must be an integer or null.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_bool(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if not isinstance(value, bool):
        raise dto_validation_error(
            f"{field_name} must be a boolean.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _get_required_string(payload: Mapping[str, Any], field_name: str, *, stage: str) -> str:
    if field_name not in payload:
        raise dto_validation_error(
            f"{field_name} is required.",
            field_name=field_name,
            stage=stage,
        )
    value = payload[field_name]
    _validate_required_string(field_name, value, stage=stage)
    return value


def _get_optional_string(payload: Mapping[str, Any], field_name: str, *, stage: str) -> str | None:
    value = payload.get(field_name)
    _validate_optional_string(field_name, value, stage=stage)
    return value


def _get_optional_int(payload: Mapping[str, Any], field_name: str, *, stage: str) -> int | None:
    value = payload.get(field_name)
    _validate_optional_int(field_name, value, stage=stage)
    return value


def _get_required_bool(payload: Mapping[str, Any], field_name: str, *, stage: str) -> bool:
    if field_name not in payload:
        raise dto_validation_error(
            f"{field_name} is required.",
            field_name=field_name,
            stage=stage,
        )
    value = payload[field_name]
    _validate_bool(field_name, value, stage=stage)
    return value


def _get_optional_mapping(payload: Mapping[str, Any], field_name: str, *, stage: str) -> Mapping[str, Any]:
    value = payload.get(field_name, {})
    return _require_mapping(value, field_name=field_name, stage=stage)


def _require_mapping(value: Any, *, field_name: str, stage: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise dto_validation_error(
        f"{field_name} must be an object mapping.",
        field_name=field_name,
        stage=stage,
        details={"value_type": type(value).__name__},
    )
