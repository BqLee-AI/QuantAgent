from __future__ import annotations

import sys
import unittest
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.raw_event_capture_repository import RawEventCaptureRepository
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.events import InMemoryEventBus
from quantagent.core.events.service import SourceEventPublisher
from quantagent.core.raw_events import RawEventService
from quantagent.core.registry import PluginManifest, PluginRecord, PluginRegistry, PluginSource, PluginStatus, PluginType
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    CreateSourceBindingInput,
    FrozenSchedulingClock,
    SourceBindingStatus,
    SchedulerRunService,
    SourceBindingSchedulerLoopService,
    SourceBindingService,
)
from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult


class StaticScanner:
    def __init__(self, records: list[PluginRecord]) -> None:
        self._records = records

    def scan(self) -> list[PluginRecord]:
        return list(self._records)


class RecordingHandler:
    def __init__(self) -> None:
        self.seen = []

    async def handle(self, envelope) -> None:
        self.seen.append(envelope)


class BlockingInvokePlugin(BasePlugin):
    started = None
    release = None

    async def invoke(self, request):
        assert BlockingInvokePlugin.started is not None
        assert BlockingInvokePlugin.release is not None
        BlockingInvokePlugin.started.set()
        await BlockingInvokePlugin.release.wait()
        return PluginInvokeResult(
            output={
                "items": [
                    {
                        "external_id": "evt-blocked-1",
                        "title": "Macro changed",
                        "raw_payload": {"id": "evt-blocked-1"},
                    }
                ],
                "metadata": {"source": "blocked"},
            }
        )


class SourceBindingSchedulerLoopServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        self.clock = FrozenSchedulingClock(datetime(2026, 6, 1, 8, 0, tzinfo=UTC))
        self.binding_repository = SourceBindingRepository(self.session)
        self.run_repository = SchedulerRunRepository(self.session)
        self.raw_event_repository = RawEventRepository(self.session)
        self.raw_event_capture_repository = RawEventCaptureRepository(self.session)
        self.binding_service = SourceBindingService(self.binding_repository, clock=self.clock)
        self.run_service = SchedulerRunService(self.run_repository, clock=self.clock)
        self.event_bus = InMemoryEventBus()
        self.event_handler = RecordingHandler()
        await self.event_bus.subscribe(
            topics=("source.event.captured",),
            group_id="test-scheduler-loop",
            handler=self.event_handler,
        )
        self.module_name = "test_scheduler_loop_source_plugin"
        BlockingInvokePlugin.started = None
        BlockingInvokePlugin.release = None

    async def asyncTearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        sys.modules.pop(self.module_name, None)

    async def test_run_once_processes_due_binding_and_updates_next_run(self) -> None:
        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(
                    output={
                        "items": [
                            {
                                "external_id": "evt-1",
                                "title": "Oil moved",
                                "raw_payload": {"id": "evt-1"},
                            }
                        ],
                        "next_cursor": "cursor-2",
                        "metadata": {"source": "rss"},
                    }
                )

        plugin_path = Path(__file__).resolve()
        module = type(sys)(self.module_name)
        module.plugin = SourcePlugin
        sys.modules[self.module_name] = module
        registry = PluginRegistry(
            StaticScanner(
                [
                    PluginRecord(
                        id="quantagent.official.source.test",
                        source=PluginSource.OFFICIAL,
                        path=plugin_path,
                        status=PluginStatus.VALID,
                        manifest=PluginManifest(
                            id="quantagent.official.source.test",
                            name="Test Source",
                            type=PluginType.SOURCE,
                            version="1.0.0",
                            entrypoint=f"{self.module_name}:plugin",
                            capabilities=("source.fetch",),
                            config_schema="config.schema.json",
                        ),
                        config_schema_path=plugin_path,
                    )
                ]
            )
        )
        binding = self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-due",
                owner_type="industry",
                owner_id="oil",
                source_plugin_id="quantagent.official.source.test",
                source_plugin_version="1.0.0",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.test",
                    "config": {"feed": "https://example.com/rss.xml"},
                    "config_fingerprint": "fingerprint-1",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=10),
                created_by="issue-217",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            raw_event_service=RawEventService(
                raw_event_repository=self.raw_event_repository,
                raw_event_capture_repository=self.raw_event_capture_repository,
                source_binding_repository=self.binding_repository,
                scheduler_run_repository=self.run_repository,
            ),
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )

        self.clock.advance(seconds=2)
        with self.assertLogs("quantagent.core.scheduling.loop_service", level="INFO") as logs:
            result = await service.run_once()

        self.assertEqual(result.due_bindings, 1)
        self.assertEqual(result.succeeded_runs, 1)
        self.assertEqual(result.failed_runs, 0)
        self.assertEqual(result.emitted_events, 1)
        self.assertTrue(
            any("Scheduler persisted raw events" in item for item in logs.output),
            logs.output,
        )
        self.assertEqual(len(result.binding_results), 1)
        binding_result = result.binding_results[0]
        self.assertEqual(binding_result.binding_id, binding.binding_id)
        self.assertEqual(binding_result.status.value, "succeeded")
        self.assertEqual(binding_result.captured_count, 1)

        updated_binding = self.binding_repository.get(binding.binding_id)
        self.assertIsNotNone(updated_binding)
        assert updated_binding is not None
        self.assertEqual(updated_binding.last_run_status, "succeeded")
        self.assertIsNotNone(updated_binding.last_run_at)
        self.assertIsNotNone(updated_binding.last_heartbeat_at)
        self.assertEqual(updated_binding.consecutive_failure_count, 0)
        self.assertEqual(
            updated_binding.next_run_at,
            updated_binding.last_run_at + timedelta(seconds=60),
        )

        runs = self.run_repository.list_by_binding(binding_id=binding.binding_id, limit=10)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "succeeded")
        self.assertEqual(runs[0].captured_count, 1)
        self.assertEqual(runs[0].output_summary["item_count"], 1)
        raw_events = self.raw_event_repository.list_by_run(scheduler_run_id=runs[0].run_id, limit=10)
        self.assertEqual(len(raw_events), 1)
        self.assertEqual(raw_events[0].external_id, "evt-1")

        self.assertEqual(len(self.event_handler.seen), 1)
        self.assertEqual(self.event_handler.seen[0].topic, "source.event.captured")
        self.assertEqual(self.event_handler.seen[0].causation_id, runs[0].run_id)
        self.assertEqual(self.event_handler.seen[0].payload["binding_id"], binding.binding_id)
        self.assertEqual(self.event_handler.seen[0].headers["binding_id"], binding.binding_id)
        source_item_metadata = self.event_handler.seen[0].payload["items"][0]["metadata"]
        self.assertEqual(source_item_metadata["raw_event_id"], raw_events[0].raw_event_id)
        self.assertEqual(source_item_metadata["source_event_id"], "evt-1")
        self.assertEqual(source_item_metadata["source_binding_id"], binding.binding_id)
        self.assertEqual(source_item_metadata["scheduler_run_id"], runs[0].run_id)
        self.assertEqual(source_item_metadata["request_id"], runs[0].request_id)
        capture = self.raw_event_capture_repository.get(source_item_metadata["capture_id"])
        self.assertIsNotNone(capture)
        assert capture is not None
        self.assertEqual(capture.raw_event_id, raw_events[0].raw_event_id)

    async def test_invalid_schedule_policy_records_failed_run_and_clears_next_run(self) -> None:
        registry = PluginRegistry(StaticScanner([]))
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-invalid-policy",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.missing",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.missing",
                    "config": {},
                    "config_fingerprint": "fingerprint-2",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"enabled": True},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=5),
                created_by="issue-217",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )

        result = await service.run_once()

        self.assertEqual(result.failed_runs, 1)
        self.assertEqual(result.emitted_events, 0)
        self.assertEqual(result.binding_results[0].error_code, "PLUGIN_DTO_VALIDATION_FAILED")
        binding = self.binding_repository.get("binding-invalid-policy")
        self.assertIsNotNone(binding)
        assert binding is not None
        self.assertIsNone(binding.next_run_at)
        self.assertEqual(binding.last_run_status, "failed")
        runs = self.run_repository.list_by_binding(binding_id="binding-invalid-policy", limit=10)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "failed")
        self.assertEqual(runs[0].failure_code, "PLUGIN_DTO_VALIDATION_FAILED")

    async def test_run_once_publishes_one_source_event_per_captured_item(self) -> None:
        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(
                    output={
                        "items": [
                            {"external_id": "evt-batch-1", "title": "First"},
                            {"external_id": "evt-batch-2", "title": "Second"},
                        ],
                        "metadata": {"source": "rss"},
                    }
                )

        plugin_path = Path(__file__).resolve()
        module = type(sys)(self.module_name)
        module.plugin = SourcePlugin
        sys.modules[self.module_name] = module
        registry = PluginRegistry(
            StaticScanner(
                [
                    PluginRecord(
                        id="quantagent.official.source.batch",
                        source=PluginSource.OFFICIAL,
                        path=plugin_path,
                        status=PluginStatus.VALID,
                        manifest=PluginManifest(
                            id="quantagent.official.source.batch",
                            name="Batch Source",
                            type=PluginType.SOURCE,
                            version="1.0.0",
                            entrypoint=f"{self.module_name}:plugin",
                            capabilities=("source.fetch",),
                            config_schema="config.schema.json",
                        ),
                        config_schema_path=plugin_path,
                    )
                ]
            )
        )
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-batch",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.batch",
                source_plugin_version="1.0.0",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.batch",
                    "config": {},
                    "config_fingerprint": "fingerprint-batch",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=10),
                created_by="test",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            raw_event_service=RawEventService(
                raw_event_repository=self.raw_event_repository,
                raw_event_capture_repository=self.raw_event_capture_repository,
                source_binding_repository=self.binding_repository,
                scheduler_run_repository=self.run_repository,
            ),
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )

        result = await service.run_once()

        self.assertEqual(result.binding_results[0].captured_count, 2)
        self.assertEqual(result.emitted_events, 2)
        self.assertEqual(result.binding_results[0].event_published_count, 2)
        self.assertEqual(len(self.event_handler.seen), 2)
        self.assertEqual([len(envelope.payload["items"]) for envelope in self.event_handler.seen], [1, 1])
        self.assertEqual(
            [envelope.payload["items"][0]["external_id"] for envelope in self.event_handler.seen],
            ["evt-batch-1", "evt-batch-2"],
        )

    async def test_run_once_without_due_bindings_reports_cooling_down_summary(self) -> None:
        registry = PluginRegistry(StaticScanner([]))
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-next-rss",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.rss",
                    "config": {"feeds": [{"url": "https://example.com/rss.xml"}]},
                    "config_fingerprint": "fingerprint-next-rss",
                    "template_refs": {"layers": ["semiconductor"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 300},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() + timedelta(seconds=90),
                created_by="test",
            )
        )
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-active-unscheduled",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.rss",
                    "config": {},
                    "config_fingerprint": "fingerprint-unscheduled",
                    "template_refs": {"layers": ["semiconductor"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 300},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=None,
                created_by="test",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )

        result = await service.run_once()

        self.assertEqual(result.due_bindings, 0)
        self.assertEqual(result.schedule_summary.active_bindings, 2)
        self.assertEqual(result.schedule_summary.active_scheduled_bindings, 1)
        self.assertEqual(result.schedule_summary.cooling_down_bindings, 1)
        self.assertEqual(result.schedule_summary.unscheduled_active_bindings, 1)
        self.assertEqual(len(result.schedule_summary.next_due_bindings), 1)
        next_due = result.schedule_summary.next_due_bindings[0]
        self.assertEqual(next_due.binding_id, "binding-next-rss")
        self.assertEqual(next_due.source_plugin_id, "quantagent.official.source.rss")
        self.assertEqual(next_due.owner_id, "semiconductor")
        self.assertEqual(next_due.seconds_until_due, 90)

    async def test_concurrent_binding_runs_only_create_one_run_after_claim(self) -> None:
        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"items": [], "metadata": {"source": "noop"}})

        plugin_path = Path(__file__).resolve()
        module = type(sys)(self.module_name)
        module.plugin = SourcePlugin
        sys.modules[self.module_name] = module
        registry = PluginRegistry(
            StaticScanner(
                [
                    PluginRecord(
                        id="quantagent.official.source.concurrent",
                        source=PluginSource.OFFICIAL,
                        path=plugin_path,
                        status=PluginStatus.VALID,
                        manifest=PluginManifest(
                            id="quantagent.official.source.concurrent",
                            name="Concurrent Source",
                            type=PluginType.SOURCE,
                            version="1.0.0",
                            entrypoint=f"{self.module_name}:plugin",
                            capabilities=("source.fetch",),
                            config_schema="config.schema.json",
                        ),
                        config_schema_path=plugin_path,
                    )
                ]
            )
        )
        binding = self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-concurrent",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.concurrent",
                source_plugin_version="1.0.0",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.concurrent",
                    "config": {},
                    "config_fingerprint": "fingerprint-concurrent",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=5),
                created_by="issue-251",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )

        due_snapshot = self.binding_service.list_due_bindings(limit=10)[0]
        first, second = await asyncio.gather(
            service._run_binding(due_snapshot),
            service._run_binding(due_snapshot),
        )

        self.assertEqual(len(self.run_repository.list_by_binding(binding_id=binding.binding_id, limit=10)), 1)
        self.assertEqual(sum(1 for item in (first, second) if item.skipped), 1)
        self.assertEqual(sum(1 for item in (first, second) if item.status is not None), 1)

    async def test_pause_during_invoke_only_records_run_terminal_state(self) -> None:
        plugin_path = Path(__file__).resolve()
        pause_module_name = f"{self.module_name}_pause"
        module = type(sys)(pause_module_name)
        module.plugin = BlockingInvokePlugin
        sys.modules[pause_module_name] = module
        registry = PluginRegistry(
            StaticScanner(
                [
                    PluginRecord(
                        id="quantagent.official.source.blocking",
                        source=PluginSource.OFFICIAL,
                        path=plugin_path,
                        status=PluginStatus.VALID,
                        manifest=PluginManifest(
                            id="quantagent.official.source.blocking",
                            name="Blocking Source",
                            type=PluginType.SOURCE,
                            version="1.0.0",
                            entrypoint=f"{pause_module_name}:plugin",
                            capabilities=("source.fetch",),
                            config_schema="config.schema.json",
                        ),
                        config_schema_path=plugin_path,
                    )
                ]
            )
        )
        binding = self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-pause-during-invoke",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.blocking",
                source_plugin_version="1.0.0",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.blocking",
                    "config": {},
                    "config_fingerprint": "fingerprint-blocking",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=5),
                created_by="issue-251",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )
        BlockingInvokePlugin.started = asyncio.Event()
        BlockingInvokePlugin.release = asyncio.Event()

        run_task = asyncio.create_task(service.run_once())
        await BlockingInvokePlugin.started.wait()

        self.binding_service.pause_binding(binding.binding_id, actor="reviewer")
        self.session.commit()
        BlockingInvokePlugin.release.set()

        result = await run_task

        updated_binding = self.binding_repository.get(binding.binding_id)
        self.assertIsNotNone(updated_binding)
        assert updated_binding is not None
        self.assertEqual(updated_binding.status, SourceBindingStatus.PAUSED.value)
        self.assertIsNone(updated_binding.last_run_id)
        self.assertIsNone(updated_binding.last_run_status)
        self.assertIsNone(updated_binding.next_run_at)
        self.assertEqual(result.emitted_events, 0)
        self.assertEqual(len(self.event_handler.seen), 0)

        runs = self.run_repository.list_by_binding(binding_id=binding.binding_id, limit=10)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "succeeded")

    async def test_disable_during_invoke_only_records_run_terminal_state(self) -> None:
        plugin_path = Path(__file__).resolve()
        disable_module_name = f"{self.module_name}_disable"
        module = type(sys)(disable_module_name)
        module.plugin = BlockingInvokePlugin
        sys.modules[disable_module_name] = module
        registry = PluginRegistry(
            StaticScanner(
                [
                    PluginRecord(
                        id="quantagent.official.source.blocking-disable",
                        source=PluginSource.OFFICIAL,
                        path=plugin_path,
                        status=PluginStatus.VALID,
                        manifest=PluginManifest(
                            id="quantagent.official.source.blocking-disable",
                            name="Blocking Disable Source",
                            type=PluginType.SOURCE,
                            version="1.0.0",
                            entrypoint=f"{disable_module_name}:plugin",
                            capabilities=("source.fetch",),
                            config_schema="config.schema.json",
                        ),
                        config_schema_path=plugin_path,
                    )
                ]
            )
        )
        binding = self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-disable-during-invoke",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.blocking-disable",
                source_plugin_version="1.0.0",
                effective_config_snapshot={
                    "source_plugin_id": "quantagent.official.source.blocking-disable",
                    "config": {},
                    "config_fingerprint": "fingerprint-disable",
                    "template_refs": {"layers": ["override"]},
                    "validated_at": "2026-06-01T08:00:00+00:00",
                },
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 1},
                rate_limit_policy={"requests_per_window": 10, "window_seconds": 60},
                next_run_at=self.clock.now() - timedelta(seconds=5),
                created_by="issue-251",
            )
        )
        service = SourceBindingSchedulerLoopService(
            registry=registry,
            runtime=PluginRuntimeService(),
            binding_service=self.binding_service,
            run_service=self.run_service,
            clock=self.clock,
            commit=self.session.commit,
            rollback=self.session.rollback,
            publisher=SourceEventPublisher(self.event_bus),
            default_timeout_ms=30_000,
        )
        BlockingInvokePlugin.started = asyncio.Event()
        BlockingInvokePlugin.release = asyncio.Event()

        run_task = asyncio.create_task(service.run_once())
        await BlockingInvokePlugin.started.wait()

        self.binding_service.disable_binding(binding.binding_id, reason="reviewer-disable", actor="reviewer")
        self.session.commit()
        BlockingInvokePlugin.release.set()

        result = await run_task

        updated_binding = self.binding_repository.get(binding.binding_id)
        self.assertIsNotNone(updated_binding)
        assert updated_binding is not None
        self.assertEqual(updated_binding.status, SourceBindingStatus.DISABLED.value)
        self.assertEqual(updated_binding.disabled_reason, "reviewer-disable")
        self.assertIsNone(updated_binding.last_run_id)
        self.assertIsNone(updated_binding.last_run_status)
        self.assertIsNone(updated_binding.next_run_at)
        self.assertEqual(result.emitted_events, 0)
        self.assertEqual(len(self.event_handler.seen), 0)

        runs = self.run_repository.list_by_binding(binding_id=binding.binding_id, limit=10)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "succeeded")


if __name__ == "__main__":
    unittest.main()
