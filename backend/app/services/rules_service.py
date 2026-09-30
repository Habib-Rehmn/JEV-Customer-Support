"""Deterministic business rules: Jev recommends, these rules decide what is permitted.

Pure functions over the Jev decision and the ContextBuilder context, so every rule is unit-testable.
"""
from dataclasses import dataclass, field

from app.core.config import settings
from app.models.enums import SupportAction, TicketStatus
from app.schemas.jev import JevDecision

ORDER_ACTIONS = {SupportAction.REFUND, SupportAction.REPLACEMENT}


@dataclass(frozen=True)
class RulesPolicy:
    min_confidence: float = settings.rule_min_confidence
    refund_approval_limit: float = settings.rule_refund_approval_limit
    max_refunds_30_days: int = settings.rule_max_refunds_30_days
    replacement_window_days: int = settings.rule_replacement_window_days
    auto_replacement_limit: float = settings.rule_auto_replacement_limit
    signal_threshold: float = settings.rule_signal_threshold


@dataclass
class RuleOutcome:
    recommended_action: SupportAction
    permitted_action: SupportAction
    status: TicketStatus
    requires_approval: bool
    hits: list[dict] = field(default_factory=list)

    @property
    def escalated(self) -> bool:
        return self.status == TicketStatus.ESCALATED


def evaluate(decision: JevDecision, context: dict, policy: RulesPolicy = RulesPolicy()) -> RuleOutcome:
    action = decision.action
    order = context.get("order") or {}
    customer = context.get("customer") or {}
    hits: list[dict] = []

    def escalate(rule: str, reason: str) -> RuleOutcome:
        hits.append({"rule": rule, "reason": reason})
        return RuleOutcome(action, SupportAction.HUMAN_ESCALATION, TicketStatus.ESCALATED, True, hits)

    def permit(requires_approval: bool, rule: str | None = None, reason: str | None = None) -> RuleOutcome:
        if rule:
            hits.append({"rule": rule, "reason": reason})
        return RuleOutcome(action, action, TicketStatus.WAITING_FOR_AGENT, requires_approval, hits)

    # 1. Jev itself is unsure.
    if action == SupportAction.HUMAN_ESCALATION:
        return escalate("jev_recommended_escalation", "Jev recommended human escalation")
    if decision.confidence < policy.min_confidence:
        return escalate("low_confidence", f"Jev confidence {decision.confidence:.2f} < {policy.min_confidence:.2f}")
    if decision.probabilities[action] < policy.min_confidence:
        return escalate(
            "low_probability",
            f"{action} probability {decision.probabilities[action]:.2f} < {policy.min_confidence:.2f}",
        )

    # 2. Billing disputes always go to a person.
    if (decision.billing_dispute or 0) >= policy.signal_threshold:
        return escalate("billing_dispute", f"billing dispute signal {decision.billing_dispute:.2f}")

    # 3. Refunds and replacements need a real order owned by this customer.
    if action in ORDER_ACTIONS and not order.get("found"):
        return escalate("unknown_order", "no matching order for this customer")

    # 4. Repeated refunds are an abuse signal.
    refunds_30 = customer.get("refunds_last_30_days") or 0
    if action in ORDER_ACTIONS and refunds_30 >= policy.max_refunds_30_days:
        return escalate("repeated_refunds", f"{refunds_30} refunds in the last 30 days")

    amount = order.get("amount") or 0

    if action == SupportAction.REFUND:
        if amount > policy.refund_approval_limit:
            return permit(True, "large_refund", f"refund ${amount:.2f} > ${policy.refund_approval_limit:.2f}")
        return permit(True)  # every refund is money out: agent approves explicitly

    if action == SupportAction.REPLACEMENT:
        days = order.get("days_since_delivery")
        if days is None:
            return escalate("not_delivered", "replacement requested for an order that has not been delivered")
        if days > policy.replacement_window_days:
            return escalate(
                "replacement_window",
                f"delivered {days} days ago (> {policy.replacement_window_days}-day window)",
            )
        damaged = (decision.item_damaged or 0) >= policy.signal_threshold
        if damaged and amount < policy.auto_replacement_limit:
            return permit(False, "damaged_low_value_replacement", f"damaged item under ${policy.auto_replacement_limit:.2f}")
        return permit(True)

    # technical_support and billing (non-dispute) are informational; the agent still reviews the reply.
    return permit(False)
