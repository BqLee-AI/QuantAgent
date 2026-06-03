from __future__ import annotations
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.core.scheduling import SchedulerLoopScheduleSummary, SchedulerLoopTickResult, SourceBindingSchedulePreview
from quantagent.scheduler.main import create_scheduler_app, create_scheduler_runtime


class SchedulerMainTestCase(unittest.TestCase):
    def test_scheduler_runtime_uses_memory_backend_when_explicitly_overridden(self) -> None:
        with patch("quantagent.scheduler.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_scheduler_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)

    def test_create_scheduler_app_requires_database_url(self) -> None:
        with patch("quantagent.scheduler.main.settings.DATABASE_URL", None):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
                create_scheduler_app()

    def test_create_scheduler_app_builds_loop_service_when_database_url_exists(self) -> None:
        with patch("quantagent.scheduler.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.scheduler.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_scheduler_app()
        self.assertIsNotNone(app.loop_service)
        self.assertEqual(app.runtime.backend, "memory")

    def test_idle_tick_log_is_throttled_until_interval_or_summary_changes(self) -> None:
        import quantagent.scheduler.main as scheduler_main

        scheduler_main._last_idle_log_at = None
        scheduler_main._last_idle_signature = None
        next_run_at = datetime(2026, 6, 1, 8, 2, tzinfo=UTC)
        first = _idle_tick(
            now=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
            next_binding_id="binding-a",
            next_run_at=next_run_at,
        )
        same = _idle_tick(
            now=datetime(2026, 6, 1, 8, 0, 30, tzinfo=UTC),
            next_binding_id="binding-a",
            next_run_at=next_run_at,
        )
        changed = _idle_tick(
            now=datetime(2026, 6, 1, 8, 0, 31, tzinfo=UTC),
            next_binding_id="binding-b",
            next_run_at=next_run_at,
        )
        delayed = _idle_tick(
            now=datetime(2026, 6, 1, 8, 1, 40, tzinfo=UTC),
            next_binding_id="binding-b",
            next_run_at=next_run_at,
        )

        with patch("quantagent.scheduler.main.settings.SCHEDULER_IDLE_LOG_INTERVAL_SECONDS", 60):
            with self.assertLogs("quantagent.scheduler.main", level="INFO") as first_logs:
                scheduler_main._log_tick_result(first)
            self.assertIn("Scheduler idle", "\n".join(first_logs.output))

            with patch.object(scheduler_main.logger, "info") as info:
                scheduler_main._log_tick_result(same)
            info.assert_not_called()

            with patch.object(scheduler_main.logger, "info") as info:
                scheduler_main._log_tick_result(changed)
            info.assert_called_once()

            with patch.object(scheduler_main.logger, "info") as info:
                scheduler_main._log_tick_result(delayed)
            info.assert_called_once()


def _idle_tick(*, now: datetime, next_binding_id: str, next_run_at: datetime) -> SchedulerLoopTickResult:
    return SchedulerLoopTickResult(
        started_at=now,
        finished_at=now,
        duration_ms=1,
        due_bindings=0,
        processed_bindings=0,
        succeeded_runs=0,
        failed_runs=0,
        skipped_bindings=0,
        persistence_failures=0,
        emitted_events=0,
        heartbeat_at=now,
        schedule_summary=SchedulerLoopScheduleSummary(
            active_bindings=2,
            active_scheduled_bindings=1,
            cooling_down_bindings=1,
            unscheduled_active_bindings=1,
            next_due_bindings=(
                SourceBindingSchedulePreview(
                    binding_id=next_binding_id,
                    source_plugin_id="quantagent.official.source.rss",
                    owner_type="industry",
                    owner_id="semiconductor",
                    next_run_at=next_run_at,
                    seconds_until_due=90,
                ),
            ),
        ),
        binding_results=(),
    )


if __name__ == "__main__":
    unittest.main()
