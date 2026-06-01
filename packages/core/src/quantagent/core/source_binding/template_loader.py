from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quantagent.core.source_binding.policy_models import (
    RateLimitPolicyHint,
    RetryPolicyHint,
    SchedulePolicyHint,
)
from quantagent.core.source_binding.template_models import SourceBindingTemplate


class SourceBindingTemplateLoader:
    """将行业包侧声明归一化为平台模板对象。"""

    _ALLOWED_KEYS = frozenset(
        {
            "source_plugin_id",
            "required",
            "config_template",
            "config_template_ref",
            "config_override",
            "schedule_policy_hint",
            "retry_policy_hint",
            "rate_limit_policy_hint",
            "metadata",
        }
    )

    def normalize(self, declaration: Mapping[str, Any]) -> SourceBindingTemplate:
        unknown_keys = sorted(set(declaration) - self._ALLOWED_KEYS)
        if unknown_keys:
            raise ValueError(f"Unsupported source binding template fields: {', '.join(unknown_keys)}")

        source_plugin_id = declaration.get("source_plugin_id")
        required = declaration.get("required")
        if source_plugin_id is None:
            raise ValueError("source_plugin_id is required.")
        if required is None:
            raise ValueError("required is required.")

        config_template_ref = declaration.get("config_template_ref") or declaration.get("config_template")
        config_override = declaration.get("config_override") or {}
        if not isinstance(config_override, Mapping):
            raise ValueError("config_override must be an object when provided.")

        return SourceBindingTemplate(
            source_plugin_id=source_plugin_id,
            required=required,
            config_template_ref=config_template_ref,
            config_override=config_override,
            schedule_policy_hint=self._load_schedule_policy(declaration.get("schedule_policy_hint")),
            retry_policy_hint=self._load_retry_policy(declaration.get("retry_policy_hint")),
            rate_limit_policy_hint=self._load_rate_limit_policy(declaration.get("rate_limit_policy_hint")),
            metadata=declaration.get("metadata") or {},
        )

    @staticmethod
    def _load_schedule_policy(value: Any) -> SchedulePolicyHint | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("schedule_policy_hint must be an object when provided.")
        return SchedulePolicyHint.from_mapping(value)

    @staticmethod
    def _load_retry_policy(value: Any) -> RetryPolicyHint | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("retry_policy_hint must be an object when provided.")
        return RetryPolicyHint.from_mapping(value)

    @staticmethod
    def _load_rate_limit_policy(value: Any) -> RateLimitPolicyHint | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("rate_limit_policy_hint must be an object when provided.")
        return RateLimitPolicyHint.from_mapping(value)
