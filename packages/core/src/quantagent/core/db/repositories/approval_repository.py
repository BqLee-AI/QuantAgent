from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Select, and_, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.approval.models import (
    ActionRequest,
    ApprovalAuditRecord,
    ApprovalDecision,
    ApprovalEvaluation,
    ApprovalInput,
    ApprovalRequest,
)
from quantagent.core.db.models.approval import (
    ApprovalActionRequestORM,
    ApprovalAuditRecordORM,
    ApprovalDecisionORM,
    ApprovalEvaluationORM,
    ApprovalInputORM,
    ApprovalRequestORM,
)
from quantagent.plugin_sdk.io import JsonObject

DEFAULT_APPROVAL_LIST_LIMIT = 50
MAX_APPROVAL_LIST_LIMIT = 200
_MASKED = "[masked]"
_SENSITIVE_KEYWORDS = (
    "account",
    "api_key",
    "authorization",
    "broker_credential",
    "credential",
    "password",
    "private_policy",
    "prompt",
    "secret",
    "token",
)


class SQLAlchemyApprovalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_action_request(self, action: ActionRequest) -> None:
        existing = self._session.get(ApprovalActionRequestORM, action.id)
        if existing is None:
            self._session.add(_action_to_orm(action))
        else:
            _apply_action(existing, action)
        self._session.flush()

    def get_action_request(self, action_request_id: str) -> ActionRequest | None:
        row = self._session.get(ApprovalActionRequestORM, action_request_id)
        return _action_from_orm(row) if row is not None else None

    def save_approval_request(self, approval: ApprovalRequest) -> None:
        existing = self._session.get(ApprovalRequestORM, approval.id)
        if existing is None:
            self._session.add(_approval_to_orm(approval))
        else:
            _apply_approval(existing, approval)
        self._session.flush()

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None:
        row = self._session.get(ApprovalRequestORM, approval_id)
        return _approval_from_orm(row) if row is not None else None

    def get_approval_request_for_update(self, approval_id: str) -> ApprovalRequest | None:
        statement: Select[tuple[ApprovalRequestORM]] = (
            select(ApprovalRequestORM)
            .where(ApprovalRequestORM.approval_id == approval_id)
            .with_for_update()
            .limit(1)
        )
        row = self._session.scalars(statement).first()
        return _approval_from_orm(row) if row is not None else None

    def get_approval_request_by_action_id(self, action_request_id: str) -> ApprovalRequest | None:
        statement = select(ApprovalRequestORM).where(ApprovalRequestORM.action_request_id == action_request_id).limit(1)
        row = self._session.scalars(statement).first()
        return _approval_from_orm(row) if row is not None else None

    def save_input(self, user_input: ApprovalInput) -> ApprovalInput:
        existing = self.get_input(user_input.id, approval_id=user_input.approval_id)
        if existing is not None:
            return existing
        row = ApprovalInputORM(
            record_id=_record_id("approval_input"),
            approval_id=user_input.approval_id,
            input_id=user_input.id,
            channel=user_input.channel,
            actor_ref=user_input.actor_ref,
            raw_text_summary=_summarize_text(user_input.raw_text),
            structured_payload_summary=_redact_json_mapping(user_input.structured_payload),
            received_at=_parse_datetime(user_input.received_at),
            created_at=_utcnow(),
        )
        try:
            # 幂等：同 approval/input_id 唯一，重复提交复用首个输入，不重复触发后续评估。
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
            return user_input
        except IntegrityError:
            existing = self.get_input(user_input.id, approval_id=user_input.approval_id)
            if existing is None:
                raise
            return existing

    def get_input(self, input_id: str, *, approval_id: str | None = None) -> ApprovalInput | None:
        statement = select(ApprovalInputORM).where(ApprovalInputORM.input_id == input_id)
        if approval_id is not None:
            statement = statement.where(ApprovalInputORM.approval_id == approval_id)
        statement = statement.order_by(ApprovalInputORM.created_at.asc(), ApprovalInputORM.record_id.asc()).limit(1)
        row = self._session.scalars(statement).first()
        return _input_from_orm(row) if row is not None else None

    def list_inputs(self, approval_id: str) -> tuple[ApprovalInput, ...]:
        statement = (
            select(ApprovalInputORM)
            .where(ApprovalInputORM.approval_id == approval_id)
            .order_by(ApprovalInputORM.created_at.asc(), ApprovalInputORM.record_id.asc())
            .limit(MAX_APPROVAL_LIST_LIMIT)
        )
        return tuple(_input_from_orm(row) for row in self._session.scalars(statement).all())

    def save_evaluation(self, evaluation: ApprovalEvaluation) -> None:
        if self.get_evaluation_by_input_id(evaluation.input_id, approval_id=evaluation.approval_id) is not None:
            return
        row = ApprovalEvaluationORM(
            record_id=_record_id("approval_eval"),
            approval_id=evaluation.approval_id,
            input_id=evaluation.input_id,
            evaluator_type=evaluation.evaluator_type,
            interpreted_intent=evaluation.interpreted_intent.value,
            confidence=evaluation.confidence,
            extracted_changes_summary=_redact_json_mapping(evaluation.extracted_changes),
            requires_stronger_confirmation=evaluation.requires_stronger_confirmation,
            reason_summary=evaluation.reason_summary,
            created_at=_utcnow(),
        )
        try:
            # 幂等：并发重复评估以唯一约束兜底，冲突时复用已落库记录。
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError:
            existing = self.get_evaluation_by_input_id(evaluation.input_id, approval_id=evaluation.approval_id)
            if existing is None:
                raise

    def get_evaluation_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalEvaluation | None:
        statement = select(ApprovalEvaluationORM).where(ApprovalEvaluationORM.input_id == input_id)
        if approval_id is not None:
            statement = statement.where(ApprovalEvaluationORM.approval_id == approval_id)
        statement = statement.order_by(ApprovalEvaluationORM.created_at.asc(), ApprovalEvaluationORM.record_id.asc()).limit(1)
        row = self._session.scalars(statement).first()
        return _evaluation_from_orm(row) if row is not None else None

    def list_evaluations(self, approval_id: str) -> tuple[ApprovalEvaluation, ...]:
        statement = (
            select(ApprovalEvaluationORM)
            .where(ApprovalEvaluationORM.approval_id == approval_id)
            .order_by(ApprovalEvaluationORM.created_at.asc(), ApprovalEvaluationORM.record_id.asc())
            .limit(MAX_APPROVAL_LIST_LIMIT)
        )
        return tuple(_evaluation_from_orm(row) for row in self._session.scalars(statement).all())

    def save_decision(self, decision: ApprovalDecision) -> None:
        row = _decision_to_orm(decision)
        self._session.add(row)
        approval_row = self._session.get(ApprovalRequestORM, decision.approval_id)
        if approval_row is not None:
            approval_row.latest_decision_record_id = row.record_id
        self._session.flush()

    def link_decision_to_input(self, input_id: str, approval_id: str) -> None:
        row = self._latest_decision_row(approval_id)
        if row is None:
            return
        if row.input_id is None:
            row.input_id = input_id
        self._session.flush()

    def get_decision_by_input_id(self, input_id: str, *, approval_id: str | None = None) -> ApprovalDecision | None:
        statement = select(ApprovalDecisionORM).where(ApprovalDecisionORM.input_id == input_id)
        if approval_id is not None:
            statement = statement.where(ApprovalDecisionORM.approval_id == approval_id)
        statement = statement.order_by(ApprovalDecisionORM.created_at.asc(), ApprovalDecisionORM.record_id.asc()).limit(1)
        row = self._session.scalars(statement).first()
        return _decision_from_orm(row) if row is not None else None

    def latest_decision(self, approval_id: str) -> ApprovalDecision | None:
        row = self._latest_decision_row(approval_id)
        return _decision_from_orm(row) if row is not None else None

    def list_latest_decisions(self, approval_ids: tuple[str, ...]) -> dict[str, ApprovalDecision]:
        if not approval_ids:
            return {}
        approval_rows = self._session.scalars(
            select(ApprovalRequestORM).where(ApprovalRequestORM.approval_id.in_(approval_ids))
        ).all()
        latest_record_by_approval = {
            row.approval_id: row.latest_decision_record_id
            for row in approval_rows
            if row.latest_decision_record_id
        }
        if not latest_record_by_approval:
            return {}
        decision_rows = self._session.scalars(
            select(ApprovalDecisionORM).where(
                ApprovalDecisionORM.record_id.in_(latest_record_by_approval.values())
            )
        ).all()
        decisions_by_record_id = {row.record_id: _decision_from_orm(row) for row in decision_rows}
        return {
            approval_id: decisions_by_record_id[record_id]
            for approval_id, record_id in latest_record_by_approval.items()
            if record_id in decisions_by_record_id
        }

    def list_decisions(self, approval_id: str) -> tuple[ApprovalDecision, ...]:
        statement = (
            select(ApprovalDecisionORM)
            .where(ApprovalDecisionORM.approval_id == approval_id)
            .order_by(ApprovalDecisionORM.created_at.asc(), ApprovalDecisionORM.record_id.asc())
            .limit(MAX_APPROVAL_LIST_LIMIT)
        )
        return tuple(_decision_from_orm(row) for row in self._session.scalars(statement).all())

    def save_audit_record(self, record: ApprovalAuditRecord) -> None:
        self._session.add(_audit_to_orm(record))
        self._session.flush()

    def list_audit_records(self, approval_id: str) -> tuple[ApprovalAuditRecord, ...]:
        statement = (
            select(ApprovalAuditRecordORM)
            .where(ApprovalAuditRecordORM.approval_id == approval_id)
            .order_by(ApprovalAuditRecordORM.created_at.asc(), ApprovalAuditRecordORM.record_id.asc())
            .limit(MAX_APPROVAL_LIST_LIMIT)
        )
        return tuple(_audit_from_orm(row) for row in self._session.scalars(statement).all())

    def list_approval_requests(
        self,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        required_confirmation_level: str | None = None,
        expires_before: datetime | None = None,
        cursor: dict[str, str] | None = None,
        sort: str = "-updated_at",
        limit: int = DEFAULT_APPROVAL_LIST_LIMIT,
    ) -> tuple[list[ApprovalRequest], dict[str, str] | None]:
        bounded_limit = _bounded_limit(limit)
        statement: Select[tuple[ApprovalRequestORM]] = select(ApprovalRequestORM)
        if status is not None:
            statement = statement.where(ApprovalRequestORM.status == status)
        if risk_level is not None:
            statement = statement.where(ApprovalRequestORM.risk_level == risk_level)
        if required_confirmation_level is not None:
            statement = statement.where(ApprovalRequestORM.required_confirmation_level == required_confirmation_level)
        if expires_before is not None:
            statement = statement.where(ApprovalRequestORM.expires_at.is_not(None)).where(ApprovalRequestORM.expires_at <= expires_before)

        if sort == "created_at":
            order_column = ApprovalRequestORM.created_at
            descending = False
        elif sort == "-created_at":
            order_column = ApprovalRequestORM.created_at
            descending = True
        elif sort == "updated_at":
            order_column = ApprovalRequestORM.updated_at
            descending = False
        else:
            order_column = ApprovalRequestORM.updated_at
            descending = True

        if cursor is not None:
            cursor_at, cursor_id = _parse_cursor(cursor)
            if descending:
                statement = statement.where(
                    or_(
                        order_column < cursor_at,
                        and_(order_column == cursor_at, ApprovalRequestORM.approval_id < cursor_id),
                    )
                )
            else:
                statement = statement.where(
                    or_(
                        order_column > cursor_at,
                        and_(order_column == cursor_at, ApprovalRequestORM.approval_id > cursor_id),
                    )
                )

        order_by = (desc(order_column), desc(ApprovalRequestORM.approval_id)) if descending else (order_column.asc(), ApprovalRequestORM.approval_id.asc())
        rows = list(self._session.scalars(statement.order_by(*order_by).limit(bounded_limit + 1)).all())
        next_cursor = None
        if len(rows) > bounded_limit:
            last = rows[bounded_limit - 1]
            value = getattr(last, order_column.key)
            next_cursor = {"at": _isoformat_utc(value), "approval_id": last.approval_id}
            rows = rows[:bounded_limit]
        return [_approval_from_orm(row) for row in rows], next_cursor

    def count_approval_requests(
        self,
        *,
        status: str | None = None,
        risk_level: str | None = None,
        required_confirmation_level: str | None = None,
        expires_before: datetime | None = None,
    ) -> int:
        statement = select(func.count()).select_from(ApprovalRequestORM)
        if status is not None:
            statement = statement.where(ApprovalRequestORM.status == status)
        if risk_level is not None:
            statement = statement.where(ApprovalRequestORM.risk_level == risk_level)
        if required_confirmation_level is not None:
            statement = statement.where(ApprovalRequestORM.required_confirmation_level == required_confirmation_level)
        if expires_before is not None:
            statement = statement.where(ApprovalRequestORM.expires_at.is_not(None)).where(
                ApprovalRequestORM.expires_at <= expires_before
            )
        return int(self._session.execute(statement).scalar_one())

    def _latest_decision_row(self, approval_id: str) -> ApprovalDecisionORM | None:
        approval_row = self._session.get(ApprovalRequestORM, approval_id)
        if approval_row is not None and approval_row.latest_decision_record_id:
            latest = self._session.get(ApprovalDecisionORM, approval_row.latest_decision_record_id)
            if latest is not None:
                return latest
        statement = (
            select(ApprovalDecisionORM)
            .where(ApprovalDecisionORM.approval_id == approval_id)
            .order_by(ApprovalDecisionORM.created_at.desc(), ApprovalDecisionORM.record_id.desc())
            .limit(1)
        )
        return self._session.scalars(statement).first()


