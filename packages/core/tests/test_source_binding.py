from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.source_binding import (
    DEFAULT_BASELINE_BINDING_ID,
    DEFAULT_EXPANSION_BINDING_ID,
    EffectiveSourceConfigComposer,
    SecretValueRef,
    SemiconductorSourceBindingInstaller,
    SemiconductorSourceBindingInstallOptions,
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


class SemiconductorSourceBindingInstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        repo_root = Path(__file__).resolve().parents[3]
        self.registry = PluginRegistry(
            RegistryScanner(
                official_root=repo_root / "plugins",
                runtime_root=repo_root / "runtime" / "plugins",
            )
        )
        self.repository = SourceBindingRepository(self.session)
        self.now = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_installs_semiconductor_baseline_and_expansion_as_due_bindings(self) -> None:
        installer = SemiconductorSourceBindingInstaller(
            registry=self.registry,
            repository=self.repository,
            now=self.now,
        )

        result = installer.install_defaults()

        self.assertEqual([item.binding_id for item in result.installed], [DEFAULT_BASELINE_BINDING_ID, DEFAULT_EXPANSION_BINDING_ID])
        baseline = self.repository.get(DEFAULT_BASELINE_BINDING_ID)
        expansion = self.repository.get(DEFAULT_EXPANSION_BINDING_ID)
        self.assertIsNotNone(baseline)
        self.assertIsNotNone(expansion)
        assert baseline is not None
        assert expansion is not None
        self.assertEqual(baseline.status, "active")
        self.assertEqual(expansion.status, "active")
        self.assertEqual(baseline.next_run_at, self.now.replace(tzinfo=None))
        self.assertEqual(expansion.next_run_at, self.now.replace(tzinfo=None))
        self.assertEqual(baseline.owner_type, "industry")
        self.assertEqual(baseline.owner_id, "semiconductor")
        self.assertEqual(baseline.source_plugin_id, "quantagent.official.source.rss")
        self.assertEqual(len(baseline.effective_config_snapshot["config"]["feeds"]), 4)
        self.assertEqual(len(expansion.effective_config_snapshot["config"]["feeds"]), 9)
        self.assertEqual(baseline.effective_config_snapshot["config"]["max_items_per_feed"], 20)
        self.assertEqual(expansion.effective_config_snapshot["config"]["max_response_bytes"], 1_048_576)
        self.assertEqual(baseline.schedule_policy["interval_seconds"], 300)
        self.assertEqual(expansion.schedule_policy["interval_seconds"], 900)

    def test_reinstall_updates_existing_bindings_without_creating_duplicates(self) -> None:
        installer = SemiconductorSourceBindingInstaller(
            registry=self.registry,
            repository=self.repository,
            now=self.now,
        )
        installer.install_defaults()

        result = installer.install_defaults(
            SemiconductorSourceBindingInstallOptions(
                baseline_interval_seconds=600,
                expansion_interval_seconds=1200,
                max_items_per_feed=10,
            )
        )

        self.assertEqual([item.action for item in result.installed], ["updated", "updated"])
        rows = self.repository.list_by_owner(owner_type="industry", owner_id="semiconductor", limit=10)
        self.assertEqual(
            sorted(item.binding_id for item in rows),
            [DEFAULT_BASELINE_BINDING_ID, DEFAULT_EXPANSION_BINDING_ID],
        )
        baseline = self.repository.get(DEFAULT_BASELINE_BINDING_ID)
        assert baseline is not None
        self.assertEqual(baseline.schedule_policy["interval_seconds"], 600)
        self.assertEqual(baseline.effective_config_snapshot["config"]["max_items_per_feed"], 10)

    def test_expansion_can_be_installed_paused(self) -> None:
        installer = SemiconductorSourceBindingInstaller(
            registry=self.registry,
            repository=self.repository,
            now=self.now,
        )

        installer.install_defaults(SemiconductorSourceBindingInstallOptions(activate_expansion=False))

        baseline = self.repository.get(DEFAULT_BASELINE_BINDING_ID)
        expansion = self.repository.get(DEFAULT_EXPANSION_BINDING_ID)
        assert baseline is not None
        assert expansion is not None
        self.assertEqual(baseline.status, "active")
        self.assertEqual(expansion.status, "paused")
        self.assertEqual(baseline.next_run_at, self.now.replace(tzinfo=None))
        self.assertIsNone(expansion.next_run_at)
