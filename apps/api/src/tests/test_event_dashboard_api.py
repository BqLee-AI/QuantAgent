from __future__ import annotations

from datetime import UTC, datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from quantagent.api.config.settings import Settings
from quantagent.api.main import create_app
from quantagent.core.approval.query_service import ApprovalPage
from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalRequest,
    ConfirmationLevel,
    ExpirationAction,
)
from quantagent.core.db.base import Base
from quantagent.core.db.repositories.approval_repository import SQLAlchemyApprovalRepository
from quantagent.core.db.repositories.event_repository import SqlAlchemyEventReadModelRepository
from quantagent.core.event_read_model import (
    EventAnalysisStatus,
    EventCurrentStatus,
    EventIdentityKind,
    EventMaterializationInput,
    EventReadModelMaterializer,
    EventSourceType,
)


class EventDashboardApiTestCase(unittest.TestCase):
    def test_events_and_dashboard_routes_require_session(self) -> None:
        settings = self._settings()
        with TestClient(create_app(settings)) as client:
            list_response = client.get("/api/v1/events")
            detail_response = client.get("/api/v1/events/evt-missing")
            dashboard_response = client.get("/api/v1/dashboard/summary")

        for response in (list_response, detail_response, dashboard_response):
            body = response.json()
            self.assertEqual(response.status_code, 401)
            self.assertEqual(body["error"]["code"], "UNAUTHORIZED")

    def test_events_list_detail_and_dashboard_return_envelope(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._seed_event_and_approval(client)
            csrf = self._login(client, settings)

            list_response = client.get(
                "/api/v1/events",
                headers={"X-Request-ID": "req-events-ok"},
                params=[("time_range", "7d"), ("industry", "semiconductor"), ("limit", "20"), ("sort", "priority")],
            )
            list_body = list_response.json()
            event_id = list_body["data"]["items"][0]["event_id"]

            detail_response = client.get(f"/api/v1/events/{event_id}")
            dashboard_response = client.get("/api/v1/dashboard/summary")
            openapi_response = client.get("/openapi.json")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_body["code"], 0)
        self.assertEqual(list_body["data"]["filters"]["time_range"], "7d")
        self.assertEqual(list_body["data"]["filters"]["industry"], ["semiconductor"])
        self.assertEqual(list_body["data"]["summary_buckets"]["featured_count"], 1)
        self.assertEqual(list_body["data"]["items"][0]["raw_event_ref"]["id"], "raw-api-1")

        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["data"]["event_id"], event_id)
        self.assertEqual(detail_body["data"]["best_action"]["approval_ref"]["id"], "approval-api-1")
        self.assertNotEqual(detail_body["data"]["best_action"]["title"], None)
        self.assertEqual(detail_body["data"]["state_summary"]["version"], 1)
        self.assertNotIn("secret", str(detail_body))
        self.assertNotIn("provider_raw_response", str(detail_body))

        dashboard_body = dashboard_response.json()
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_body["data"]["featured_events"]["meta"]["status"], "ok")
        self.assertEqual(dashboard_body["data"]["entry_metrics"]["meta"]["status"], "ok")
        self.assertEqual(dashboard_body["data"]["approval_summary"]["meta"]["status"], "ok")
        self.assertEqual(dashboard_body["data"]["health_summary"]["meta"]["status"], "unavailable")
        self.assertEqual(dashboard_body["data"]["approval_summary"]["data"]["pending_count"], 1)
        self.assertEqual(dashboard_body["data"]["approval_summary"]["data"]["expiring_soon_count"], 0)

        schema = openapi_response.json()
        self.assertIn("/api/v1/events", schema["paths"])
        self.assertIn("/api/v1/events/{event_id}", schema["paths"])
        self.assertIn("/api/v1/dashboard/summary", schema["paths"])
        self.assertIn("events", schema["paths"]["/api/v1/events"]["get"]["tags"])
        self.assertIn("dashboard", schema["paths"]["/api/v1/dashboard/summary"]["get"]["tags"])
        response_schema = schema["paths"]["/api/v1/events"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertTrue("$ref" in response_schema or "allOf" in response_schema or "anyOf" in response_schema)
        self.assertEqual(list_response.headers["X-Request-ID"], "req-events-ok")
        self.assertTrue(csrf)

    def test_unknown_event_returns_404_envelope(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            response = client.get("/api/v1/events/evt_missing", headers={"X-Request-ID": "req-events-missing"})

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")
        self.assertEqual(body["error"]["details"]["event_id"], "evt_missing")
        self.assertEqual(response.headers["X-Request-ID"], "req-events-missing")
        self.assertEqual(body["error"]["request_id"], "req-events-missing")

    def test_invalid_event_query_uses_bad_request_envelope(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        invalid_cases = (
            {"sort": "bad"},
            {"credibility": "bad"},
            {"analysis_status": "bad"},
            {"source_type": "bad"},
        )
        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            for params in invalid_cases:
                response = client.get("/api/v1/events", params=params, headers={"X-Request-ID": "req-events-bad"})
                body = response.json()
                self.assertEqual(response.status_code, 400)
                self.assertEqual(body["error"]["code"], "BAD_REQUEST")
                self.assertEqual(response.headers["X-Request-ID"], "req-events-bad")
                self.assertEqual(body["error"]["request_id"], "req-events-bad")

    def test_dashboard_summary_uses_empty_sections_without_seed_data(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            response = client.get("/api/v1/dashboard/summary", headers={"X-Request-ID": "req-dashboard-empty"})

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-dashboard-empty")
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["featured_events"]["meta"]["status"], "empty")
        self.assertEqual(body["data"]["approval_summary"]["meta"]["status"], "empty")
        self.assertEqual(body["data"]["entry_metrics"]["meta"]["status"], "ok")
        self.assertEqual(body["data"]["health_summary"]["meta"]["status"], "unavailable")

    def test_dashboard_summary_counts_are_not_truncated_by_preview_limit(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")
        app = create_app(settings)

        with TestClient(app) as client:
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            self._seed_many_pending_approvals(client, total=25)
            response = client.get("/api/v1/dashboard/summary")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["data"]["approval_summary"]["meta"]["status"], "ok")
        self.assertEqual(body["data"]["approval_summary"]["data"]["pending_count"], 25)
        self.assertEqual(len(body["data"]["approval_summary"]["data"]["items"]), 5)

    def test_dashboard_summary_degrades_sections_without_failing_envelope(self) -> None:
        database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database_file.close()
        self.addCleanup(lambda: os.unlink(database_file.name))
        settings = self._settings(DATABASE_URL=f"sqlite+pysqlite:///{database_file.name}")

        app = create_app(settings)
        with (
            patch(
                "quantagent.api.services.dashboard_api.EventReadModelService.get_dashboard_snapshot",
                side_effect=RuntimeError("snapshot down"),
            ),
            patch(
                "quantagent.api.services.dashboard_api.ApprovalQueryService.list_approvals",
                return_value=ApprovalPage(items=(), next_cursor=None),
            ),
            TestClient(app) as client,
        ):
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            empty_response = client.get(
                "/api/v1/dashboard/summary",
                headers={"X-Request-ID": "req-dashboard-empty-approval"},
            )

        empty_body = empty_response.json()
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_body["code"], 0)
        self.assertEqual(empty_body["data"]["featured_events"]["meta"]["status"], "error")
        self.assertEqual(empty_body["data"]["entry_metrics"]["meta"]["status"], "error")
        self.assertEqual(empty_body["data"]["approval_summary"]["meta"]["status"], "empty")
        self.assertEqual(empty_body["data"]["health_summary"]["meta"]["status"], "unavailable")
        self.assertEqual(empty_response.headers["X-Request-ID"], "req-dashboard-empty-approval")

        app = create_app(settings)
        with (
            patch(
                "quantagent.api.services.dashboard_api.EventReadModelService.get_dashboard_snapshot",
                side_effect=RuntimeError("snapshot down"),
            ),
            patch(
                "quantagent.api.services.dashboard_api.ApprovalQueryService.list_approvals",
                side_effect=RuntimeError("approval down"),
            ),
            TestClient(app) as client,
        ):
            Base.metadata.create_all(client.app.state.db_engine)
            self._login(client, settings)
            unavailable_response = client.get(
                "/api/v1/dashboard/summary",
                headers={"X-Request-ID": "req-dashboard-unavailable"},
            )

        unavailable_body = unavailable_response.json()
        self.assertEqual(unavailable_response.status_code, 200)
        self.assertEqual(unavailable_body["code"], 0)
        self.assertEqual(unavailable_body["data"]["featured_events"]["meta"]["status"], "error")
        self.assertEqual(unavailable_body["data"]["entry_metrics"]["meta"]["status"], "error")
        self.assertEqual(unavailable_body["data"]["approval_summary"]["meta"]["status"], "unavailable")
        self.assertEqual(unavailable_body["data"]["health_summary"]["meta"]["status"], "unavailable")
        self.assertEqual(unavailable_response.headers["X-Request-ID"], "req-dashboard-unavailable")

    def _seed_event_and_approval(self, client: TestClient) -> None:
        with client.app.state.db_session_factory() as session:
            approval_repository = SQLAlchemyApprovalRepository(session)
            approval_repository.save_action_request(
                ActionRequest(
                    id="action-api-1",
                    action_type="adjust_strategy",
                    action_side="buy",
                    target_type="strategy",
                    target_id="semi-growth",
                    urgency="normal",
                    proposed_payload={"summary": "masked"},
                )
            )
            approval_repository.save_approval_request(
                ApprovalRequest(
                    id="approval-api-1",
                    action_request_id="action-api-1",
                    target_type="strategy",
                    target_id="semi-growth",
                    action_type="adjust_strategy",
                    action_side="buy",
                    risk_level="medium",
                    urgency="normal",
                    summary="adjust strategy after event",
                    required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
                    expiration_action=ExpirationAction.EXPIRE_REJECT,
                    policy_source="test",
                    allowed_channels=("web",),
                )
            )
            materializer = EventReadModelMaterializer(SqlAlchemyEventReadModelRepository(session))
            materializer.materialize(
                EventMaterializationInput(
                    identity_kind=EventIdentityKind.RAW_EVENT_ID,
                    identity_value="raw-api-1",
                    raw_event_id="raw-api-1",
                    title="HBM supply chain improves",
                    summary="Micron and packaging capacity trend",
                    current_status=EventCurrentStatus.PENDING_APPROVAL,
                    analysis_status=EventAnalysisStatus.PENDING_APPROVAL,
                    source_type=EventSourceType.RSS,
                    source_name="Example RSS",
                    source_authority="example.com",
                    source_url="https://example.com/hbm",
                    industries=("semiconductor",),
                    priority_score=0.95,
                    recommendation_score=0.84,
                    confidence=0.79,
                    is_featured=True,
                    featured_reason="priority",
                    captured_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
                    approval_id="approval-api-1",
                    trace_id="trace-api-1",
                    evidence_summary={"summary": "public evidence"},
                    industry_impact_summary={"summary": "sector impact"},
                    best_action_summary={
                        "title": "Review strategy",
                        "action_hint": "open approval",
                        "approval_ref": "approval-api-1",
                        "recommendation_score": 0.84,
                        "confidence": 0.79,
                        "risk_level": "medium",
                        "risk_direction": "positive",
                        "token": "masked-secret",
                    },
                    degradation_notices=({"status": "ok"},),
                    audit_refs=({"kind": "raw_event", "id": "raw-api-1"},),
                    reason_code="approval_required",
                    source_ref={"kind": "seed", "id": "raw-api-1"},
                )
            )
            session.commit()

    def _login(self, client: TestClient, settings: Settings) -> str:
        response = client.post("/api/v1/auth/login", json={"password": settings.AUTH_ADMIN_PASSWORD})
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["csrf_token"]

    def _seed_many_pending_approvals(self, client: TestClient, *, total: int) -> None:
        with client.app.state.db_session_factory() as session:
            approval_repository = SQLAlchemyApprovalRepository(session)
            for index in range(total):
                action_id = f"action-bulk-{index}"
                approval_id = f"approval-bulk-{index}"
                approval_repository.save_action_request(
                    ActionRequest(
                        id=action_id,
                        action_type="adjust_strategy",
                        action_side="buy",
                        target_type="strategy",
                        target_id=f"strategy-{index}",
                        urgency="normal",
                        proposed_payload={"summary": "masked"},
                    )
                )
                approval_repository.save_approval_request(
                    ApprovalRequest(
                        id=approval_id,
                        action_request_id=action_id,
                        target_type="strategy",
                        target_id=f"strategy-{index}",
                        action_type="adjust_strategy",
                        action_side="buy",
                        risk_level="medium",
                        urgency="normal",
                        summary=f"bulk approval {index}",
                        required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
                        expiration_action=ExpirationAction.EXPIRE_REJECT,
                        policy_source="test",
                        allowed_channels=("web",),
                    )
                )
            session.commit()

    def _settings(self, **overrides) -> Settings:
        baseline = {
            "_env_file": None,
            "APP_ENV": "development",
            "DATABASE_URL": None,
            "AUTH_ADMIN_PASSWORD": "test-admin-password",
            "AUTH_SESSION_SECRET": "test-session-secret-0123456789abcdef",
        }
        baseline.update(overrides)
        return Settings(**baseline)


if __name__ == "__main__":
    unittest.main()
