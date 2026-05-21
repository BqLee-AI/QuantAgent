from __future__ import annotations

import unittest
from datetime import datetime, timezone
from importlib import util
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine

from quantagent.core.config.settings import Settings
from quantagent.core.db.base import Base
from quantagent.core.db.models.sources import RawEvent, SourceFetchRun, SourceFetchRunStatus
from quantagent.core.db.repositories.raw_events import RawEventRepository
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
            self.assertIn("RuntimeError", result.error_summary)
            run = session.scalar(select(SourceFetchRun).where(SourceFetchRun.source_binding_id == "binding-2"))
            self.assertEqual(run.status, SourceFetchRunStatus.failed)
            self.assertIn("fetch failed", run.error_summary)

    def test_rss_plugin_manifest_is_discoverable(self) -> None:
        root = Path(__file__).resolve().parents[3]
        manifest = load_plugin_manifest(root / "plugins" / "sources" / "rss-source")

        self.assertEqual(manifest.id, "quantagent.official.source.rss")
        self.assertEqual(manifest.type, "source")
        self.assertEqual(manifest.execution_mode, "pull")
        self.assertIn("source.fetch", manifest.capabilities)

        source_manifests = discover_plugin_manifests(root / "plugins" / "sources", plugin_type="source")
        self.assertIn("quantagent.official.source.rss", {item.id for item in source_manifests})

    def test_rss_plugin_parses_rss_items_to_raw_events(self) -> None:
        module = _load_rss_plugin_module()
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


def _load_rss_plugin_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "plugins" / "sources" / "rss-source" / "src" / "rss_source.py"
    spec = util.spec_from_file_location("rss_source", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load RSS source plugin module.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
