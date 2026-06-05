from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.event_repository import SqlAlchemyEventReadModelRepository
from quantagent.core.event_read_model import (
    EventAnalysisStatus,
    EventCredibility,
    EventCurrentStatus,
    EventIdentityKind,
    EventListQuery,
    EventMaterializationInput,
    EventReadModelMaterializer,
    EventReadModelNotFoundError,
    EventReadModelService,
    EventRiskDirection,
    EventRiskLevel,
    EventSortMode,
    EventSourceType,
    EventTimeRange,
)


class EventReadModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()
        self.repository = SqlAlchemyEventReadModelRepository(self.session)
        self.materializer = EventReadModelMaterializer(self.repository)
        self.now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
        self.service = EventReadModelService(repository=self.repository, now_factory=lambda: self.now)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_materialize_creates_event_and_transition_once(self) -> None:
        result = self.materializer.materialize(
            self._input(
                identity_value="raw-1",
                raw_event_id="raw-1",
                title="Micron HBM capacity update",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.PENDING,
            )
        )
        self.session.commit()

        self.assertTrue(result.created)
        self.assertEqual(result.previous_status, None)
        self.assertEqual(result.current_status, EventCurrentStatus.CAPTURED.value)

        detail = self.service.get_event_detail(result.event_id)
        self.assertEqual(detail.event.raw_event_id, "raw-1")
        self.assertEqual(detail.state_summary.current_status, EventCurrentStatus.CAPTURED.value)
        self.assertEqual(len(detail.state_summary.transitions), 1)
        self.assertEqual(detail.state_summary.transitions[0].from_status, None)

    def test_materialize_same_identity_is_idempotent_when_transition_same(self) -> None:
        first = self.materializer.materialize(
            self._input(
                identity_value="raw-2",
                raw_event_id="raw-2",
                title="TSMC capacity check",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.PENDING,
                request_id="req-same",
                source_ref={"kind": "raw_event", "id": "raw-2"},
            )
        )
        second = self.materializer.materialize(
            self._input(
                identity_value="raw-2",
                raw_event_id="raw-2",
                title="TSMC capacity check newer summary",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.PENDING,
                request_id="req-same",
                source_ref={"kind": "raw_event", "id": "raw-2"},
            )
        )
        self.session.commit()

        self.assertTrue(first.created)
        self.assertFalse(second.created)

        detail = self.service.get_event_detail(first.event_id)
        self.assertEqual(detail.event.title, "TSMC capacity check newer summary")
        self.assertEqual(len(detail.state_summary.transitions), 1)

    def test_materialize_status_change_appends_transition_and_increments_version(self) -> None:
        created = self.materializer.materialize(
            self._input(
                identity_value="raw-3",
                raw_event_id="raw-3",
                title="NVIDIA earnings surprise",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.PENDING,
            )
        )
        updated = self.materializer.materialize(
            self._input(
                identity_value="raw-3",
                raw_event_id="raw-3",
                title="NVIDIA earnings surprise",
                current_status=EventCurrentStatus.DECISION_READY,
                analysis_status=EventAnalysisStatus.DECISION_READY,
                recommendation_score=0.82,
                confidence=0.76,
                reason_code="analysis_completed",
                reason_summary="analysis finished",
                request_id="req-analysis-3",
                source_ref={"kind": "analysis", "id": "analysis-3"},
            )
        )
        self.session.commit()

        self.assertTrue(created.created)
        self.assertFalse(updated.created)
        self.assertEqual(updated.previous_status, EventCurrentStatus.CAPTURED.value)

        detail = self.service.get_event_detail(created.event_id)
        self.assertEqual(detail.state_summary.current_status, EventCurrentStatus.DECISION_READY.value)
        self.assertEqual(detail.state_summary.analysis_status, EventAnalysisStatus.DECISION_READY.value)
        self.assertEqual(detail.state_summary.version, 2)
        self.assertEqual(len(detail.state_summary.transitions), 2)
        self.assertEqual(detail.state_summary.transitions[-1].from_status, EventCurrentStatus.CAPTURED.value)

    def test_backward_transition_requires_reason_code(self) -> None:
        self.materializer.materialize(
            self._input(
                identity_value="raw-4",
                raw_event_id="raw-4",
                title="Backfill test",
                current_status=EventCurrentStatus.DECISION_READY,
                analysis_status=EventAnalysisStatus.DECISION_READY,
                reason_code="seed",
            )
        )

        with self.assertRaisesRegex(ValueError, "backward status transition"):
            self.materializer.materialize(
                self._input(
                    identity_value="raw-4",
                    raw_event_id="raw-4",
                    title="Backfill test",
                    current_status=EventCurrentStatus.CAPTURED,
                    analysis_status=EventAnalysisStatus.PENDING,
                )
            )

    def test_list_events_supports_filters_sort_cursor_and_buckets(self) -> None:
        self._seed_events()

        page = self.service.list_events(
            EventListQuery(
                time_range=EventTimeRange.LAST_7D,
                industries=("semiconductor",),
                sort=EventSortMode.PRIORITY,
                limit=2,
            )
        )

        self.assertEqual(len(page.items), 2)
        self.assertIsNotNone(page.next_cursor)
        self.assertGreaterEqual(page.buckets.featured_count, 1)
        self.assertGreaterEqual(page.buckets.failed_or_review_count, 1)

        second_page = self.service.list_events(
            EventListQuery(
                time_range=EventTimeRange.LAST_7D,
                industries=("semiconductor",),
                sort=EventSortMode.PRIORITY,
                limit=2,
                cursor=page.next_cursor,
            )
        )
        self.assertEqual(len(second_page.items), 1)

    def test_dashboard_snapshot_returns_featured_and_metrics(self) -> None:
        self._seed_events()

        snapshot = self.service.get_dashboard_snapshot(featured_limit=2, time_range=EventTimeRange.LAST_7D)

        self.assertEqual(len(snapshot.featured_events), 2)
        self.assertGreaterEqual(snapshot.entry_metrics.new_count, 1)
        self.assertGreaterEqual(snapshot.entry_metrics.featured_count, 1)

    def test_dashboard_snapshot_filters_featured_events_by_time_range(self) -> None:
        self._seed_events()
        self.materializer.materialize(
            self._input(
                identity_value="seed-old",
                raw_event_id="seed-old",
                title="Old featured event",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.PENDING,
                priority_score=0.99,
                source_type=EventSourceType.RSS,
                industries=("semiconductor",),
                is_featured=True,
                featured_reason="old high priority",
                captured_at=self.now - timedelta(days=2),
            )
        )
        self.session.commit()

        snapshot = self.service.get_dashboard_snapshot(featured_limit=5, time_range=EventTimeRange.LAST_24H)

        self.assertNotIn("Old featured event", {item.title for item in snapshot.featured_events})

    def test_unknown_event_raises_service_error(self) -> None:
        with self.assertRaises(EventReadModelNotFoundError):
            self.service.get_event_detail("evt_missing")

    def _seed_events(self) -> None:
        self.materializer.materialize(
            self._input(
                identity_value="seed-1",
                raw_event_id="seed-1",
                title="HBM demand upgrade",
                current_status=EventCurrentStatus.CAPTURED,
                analysis_status=EventAnalysisStatus.ANALYZING,
                priority_score=0.91,
                recommendation_score=0.8,
                confidence=0.75,
                credibility=EventCredibility.HIGH,
                source_type=EventSourceType.RSS,
                industries=("semiconductor",),
                is_featured=True,
                featured_reason="high priority",
                captured_at=self.now - timedelta(hours=2),
            )
        )
        self.materializer.materialize(
            self._input(
                identity_value="seed-2",
                raw_event_id="seed-2",
                title="Fab outage rumor",
                current_status=EventCurrentStatus.REVIEW_REQUIRED,
                analysis_status=EventAnalysisStatus.REVIEW_REQUIRED,
                priority_score=0.4,
                confidence=0.2,
                credibility=EventCredibility.CONFLICT,
                source_type=EventSourceType.WEBHOOK,
                industries=("semiconductor",),
                risk_level=EventRiskLevel.HIGH,
                risk_direction=EventRiskDirection.NEGATIVE,
                captured_at=self.now - timedelta(hours=3),
                reason_code="conflict",
            )
        )
        self.materializer.materialize(
            self._input(
                identity_value="seed-3",
                raw_event_id="seed-3",
                title="Cloud GPU order increase",
                current_status=EventCurrentStatus.PENDING_APPROVAL,
                analysis_status=EventAnalysisStatus.PENDING_APPROVAL,
                priority_score=0.88,
                recommendation_score=0.83,
                confidence=0.81,
                credibility=EventCredibility.MEDIUM,
                source_type=EventSourceType.API,
                industries=("semiconductor", "ai-infra"),
                is_featured=True,
                featured_reason="actionable",
                captured_at=self.now - timedelta(hours=1),
                approval_id="approval-evt-3",
                reason_code="approval_needed",
            )
        )
        self.session.commit()

    def _input(
        self,
        *,
        identity_value: str,
        raw_event_id: str | None,
        title: str,
        current_status: EventCurrentStatus,
        analysis_status: EventAnalysisStatus,
        captured_at: datetime | None = None,
        request_id: str | None = None,
        source_ref: dict[str, object] | None = None,
        reason_code: str | None = None,
        reason_summary: str | None = None,
        priority_score: float | None = None,
        recommendation_score: float | None = None,
        confidence: float | None = None,
        credibility: EventCredibility | None = None,
        source_type: EventSourceType | None = None,
        industries: tuple[str, ...] = (),
        is_featured: bool = False,
        featured_reason: str | None = None,
        approval_id: str | None = None,
        risk_level: EventRiskLevel | None = None,
        risk_direction: EventRiskDirection | None = None,
    ) -> EventMaterializationInput:
        return EventMaterializationInput(
            identity_kind=EventIdentityKind.RAW_EVENT_ID if raw_event_id else EventIdentityKind.EXTERNAL,
            identity_value=identity_value,
            raw_event_id=raw_event_id,
            title=title,
            summary=f"{title} summary",
            current_status=current_status,
            analysis_status=analysis_status,
            captured_at=captured_at or self.now,
            request_id=request_id,
            source_ref=source_ref or {"kind": "seed", "id": identity_value},
            reason_code=reason_code,
            reason_summary=reason_summary,
            priority_score=priority_score,
            recommendation_score=recommendation_score,
            confidence=confidence,
            credibility=credibility,
            source_type=source_type,
            industries=industries,
            is_featured=is_featured,
            featured_reason=featured_reason,
            approval_id=approval_id,
            risk_level=risk_level,
            risk_direction=risk_direction,
            evidence_summary={"public_summary": "kept"},
            best_action_summary={"title": "Monitor", "approval_ref": approval_id, "token": "secret"},
            industry_impact_summary={"sector": list(industries)},
            degradation_notices=({"status": "ok"},),
            audit_refs=({"kind": "raw_event", "id": raw_event_id or identity_value},),
        )


if __name__ == "__main__":
    unittest.main()
