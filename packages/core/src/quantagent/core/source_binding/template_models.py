from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quantagent.core.source_binding.policy_models import (
    RateLimitPolicyHint,
    RetryPolicyHint,
    SchedulePolicyHint,
)
from quantagent.plugin_sdk import JsonObject, freeze_json_mapping


@dataclass(frozen=True)
class SecretValueRef:
    secret_ref: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.secret_ref, str) or not self.secret_ref.strip():
            raise ValueError("secret_ref must be a non-empty string.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="secret_ref"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "secret_ref": self.secret_ref,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SecretValueRef:
        if "secret_ref" not in payload:
            raise ValueError("secret_ref.secret_ref is required.")
        return cls(
            secret_ref=payload["secret_ref"],
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True)
class SourceBindingTemplate:
    source_plugin_id: str
    required: bool
    config_template_ref: str | None = None
    config_override: JsonObject = field(default_factory=dict)
    schedule_policy_hint: SchedulePolicyHint | None = None
    retry_policy_hint: RetryPolicyHint | None = None
    rate_limit_policy_hint: RateLimitPolicyHint | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_plugin_id, str) or not self.source_plugin_id.strip():
            raise ValueError("source_plugin_id must be a non-empty string.")
        if not isinstance(self.required, bool):
            raise ValueError("required must be a boolean.")
        if self.config_template_ref is not None and (
            not isinstance(self.config_template_ref, str) or not self.config_template_ref.strip()
        ):
            raise ValueError("config_template_ref must be a non-empty string when provided.")
        object.__setattr__(self, "config_override", freeze_json_mapping(self.config_override, stage="config"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="template"))

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_plugin_id": self.source_plugin_id,
            "required": self.required,
            "config_template_ref": self.config_template_ref,
            "config_override": dict(self.config_override),
            "metadata": dict(self.metadata),
        }
        if self.schedule_policy_hint is not None:
            payload["schedule_policy_hint"] = self.schedule_policy_hint.to_mapping()
        if self.retry_policy_hint is not None:
            payload["retry_policy_hint"] = self.retry_policy_hint.to_mapping()
        if self.rate_limit_policy_hint is not None:
            payload["rate_limit_policy_hint"] = self.rate_limit_policy_hint.to_mapping()
        return payload
