from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from quantagent.core.source_binding.policy_models import (
    RateLimitPolicyHint,
    RetryPolicyHint,
    SchedulePolicyHint,
)
from quantagent.core.source_binding.template_models import SecretValueRef, SourceBindingTemplate
from quantagent.plugin_sdk import JsonObject, JsonValue, freeze_json_mapping, to_json_value


STRUCTURED_SECRET_REF_PATTERN = re.compile(r"^[a-z0-9+._-]+://.+$", re.IGNORECASE)


def extract_defaults_from_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    schema_type = schema.get("type")
    if schema_type != "object":
        return {}

    defaults: dict[str, Any] = {}
    for key, field_schema in _schema_properties(schema).items():
        if not isinstance(field_schema, Mapping):
            continue
        if "default" in field_schema:
            defaults[key] = _clone_json_like(field_schema["default"])
            continue
        nested_default = extract_defaults_from_schema(field_schema)
        if nested_default:
            defaults[key] = nested_default
    return defaults


@dataclass(frozen=True)
class EffectiveSourceConfig:
    source_plugin_id: str
    config: JsonObject = field(default_factory=dict)
    schedule_policy: SchedulePolicyHint | None = None
    retry_policy: RetryPolicyHint | None = None
    rate_limit_policy: RateLimitPolicyHint | None = None
    config_fingerprint: str = ""
    source_schema_version: str | None = None
    template_refs: JsonObject = field(default_factory=dict)
    validated_at: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_plugin_id, str) or not self.source_plugin_id.strip():
            raise ValueError("source_plugin_id must be a non-empty string.")
        if not isinstance(self.config_fingerprint, str) or not self.config_fingerprint.strip():
            raise ValueError("config_fingerprint must be a non-empty string.")
        if not isinstance(self.validated_at, str) or not self.validated_at.strip():
            raise ValueError("validated_at must be a non-empty string.")
        object.__setattr__(self, "config", freeze_json_mapping(self.config, stage="config"))
        object.__setattr__(self, "template_refs", freeze_json_mapping(self.template_refs, stage="config"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="config"))

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_plugin_id": self.source_plugin_id,
            "config": to_json_value(self.config),
            "config_fingerprint": self.config_fingerprint,
            "source_schema_version": self.source_schema_version,
            "template_refs": to_json_value(self.template_refs),
            "validated_at": self.validated_at,
            "metadata": to_json_value(self.metadata),
        }
        if self.schedule_policy is not None:
            payload["schedule_policy"] = self.schedule_policy.to_mapping()
        if self.retry_policy is not None:
            payload["retry_policy"] = self.retry_policy.to_mapping()
        if self.rate_limit_policy is not None:
            payload["rate_limit_policy"] = self.rate_limit_policy.to_mapping()
        return payload

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> EffectiveSourceConfig:
        _validate_effective_config_payload(payload)
        config = payload.get("config")
        if not isinstance(config, Mapping):
            raise ValueError("EffectiveSourceConfig.config must be an object.")
        template_refs = payload.get("template_refs") or {}
        if not isinstance(template_refs, Mapping):
            raise ValueError("EffectiveSourceConfig.template_refs must be an object.")
        return cls(
            source_plugin_id=payload.get("source_plugin_id"),
            config=config,
            schedule_policy=_optional_schedule_policy(payload.get("schedule_policy")),
            retry_policy=_optional_retry_policy(payload.get("retry_policy")),
            rate_limit_policy=_optional_rate_limit_policy(payload.get("rate_limit_policy")),
            config_fingerprint=payload.get("config_fingerprint"),
            source_schema_version=payload.get("source_schema_version"),
            template_refs=template_refs,
            validated_at=payload.get("validated_at"),
            metadata=payload.get("metadata") or {},
        )


