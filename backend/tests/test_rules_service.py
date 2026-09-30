from app.models.enums import SupportAction as A
from app.models.enums import TicketStatus as S
from app.services.jev_service import parse_response
from app.services.rules_service import RulesPolicy, evaluate
from tests.conftest import jev_response

POLICY = RulesPolicy(
    min_confidence=0.70,
    refund_approval_limit=500,
    max_refunds_30_days=3,
    replacement_window_days=30,
    auto_replacement_limit=100,
    signal_threshold=0.5,
)


def decision(action, **kw):
    return parse_response(jev_response(action, **kw))


def context(found=True, amount=89.99, days_since_delivery=4, refunds_30=0):
    return {
        "order": {"found": found, "amount": amount if found else None,
                  "days_since_delivery": days_since_delivery if found else None},
        "customer": {"refunds_last_30_days": refunds_30},
    }


def run(action, ctx=None, **kw):
    return evaluate(decision(action, **kw), ctx or context(), POLICY)


def rules(outcome):
    return [h["rule"] for h in outcome.hits]


def assert_escalated(outcome, rule):
    assert outcome.status == S.ESCALATED
    assert outcome.permitted_action == A.HUMAN_ESCALATION
    assert rules(outcome) == [rule]


# Jev confidence

def test_low_confidence_escalates():
    assert_escalated(run("replacement", confidence=0.69), "low_confidence")


def test_confidence_at_threshold_is_allowed():
    assert run("technical_support", confidence=0.70).status == S.WAITING_FOR_AGENT


def test_low_winning_probability_escalates():
    body = jev_response("refund")
    body["answers"]["support_action"]["probabilities"].update(refund=0.55, billing=0.45)
    outcome = evaluate(parse_response(body), context(), POLICY)
    assert_escalated(outcome, "low_probability")


def test_jev_escalation_is_respected():
    assert_escalated(run("human_escalation"), "jev_recommended_escalation")


def test_recommended_action_is_kept_when_escalating():
    assert run("refund", confidence=0.2).recommended_action == A.REFUND


# Billing

def test_billing_dispute_goes_to_human():
    assert_escalated(run("billing", billing_dispute=0.97), "billing_dispute")


def test_plain_billing_question_is_allowed():
    outcome = run("billing", billing_dispute=0.1)
    assert outcome.permitted_action == A.BILLING
    assert outcome.status == S.WAITING_FOR_AGENT
    assert outcome.requires_approval is False


# Orders

def test_unknown_order_escalates_refund():
    assert_escalated(run("refund", context(found=False)), "unknown_order")


def test_unknown_order_escalates_replacement():
    assert_escalated(run("replacement", context(found=False), item_damaged=0.9), "unknown_order")


def test_technical_support_does_not_need_an_order():
    assert run("technical_support", context(found=False)).permitted_action == A.TECHNICAL_SUPPORT


def test_three_refunds_in_30_days_escalates():
    assert_escalated(run("refund", context(refunds_30=3)), "repeated_refunds")


def test_two_refunds_in_30_days_is_allowed():
    assert run("refund", context(refunds_30=2)).permitted_action == A.REFUND


# Refunds

def test_large_refund_requires_human():
    outcome = run("refund", context(amount=649.00))
    assert outcome.permitted_action == A.REFUND
    assert outcome.status == S.WAITING_FOR_AGENT
    assert outcome.requires_approval is True
    assert rules(outcome) == ["large_refund"]


def test_small_refund_still_requires_approval():
    outcome = run("refund", context(amount=40))
    assert outcome.requires_approval is True
    assert outcome.hits == []


# Replacements

def test_damaged_item_below_100_replacement_allowed():
    outcome = run("replacement", item_damaged=0.92)
    assert outcome.permitted_action == A.REPLACEMENT
    assert outcome.requires_approval is False
    assert rules(outcome) == ["damaged_low_value_replacement"]


def test_damaged_expensive_item_replacement_needs_approval():
    outcome = run("replacement", context(amount=140), item_damaged=0.92)
    assert outcome.permitted_action == A.REPLACEMENT
    assert outcome.requires_approval is True


def test_undamaged_replacement_needs_approval():
    assert run("replacement", item_damaged=0.1).requires_approval is True


def test_replacement_within_30_days_allowed():
    assert run("replacement", context(days_since_delivery=30), item_damaged=0.9).status == S.WAITING_FOR_AGENT


def test_replacement_after_30_days_escalates():
    assert_escalated(run("replacement", context(days_since_delivery=31), item_damaged=0.9), "replacement_window")


def test_replacement_for_undelivered_order_escalates():
    assert_escalated(run("replacement", context(days_since_delivery=None), item_damaged=0.9), "not_delivered")


# Rule order: the first escalation reason wins

def test_low_confidence_wins_over_other_rules():
    assert_escalated(run("refund", context(found=False), confidence=0.3), "low_confidence")
