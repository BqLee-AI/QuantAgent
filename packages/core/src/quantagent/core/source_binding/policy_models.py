from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quantagent.plugin_sdk import JsonObject, freeze_json_mapping


def _require_positive_int(field_name: str, value: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def _require_non_negative_int(field_name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")


def _require_non_negative_number(field_name: str, value: float | int) -> None:
    if not isinstance(value, int | float) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number.")


def _coerce_optional_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> JsonObject:
    if value is None:
        return freeze_json_mapping({}, stage=field_name)
    return freeze_json_mapping(value, stage=field_name)


def _reject_unknown_fields(payload: Mapping[str, Any], *, field_name: str, allowed_fields: set[str]) -> None:
    unknown_fields = sorted(key for key in payload if key not in allowed_fields)
    if unknown_fields:
        raise ValueError(f"{field_name} contains unsupported fields: {', '.join(unknown_fields)}")


@dataclass(frozen=True)
class SchedulePolicyHint:
    interval_seconds: int
    jitter_seconds: int = 0
    enabled: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_positive_int("interval_seconds", self.interval_seconds)
        _require_non_negative_int("jitter_seconds", self.jitter_seconds)
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean.")
        object.__setattr__(self, "metadata", _coerce_optional_mapping(self.metadata, field_name="schedule_policy"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "interval_seconds": self.interval_seconds,
            "jitter_seconds": self.jitter_seconds,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SchedulePolicyHint:
        _reject_unknown_fields(
            payload,
            field_name="schedule_policy",
            allowed_fields={"interval_seconds", "jitter_seconds", "enabled", "metadata"},
        )
        if "interval_seconds" not in payload:
            raise ValueError("schedule_policy.interval_seconds is required.")
        return cls(
            interval_seconds=payload["interval_seconds"],
            jitter_seconds=payload.get("jitter_seconds", 0),
            enabled=payload.get("enabled", True),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True)
class RetryPolicyHint:
    max_attempts: int
    backoff_seconds: float = 0
    max_backoff_seconds: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_positive_int("max_attempts", self.max_attempts)
        _require_non_negative_number("backoff_seconds", self.backoff_seconds)
        if self.max_backoff_seconds is not None:
            _require_non_negative_number("max_backoff_seconds", self.max_backoff_seconds)
            if self.max_backoff_seconds < self.backoff_seconds:
                raise ValueError("max_backoff_seconds must be greater than or equal to backoff_seconds.")
        object.__setattr__(self, "metadata", _coerce_optional_mapping(self.metadata, field_name="retry_policy"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "backoff_seconds": self.backoff_seconds,
            "max_backoff_seconds": self.max_backoff_seconds,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RetryPolicyHint:
        _reject_unknown_fields(
            payload,
            field_name="retry_policy",
            allowed_fields={"max_attempts", "backoff_seconds", "max_backoff_seconds", "metadata"},
        )
        if "max_attempts" not in payload:
            raise ValueError("retry_policy.max_attempts is required.")
        return cls(
            max_attempts=payload["max_attempts"],
            backoff_seconds=payload.get("backoff_seconds", 0),
            max_backoff_seconds=payload.get("max_backoff_seconds"),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True)
class RateLimitPolicyHint:
    requests_per_window: int
    window_seconds: int
    scope: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_positive_int("requests_per_window", self.requests_per_window)
        _require_positive_int("window_seconds", self.window_seconds)
        if self.scope is not None and (not isinstance(self.scope, str) or not self.scope.strip()):
            raise ValueError("scope must be a non-empty string when provided.")
        object.__setattr__(self, "metadata", _coerce_optional_mapping(self.metadata, field_name="rate_limit_policy"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "requests_per_window": self.requests_per_window,
            "window_seconds": self.window_seconds,
            "scope": self.scope,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RateLimitPolicyHint:
        _reject_unknown_fields(
            payload,
            field_name="rate_limit_policy",
            allowed_fields={"requests_per_window", "window_seconds", "scope", "metadata"},
        )
        if "requests_per_window" not in payload:
            raise ValueError("rate_limit_policy.requests_per_window is required.")
        if "window_seconds" not in payload:
            raise ValueError("rate_limit_policy.window_seconds is required.")
        return cls(
            requests_per_window=payload["requests_per_window"],
            window_seconds=payload["window_seconds"],
            scope=payload.get("scope"),
            metadata=payload.get("metadata") or {},
        )
