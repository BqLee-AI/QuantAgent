from __future__ import annotations

from datetime import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalDecision,
    ApprovalDecisionStatus,
    ApprovalEvaluation,
    ApprovalInput,
    ApprovalIntent,
    ApprovalRequest,
    ApprovalAuditRecord,
    ConfirmationLevel,
    ExecutionStatus,
    ExpirationAction,
    PolicyGateStatus,
)
from quantagent.core.db.base import Base
from quantagent.core.db.models.approval import ApprovalRequestORM
from quantagent.core.db.repositories.approval_repository import SQLAlchemyApprovalRepository
from quantagent.core.approval.query_service import ApprovalListQuery, ApprovalQueryService


class SQLAlchemyApprovalRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.repository = SQLAlchemyApprovalRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_round_trips_action_approval_input_evaluation_and_decision(self) -> None:
        action = _action()
        approval = _approval()
        user_input = _input()
        evaluation = _evaluation()
        decision = _decision(status=ApprovalDecisionStatus.REJECTED, request_id="req-decision-1")

        self.repository.save_action_request(action)
        self.repository.save_approval_request(approval)
        stored_input = self.repository.save_input(user_input)
        self.repository.save_evaluation(evaluation)
        self.repository.save_decision(decision)
        self.repository.link_decision_to_input(user_input.id, decision.approval_id)
        self.session.commit()

        self.assertEqual(self.repository.get_action_request(action.id), action)
        stored_approval = self.repository.get_approval_request(approval.id)
        self.assertEqual(stored_approval.to_mapping() | {"created_at": None, "updated_at": None}, approval.to_mapping())
        self.assertIsNotNone(stored_approval.created_at)
        self.assertIsNotNone(stored_approval.updated_at)
        self.assertEqual(stored_input, user_input)
        self.assertEqual(self.repository.get_input(user_input.id), user_input)
        self.assertEqual(self.repository.get_evaluation_by_input_id(user_input.id), evaluation)
        self.assertEqual(self.repository.get_decision_by_input_id(user_input.id), decision)
        self.assertEqual(self.repository.get_decision_by_input_id(user_input.id).request_id, "req-decision-1")
        self.assertEqual(self.repository.latest_decision(approval.id), decision)
        self.assertEqual(self.repository.list_inputs(approval.id), (user_input,))
        self.assertEqual(self.repository.list_evaluations(approval.id), (evaluation,))
        self.assertEqual(self.repository.list_decisions(approval.id), (decision,))

    def test_duplicate_input_id_reuses_existing_input(self) -> None:
        self.repository.save_action_request(_action())
        self.repository.save_approval_request(_approval())
        first = _input(raw_text="first")
        second = _input(raw_text="second")

        stored_first = self.repository.save_input(first)
        stored_second = self.repository.save_input(second)

        self.assertEqual(stored_first.raw_text, "first")
        self.assertEqual(stored_second.raw_text, "first")
        self.assertEqual(self.repository.list_inputs("approval-1"), (first,))

    def test_duplicate_input_id_is_scoped_to_approval(self) -> None:
        self.repository.save_action_request(_action(action_id="action-1"))
        self.repository.save_approval_request(_approval(approval_id="approval-1", action_id="action-1"))
        self.repository.save_action_request(_action(action_id="action-2"))
        self.repository.save_approval_request(_approval(approval_id="approval-2", action_id="action-2"))
        first_input = _input(input_id="shared-input", approval_id="approval-1")
        first_evaluation = _evaluation(input_id="shared-input", approval_id="approval-1")
        first_decision = _decision(status=ApprovalDecisionStatus.REJECTED, approval_id="approval-1", action_id="action-1")
        second_input = _input(input_id="shared-input", approval_id="approval-2")
        second_evaluation = _evaluation(input_id="shared-input", approval_id="approval-2")
        second_decision = _decision(status=ApprovalDecisionStatus.REANALYSIS_REQUESTED, approval_id="approval-2", action_id="action-2")

        self.repository.save_input(first_input)
        self.repository.save_evaluation(first_evaluation)
        self.repository.save_decision(first_decision)
        self.repository.link_decision_to_input(first_input.id, first_decision.approval_id)
        self.repository.save_input(second_input)
        self.repository.save_evaluation(second_evaluation)
        self.repository.save_decision(second_decision)
        self.repository.link_decision_to_input(second_input.id, second_decision.approval_id)
        self.session.commit()

        self.assertEqual(self.repository.get_input("shared-input", approval_id="approval-1"), first_input)
        self.assertEqual(self.repository.get_input("shared-input", approval_id="approval-2"), second_input)
        self.assertEqual(self.repository.get_evaluation_by_input_id("shared-input", approval_id="approval-2"), second_evaluation)
        self.assertEqual(self.repository.get_decision_by_input_id("shared-input", approval_id="approval-2"), second_decision)

    def test_latest_decision_uses_main_table_ref_and_stable_ordering(self) -> None:
        self.repository.save_action_request(_action())
        self.repository.save_approval_request(_approval())
        first = _decision(status=ApprovalDecisionStatus.PENDING, reason_summary="pending")
        second = _decision(status=ApprovalDecisionStatus.REJECTED, reason_summary="rejected")

        self.repository.save_decision(first)
        self.repository.save_decision(second)
        self.session.commit()

        self.assertEqual(self.repository.latest_decision("approval-1"), second)
        approval_row = self.session.get(ApprovalRequestORM, "approval-1")
        self.assertIsNotNone(approval_row.latest_decision_record_id)

    def test_query_service_batches_latest_decisions_for_list(self) -> None:
        class CountingApprovalRepository(SQLAlchemyApprovalRepository):
            def __init__(self, session: Session) -> None:
                super().__init__(session)
                self.latest_decision_calls = 0
                self.list_latest_decisions_calls = 0

            def latest_decision(self, approval_id: str) -> ApprovalDecision | None:
                self.latest_decision_calls += 1
                return super().latest_decision(approval_id)

            def list_latest_decisions(self, approval_ids: tuple[str, ...]) -> dict[str, ApprovalDecision]:
                self.list_latest_decisions_calls += 1
                return super().list_latest_decisions(approval_ids)

        repository = CountingApprovalRepository(self.session)
        repository.save_action_request(_action(action_id="action-1"))
        repository.save_approval_request(_approval(approval_id="approval-1", action_id="action-1"))
        repository.save_decision(_decision(status=ApprovalDecisionStatus.REJECTED, approval_id="approval-1", action_id="action-1"))
        repository.save_action_request(_action(action_id="action-2"))
        repository.save_approval_request(_approval(approval_id="approval-2", action_id="action-2"))
        repository.save_decision(
            _decision(
                status=ApprovalDecisionStatus.REANALYSIS_REQUESTED,
                approval_id="approval-2",
                action_id="action-2",
            )
        )
        self.session.commit()

        page = ApprovalQueryService(repository).list_approvals(ApprovalListQuery(limit=10))

        self.assertEqual(repository.list_latest_decisions_calls, 1)
        self.assertEqual(repository.latest_decision_calls, 0)
        self.assertEqual(
            {item.id: item.latest_decision_summary.status for item in page.items},
            {"approval-1": "rejected", "approval-2": "reanalysis_requested"},
        )

    def test_list_approval_requests_filters_and_returns_cursor(self) -> None:
        self.repository.save_action_request(_action(action_id="action-1"))
        self.repository.save_approval_request(_approval(approval_id="approval-1", action_id="action-1", risk_level="high"))
        self.repository.save_action_request(_action(action_id="action-2"))
        self.repository.save_approval_request(_approval(approval_id="approval-2", action_id="action-2", risk_level="low"))
        self.session.commit()

        items, next_cursor = self.repository.list_approval_requests(risk_level="high", limit=1)

        self.assertEqual([item.id for item in items], ["approval-1"])
        self.assertIsNone(next_cursor)

    def test_query_service_returns_summary_detail_history_and_audit_refs(self) -> None:
        self.repository.save_action_request(_action())
        self.repository.save_approval_request(_approval())
        self.repository.save_input(_input())
        self.repository.save_evaluation(_evaluation())
        decision = _decision(status=ApprovalDecisionStatus.REJECTED)
        self.repository.save_decision(decision)
        self.repository.link_decision_to_input("input-1", decision.approval_id)
        self.repository.save_audit_record(
            ApprovalAuditRecord(
                record_id="audit-1",
                approval_id="approval-1",
                action="decision.rejected",
                resource_id="approval-1",
                reason_summary="rejected",
                before_status="pending",
                after_status="completed",
                channel="web",
                record_refs={"input_id": "input-1"},
                created_at="2026-06-04T00:00:01+00:00",
            )
        )
        self.session.commit()
        service = ApprovalQueryService(self.repository)

        page = service.list_approvals(ApprovalListQuery(status="pending", limit=10))
        detail = service.get_detail("approval-1")

        self.assertEqual([item.id for item in page.items], ["approval-1"])
        self.assertEqual(page.items[0].latest_decision_summary.status, "rejected")
        self.assertEqual(page.items[0].allowed_actions, ("approve", "reject", "request-reanalysis"))
        self.assertEqual(detail.summary.id, "approval-1")
        self.assertEqual(detail.action_request_summary["id"], "action-1")
        self.assertIsNotNone(detail.summary.created_at)
        self.assertIsNotNone(detail.summary.updated_at)
        self.assertEqual(len(detail.inputs), 1)
        self.assertEqual(len(detail.evaluations), 1)
        self.assertEqual(len(detail.decisions), 1)
        self.assertEqual(detail.audit_refs[0]["record_id"], "audit-1")

    def test_query_service_counts_pending_and_expiring_approvals(self) -> None:
        self.repository.save_action_request(_action(action_id="action-1"))
        self.repository.save_approval_request(
            _approval(
                approval_id="approval-1",
                action_id="action-1",
                proposed_payload={"summary": "one"},
            )
        )
        self.repository.save_action_request(_action(action_id="action-2"))
        self.repository.save_approval_request(
            ApprovalRequest(
                id="approval-2",
                action_request_id="action-2",
                target_type="strategy",
                target_id="strategy-2",
                action_type="adjust_strategy",
                action_side="increase_risk",
                risk_level="medium",
                urgency="normal",
                summary="expiring soon",
                proposed_payload={"summary": "two"},
                required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
                expires_at="2026-06-04T12:00:00+00:00",
                expiration_action=ExpirationAction.EXPIRE_REJECT,
                policy_source="unit_test",
                allowed_channels=("web",),
            )
        )
        self.session.commit()

        service = ApprovalQueryService(self.repository)

        self.assertEqual(service.count_approvals(status="pending").total, 2)
        self.assertEqual(
            service.count_approvals(
                status="pending",
                expires_before=datetime.fromisoformat("2026-06-04T18:00:00+00:00"),
            ).total,
            1,
        )

    def test_query_detail_uses_redacted_payload_summaries(self) -> None:
        self.repository.save_action_request(
            _action(
                proposed_payload={
                    "summary": "safe summary",
                    "prompt": "full private prompt",
                    "broker_credential": {"token": "broker-token"},
                },
                strategy_policy={"private_policy": "strategy secret"},
                user_policy={"api_key": "user-api-key"},
                ai_policy_hint={"secret": "hint secret"},
            )
        )
        self.repository.save_approval_request(_approval(proposed_payload={"token": "approval-token"}))
        self.repository.save_input(
            _input(
                structured_payload={
                    "intent": "approve",
                    "request_id": "req-1",
                    "secret": "input secret",
                }
            )
        )
        self.repository.save_evaluation(_evaluation(extracted_changes={"token": "eval-token"}))
        decision = _decision(status=ApprovalDecisionStatus.REJECTED)
        self.repository.save_decision(decision)
        self.repository.link_decision_to_input("input-1", decision.approval_id)
        self.repository.save_audit_record(
            ApprovalAuditRecord(
                record_id="audit-sensitive",
                approval_id="approval-1",
                action="decision.rejected",
                resource_id="approval-1",
                reason_summary="rejected",
                before_status="pending",
                after_status="completed",
                channel="web",
                record_refs={"input_id": "input-1", "token": "audit-token"},
                payload_summary={"secret": "audit secret"},
                created_at="2026-06-04T00:00:01+00:00",
            )
        )
        self.session.commit()

        detail = ApprovalQueryService(self.repository).get_detail("approval-1")
        rendered = str(detail)

        self.assertEqual(detail.action_request_summary["proposed_payload_summary"]["summary"], "safe summary")
        self.assertNotIn("full private prompt", rendered)
        self.assertNotIn("broker-token", rendered)
        self.assertNotIn("strategy secret", rendered)
        self.assertNotIn("user-api-key", rendered)
        self.assertNotIn("approval-token", rendered)
        self.assertNotIn("input secret", rendered)
        self.assertNotIn("eval-token", rendered)
        self.assertNotIn("audit-token", rendered)
        self.assertNotIn("audit secret", rendered)