def _action_to_orm(action: ActionRequest) -> ApprovalActionRequestORM:
    row = ApprovalActionRequestORM(action_request_id=action.id, created_at=_utcnow())
    _apply_action(row, action)
    return row


def _apply_action(row: ApprovalActionRequestORM, action: ActionRequest) -> None:
    row.action_type = action.action_type
    row.action_side = action.action_side
    row.target_type = action.target_type
    row.target_id = action.target_id
    row.instrument = action.instrument
    row.market = action.market
    row.amount = action.amount
    row.leverage = action.leverage
    row.confidence_score = action.confidence_score
    row.risk_flags = list(action.risk_flags)
    row.urgency = action.urgency
    # 安全边界：这些字段只作为查询摘要持久化，不能保存完整 prompt、私有策略或凭证类 payload。
    row.proposed_payload_summary = _redact_json_mapping(action.proposed_payload)
    row.strategy_policy_summary = _redact_json_mapping(action.strategy_policy)
    row.user_policy_summary = _redact_json_mapping(action.user_policy)
    row.ai_policy_hint_summary = _redact_json_mapping(action.ai_policy_hint)
    row.correlation_id = action.correlation_id


def _action_from_orm(row: ApprovalActionRequestORM) -> ActionRequest:
    return ActionRequest(
        id=row.action_request_id,
        action_type=row.action_type,
        action_side=row.action_side,
        target_type=row.target_type,
        target_id=row.target_id,
        instrument=row.instrument,
        market=row.market,
        amount=row.amount,
        leverage=row.leverage,
        confidence_score=row.confidence_score,
        risk_flags=tuple(row.risk_flags or ()),
        urgency=row.urgency,
        proposed_payload=row.proposed_payload_summary or {},
        strategy_policy=row.strategy_policy_summary or {},
        user_policy=row.user_policy_summary or {},
        ai_policy_hint=row.ai_policy_hint_summary or {},
        correlation_id=row.correlation_id,
    )


