from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
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
    SchedulingActionStateError,
    SchedulingQueryService,
    SchedulerRunQuery,
    SourceBindingActionService,
    SourceBindingQuery,
    SourceBindingStatus,
)
from quantagent.core.scheduling.run_service import SchedulerRunService


class SourceBindingApiServicesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        self.clock = FrozenSchedulingClock(datetime(2026, 6, 1, 9, 0, tzinfo=UTC))
        self.binding_repository = SourceBindingRepository(self.session)
        self.run_repository = SchedulerRunRepository(self.session)
        self.query_service = SchedulingQueryService(
            binding_repository=self.binding_repository,
            run_repository=self.run_repository,
        )
        self.action_service = SourceBindingActionService(
            binding_repository=self.binding_repository,
            run_repository=self.run_repository,
            clock=self.clock,
        )
        self.run_service = SchedulerRunService(self.run_repository, clock=self.clock)
        self.binding_repository.create(
            __import__("quantagent.core.db.models.source_binding", fromlist=["SourceBindingORM"]).SourceBindingORM(
                binding_id="binding-api-001",
                owner_type="industry",
                owner_id="semiconductor",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={
                    "feed": "https://example.com/rss",
                    "api_key": "should-not-leak",
                    "keywords": ["chip", "fab"],
                },
                schedule_policy={"interval_seconds": 300},
                retry_policy={"max_attempts": 3},
                rate_limit_policy={"requests_per_minute": 10},
                status="active",
                created_by="issue-226",
                updated_by="issue-226",
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_query_service_masks_sensitive_config_fields(self) -> None:
        detail = self.query_service.get_binding_detail("binding-api-001")

        self.assertEqual(detail.summary.id, "binding-api-001")
        self.assertIn("api_key", detail.effective_config_summary.secret_fields_masked)
        self.assertNotIn("api_key", detail.effective_config_summary.values)
        self.assertIn("run-now", detail.summary.allowed_actions)

    def test_pause_and_resume_are_idempotent(self) -> None:
        first_pause = self.action_service.pause_binding(
            binding_id="binding-api-001",
            actor_id="local_admin",
            request_id="req-pause-1",
        )
        second_pause = self.action_service.pause_binding(
            binding_id="binding-api-001",
            actor_id="local_admin",
            request_id="req-pause-2",
        )
        resumed = self.action_service.resume_binding(
            binding_id="binding-api-001",
            actor_id="local_admin",
            request_id="req-resume-1",
        )

        self.assertFalse(first_pause.already_in_target_state)
        self.assertTrue(second_pause.already_in_target_state)
        self.assertEqual(resumed.target_state, SourceBindingStatus.ACTIVE)

    def test_run_now_creates_manual_queued_run_record(self) -> None:
        accepted = self.action_service.request_run_now(
            binding_id="binding-api-001",
            actor_id="local_admin",
            actor_type="local_single_user",
            request_id="req-run-now-1",
        )

        created = self.run_repository.list_by_request(request_id="req-run-now-1")
        self.assertEqual(accepted.requested_run_ref, created[0].run_id)
        self.assertEqual(created[0].trigger_mode, PluginTriggerType.MANUAL.value)
        self.assertEqual(created[0].status, PluginRunStatus.QUEUED.value)

    def test_run_list_filters_by_binding_and_status(self) -> None:
        self.run_service.create_run(
            run_id="run-api-1",
            binding_id="binding-api-001",
            source_plugin_id="quantagent.official.source.rss",
            source_plugin_version=None,
            trigger_mode=PluginTriggerType.MANUAL,
            request_id="req-runs",
            status=PluginRunStatus.RUNNING,
        )
        page = self.query_service.list_runs(
            SchedulerRunQuery(binding_id="binding-api-001", status=PluginRunStatus.RUNNING, limit=10)
        )

        self.assertEqual(len(page.items), 1)
        self.assertEqual(page.items[0].binding_id, "binding-api-001")

    def test_query_service_rejects_invalid_cursor_encoding(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid cursor"):
            self.query_service.list_bindings(SourceBindingQuery(cursor="not-base64", limit=10))

    def test_scheduler_run_repository_rejects_incomplete_cursor(self) -> None:
        with self.assertRaisesRegex(ValueError, "scheduler run cursor missing created_at"):
            self.run_repository.list_for_api(cursor={"run_id": "run-api-1"}, limit=10)

    def test_scheduler_run_repository_rejects_invalid_cursor_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "scheduler run cursor has invalid created_at"):
            self.run_repository.list_for_api(cursor={"created_at": "bad-time", "run_id": "run-api-1"}, limit=10)

    def test_source_binding_repository_rejects_incomplete_cursor(self) -> None:
        with self.assertRaisesRegex(ValueError, "source binding cursor missing updated_at"):
            self.binding_repository.list_for_api(cursor={"binding_id": "binding-api-001"}, limit=10)

    def test_source_binding_repository_rejects_invalid_cursor_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "source binding cursor has invalid updated_at"):
            self.binding_repository.list_for_api(
                cursor={"updated_at": "bad-time", "binding_id": "binding-api-001"},
                limit=10,
            )

    def test_query_service_accepts_valid_cursor_payload(self) -> None:
        encoded_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "updated_at": datetime(2026, 6, 1, 9, 0, tzinfo=UTC).isoformat(),
                    "binding_id": "binding-api-001",
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).decode("ascii")

        page = self.query_service.list_bindings(SourceBindingQuery(cursor=encoded_cursor, limit=10))
        self.assertEqual(page.items, ())

    def test_disabled_binding_rejects_actions(self) -> None:
        binding = self.binding_repository.get("binding-api-001")
        assert binding is not None
        binding.status = "disabled"
        self.binding_repository.save(binding)
        self.session.commit()

        with self.assertRaises(SchedulingActionStateError):
            self.action_service.pause_binding(
                binding_id="binding-api-001",
                actor_id="local_admin",
                request_id="req-disabled",
            )


if __name__ == "__main__":
    unittest.main()
