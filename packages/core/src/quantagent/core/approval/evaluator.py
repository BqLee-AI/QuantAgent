from __future__ import annotations

import re
from dataclasses import dataclass

from quantagent.core.approval.models import (
    ApprovalEvaluation,
    ApprovalInput,
    ApprovalIntent,
    ApprovalRequest,
    ConfirmationLevel,
    TEXT_CHANNELS,
    WEAK_CONFIRMATION_CHANNELS,
)


APPROVE_WORDS = frozenset({"approve", "approved", "yes", "confirm", "confirmed"})
REJECT_WORDS = frozenset({"reject", "rejected", "no", "deny", "denied", "cancel"})
REANALYSIS_WORDS = frozenset({"reanalyze", "reanalyse", "reanalysis", "重新分析", "重分析"})
APPROVAL_ID_PREFIX_PATTERN = re.compile(r"(?i)\bapproval[_ -]?id\s*[:=]\s*[A-Za-z0-9_.:-]+")


@dataclass(frozen=True)
class ApprovalRuleEvaluator:
    min_text_confidence: float = 0.8

    def evaluate(self, approval: ApprovalRequest, user_input: ApprovalInput) -> ApprovalEvaluation:
        structured_intent = user_input.structured_payload.get("intent")
        if isinstance(structured_intent, str) and structured_intent.strip():
            return self._from_structured_intent(approval, user_input, structured_intent)
        return self._from_raw_text(approval, user_input)

    def _from_structured_intent(
        self,
        approval: ApprovalRequest,
        user_input: ApprovalInput,
        intent_value: str,
    ) -> ApprovalEvaluation:
        try:
            intent = ApprovalIntent(intent_value.strip().lower())
        except ValueError:
            intent = ApprovalIntent.UNCLEAR
        requires_stronger = _requires_stronger_confirmation(approval, user_input, intent)
        if requires_stronger:
            intent = ApprovalIntent.ESCALATE
        return ApprovalEvaluation(
            approval_id=approval.id,
            input_id=user_input.id,
            evaluator_type="rule",
            interpreted_intent=intent,
            confidence=1.0 if intent != ApprovalIntent.UNCLEAR else 0.0,
            extracted_changes={},
            requires_stronger_confirmation=requires_stronger,
            reason_summary=_reason_for(intent, user_input.channel, requires_stronger),
        )

    def _from_raw_text(self, approval: ApprovalRequest, user_input: ApprovalInput) -> ApprovalEvaluation:
        # 安全边界：自然语言文本只做意图判断；高风险确认仍需结构化输入或更强通道。
        normalized = _normalize_approval_text(user_input.raw_text)
        if not normalized:
            intent = ApprovalIntent.UNCLEAR
            confidence = 0.0
        elif normalized in APPROVE_WORDS:
            intent = ApprovalIntent.APPROVE
            confidence = self.min_text_confidence
        elif normalized in REJECT_WORDS:
            intent = ApprovalIntent.REJECT
            confidence = 0.95
        elif normalized in REANALYSIS_WORDS:
            intent = ApprovalIntent.REQUEST_REANALYSIS
            confidence = 0.95
        else:
            intent = ApprovalIntent.UNCLEAR
            confidence = 0.2

        requires_stronger = (
            intent == ApprovalIntent.APPROVE
            and approval.required_confirmation_level
            in {ConfirmationLevel.STRONG_CONFIRM, ConfirmationLevel.LINK_CONFIRM, ConfirmationLevel.MANUAL_ONLY}
        ) or _requires_stronger_confirmation(approval, user_input, intent)
        if requires_stronger or (intent == ApprovalIntent.APPROVE and user_input.channel in TEXT_CHANNELS):
            intent = ApprovalIntent.ESCALATE
            requires_stronger = True

        return ApprovalEvaluation(
            approval_id=approval.id,
            input_id=user_input.id,
            evaluator_type="rule",
            interpreted_intent=intent,
            confidence=confidence,
            extracted_changes={},
            requires_stronger_confirmation=requires_stronger,
            reason_summary=_reason_for(intent, user_input.channel, requires_stronger),
        )


def _requires_stronger_confirmation(
    approval: ApprovalRequest,
    user_input: ApprovalInput,
    intent: ApprovalIntent,
) -> bool:
    if intent != ApprovalIntent.APPROVE:
        return False
    return (
        approval.required_confirmation_level == ConfirmationLevel.MANUAL_ONLY
        and user_input.channel in WEAK_CONFIRMATION_CHANNELS
    )


def _reason_for(intent: ApprovalIntent, channel: str, requires_stronger: bool) -> str:
    if requires_stronger:
        return f"{channel} input requires stronger confirmation before approval."
    return f"{channel} input interpreted as {intent.value}."


def _normalize_approval_text(raw_text: str | None) -> str:
    text = (raw_text or "").strip().lower()
    if not text:
        return ""
    # 协议适配：notification 回流文本会携带 approval_id 用于定位请求，意图判断只读取剩余命令词。
    without_approval_id = APPROVAL_ID_PREFIX_PATTERN.sub(" ", text)
    return " ".join(without_approval_id.split())