def _action(
    *,
    action_id: str = "action-1",
    proposed_payload: dict[str, object] | None = None,
    strategy_policy: dict[str, object] | None = None,
    user_policy: dict[str, object] | None = None,
    ai_policy_hint: dict[str, object] | None = None,
) -> ActionRequest:
    return ActionRequest(
        id=action_id,
        action_type="adjust_strategy",
        action_side="increase_risk",
        target_type="strategy",
        target_id="strategy-1",
        confidence_score=0.8,
        risk_flags=("high_risk",),
        proposed_payload=proposed_payload or {"summary": "masked"},
        strategy_policy=strategy_policy or {},
        user_policy=user_policy or {},
        ai_policy_hint=ai_policy_hint or {},
    )


def _approval(
    *,
    approval_id: str = "approval-1",
    action_id: str = "action-1",
    risk_level: str = "high",
    proposed_payload: dict[str, object] | None = None,
) -> ApprovalRequest:
    return ApprovalRequest(
        id=approval_id,
        action_request_id=action_id,
        target_type="strategy",
        target_id="strategy-1",
        action_type="adjust_strategy",
        action_side="increase_risk",
        risk_level=risk_level,
        urgency="normal",
        summary="adjust_strategy increase_risk for strategy:strategy-1",
        proposed_payload=proposed_payload or {"summary": "masked"},
        required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
        expires_at=None,
        expiration_action=ExpirationAction.EXPIRE_REJECT,
        policy_source="unit_test",
        allowed_channels=("web",),
    )