def _approval_to_orm(approval: ApprovalRequest) -> ApprovalRequestORM:
    row = ApprovalRequestORM(approval_id=approval.id, action_request_id=approval.action_request_id)
    _apply_approval(row, approval)
    row.created_at = _utcnow()
    return row


def _apply_approval(row: ApprovalRequestORM, approval: ApprovalRequest) -> None:
    now = _utcnow()
    row.action_request_id = approval.action_request_id
    row.target_type = approval.target_type
    row.target_id = approval.target_id
    row.action_type = approval.action_type
    row.action_side = approval.action_side
    row.risk_level = approval.risk_level
    row.urgency = approval.urgency
    row.summary = approval.summary
    row.proposed_payload_summary = _redact_json_mapping(approval.proposed_payload)
    row.required_confirmation_level = approval.required_confirmation_level.value
    row.expires_at = _parse_optional_datetime(approval.expires_at)
    row.expiration_action = approval.expiration_action.value
    row.policy_source = approval.policy_source
    row.status = approval.status.value
    row.allowed_channels = list(approval.allowed_channels)
    row.updated_at = now
    row.version = (row.version or 0) + 1
    if approval.status.value in {"completed", "expired", "escalated", "blocked"} and row.finalized_at is None:
        row.finalized_at = now


def _approval_from_orm(row: ApprovalRequestORM) -> ApprovalRequest:
    return ApprovalRequest(
        id=row.approval_id,
        action_request_id=row.action_request_id,
        target_type=row.target_type,
        target_id=row.target_id,
        action_type=row.action_type,
        action_side=row.action_side,
        risk_level=row.risk_level,
        urgency=row.urgency,
        summary=row.summary,
        proposed_payload=row.proposed_payload_summary or {},
        required_confirmation_level=row.required_confirmation_level,
        expires_at=_isoformat_utc(row.expires_at) if row.expires_at else None,
        expiration_action=row.expiration_action,
        policy_source=row.policy_source,
        status=row.status,
        allowed_channels=tuple(row.allowed_channels or ()),
        created_at=_isoformat_utc(row.created_at),
        updated_at=_isoformat_utc(row.updated_at),
    )