@dataclass(frozen=True)
class ResolvedSourceExecutionConfig:
    config: JsonObject = field(default_factory=dict)
    schedule_policy: SchedulePolicyHint | None = None
    retry_policy: RetryPolicyHint | None = None
    rate_limit_policy: RateLimitPolicyHint | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", freeze_json_mapping(self.config, stage="config"))

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"config": to_json_value(self.config)}
        if self.schedule_policy is not None:
            payload["schedule_policy"] = self.schedule_policy.to_mapping()
        if self.retry_policy is not None:
            payload["retry_policy"] = self.retry_policy.to_mapping()
        if self.rate_limit_policy is not None:
            payload["rate_limit_policy"] = self.rate_limit_policy.to_mapping()
        return payload


class EffectiveSourceConfigComposer:
    def compose(
        self,
        *,
        template: SourceBindingTemplate,
        plugin_schema: Mapping[str, Any],
        template_assets: Mapping[str, Mapping[str, Any]] | None = None,
        source_defaults: Mapping[str, Any] | None = None,
        source_schema_version: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        validated_at: datetime | None = None,
    ) -> EffectiveSourceConfig:
        resolved_defaults = dict(source_defaults or extract_defaults_from_schema(plugin_schema))
        resolved_template_asset = self._resolve_template_asset(
            template.config_template_ref,
            template_assets=template_assets,
        )
        merged_config = _deep_merge(resolved_defaults, resolved_template_asset)
        merged_config = _deep_merge(merged_config, dict(template.config_override))
        validated_config = _validate_schema(
            merged_config,
            plugin_schema,
            path="config",
        )

        refs = {
            "config_template_ref": template.config_template_ref,
            "layers": (
                "source_defaults",
                "config_template_ref" if template.config_template_ref else "no_config_template_ref",
                "config_override",
            ),
        }
        timestamp = (validated_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        fingerprint = _fingerprint_payload(
            {
                "source_plugin_id": template.source_plugin_id,
                "config": validated_config,
                "schedule_policy": template.schedule_policy_hint.to_mapping() if template.schedule_policy_hint else None,
                "retry_policy": template.retry_policy_hint.to_mapping() if template.retry_policy_hint else None,
                "rate_limit_policy": template.rate_limit_policy_hint.to_mapping() if template.rate_limit_policy_hint else None,
                "source_schema_version": source_schema_version,
                "template_refs": refs,
            }
        )
        return EffectiveSourceConfig(
            source_plugin_id=template.source_plugin_id,
            config=validated_config,
            schedule_policy=template.schedule_policy_hint,
            retry_policy=template.retry_policy_hint,
            rate_limit_policy=template.rate_limit_policy_hint,
            config_fingerprint=fingerprint,
            source_schema_version=source_schema_version,
            template_refs=refs,
            validated_at=timestamp,
            metadata=metadata or {},
        )

    @staticmethod
    def _resolve_template_asset(
        template_ref: str | None,
        *,
        template_assets: Mapping[str, Mapping[str, Any]] | None,
    ) -> dict[str, Any]:
        if template_ref is None:
            return {}
        if template_assets is None or template_ref not in template_assets:
            raise ValueError(f"Unknown config_template_ref: {template_ref}")
        template_asset = template_assets[template_ref]
        if not isinstance(template_asset, Mapping):
            raise ValueError("Template asset must be an object.")
        return dict(template_asset)


def is_effective_source_config_mapping(value: Mapping[str, Any]) -> bool:
    try:
        _validate_effective_config_payload(value)
    except ValueError:
        return False
    return True


def build_runtime_source_config(value: Mapping[str, Any] | EffectiveSourceConfig) -> JsonObject:
    snapshot = _coerce_effective_config(value)
    return freeze_json_mapping(snapshot.config, stage="config")


def resolve_runtime_source_config(
    value: Mapping[str, Any] | EffectiveSourceConfig,
    *,
    secret_resolver: Callable[[str], Any],
) -> ResolvedSourceExecutionConfig:
    snapshot = _coerce_effective_config(value)
    # 为什么这里单独做运行时解引用：审计快照必须保留 secret ref，避免 scheduler / ORM / API 看到明文。
    resolved_config = _resolve_secret_refs(snapshot.config, secret_resolver=secret_resolver)
    return ResolvedSourceExecutionConfig(
        config=resolved_config,
        schedule_policy=snapshot.schedule_policy,
        retry_policy=snapshot.retry_policy,
        rate_limit_policy=snapshot.rate_limit_policy,
    )


def _coerce_effective_config(value: Mapping[str, Any] | EffectiveSourceConfig) -> EffectiveSourceConfig:
    if isinstance(value, EffectiveSourceConfig):
        return value
    return EffectiveSourceConfig.from_mapping(value)


def _validate_effective_config_payload(payload: Mapping[str, Any]) -> None:
    required_fields = {
        "source_plugin_id",
        "config",
        "config_fingerprint",
        "template_refs",
        "validated_at",
    }
    missing_fields = sorted(field for field in required_fields if field not in payload)
    if missing_fields:
        raise ValueError(f"EffectiveSourceConfig is missing required fields: {', '.join(missing_fields)}")

    unknown_fields = sorted(
        key
        for key in payload
        if key
        not in {
            "source_plugin_id",
            "config",
            "schedule_policy",
            "retry_policy",
            "rate_limit_policy",
            "config_fingerprint",
            "source_schema_version",
            "template_refs",
            "validated_at",
            "metadata",
        }
    )
    if unknown_fields:
        raise ValueError(f"EffectiveSourceConfig contains unsupported fields: {', '.join(unknown_fields)}")


def _schema_properties(schema: Mapping[str, Any]) -> Mapping[str, Any]:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return {}
    return properties


def _validate_schema(value: Any, schema: Mapping[str, Any], *, path: str) -> Any:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        if value is None and "null" in schema_type:
            return None
        allowed_types = [item for item in schema_type if item != "null"]
        if len(allowed_types) != 1:
            raise ValueError(f"{path} uses an unsupported type union.")
        schema = dict(schema)
        schema["type"] = allowed_types[0]
        return _validate_schema(value, schema, path=path)

    if value is None:
        raise ValueError(f"{path} does not allow null.")

    if schema_type == "object":
        if not isinstance(value, Mapping):
            raise ValueError(f"{path} must be an object.")
        properties = _schema_properties(schema)
        required = schema.get("required") or []
        if not isinstance(required, list):
            raise ValueError(f"{path}.required must be an array.")
        normalized: dict[str, Any] = {}
        for required_key in required:
            if required_key not in value and required_key not in properties:
                raise ValueError(f"{path} declares an unknown required field: {required_key}")
        additional_properties = schema.get("additionalProperties", True)
        property_names = schema.get("propertyNames")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings.")
            if property_names is not None:
                _validate_schema(key, property_names, path=f"{path}.{key}#name")
            if key in properties:
                normalized[key] = _validate_schema(item, properties[key], path=f"{path}.{key}")
                continue
            if additional_properties is False:
                raise ValueError(f"{path}.{key} is not allowed by schema.")
            if isinstance(additional_properties, Mapping):
                normalized[key] = _validate_schema(item, additional_properties, path=f"{path}.{key}")
            else:
                normalized[key] = _clone_json_like(item)
        for key, property_schema in properties.items():
            if key in normalized:
                continue
            if not isinstance(property_schema, Mapping):
                continue
            if "default" in property_schema:
                normalized[key] = _clone_json_like(property_schema["default"])
        for required_key in required:
            if required_key not in normalized:
                raise ValueError(f"{path}.{required_key} is required.")
        return normalized

    if schema_type == "array":
        if not isinstance(value, list | tuple):
            raise ValueError(f"{path} must be an array.")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            raise ValueError(f"{path} must contain at least {min_items} items.")
        if isinstance(max_items, int) and len(value) > max_items:
            raise ValueError(f"{path} must contain at most {max_items} items.")
        item_schema = schema.get("items")
        if not isinstance(item_schema, Mapping):
            return [_clone_json_like(item) for item in value]
        return [_validate_schema(item, item_schema, path=f"{path}[{index}]") for index, item in enumerate(value)]

    if schema_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path} must be a string.")
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        pattern = schema.get("pattern")
        enum = schema.get("enum")
        if isinstance(min_length, int) and len(value) < min_length:
            raise ValueError(f"{path} must be at least {min_length} characters long.")
        if isinstance(max_length, int) and len(value) > max_length:
            raise ValueError(f"{path} must be at most {max_length} characters long.")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise ValueError(f"{path} does not match the required pattern.")
        if isinstance(enum, list) and value not in enum:
            raise ValueError(f"{path} must be one of {enum}.")
        return value

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{path} must be an integer.")
        _validate_numeric_bounds(value, schema, path=path)
        return value

    if schema_type == "number":
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise ValueError(f"{path} must be a number.")
        _validate_numeric_bounds(float(value), schema, path=path)
        return value

    if schema_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{path} must be a boolean.")
        return value

    if schema_type is None:
        return _clone_json_like(value)

    raise ValueError(f"{path} uses an unsupported schema type: {schema_type}")