def _input(
    *,
    raw_text: str = "looks good",
    input_id: str = "input-1",
    approval_id: str = "approval-1",
    structured_payload: dict[str, object] | None = None,
) -> ApprovalInput:
    return ApprovalInput(
        id=input_id,
        approval_id=approval_id,
        channel="web",
        actor_ref="user:test",
        raw_text=raw_text,
        structured_payload=structured_payload or {"intent": "approve"},
        received_at="2026-06-04T00:00:00+00:00",
    )


def _evaluation(
    *,
    approval_id: str = "approval-1",
    input_id: str = "input-1",
    extracted_changes: dict[str, object] | None = None,
) -> ApprovalEvaluation:
    return ApprovalEvaluation(
        approval_id=approval_id,
        input_id=input_id,
        evaluator_type="rule",
        interpreted_intent=ApprovalIntent.APPROVE,
        confidence=1.0,
        extracted_changes=extracted_changes or {"intent": "approve"},
        requires_stronger_confirmation=False,
        reason_summary="Approved by structured intent.",
    )


def _decision(
    *,
    status: ApprovalDecisionStatus,
    reason_summary: str = "decision recorded",
    approval_id: str = "approval-1",
    action_id: str = "action-1",
    request_id: str | None = None,
) -> ApprovalDecision:
    return ApprovalDecision(
        approval_id=approval_id,
        action_request_id=action_id,
        status=status,
        intent=ApprovalIntent.APPROVE,
        policy_gate_status=PolicyGateStatus.NOT_REQUIRED,
        execution_status=ExecutionStatus.NOT_REQUESTED,
        reason_summary=reason_summary,
        correlation_id="corr-1",
        request_id=request_id,
    )


if __name__ == "__main__":
    unittest.main()
