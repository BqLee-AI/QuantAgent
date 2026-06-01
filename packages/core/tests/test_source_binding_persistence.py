from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.scheduling import (
    CreateSourceBindingInput,
    FrozenSchedulingClock,
    PluginRunStatus,
    PluginTriggerType,
    SchedulerRunService,
    SourceBindingService,
    SourceBindingStatus,
)


class SourceBindingPersistenceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        self.clock = FrozenSchedulingClock(datetime(2026, 6, 1, 8, 0, tzinfo=UTC))
        self.binding_repository = SourceBindingRepository(self.session)
        self.run_repository = SchedulerRunRepository(self.session)
        self.binding_service = SourceBindingService(self.binding_repository, clock=self.clock)
        self.run_service = SchedulerRunService(self.run_repository, clock=self.clock)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_list_due_bindings_only_returns_active_records_before_now(self) -> None:
        due_time = self.clock.now() - timedelta(minutes=1)
        future_time = self.clock.now() + timedelta(minutes=5)
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-due",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/rss"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=due_time,
                created_by="issue-216",
            )
        )
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-future",
                owner_type="industry",
                owner_id="oil",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/oil"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=future_time,
                created_by="issue-216",
            )
        )
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-paused",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/macro"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                status=SourceBindingStatus.PAUSED,
                next_run_at=due_time,
                created_by="issue-216",
            )
        )

        due_bindings = self.binding_service.list_due_bindings(limit=10)

        self.assertEqual([item.binding_id for item in due_bindings], ["binding-due"])

    def test_run_finish_and_binding_summary_update_keep_history_fields_stable(self) -> None:
        binding = self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-run",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.rss",
                source_plugin_version="1.0.0",
                effective_config_snapshot={"feed": "https://example.com/rss"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=self.clock.now(),
                created_by="issue-216",
            )
        )
        run = self.run_service.create_run(
            run_id="run-1",
            binding_id=binding.binding_id,
            source_plugin_id=binding.source_plugin_id,
            source_plugin_version=binding.source_plugin_version,
            trigger_mode=PluginTriggerType.INTERVAL,
            request_id="req-1",
            status=PluginRunStatus.RUNNING,
            started_at=self.clock.now(),
            timeout_ms=30_000,
            metadata={"loop": "scheduler"},
        )
        finished_at = self.clock.now() + timedelta(seconds=2)
        finished = self.run_service.finish_run(
            run_id=run.run_id,
            status=PluginRunStatus.SUCCEEDED,
            finished_at=finished_at,
            duration_ms=2_000,
            captured_count=3,
            output_summary={"items": 3},
        )
        updated_binding = self.binding_service.apply_run_result(
            binding_id=binding.binding_id,
            run_id=finished.run_id,
            status=finished.status,
            finished_at=finished.finished_at or finished_at,
            next_run_at=finished_at + timedelta(minutes=5),
            actor="scheduler-loop",
        )

        self.assertEqual(finished.binding_id, binding.binding_id)
        self.assertEqual(finished.captured_count, 3)
        self.assertEqual(updated_binding.last_run_id, "run-1")
        self.assertEqual(updated_binding.last_run_status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(updated_binding.last_success_at, finished_at)
        self.assertEqual(updated_binding.consecutive_failure_count, 0)
        self.assertEqual(updated_binding.updated_by, "scheduler-loop")

    def test_finished_run_cannot_be_overwritten(self) -> None:
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-guard",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/rss"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=self.clock.now(),
                created_by="issue-216",
            )
        )
        run = self.run_service.create_run(
            run_id="run-guard",
            binding_id="binding-guard",
            source_plugin_id="quantagent.official.source.rss",
            source_plugin_version=None,
            trigger_mode=PluginTriggerType.MANUAL,
            request_id="req-guard",
            status=PluginRunStatus.RUNNING,
        )
        self.run_service.finish_run(
            run_id=run.run_id,
            status=PluginRunStatus.FAILED,
            finished_at=self.clock.now(),
            duration_ms=1000,
            failure_code="PLUGIN_TIMEOUT",
            failure_message="timeout",
            failure_stage="invoke",
            retryable=True,
        )

        with self.assertRaises(ValueError):
            self.run_service.finish_run(
                run_id=run.run_id,
                status=PluginRunStatus.SUCCEEDED,
                finished_at=self.clock.now(),
                duration_ms=1500,
            )

    def test_finish_run_rejects_non_terminal_status(self) -> None:
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-non-terminal",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/rss"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=self.clock.now(),
                created_by="issue-216",
            )
        )
        run = self.run_service.create_run(
            run_id="run-non-terminal",
            binding_id="binding-non-terminal",
            source_plugin_id="quantagent.official.source.rss",
            source_plugin_version=None,
            trigger_mode=PluginTriggerType.MANUAL,
            request_id="req-non-terminal",
            status=PluginRunStatus.RUNNING,
        )

        with self.assertRaisesRegex(ValueError, "terminal scheduler run statuses"):
            self.run_service.finish_run(
                run_id=run.run_id,
                status=PluginRunStatus.RUNNING,
                finished_at=self.clock.now(),
            )

    def test_finish_run_sanitizes_failure_message_before_persisting(self) -> None:
        self.binding_service.create_binding(
            CreateSourceBindingInput(
                binding_id="binding-sanitize",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feed": "https://example.com/rss"},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 2},
                rate_limit_policy={"requests_per_minute": 10},
                next_run_at=self.clock.now(),
                created_by="issue-216",
            )
        )
        run = self.run_service.create_run(
            run_id="run-sanitize",
            binding_id="binding-sanitize",
            source_plugin_id="quantagent.official.source.rss",
            source_plugin_version=None,
            trigger_mode=PluginTriggerType.MANUAL,
            request_id="req-sanitize",
            status=PluginRunStatus.RUNNING,
        )

        finished = self.run_service.finish_run(
            run_id=run.run_id,
            status=PluginRunStatus.FAILED,
            finished_at=self.clock.now(),
            failure_message="token=abc123 refused at /Users/private/app.env",
            failure_code="PLUGIN_FAILED",
            failure_stage="invoke",
        )

        self.assertEqual(finished.failure_message, "[REDACTED] refused at [REDACTED]")
        self.assertNotIn("abc123", finished.failure_message or "")
        self.assertNotIn("/Users/private/app.env", finished.failure_message or "")

    def test_repository_list_queries_apply_default_limit_and_cap(self) -> None:
        request_id = "req-limit"
        owner_id = "semiconductor"
        plugin_id = "quantagent.official.source.rss"
        for index in range(205):
            binding = self.binding_service.create_binding(
                CreateSourceBindingInput(
                    binding_id=f"binding-limit-{index:03d}",
                    owner_type="industry",
                    owner_id=owner_id,
                    source_plugin_id=plugin_id,
                    effective_config_snapshot={"feed": f"https://example.com/rss/{index}"},
                    schedule_policy={"interval_seconds": 60},
                    retry_policy={"max_attempts": 2},
                    rate_limit_policy={"requests_per_minute": 10},
                    next_run_at=self.clock.now(),
                    created_by="issue-216",
                )
            )
            self.run_service.create_run(
                run_id=f"run-limit-{index:03d}",
                binding_id=binding.binding_id,
                source_plugin_id=plugin_id,
                source_plugin_version=None,
                trigger_mode=PluginTriggerType.MANUAL,
                request_id=request_id,
                status=PluginRunStatus.RUNNING,
            )

        owner_default = self.binding_repository.list_by_owner(owner_type="industry", owner_id=owner_id)
        plugin_capped = self.binding_repository.list_by_plugin(source_plugin_id=plugin_id, limit=999)
        request_default = self.run_repository.list_by_request(request_id=request_id)
        binding_capped = self.run_repository.list_by_binding(binding_id="binding-limit-000", limit=999)

        self.assertEqual(len(owner_default), 50)
        self.assertEqual(len(plugin_capped), 200)
        self.assertEqual(len(request_default), 50)
        self.assertEqual(len(binding_capped), 1)

    def test_repository_list_queries_reject_non_positive_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            self.binding_repository.list_by_owner(owner_type="industry", owner_id="owner", limit=0)

        with self.assertRaisesRegex(ValueError, "limit must be greater than zero"):
            self.run_repository.list_by_request(request_id="req", limit=-1)


if __name__ == "__main__":
    unittest.main()