def _input_from_orm(row: ApprovalInputORM) -> ApprovalInput:
    return ApprovalInput(
        id=row.input_id,
        approval_id=row.approval_id,
        channel=row.channel,
        actor_ref=row.actor_ref,
        raw_text=row.raw_text_summary,
        structured_payload=row.structured_payload_summary or {},
        received_at=_isoformat_utc(row.received_at),
    )


def _evaluation_from_orm(row: ApprovalEvaluationORM) -> ApprovalEvaluation:
    return ApprovalEvaluation(
        approval_id=row.approval_id,
        input_id=row.input_id,
        evaluator_type=row.evaluator_type,
        interpreted_intent=row.interpreted_intent,
        confidence=row.confidence,
        extracted_changes=row.extracted_changes_summary or {},
        requires_stronger_confirmation=row.requires_stronger_confirmation,
        reason_summary=row.reason_summary,
    )


def _decision_to_orm(decision: ApprovalDecision) -> ApprovalDecisionORM:
    return ApprovalDecisionORM(
        record_id=_record_id("approval_decision"),
        approval_id=decision.approval_id,
        action_request_id=decision.action_request_id,
        input_id=None,
        status=decision.status.value,
        intent=decision.intent.value if decision.intent else None,
        policy_gate_status=decision.policy_gate_status.value,
        execution_status=decision.execution_status.value,
        reason_summary=decision.reason_summary,
        correlation_id=decision.correlation_id,
        request_id=decision.request_id,
        created_at=_utcnow(),
    )


