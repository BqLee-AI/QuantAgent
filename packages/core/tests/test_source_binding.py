from __future__ import annotations

import unittest

from quantagent.core.source_binding import (
    EffectiveSourceConfigComposer,
    SecretValueRef,
    SourceBindingTemplate,
    SourceBindingTemplateLoader,
    build_runtime_source_config,
    extract_defaults_from_schema,
    is_effective_source_config_mapping,
    resolve_runtime_source_config,
)
from quantagent.core.source_binding.policy_models import (
    RateLimitPolicyHint,
    RetryPolicyHint,
    SchedulePolicyHint,
)


class SourceBindingContractTestCase(unittest.TestCase):
    def test_loader_normalizes_industry_binding_declaration(self) -> None:
        template = SourceBindingTemplateLoader().normalize(
            {
                "source_plugin_id": "quantagent.official.source.rss",
                "required": True,
                "config_template": "rss.oil.yaml",
                "config_override": {"feeds": ["https://example.com/rss.xml"]},
                "schedule_policy_hint": {"interval_seconds": 300},
                "metadata": {"owner": "oil"},
            }
        )

        self.assertEqual(template.source_plugin_id, "quantagent.official.source.rss")
        self.assertEqual(template.config_template_ref, "rss.oil.yaml")
        self.assertEqual(template.config_override["feeds"], ("https://example.com/rss.xml",))
        self.assertEqual(template.schedule_policy_hint.interval_seconds, 300)
        self.assertEqual(template.metadata["owner"], "oil")

    def test_loader_rejects_unknown_template_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported source binding template fields"):
            SourceBindingTemplateLoader().normalize(
                {
                    "source_plugin_id": "quantagent.official.source.rss",
                    "required": True,
                    "owner_id": "should-not-live-here",
                }
            )

    def test_extract_defaults_from_schema_reads_nested_defaults(self) -> None:
        defaults = extract_defaults_from_schema(
            {
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}, "default": ["https://default.example/rss.xml"]},
                    "headers": {
                        "type": "object",
                        "properties": {
                            "Accept": {"type": "string", "default": "application/rss+xml"},
                        },
                    },
                },
            }
        )

        self.assertEqual(defaults["feeds"], ["https://default.example/rss.xml"])
        self.assertEqual(defaults["headers"]["Accept"], "application/rss+xml")

    def test_compose_effective_config_uses_deterministic_precedence(self) -> None:
        template = SourceBindingTemplate(
            source_plugin_id="quantagent.official.source.rss",
            required=True,
            config_template_ref="rss.oil.yaml",
            config_override={"timeout_seconds": 12, "headers": {"X-Feed": "oil"}},
            schedule_policy_hint=SchedulePolicyHint(interval_seconds=300),
            retry_policy_hint=RetryPolicyHint(max_attempts=3, backoff_seconds=1),
            rate_limit_policy_hint=RateLimitPolicyHint(requests_per_window=10, window_seconds=60),
        )
        composer = EffectiveSourceConfigComposer()
        snapshot = composer.compose(
            template=template,
            plugin_schema={
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}, "default": ["https://default.example/rss.xml"]},
                    "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 30, "default": 10},
                    "headers": {
                        "type": "object",
                        "properties": {
                            "Accept": {"type": "string", "default": "application/rss+xml"},
                            "X-Feed": {"type": "string"},
                        },
                        "additionalProperties": False,
                        "default": {},
                    },
                },
                "required": ["feeds"],
                "additionalProperties": False,
            },
            template_assets={
                "rss.oil.yaml": {
                    "feeds": ["https://template.example/rss.xml"],
                    "headers": {"Accept": "application/atom+xml"},
                }
            },
            metadata={"owner": "oil"},
            source_schema_version="v1",
        )

        self.assertEqual(snapshot.config["feeds"], ("https://template.example/rss.xml",))
        self.assertEqual(snapshot.config["timeout_seconds"], 12)
        self.assertEqual(snapshot.config["headers"]["Accept"], "application/atom+xml")
        self.assertEqual(snapshot.config["headers"]["X-Feed"], "oil")
        self.assertEqual(snapshot.schedule_policy.interval_seconds, 300)
        self.assertEqual(snapshot.retry_policy.max_attempts, 3)
        self.assertEqual(snapshot.rate_limit_policy.requests_per_window, 10)
        self.assertEqual(snapshot.template_refs["config_template_ref"], "rss.oil.yaml")
        self.assertEqual(snapshot.metadata["owner"], "oil")
        self.assertTrue(snapshot.config_fingerprint)
        self.assertTrue(snapshot.validated_at.endswith("+00:00"))

    def test_compose_rejects_unknown_override_fields(self) -> None:
        template = SourceBindingTemplate(
            source_plugin_id="quantagent.official.source.rss",
            required=True,
            config_override={"unknown_field": True},
        )

        with self.assertRaisesRegex(ValueError, "config.unknown_field is not allowed by schema"):
            EffectiveSourceConfigComposer().compose(
                template=template,
                plugin_schema={
                    "type": "object",
                    "properties": {"feeds": {"type": "array", "items": {"type": "string"}}},
                    "required": ["feeds"],
                    "additionalProperties": False,
                },
            )

    def test_compose_rejects_null_override_when_schema_disallows_it(self) -> None:
        template = SourceBindingTemplate(
            source_plugin_id="quantagent.official.source.rss",
            required=True,
            config_override={"feeds": None},
        )

        with self.assertRaisesRegex(ValueError, "config.feeds does not allow null"):
            EffectiveSourceConfigComposer().compose(
                template=template,
                plugin_schema={
                    "type": "object",
                    "properties": {
                        "feeds": {"type": "array", "items": {"type": "string"}, "default": ["https://default.example/rss.xml"]},
                    },
                    "required": ["feeds"],
                    "additionalProperties": False,
                },
            )

    def test_runtime_view_extracts_flat_plugin_config_for_backward_compatibility(self) -> None:
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.official.source.rss",
                required=True,
                config_override={"feeds": ["https://override.example/rss.xml"]},
                schedule_policy_hint=SchedulePolicyHint(interval_seconds=60),
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["feeds"],
                "additionalProperties": False,
            },
        )

        runtime_config = build_runtime_source_config(snapshot)
        self.assertEqual(runtime_config["feeds"], ("https://override.example/rss.xml",))
        self.assertFalse("config_fingerprint" in runtime_config)
        self.assertTrue(is_effective_source_config_mapping(snapshot.to_mapping()))

    def test_effective_config_detection_rejects_legacy_flat_config_shape(self) -> None:
        self.assertFalse(
            is_effective_source_config_mapping(
                {
                    "config": {"feeds": ["https://legacy.example/rss.xml"]},
                    "validated_at": "2026-06-01T00:00:00+00:00",
                }
            )
        )

    def test_effective_config_from_mapping_rejects_unknown_top_level_fields(self) -> None:
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.official.source.rss",
                required=True,
                config_override={"feeds": ["https://override.example/rss.xml"]},
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["feeds"],
                "additionalProperties": False,
            },
        ).to_mapping()
        snapshot["unexpected"] = True

        with self.assertRaisesRegex(ValueError, "EffectiveSourceConfig contains unsupported fields"):
            build_runtime_source_config(snapshot)

    def test_runtime_secret_resolution_keeps_snapshot_auditable(self) -> None:
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.official.source.tavily",
                required=True,
                config_override={
                    "api_key_ref": SecretValueRef(secret_ref="env://TAVILY_API_KEY").to_mapping(),
                    "timeout_seconds": 8,
                },
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "api_key_ref": {
                        "type": "object",
                        "properties": {"secret_ref": {"type": "string"}, "metadata": {"type": "object"}},
                        "required": ["secret_ref"],
                        "additionalProperties": False,
                    },
                    "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 30},
                },
                "required": ["api_key_ref"],
                "additionalProperties": False,
            },
        )

        resolved = resolve_runtime_source_config(
            snapshot,
            secret_resolver=lambda secret_ref: {"env://TAVILY_API_KEY": "resolved-secret"}[secret_ref],
        )

        self.assertEqual(snapshot.config["api_key_ref"]["secret_ref"], "env://TAVILY_API_KEY")
        self.assertEqual(resolved.config["api_key_ref"], "resolved-secret")
        self.assertEqual(resolved.config["timeout_seconds"], 8)

    def test_policy_hints_reject_unknown_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "schedule_policy contains unsupported fields"):
            SchedulePolicyHint.from_mapping({"interval_seconds": 60, "cron": "* * * * *"})

        with self.assertRaisesRegex(ValueError, "retry_policy contains unsupported fields"):
            RetryPolicyHint.from_mapping({"max_attempts": 3, "strategy": "linear"})

        with self.assertRaisesRegex(ValueError, "rate_limit_policy contains unsupported fields"):
            RateLimitPolicyHint.from_mapping({"requests_per_window": 10, "window_seconds": 60, "burst": 1})
