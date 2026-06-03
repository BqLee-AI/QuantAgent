from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from quantagent.core.db.models.source_binding import SourceBindingORM
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.registry import PluginRegistry
from quantagent.core.registry.models import PluginRecord
from quantagent.core.scheduling import SourceBindingStatus
from quantagent.core.source_binding.effective_config import EffectiveSourceConfig, EffectiveSourceConfigComposer
from quantagent.core.source_binding.policy_models import RateLimitPolicyHint, RetryPolicyHint, SchedulePolicyHint
from quantagent.core.source_binding.template_loader import SourceBindingTemplateLoader
from quantagent.core.source_binding.template_models import SourceBindingTemplate
from quantagent.plugin_sdk.io import to_json_value


SEMICONDUCTOR_INDUSTRY_PLUGIN_ID = "quantagent.official.industry.semiconductor"
RSS_SOURCE_PLUGIN_ID = "quantagent.official.source.rss"

DEFAULT_BASELINE_BINDING_ID = "binding-semiconductor-rss-baseline"
DEFAULT_EXPANSION_BINDING_ID = "binding-semiconductor-rss-expansion"

DEFAULT_BASELINE_INTERVAL_SECONDS = 300
DEFAULT_EXPANSION_INTERVAL_SECONDS = 900
DEFAULT_MAX_ITEMS_PER_FEED = 20
DEFAULT_RSS_MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_RSS_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class InstalledSourceBinding:
    binding_id: str
    source_tier: str
    action: str
    feed_count: int
    interval_seconds: int
    next_run_at: datetime | None


@dataclass(frozen=True)
class InstallSemiconductorSourceBindingsResult:
    installed: tuple[InstalledSourceBinding, ...]


@dataclass(frozen=True)
class SemiconductorSourceBindingInstallOptions:
    include_expansion: bool = True
    activate_expansion: bool = True
    force_due: bool = True
    baseline_interval_seconds: int = DEFAULT_BASELINE_INTERVAL_SECONDS
    expansion_interval_seconds: int = DEFAULT_EXPANSION_INTERVAL_SECONDS
    max_items_per_feed: int = DEFAULT_MAX_ITEMS_PER_FEED
    actor: str = "quantagent-source-bindings"


