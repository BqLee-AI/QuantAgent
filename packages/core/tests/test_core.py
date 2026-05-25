from __future__ import annotations

import unittest
from datetime import datetime, timezone
from importlib import util
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from quantagent.core.config.settings import Settings
from quantagent.core.db.base import Base
from quantagent.core.db.models.sources import RawEvent, SourceFetchRun, SourceFetchRunStatus
from quantagent.core.db.repositories.raw_events import RawEventRepository
from quantagent.core.events.dedupe import build_dedupe_identity
from quantagent.core.db.session import create_session_factory, create_sync_engine, require_database_url
from quantagent.core.events.dto import RawEventDraft
from quantagent.core.plugins.manifest import discover_plugin_manifests, load_plugin_manifest
from quantagent.core.sources.protocols import RuntimeContext, SourceBindingConfig
from quantagent.core.sources.service import SourceFetchService


class CorePackageTestCase(unittest.TestCase):
    def test_settings_accept_shared_runtime_values(self) -> None:
        settings = Settings(
            APP_ENV="production",
            DATABASE_URL="sqlite:///:memory:",
            RUNTIME_DIR=Path("/tmp/quantagent-runtime"),
            LOG_LEVEL="DEBUG",
        )

        self.assertTrue(settings.is_production)
        self.assertEqual(settings.DATABASE_URL, "sqlite:///:memory:")
        self.assertEqual(settings.RUNTIME_DIR, Path("/tmp/quantagent-runtime"))
        self.assertEqual(settings.LOG_LEVEL, "DEBUG")

    def test_database_url_has_no_hardcoded_default(self) -> None:
        settings = Settings(_env_file=None)

        self.assertIsNone(settings.DATABASE_URL)

    def test_base_metadata_is_importable(self) -> None:
        self.assertIsNotNone(Base.metadata)
        self.assertIn("raw_events", Base.metadata.tables)
        self.assertIn("source_bindings", Base.metadata.tables)
        self.assertIn("source_fetch_runs", Base.metadata.tables)

    def test_database_url_is_required_for_default_engine(self) -> None:
        with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
            require_database_url()

    def test_sync_engine_and_session_factory_are_importable(self) -> None:
        engine = create_sync_engine("sqlite:///:memory:")
        session_factory = create_session_factory(engine)

        self.assertIsInstance(engine, Engine)
        self.assertFalse(session_factory.kw["autoflush"])
        self.assertFalse(session_factory.kw["expire_on_commit"])


class SourceRuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_sync_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = create_session_factory(self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_raw_event_repository_stores_and_skips_duplicates(self) -> None:
        with self.session_factory() as session:
            repository = RawEventRepository(session)
            draft = RawEventDraft(
                source_plugin_id="quantagent.official.source.rss",
                source_type="rss",
                external_id="rss-item-1",
                title="Oil supply update",
                url="https://example.test/oil",
                captured_at=datetime(2026, 5, 21, tzinfo=timezone.utc),
            )

            first = repository.store_if_new(draft)
            second = repository.store_if_new(draft)

            self.assertFalse(first.is_duplicate)
            self.assertTrue(second.is_duplicate)
            self.assertEqual(session.scalar(select(RawEvent).where(RawEvent.external_id == "rss-item-1")).title, "Oil supply update")

    def test_raw_event_repository_does_not_swallow_non_duplicate_integrity_error(self) -> None:
        with self.session_factory() as session:
            repository = RawEventRepository(session)
            draft = RawEventDraft(
                source_plugin_id="quantagent.official.source.rss",
                source_type="rss",
                title="Integrity conflict probe",
            )

            with patch.object(session, "flush", side_effect=IntegrityError("stmt", "params", Exception("boom"))):
                with self.assertRaises(IntegrityError):
                    repository.store_if_new(draft)

    def test_dedupe_identity_uses_plugin_namespace_and_hashed_url(self) -> None:
        draft = RawEventDraft(
            source_plugin_id="quantagent.official.source.rss",
            source_type="rss",
            title="Oil supply update",
            url="https://example.test/path?q=very-long",
            content="Inventory dropped again.",
        )

        identity = build_dedupe_identity(draft)

        self.assertTrue(identity.key.startswith("quantagent.official.source.rss:url_content:"))
        self.assertNotIn("https://example.test/path", identity.key)
        self.assertEqual(identity.reason, "source_plugin_id+canonical_url+content_hash")

    def test_source_fetch_service_records_success_and_duplicates(self) -> None:
        with self.session_factory() as session:
            plugin = FakeSourcePlugin(
                [
                    RawEventDraft(
                        source_plugin_id="quantagent.official.source.rss",
                        source_type="rss",
                        external_id="rss-item-1",
                        title="First item",
                    ),
                    RawEventDraft(
                        source_plugin_id="quantagent.official.source.rss",
                        source_type="rss",
                        external_id="rss-item-1",
                        title="First item duplicate",
                    ),
                ]
            )
            binding = SourceBindingConfig(
                id="binding-1",
                source_plugin_id="quantagent.official.source.rss",
                owner_type="industry",
                owner_id="oil",
                effective_config={"feeds": ["https://example.test/rss.xml"]},
            )

            result = SourceFetchService(session).trigger_fetch(plugin=plugin, binding=binding)

            self.assertEqual(result.status, SourceFetchRunStatus.succeeded.value)
            self.assertEqual(result.fetched_count, 2)
            self.assertEqual(result.stored_count, 1)
            self.assertEqual(result.duplicate_count, 1)
            run = session.scalar(select(SourceFetchRun).where(SourceFetchRun.source_binding_id == "binding-1"))
            self.assertEqual(run.status, SourceFetchRunStatus.succeeded)
            self.assertEqual(run.stored_count, 1)

    def test_source_fetch_service_records_failure_summary(self) -> None:
        with self.session_factory() as session:
            plugin = FailingSourcePlugin()
            binding = SourceBindingConfig(
                id="binding-2",
                source_plugin_id="quantagent.official.source.rss",
                owner_type="industry",
                owner_id="oil",
                effective_config={"feeds": ["https://example.test/rss.xml"]},
            )

            result = SourceFetchService(session).trigger_fetch(plugin=plugin, binding=binding)

            self.assertEqual(result.status, SourceFetchRunStatus.failed.value)
            self.assertEqual(result.error_summary, "RuntimeError: fetch failed")
            run = session.scalar(select(SourceFetchRun).where(SourceFetchRun.source_binding_id == "binding-2"))
            self.assertEqual(run.status, SourceFetchRunStatus.failed)
            self.assertEqual(run.error_summary, "RuntimeError: fetch failed")

    def test_source_fetch_service_rejects_plugin_binding_id_mismatch(self) -> None:
        with self.session_factory() as session:
            plugin = FakeSourcePlugin([])
            plugin.id = "quantagent.official.source.other"
            binding = SourceBindingConfig(
                id="binding-3",
                source_plugin_id="quantagent.official.source.rss",
                owner_type="industry",
                owner_id="oil",
                effective_config={"feeds": ["https://example.test/rss.xml"]},
            )

            with self.assertRaisesRegex(ValueError, "does not match"):
                SourceFetchService(session).trigger_fetch(plugin=plugin, binding=binding)

    def test_source_fetch_service_persists_fetched_count_on_partial_failure(self) -> None:
        with self.session_factory() as session:
            plugin = PartialFailingSourcePlugin([])
            binding = SourceBindingConfig(
                id="binding-4",
                source_plugin_id="quantagent.official.source.rss",
                owner_type="industry",
                owner_id="oil",
                effective_config={"feeds": ["https://example.test/rss.xml"]},
            )

            result = SourceFetchService(session).trigger_fetch(plugin=plugin, binding=binding)

            self.assertEqual(result.status, SourceFetchRunStatus.failed.value)
            self.assertEqual(result.fetched_count, 1)
            self.assertEqual(result.stored_count, 1)
            self.assertEqual(result.duplicate_count, 0)
            run = session.scalar(select(SourceFetchRun).where(SourceFetchRun.source_binding_id == "binding-4"))
            self.assertEqual(run.fetched_count, 1)
            self.assertEqual(run.stored_count, 1)

    def test_source_fetch_service_stops_plugin_when_start_fails(self) -> None:
        with self.session_factory() as session:
            plugin = StartFailingSourcePlugin([])
            binding = SourceBindingConfig(
                id="binding-5",
                source_plugin_id="quantagent.official.source.rss",
                owner_type="industry",
                owner_id="oil",
                effective_config={"feeds": ["https://example.test/rss.xml"]},
            )

            result = SourceFetchService(session).trigger_fetch(plugin=plugin, binding=binding)

            self.assertEqual(result.status, SourceFetchRunStatus.failed.value)
            self.assertFalse(plugin.started)
            self.assertTrue(plugin.stop_called)

    def test_placeholder_plugin_manifest_and_minimum_files_are_present(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plugin_root = root / "plugins" / "sources" / "placeholder-source"

        manifest = load_plugin_manifest(plugin_root)

        self.assertEqual(manifest.id, "quantagent.official.source.placeholder")
        self.assertEqual(manifest.type, "source")
        self.assertEqual(manifest.config_schema, "config.schema.json")
        self.assertTrue((plugin_root / "README.md").is_file())
        self.assertTrue((plugin_root / "src" / "placeholder_source.py").is_file())
        self.assertTrue((plugin_root / "config.schema.json").is_file())

    def test_rss_plugin_manifest_is_discoverable(self) -> None:
        root = Path(__file__).resolve().parents[3]
        manifest = load_plugin_manifest(root / "plugins" / "sources" / "rss-source")

        self.assertEqual(manifest.id, "quantagent.official.source.rss")
        self.assertEqual(manifest.type, "source")
        self.assertEqual(manifest.execution_mode, "pull")
        self.assertIn("source.fetch", manifest.capabilities)

        source_manifests = discover_plugin_manifests(root / "plugins" / "sources", plugin_type="source")
        self.assertIn("quantagent.official.source.rss", {item.id for item in source_manifests})
        self.assertIn("quantagent.official.source.placeholder", {item.id for item in source_manifests})

    def test_rss_plugin_minimum_files_are_present(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plugin_root = root / "plugins" / "sources" / "rss-source"

        self.assertTrue((plugin_root / "README.md").is_file())
        self.assertTrue((plugin_root / "src" / "rss_source.py").is_file())
        self.assertTrue((plugin_root / "config.schema.json").is_file())

    def test_placeholder_plugin_supports_minimum_source_protocol(self) -> None:
        module = _load_plugin_module("placeholder_source", "placeholder-source", "placeholder_source.py")
        plugin = module.PlaceholderSourcePlugin()
        context = RuntimeContext(plugin_id=plugin.id)

        plugin.load(context)
        plugin.start()

        self.assertEqual(plugin.fetch(cursor=None, config={}), [])
        self.assertTrue(plugin.health_check()["started"])

        plugin.stop()
        self.assertFalse(plugin.health_check()["started"])

    def test_rss_plugin_parses_rss_items_to_raw_events(self) -> None:
        module = _load_plugin_module("rss_source", "rss-source", "rss_source.py")
        body = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <guid>item-1</guid>
      <title>Oil inventory surprise</title>
      <link>https://example.test/oil-inventory</link>
      <pubDate>Thu, 21 May 2026 01:02:03 GMT</pubDate>
      <description>Inventories fell more than expected.</description>
    </item>
  </channel>
</rss>"""

        events = module._parse_feed(body, "https://example.test/rss.xml", max_items=10)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source_plugin_id, "quantagent.official.source.rss")
        self.assertEqual(events[0].source_type, "rss")
        self.assertEqual(events[0].external_id, "item-1")
        self.assertEqual(events[0].title, "Oil inventory surprise")
        self.assertEqual(events[0].metadata["feed_url"], "https://example.test/rss.xml")


class FakeSourcePlugin:
    id = "quantagent.official.source.rss"

    def __init__(self, events: list[RawEventDraft]) -> None:
        self._events = events
        self.started = False

    def load(self, context: RuntimeContext) -> None:
        self.context = context

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def reload(self, config: dict[str, object]) -> None:
        self.config = config

    def health_check(self) -> dict[str, object]:
        return {"status": "ok"}

    def fetch(self, cursor: str | None, config: dict[str, object]) -> list[RawEventDraft]:
        del cursor, config
        return self._events


class FailingSourcePlugin(FakeSourcePlugin):
    def __init__(self) -> None:
        super().__init__([])

    def fetch(self, cursor: str | None, config: dict[str, object]) -> list[RawEventDraft]:
        del cursor, config
        raise RuntimeError("fetch failed")


class PartialFailingSourcePlugin(FakeSourcePlugin):
    def fetch(self, cursor: str | None, config: dict[str, object]):
        del cursor, config
        return OneThenFailDrafts(
            RawEventDraft(
                source_plugin_id="quantagent.official.source.rss",
                source_type="rss",
                external_id="rss-item-2",
                title="Stored before failure",
            )
        )


class StartFailingSourcePlugin(FakeSourcePlugin):
    def __init__(self, events: list[RawEventDraft]) -> None:
        super().__init__(events)
        self.stop_called = False

    def start(self) -> None:
        self.started = True
        raise RuntimeError("start failed")

    def stop(self) -> None:
        self.stop_called = True
        super().stop()


class OneThenFailDrafts:
    def __init__(self, draft: RawEventDraft) -> None:
        self._draft = draft

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        yield self._draft
        raise RuntimeError("iteration failed")


def _load_plugin_module(module_name: str, plugin_dir: str, module_file: str):
    root = Path(__file__).resolve().parents[3]
    module_path = root / "plugins" / "sources" / plugin_dir / "src" / module_file
    spec = util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load plugin module: {module_name}.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
