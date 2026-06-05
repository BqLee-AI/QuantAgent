from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from quantagent.api.schemas.dashboard import DashboardSummaryResponse
from quantagent.api.services.event_api import _to_list_item
from quantagent.core.approval import ApprovalListQuery, ApprovalQueryService
from quantagent.core.db.repositories.approval_repository import SQLAlchemyApprovalRepository
from quantagent.core.db.repositories.event_repository import SqlAlchemyEventReadModelRepository
from quantagent.core.event_read_model import EventReadModelService, EventTimeRange


class DashboardApiService:
    def __init__(self, *, session: Session, request: Request) -> None:
        self._session = session
        self._event_service = EventReadModelService(
            repository=SqlAlchemyEventReadModelRepository(session),
            now_factory=lambda: datetime.now(UTC),
        )
        self._approval_service = ApprovalQueryService(SQLAlchemyApprovalRepository(session))
        self._request = request

    def get_summary(self) -> DashboardSummaryResponse:
        now = datetime.now(UTC)
        featured_payload = {"items": [], "generated_at": now.isoformat()}
        featured_meta = {"status": "empty", "reason": None, "updated_at": now}
        metrics_payload = {}
        metrics_meta = {"status": "empty", "reason": None, "updated_at": now}
        try:
            snapshot = self._event_service.get_dashboard_snapshot(featured_limit=5, time_range=EventTimeRange.LAST_24H)
            featured_payload = {
                "items": [_to_list_item(item).model_dump(mode="json") for item in snapshot.featured_events],
                "generated_at": snapshot.generated_at.isoformat(),
            }
            featured_meta = {
                "status": "ok" if snapshot.featured_events else "empty",
                "reason": None,
                "updated_at": snapshot.generated_at,
            }
            metrics_payload = {
                "new_count": snapshot.entry_metrics.new_count,
                "featured_count": snapshot.entry_metrics.featured_count,
                "analyzing_count": snapshot.entry_metrics.analyzing_count,
                "failed_or_review_count": snapshot.entry_metrics.failed_or_review_count,
                "pending_approval_count": snapshot.entry_metrics.pending_approval_count,
            }
            metrics_meta = {"status": "ok", "reason": None, "updated_at": snapshot.generated_at}
        except Exception as exc:
            featured_meta = {"status": "error", "reason": f"event_read_model:{exc.__class__.__name__}", "updated_at": now}
            metrics_meta = {"status": "error", "reason": f"event_read_model:{exc.__class__.__name__}", "updated_at": now}

        approval_payload = {"pending_count": 0, "expiring_soon_count": 0, "items": []}
        approval_meta = {"status": "empty", "reason": None, "updated_at": now}
        try:
            pending_approvals = self._approval_service.list_approvals(
                ApprovalListQuery(status="pending", limit=20)
            )
            pending_counts = self._approval_service.count_approvals(status="pending")
            expiring_counts = self._approval_service.count_approvals(
                status="pending",
                expires_before=now + timedelta(days=1),
            )
            approval_payload = {
                "pending_count": pending_counts.total,
                "expiring_soon_count": expiring_counts.total,
                "items": [
                    {
                        "approval_id": item.id,
                        "summary": item.summary,
                        "risk_level": item.risk_level,
                        "expires_at": item.expires_at,
                    }
                    for item in pending_approvals.items[:5]
                ],
            }
            approval_meta = {
                "status": "ok" if pending_approvals.items else "empty",
                "reason": None,
                "updated_at": now,
            }
        except Exception as exc:
            approval_meta = {"status": "unavailable", "reason": f"approval_summary:{exc.__class__.__name__}", "updated_at": now}

        # V1 只返回影响判断质量的最小健康摘要；没有稳定 runtime read model 时明确降级。
        health_payload = {"status": "unavailable", "items": []}
        health_meta = {
            "status": "unavailable",
            "reason": "runtime_health:runtime_summary_v1_not_connected",
            "updated_at": now,
        }

        return DashboardSummaryResponse(
            featured_events={"meta": featured_meta, "data": featured_payload},
            approval_summary={"meta": approval_meta, "data": approval_payload},
            health_summary={"meta": health_meta, "data": health_payload},
            entry_metrics={"meta": metrics_meta, "data": metrics_payload},
        )