def _decision_from_orm(row: ApprovalDecisionORM) -> ApprovalDecision:
    return ApprovalDecision(
        approval_id=row.approval_id,
        action_request_id=row.action_request_id,
        status=row.status,
        intent=row.intent,
        policy_gate_status=row.policy_gate_status,
        execution_status=row.execution_status,
        reason_summary=row.reason_summary,
        correlation_id=row.correlation_id,
        request_id=row.request_id,
    )


def _audit_to_orm(record: ApprovalAuditRecord) -> ApprovalAuditRecordORM:
    return ApprovalAuditRecordORM(
        record_id=record.record_id,
        approval_id=record.approval_id,
        actor_id=record.actor_id,
        actor_type=record.actor_type,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        before_status=record.before_status.value if record.before_status else None,
        after_status=record.after_status.value if record.after_status else None,
        request_id=record.request_id,
        channel=record.channel,
        reason_summary=record.reason_summary,
        record_refs=_redact_json_mapping(record.record_refs),
        payload_summary=_redact_json_mapping(record.payload_summary),
        created_at=_parse_datetime(record.created_at),
    )


def _audit_from_orm(row: ApprovalAuditRecordORM) -> ApprovalAuditRecord:
    return ApprovalAuditRecord(
        record_id=row.record_id,
        approval_id=row.approval_id,
        actor_id=row.actor_id,
        actor_type=row.actor_type,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        before_status=row.before_status,
        after_status=row.after_status,
        request_id=row.request_id,
        channel=row.channel,
        reason_summary=row.reason_summary,
        record_refs=row.record_refs or {},
        payload_summary=row.payload_summary or {},
        created_at=_isoformat_utc(row.created_at),
    )


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_APPROVAL_LIST_LIMIT)


def _parse_cursor(cursor: dict[str, str]) -> tuple[datetime, str]:
    if not isinstance(cursor, dict):
        raise ValueError("approval cursor must be an object")
    try:
        at = datetime.fromisoformat(cursor["at"])
        approval_id = cursor["approval_id"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("approval cursor is invalid") from exc
    if not approval_id:
        raise ValueError("approval cursor missing approval_id")
    return at, approval_id


def _record_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _parse_optional_datetime(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    return datetime.fromisoformat(raw)


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _summarize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) <= 500:
        return normalized
    return f"{normalized[:497]}..."


def _redact_json_mapping(payload: JsonObject) -> JsonObject:
    value = _redact_json_value(payload)
    return value if isinstance(value, dict) else {}


def _redact_json_value(value: object, *, key: str | None = None) -> object:
    if key is not None and _is_sensitive_key(key):
        return _MASKED
    if isinstance(value, Mapping):
        return {str(item_key): _redact_json_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)
