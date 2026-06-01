from __future__ import annotations

from datetime import UTC, datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.models.source_binding import SourceBindingORM
from quantagent.core.db.models.scheduler_run import SchedulerRunORM
from quantagent.core.db.repositories.raw_event_capture_repository import RawEventCaptureRepository
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.raw_events import (
    RawEventDedupeError,
    RawEventDedupeStrategy,
    RawEventOwnershipError,
    RawEventPayloadError,
    RawEventService,
)
from quantagent.plugin_sdk import SourceFetchResult, SourceItemDraft


class RawEventServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        self.source_binding_repository = SourceBindingRepository(self.session)
        self.scheduler_run_repository = SchedulerRunRepository(self.session)
        self.raw_event_repository = RawEventRepository(self.session)
        self.raw_event_capture_repository = RawEventCaptureRepository(self.session)
        self.clock_value = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
        self.raw_event_counter = 0
        self.capture_counter = 0
        self.service = RawEventService(
            raw_event_repository=self.raw_event_repository,
            raw_event_capture_repository=self.raw_event_capture_repository,
            source_binding_repository=self.source_binding_repository,
            scheduler_run_repository=self.scheduler_run_repository,
            now_factory=lambda: self.clock_value,
            raw_event_id_factory=self._next_raw_event_id,
            capture_id_factory=self._next_capture_id,
        )
        self.source_binding_repository.create(
            SourceBindingORM(
                binding_id="binding-raw-1",
                owner_type="industry",
                owner_id="macro",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feeds": ["https://example.com/rss"]},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 3},
                rate_limit_policy={"requests_per_minute": 10},
                status="active",
                created_by="issue-221",
                updated_by="issue-221",
            )
        )
        self.source_binding_repository.create(
            SourceBindingORM(
                binding_id="binding-raw-2",
                owner_type="industry",
                owner_id="energy",
                source_plugin_id="quantagent.official.source.rss",
                effective_config_snapshot={"feeds": ["https://example.com/energy"]},
                schedule_policy={"interval_seconds": 60},
                retry_policy={"max_attempts": 3},
                rate_limit_policy={"requests_per_minute": 10},
                status="active",
                created_by="issue-221",
                updated_by="issue-221",
            )
        )
        self.scheduler_run_repository.create(
            SchedulerRunORM(
                run_id="run-raw-1",
                binding_id="binding-raw-1",
                source_plugin_id="quantagent.official.source.rss",
                source_plugin_version="1.0.0",
                trigger_mode="manual",
                request_id="req-raw-1",
                status="succeeded",
                output_summary={},
                metadata_json={},
            )
        )
        self.scheduler_run_repository.create(
            SchedulerRunORM(
                run_id="run-raw-2",
                binding_id="binding-raw-2",
                source_plugin_id="quantagent.official.source.rss",
                source_plugin_version="1.0.0",
                trigger_mode="manual",
                request_id="req-raw-2",
                status="succeeded",
                output_summary={},
                metadata_json={},
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_persist_source_fetch_result_creates_canonical_row_and_capture(self) -> None:
        summary = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            scheduler_run_id="run-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-1",
                        url="https://Example.com/news/1/?token=secret",
                        title="Oil market update",
                        content="Brent prices move higher.",
                        author="Analyst",
                        published_at="2026-06-01T08:00:00Z",
                        captured_at="2026-06-01T09:59:00Z",
                        raw_payload={"cookie": "session=abc", "body": "payload"},
                        metadata={
                            "canonical_url": "https://example.com/news/1/?token=secret",
                            "feed": "rss",
                            "private_policy": {"strategy": "do-not-store"},
                            "token": "secret",
                        },
                    ),
                )
            ),
        )

        self.assertEqual(summary.created_count, 1)
        self.assertEqual(summary.duplicate_count, 0)
        saved = summary.items[0].raw_event
        capture = summary.items[0].capture
        self.assertEqual(saved.raw_event_id, "rawevt-1")
        self.assertEqual(capture.capture_id, "rawevtcap-1")
        self.assertEqual(saved.first_binding_id, "binding-raw-1")
        self.assertEqual(saved.first_run_id, "run-raw-1")
        self.assertEqual(saved.canonical_url, "https://example.com/news/1")
        self.assertEqual(saved.dedupe_strategy, RawEventDedupeStrategy.EXTERNAL_ID)
        self.assertEqual(saved.raw_payload["cookie"], "[REDACTED]")
        self.assertEqual(saved.metadata["feed"], "rss")
        self.assertNotIn("private_policy", saved.metadata)
        self.assertNotIn("token", saved.metadata)
        self.assertEqual(capture.request_id, "req-raw-1")

    def test_duplicate_result_reuses_canonical_row_and_appends_capture_for_new_run(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            scheduler_run_id="run-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-dup",
                        title="First title",
                        content="First content",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )
        self.clock_value = datetime(2026, 6, 1, 11, 0, tzinfo=UTC)
        duplicate = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-2",
            scheduler_run_id="run-raw-2",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-dup",
                        title="Second title",
                        content="Second content",
                        captured_at="2026-06-01T10:30:00Z",
                    ),
                )
            ),
        )

        self.assertTrue(initial.items[0].created)
        self.assertFalse(duplicate.items[0].created)
        self.assertEqual(duplicate.items[0].raw_event.raw_event_id, initial.items[0].raw_event.raw_event_id)
        self.assertEqual(duplicate.items[0].raw_event.duplicate_capture_count, 1)
        self.assertEqual(duplicate.items[0].capture.capture_id, "rawevtcap-2")
        self.assertEqual(
            len(self.raw_event_capture_repository.list_by_run(scheduler_run_id="run-raw-2", limit=10)),
            1,
        )
        self.assertEqual(
            len(self.raw_event_capture_repository.list_by_binding(source_binding_id="binding-raw-2", limit=10)),
            1,
        )
        self.assertEqual(
            self.raw_event_repository.list_by_run(scheduler_run_id="run-raw-2", limit=10)[0].raw_event_id,
            initial.items[0].raw_event.raw_event_id,
        )
        self.assertEqual(
            self.raw_event_repository.list_by_binding(source_binding_id="binding-raw-2", limit=10)[0].raw_event_id,
            initial.items[0].raw_event.raw_event_id,
        )

    def test_same_run_retry_is_idempotent_for_capture_ledger(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            scheduler_run_id="run-raw-1",
            result=SourceFetchResult(
                items=(SourceItemDraft(external_id="entry-retry", title="Retry"),),
            ),
        )
        duplicate = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            scheduler_run_id="run-raw-1",
            result=SourceFetchResult(
                items=(SourceItemDraft(external_id="entry-retry", title="Retry newer"),),
            ),
        )

        self.assertFalse(duplicate.items[0].created)
        self.assertEqual(initial.items[0].capture.capture_id, duplicate.items[0].capture.capture_id)
        self.assertEqual(
            len(self.raw_event_capture_repository.list_by_run(scheduler_run_id="run-raw-1", limit=10)),
            1,
        )
        self.assertEqual(duplicate.items[0].raw_event.duplicate_capture_count, 0)

    def test_without_run_same_capture_key_is_idempotent_and_does_not_increment_duplicate_count(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-no-run-retry",
                        title="No run retry",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )
        duplicate = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-no-run-retry",
                        title="No run retry again",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )

        self.assertFalse(duplicate.items[0].created)
        self.assertEqual(initial.items[0].capture.capture_id, duplicate.items[0].capture.capture_id)
        self.assertEqual(duplicate.items[0].raw_event.duplicate_capture_count, 0)
        self.assertEqual(
            len(self.raw_event_capture_repository.list_by_binding(source_binding_id="binding-raw-1", limit=10)),
            1,
        )

    def test_without_run_distinct_captured_at_appends_capture_and_increments_duplicate_count(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-no-run-new-capture",
                        title="No run first",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )
        duplicate = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-no-run-new-capture",
                        title="No run later",
                        captured_at="2026-06-01T09:05:00Z",
                    ),
                )
            ),
        )

        self.assertFalse(duplicate.items[0].created)
        self.assertNotEqual(initial.items[0].capture.capture_id, duplicate.items[0].capture.capture_id)
        self.assertEqual(duplicate.items[0].raw_event.duplicate_capture_count, 1)
        self.assertEqual(
            len(self.raw_event_capture_repository.list_by_binding(source_binding_id="binding-raw-1", limit=10)),
            2,
        )

    def test_canonical_unique_conflict_reads_existing_row(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(items=(SourceItemDraft(external_id="entry-canonical-race"),)),
        )
        self.session.commit()
        pending_flush_error = [True]
        original_flush = self.session.flush
        original_lookup = self.raw_event_repository.get_by_canonical_identity

        def fail_once_for_savepoint(*args: object, **kwargs: object) -> object:
            if pending_flush_error[0] and self.session.in_nested_transaction():
                pending_flush_error[0] = False
                raise IntegrityError("insert raw_events", {}, Exception("unique"))
            return original_flush(*args, **kwargs)

        lookup_calls = [0]

        def miss_then_read_existing(*, source_plugin_id: str, canonical_dedupe_key: str) -> RawEventORM | None:
            lookup_calls[0] += 1
            if lookup_calls[0] == 1:
                return None
            return original_lookup(source_plugin_id=source_plugin_id, canonical_dedupe_key=canonical_dedupe_key)

        self.session.flush = fail_once_for_savepoint  # type: ignore[method-assign]
        self.raw_event_repository.get_by_canonical_identity = miss_then_read_existing  # type: ignore[method-assign]
        try:
            duplicate, created = self.raw_event_repository.get_or_create_by_canonical_identity(
                RawEventORM(
                    raw_event_id="rawevt-race-loser",
                    source_plugin_id="quantagent.official.source.rss",
                    external_id="entry-canonical-race",
                    canonical_url=None,
                    title=None,
                    content=None,
                    author=None,
                    published_at=None,
                    first_captured_at=self.clock_value,
                    last_captured_at=self.clock_value,
                    raw_payload={},
                    metadata_json={},
                    canonical_dedupe_key=initial.items[0].raw_event.canonical_dedupe_key,
                    dedupe_strategy=RawEventDedupeStrategy.EXTERNAL_ID.value,
                    content_hash=None,
                    first_binding_id="binding-raw-1",
                    first_run_id=None,
                    duplicate_capture_count=0,
                )
            )
        finally:
            self.raw_event_repository.get_by_canonical_identity = original_lookup  # type: ignore[method-assign]
            self.session.flush = original_flush  # type: ignore[method-assign]

        self.assertFalse(created)
        self.assertEqual(duplicate.raw_event_id, initial.items[0].raw_event.raw_event_id)

    def test_capture_unique_conflict_reads_existing_row(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-capture-race",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )
        self.session.commit()
        pending_flush_error = [True]
        original_flush = self.session.flush
        original_lookup = self.raw_event_capture_repository.get_by_capture_dedupe_key

        def fail_once_for_capture_savepoint(*args: object, **kwargs: object) -> object:
            if pending_flush_error[0] and self.session.in_nested_transaction():
                pending_flush_error[0] = False
                raise IntegrityError("insert raw_event_captures", {}, Exception("unique"))
            return original_flush(*args, **kwargs)

        lookup_calls = [0]

        def miss_then_read_existing(capture_dedupe_key: str) -> RawEventCaptureORM | None:
            lookup_calls[0] += 1
            if lookup_calls[0] == 1:
                return None
            return original_lookup(capture_dedupe_key)

        self.session.flush = fail_once_for_capture_savepoint  # type: ignore[method-assign]
        self.raw_event_capture_repository.get_by_capture_dedupe_key = miss_then_read_existing  # type: ignore[method-assign]
        try:
            duplicate, created = self.raw_event_capture_repository.get_or_create_by_capture_dedupe_key(
                RawEventCaptureORM(
                    capture_id="rawevtcap-race-loser",
                    raw_event_id=initial.items[0].raw_event.raw_event_id,
                    source_plugin_id="quantagent.official.source.rss",
                    source_binding_id="binding-raw-1",
                    scheduler_run_id=None,
                    capture_dedupe_key=initial.items[0].capture.capture_dedupe_key,
                    capture_status="captured",
                    captured_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
                    request_id=None,
                    metadata_json={},
                )
            )
        finally:
            self.raw_event_capture_repository.get_by_capture_dedupe_key = original_lookup  # type: ignore[method-assign]
            self.session.flush = original_flush  # type: ignore[method-assign]

        self.assertFalse(created)
        self.assertEqual(duplicate.capture_id, initial.items[0].capture.capture_id)

    def test_service_returns_existing_capture_without_incrementing_after_capture_conflict_recovery(self) -> None:
        initial = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            source_binding_id="binding-raw-1",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-capture-retry",
                        captured_at="2026-06-01T09:00:00Z",
                    ),
                )
            ),
        )
        duplicate = self.service.persist_source_fetch_result(
                source_plugin_id="quantagent.official.source.rss",
                source_binding_id="binding-raw-1",
                result=SourceFetchResult(
                    items=(
                        SourceItemDraft(
                            external_id="entry-capture-retry",
                            captured_at="2026-06-01T09:00:00Z",
                        ),
                    )
                ),
            )

        self.assertFalse(duplicate.items[0].created)
        self.assertEqual(duplicate.items[0].capture.capture_id, initial.items[0].capture.capture_id)
        self.assertEqual(duplicate.items[0].raw_event.duplicate_capture_count, 0)

    def test_fallback_dedupe_uses_canonical_url_and_content_hash(self) -> None:
        summary = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.readability",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        url="https://example.com/story?a=1",
                        title="Fallback title",
                        content="Normalized content",
                        metadata={"canonical_url": "https://example.com/story?a=1"},
                    ),
                )
            ),
        )

        self.assertEqual(summary.items[0].raw_event.dedupe_strategy, RawEventDedupeStrategy.CANONICAL_URL_CONTENT)
        self.assertIsNotNone(summary.items[0].raw_event.content_hash)

    def test_source_hint_is_last_resort_dedupe_material(self) -> None:
        summary = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.custom",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        metadata={"provider_dedupe_hint": "account:activity:1"},
                    ),
                )
            ),
        )

        self.assertEqual(summary.items[0].raw_event.dedupe_strategy, RawEventDedupeStrategy.SOURCE_HINT)

    def test_missing_dedupe_material_is_rejected(self) -> None:
        with self.assertRaises(RawEventDedupeError):
            self.service.persist_source_fetch_result(
                source_plugin_id="quantagent.official.source.rss",
                result=SourceFetchResult(items=(SourceItemDraft(),)),
            )

    def test_scheduler_run_binding_mismatch_is_rejected(self) -> None:
        with self.assertRaises(RawEventOwnershipError):
            self.service.persist_source_fetch_result(
                source_plugin_id="quantagent.official.source.rss",
                source_binding_id="binding-raw-2",
                scheduler_run_id="run-raw-1",
                result=SourceFetchResult(
                    items=(SourceItemDraft(external_id="mismatch-1"),),
                ),
            )

    def test_payload_is_trimmed_to_allowlist_and_marked(self) -> None:
        oversized_text = "x" * (130 * 1024)
        summary = self.service.persist_source_fetch_result(
            source_plugin_id="quantagent.official.source.rss",
            result=SourceFetchResult(
                items=(
                    SourceItemDraft(
                        external_id="entry-trimmed",
                        raw_payload={
                            "body": "short body",
                            "headers": {"authorization": "Bearer secret"},
                            "html": oversized_text,
                        },
                    ),
                )
            ),
        )

        payload = summary.items[0].raw_event.raw_payload
        self.assertTrue(payload["payload_truncated"])
        self.assertNotIn("html", payload)
        self.assertEqual(payload["headers"]["authorization"], "[REDACTED]")
        self.assertTrue(summary.items[0].capture.metadata["payload_truncated"])

    def test_payload_above_cap_after_trim_is_rejected(self) -> None:
        still_too_large = "x" * (129 * 1024)
        with self.assertRaises(RawEventPayloadError):
            self.service.persist_source_fetch_result(
                source_plugin_id="quantagent.official.source.rss",
                result=SourceFetchResult(
                    items=(
                        SourceItemDraft(
                            external_id="entry-too-large",
                            raw_payload={"body": still_too_large},
                        ),
                    )
                ),
            )

    def _next_raw_event_id(self) -> str:
        self.raw_event_counter += 1
        return f"rawevt-{self.raw_event_counter}"

    def _next_capture_id(self) -> str:
        self.capture_counter += 1
        return f"rawevtcap-{self.capture_counter}"


if __name__ == "__main__":
    unittest.main()