def _validate_numeric_bounds(value: float | int, schema: Mapping[str, Any], *, path: str) -> None:
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    exclusive_minimum = schema.get("exclusiveMinimum")
    exclusive_maximum = schema.get("exclusiveMaximum")
    if isinstance(minimum, int | float) and value < minimum:
        raise ValueError(f"{path} must be greater than or equal to {minimum}.")
    if isinstance(maximum, int | float) and value > maximum:
        raise ValueError(f"{path} must be less than or equal to {maximum}.")
    if isinstance(exclusive_minimum, int | float) and value <= exclusive_minimum:
        raise ValueError(f"{path} must be greater than {exclusive_minimum}.")
    if isinstance(exclusive_maximum, int | float) and value >= exclusive_maximum:
        raise ValueError(f"{path} must be less than {exclusive_maximum}.")


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = {key: _clone_json_like(value) for key, value in base.items()}
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = _clone_json_like(value)
    return merged


def _clone_json_like(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_like(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_clone_json_like(item) for item in value]
    return value


def _fingerprint_payload(payload: Mapping[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _resolve_secret_refs(
    value: Mapping[str, JsonValue],
    *,
    secret_resolver: Callable[[str], Any],
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, item in value.items():
        resolved[key] = _resolve_secret_value(item, secret_resolver=secret_resolver)
    return resolved


def _resolve_secret_value(value: JsonValue, *, secret_resolver: Callable[[str], Any]) -> Any:
    if isinstance(value, Mapping):
        if _is_secret_ref_mapping(value):
            secret_ref = SecretValueRef.from_mapping(value).secret_ref
            return secret_resolver(secret_ref)
        return {
            key: _resolve_secret_value(item, secret_resolver=secret_resolver)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [_resolve_secret_value(item, secret_resolver=secret_resolver) for item in value]
    return value


def _is_secret_ref_mapping(value: Mapping[str, Any]) -> bool:
    if "secret_ref" not in value:
        return False
    secret_ref = value.get("secret_ref")
    return isinstance(secret_ref, str) and bool(STRUCTURED_SECRET_REF_PATTERN.match(secret_ref))


def _optional_schedule_policy(value: Any) -> SchedulePolicyHint | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("schedule_policy must be an object when provided.")
    return SchedulePolicyHint.from_mapping(value)


def _optional_retry_policy(value: Any) -> RetryPolicyHint | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("retry_policy must be an object when provided.")
    return RetryPolicyHint.from_mapping(value)


def _optional_rate_limit_policy(value: Any) -> RateLimitPolicyHint | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("rate_limit_policy must be an object when provided.")
    return RateLimitPolicyHint.from_mapping(value)