class SemiconductorSourceBindingInstaller:
    """把官方行业包 source_bindings 模板安装成可调度的 DB SourceBinding。"""

    def __init__(
        self,
        *,
        registry: PluginRegistry,
        repository: SourceBindingRepository,
        now: datetime | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._now = now
        self._template_loader = SourceBindingTemplateLoader()
        self._composer = EffectiveSourceConfigComposer()

    def install_defaults(
        self,
        options: SemiconductorSourceBindingInstallOptions | None = None,
    ) -> InstallSemiconductorSourceBindingsResult:
        resolved_options = options or SemiconductorSourceBindingInstallOptions()
        now = (self._now or datetime.now(UTC)).astimezone(UTC)
        industry_record = self._require_plugin(SEMICONDUCTOR_INDUSTRY_PLUGIN_ID)
        rss_record = self._require_plugin(RSS_SOURCE_PLUGIN_ID)
        rss_schema = _load_yaml_or_json_mapping(rss_record.config_schema_path)

        installed: list[InstalledSourceBinding] = []
        for template in self._rss_templates(industry_record):
            template_asset = _load_yaml_or_json_mapping(industry_record.path / template.config_template_ref)
            source_tier = str(template_asset.get("source_tier") or "")
            if source_tier == "expansion" and not resolved_options.include_expansion:
                continue
            binding_id = _binding_id_for_tier(source_tier)
            interval_seconds = (
                resolved_options.expansion_interval_seconds
                if source_tier == "expansion"
                else resolved_options.baseline_interval_seconds
            )
            effective_config = self._compose_effective_config(
                template=template,
                template_asset=_plugin_config_asset(template_asset, plugin_schema=rss_schema),
                plugin_schema=rss_schema,
                interval_seconds=interval_seconds,
                max_items_per_feed=resolved_options.max_items_per_feed,
                source_tier=source_tier,
                validated_at=now,
            )
            active = source_tier != "expansion" or resolved_options.activate_expansion
            action = self._upsert_binding(
                binding_id=binding_id,
                effective_config=effective_config,
                active=active,
                next_run_at=now if active and resolved_options.force_due else None,
                actor=resolved_options.actor,
                updated_at=now,
            )
            installed.append(
                InstalledSourceBinding(
                    binding_id=binding_id,
                    source_tier=source_tier,
                    action=action,
                    feed_count=len(template_asset.get("feeds") or ()),
                    interval_seconds=interval_seconds,
                    next_run_at=now if active and resolved_options.force_due else None,
                )
            )
        return InstallSemiconductorSourceBindingsResult(installed=tuple(installed))

    def _rss_templates(self, industry_record: PluginRecord) -> list[SourceBindingTemplate]:
        manifest = industry_record.manifest
        if manifest is None:
            raise ValueError(f"Plugin manifest is missing: {industry_record.id}")
        templates: list[SourceBindingTemplate] = []
        for item in manifest.source_bindings:
            if item.source_plugin_id != RSS_SOURCE_PLUGIN_ID:
                continue
            templates.append(
                self._template_loader.normalize(
                    {
                        "source_plugin_id": item.source_plugin_id,
                        "required": item.required,
                        "config_template": item.config_template,
                    }
                )
            )
        if not templates:
            raise ValueError("Semiconductor industry package does not declare RSS source bindings.")
        return templates

    def _compose_effective_config(
        self,
        *,
        template: SourceBindingTemplate,
        template_asset: Mapping[str, Any],
        plugin_schema: Mapping[str, Any],
        interval_seconds: int,
        max_items_per_feed: int,
        source_tier: str,
        validated_at: datetime,
    ) -> EffectiveSourceConfig:
        # 默认安装用于本地真实抓取，显式放宽 RSS 总响应上限，同时保持单篇 content 截断在插件 schema 内。
        install_template = SourceBindingTemplate(
            source_plugin_id=template.source_plugin_id,
            required=template.required,
            config_template_ref=template.config_template_ref,
            config_override={
                "max_items_per_feed": max_items_per_feed,
                "max_response_bytes": DEFAULT_RSS_MAX_RESPONSE_BYTES,
                "timeout_seconds": DEFAULT_RSS_TIMEOUT_SECONDS,
            },
            schedule_policy_hint=SchedulePolicyHint(
                interval_seconds=interval_seconds,
                metadata={"installed_from": "semiconductor-defaults", "source_tier": source_tier},
            ),
            retry_policy_hint=RetryPolicyHint(max_attempts=2, backoff_seconds=30, max_backoff_seconds=300),
            rate_limit_policy_hint=RateLimitPolicyHint(
                requests_per_window=60,
                window_seconds=60,
                scope=f"source:rss:{source_tier}",
            ),
            metadata={"source_tier": source_tier, "industry_plugin_id": SEMICONDUCTOR_INDUSTRY_PLUGIN_ID},
        )
        return self._composer.compose(
            template=install_template,
            plugin_schema=plugin_schema,
            template_assets={template.config_template_ref: template_asset},
            metadata={"installed_by": "semiconductor-default-source-binding-installer", "source_tier": source_tier},
            validated_at=validated_at,
        )

    def _upsert_binding(
        self,
        *,
        binding_id: str,
        effective_config: EffectiveSourceConfig,
        active: bool,
        next_run_at: datetime | None,
        actor: str,
        updated_at: datetime,
    ) -> str:
        existing = self._repository.get(binding_id)
        status = SourceBindingStatus.ACTIVE.value if active else SourceBindingStatus.PAUSED.value
        config_snapshot = dict(to_json_value(effective_config.to_mapping()))
        schedule_policy = dict(to_json_value(effective_config.schedule_policy.to_mapping() if effective_config.schedule_policy else {}))
        retry_policy = dict(to_json_value(effective_config.retry_policy.to_mapping() if effective_config.retry_policy else {}))
        rate_limit_policy = dict(to_json_value(effective_config.rate_limit_policy.to_mapping() if effective_config.rate_limit_policy else {}))
        if existing is None:
            self._repository.create(
                SourceBindingORM(
                    binding_id=binding_id,
                    owner_type="industry",
                    owner_id="semiconductor",
                    source_plugin_id=RSS_SOURCE_PLUGIN_ID,
                    source_plugin_version=None,
                    effective_config_snapshot=config_snapshot,
                    schedule_policy=schedule_policy,
                    retry_policy=retry_policy,
                    rate_limit_policy=rate_limit_policy,
                    status=status,
                    next_run_at=next_run_at,
                    created_by=actor,
                    updated_by=actor,
                )
            )
            return "created"

        existing.owner_type = "industry"
        existing.owner_id = "semiconductor"
        existing.source_plugin_id = RSS_SOURCE_PLUGIN_ID
        existing.source_plugin_version = None
        existing.effective_config_snapshot = config_snapshot
        existing.schedule_policy = schedule_policy
        existing.retry_policy = retry_policy
        existing.rate_limit_policy = rate_limit_policy
        existing.status = status
        if active:
            existing.next_run_at = next_run_at
        else:
            existing.next_run_at = None
        existing.updated_by = actor
        existing.updated_at = updated_at
        self._repository.save(existing)
        return "updated"

    def _require_plugin(self, plugin_id: str) -> PluginRecord:
        record = self._registry.get_plugin(plugin_id)
        if record is None or record.manifest is None:
            raise ValueError(f"Required plugin is not available: {plugin_id}")
        return record


def _binding_id_for_tier(source_tier: str) -> str:
    if source_tier == "baseline":
        return DEFAULT_BASELINE_BINDING_ID
    if source_tier == "expansion":
        return DEFAULT_EXPANSION_BINDING_ID
    raise ValueError(f"Unsupported semiconductor RSS source_tier: {source_tier}")


def _load_yaml_or_json_mapping(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("Template or schema path is missing.")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"Expected mapping file: {path}")
    return dict(payload)


def _plugin_config_asset(template_asset: Mapping[str, Any], *, plugin_schema: Mapping[str, Any]) -> dict[str, Any]:
    properties = plugin_schema.get("properties")
    if not isinstance(properties, Mapping):
        return dict(template_asset)
    # 行业包模板允许携带 source_tier/default_enabled 这类控制面字段；真正调用 RSS 插件前必须按 schema 过滤。
    return {key: value for key, value in template_asset.items() if key in properties}
