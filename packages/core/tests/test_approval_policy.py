from __future__ import annotations

import unittest

from quantagent.core.approval import (
    ActionRequest,
    ApprovalMode,
    ApprovalPolicyResolver,
    ConfirmationLevel,
    ExpirationAction,
)


class ApprovalPolicyTestCase(unittest.TestCase):
    def test_resolver_covers_notify_only(self) -> None:
        policy = ApprovalPolicyResolver().resolve(_action(action_type="notify", action_side="neutral"))

        self.assertEqual(policy.mode, ApprovalMode.NO_APPROVAL_NOTIFY_ONLY)
        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.INFORMATIONAL)
        self.assertEqual(policy.expiration_action, ExpirationAction.EXPIRE_NOTIFY_ONLY)

    def test_resolver_covers_execute_then_notify(self) -> None:
        policy = ApprovalPolicyResolver().resolve(_action(action_type="reduce_position", action_side="reduce_risk", urgency="urgent"))

        self.assertEqual(policy.mode, ApprovalMode.EXECUTE_THEN_NOTIFY)
        self.assertEqual(policy.expiration_action, ExpirationAction.EXPIRE_APPROVE)

    def test_resolver_covers_approval_required(self) -> None:
        policy = ApprovalPolicyResolver().resolve(_action(action_type="adjust_strategy", action_side="increase_risk"))

        self.assertEqual(policy.mode, ApprovalMode.APPROVAL_REQUIRED)
        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.STRONG_CONFIRM)

    def test_resolver_covers_approval_with_timeout(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(action_type="execute_order", action_side="increase_risk", urgency="time_sensitive")
        )

        self.assertEqual(policy.mode, ApprovalMode.APPROVAL_WITH_TIMEOUT)
        self.assertEqual(policy.expiration_action, ExpirationAction.EXPIRE_REANALYSIS)
        self.assertIsNotNone(policy.expires_at)

    def test_resolver_covers_manual_only(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(action_type="execute_order", action_side="increase_risk", risk_flags=("manual_only",))
        )

        self.assertEqual(policy.mode, ApprovalMode.MANUAL_ONLY)
        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.MANUAL_ONLY)

    def test_resolver_covers_blocked(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(action_type="execute_order", action_side="increase_risk", risk_flags=("blocked",))
        )

        self.assertEqual(policy.mode, ApprovalMode.BLOCKED)

    def test_ai_hint_cannot_weaken_required_approval(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(
                action_type="execute_order",
                action_side="increase_risk",
                ai_policy_hint={"mode": "no_approval_notify_only"},
            )
        )

        self.assertEqual(policy.mode, ApprovalMode.APPROVAL_REQUIRED)
        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.LINK_CONFIRM)

    def test_user_policy_can_configure_expiration_action(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(
                action_type="execute_order",
                action_side="increase_risk",
                urgency="time_sensitive",
                user_policy={"expiration_action": "escalate", "mode": "approval_with_timeout"},
            )
        )

        self.assertEqual(policy.expiration_action, ExpirationAction.ESCALATE)

    def test_ai_hint_cannot_weaken_confirmation_or_expiration_baseline(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(
                action_type="execute_order",
                action_side="increase_risk",
                urgency="time_sensitive",
                ai_policy_hint={
                    "required_confirmation_level": "informational",
                    "expiration_action": "expire_approve",
                },
            )
        )

        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.LINK_CONFIRM)
        self.assertEqual(policy.expiration_action, ExpirationAction.EXPIRE_REANALYSIS)

    def test_policy_can_tighten_confirmation_and_expiration(self) -> None:
        policy = ApprovalPolicyResolver().resolve(
            _action(
                action_type="adjust_strategy",
                action_side="increase_risk",
                user_policy={
                    "required_confirmation_level": "manual_only",
                    "expiration_action": "escalate",
                },
            )
        )

        self.assertEqual(policy.required_confirmation_level, ConfirmationLevel.MANUAL_ONLY)
        self.assertEqual(policy.expiration_action, ExpirationAction.ESCALATE)


def _action(
    *,
    action_type: str,
    action_side: str,
    urgency: str = "normal",
    risk_flags: tuple[str, ...] = (),
    user_policy: dict[str, object] | None = None,
    ai_policy_hint: dict[str, object] | None = None,
) -> ActionRequest:
    return ActionRequest(
        id=f"act-{action_type}-{action_side}",
        action_type=action_type,
        action_side=action_side,
        target_type="portfolio",
        target_id="portfolio-1",
        risk_flags=risk_flags,
        urgency=urgency,
        user_policy=user_policy or {},
        ai_policy_hint=ai_policy_hint or {},
    )


if __name__ == "__main__":
    unittest.main()
