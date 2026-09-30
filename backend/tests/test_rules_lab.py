from app.services.jev_service import JevUnavailable
from tests.conftest import jev_response
from tests.test_analysis import TICKET

# Seeded orders: ORD-1 is Ali's $89.99 order, delivered today.
CURRENT = {
    "min_confidence": 0.70,
    "refund_approval_limit": 500,
    "max_refunds_30_days": 3,
    "replacement_window_days": 30,
    "auto_replacement_limit": 100,
    "signal_threshold": 0.5,
}


async def new_ticket(client, fake_jev, response):
    fake_jev.response = response
    return (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]


async def simulate(client, admin_headers, **changes):
    res = await client.post("/api/v1/analytics/rules/simulate", json={**CURRENT, **changes}, headers=admin_headers)
    assert res.status_code == 200, res.text
    return res.json()


async def test_current_rules_endpoint(client):
    assert (await client.get("/api/v1/analytics/rules")).json() == CURRENT


async def test_unchanged_policy_changes_nothing(client, seeded, fake_jev, admin_headers):
    await new_ticket(client, fake_jev, jev_response("replacement", item_damaged=0.9))
    await new_ticket(client, fake_jev, jev_response("billing", billing_dispute=0.9))
    result = await simulate(client, admin_headers)
    assert result["replayed"] == 2
    assert result["changed"] == []
    assert result["current"] == result["proposed"] == {"escalated": 1, "needs_approval": 0, "pre_approved": 1}


async def test_raising_confidence_threshold_escalates_less_confident_tickets(client, seeded, fake_jev, admin_headers):
    sure = await new_ticket(client, fake_jev, jev_response("replacement", confidence=0.99, item_damaged=0.9))
    unsure = await new_ticket(client, fake_jev, jev_response("replacement", confidence=0.85, item_damaged=0.9))

    result = await simulate(client, admin_headers, min_confidence=0.9)
    assert [c["ticket_id"] for c in result["changed"]] == [unsure]
    change = result["changed"][0]
    assert change["current"] == {
        "outcome": "pre_approved", "permitted_action": "replacement", "rules": ["damaged_low_value_replacement"],
    }
    assert change["proposed"] == {"outcome": "escalated", "permitted_action": "human_escalation", "rules": ["low_confidence"]}
    assert result["proposed"] == {"escalated": 1, "needs_approval": 0, "pre_approved": 1}
    assert sure not in [c["ticket_id"] for c in result["changed"]]


async def test_lowering_auto_replacement_limit_requires_approval(client, seeded, fake_jev, admin_headers):
    await new_ticket(client, fake_jev, jev_response("replacement", item_damaged=0.9))  # $89.99
    result = await simulate(client, admin_headers, auto_replacement_limit=50)
    assert result["changed"][0]["proposed"]["outcome"] == "needs_approval"


async def test_simulation_uses_context_from_analysis_time(client, seeded, fake_jev, admin_headers):
    # The order context Jev saw is replayed, not recomputed: resolving other refunds later doesn't change it.
    ticket = await new_ticket(client, fake_jev, jev_response("refund"))
    for _ in range(3):
        extra = await new_ticket(client, fake_jev, jev_response("refund"))
        await client.post(f"/api/v1/tickets/{extra}/resolve", json={"final_action": "refund"})
    result = await simulate(client, admin_headers)
    assert ticket not in [c["ticket_id"] for c in result["changed"]]


async def test_tickets_without_a_decision_are_not_replayed(client, seeded, fake_jev, admin_headers):
    fake_jev.error = JevUnavailable("down")
    await client.post("/api/v1/tickets", json=TICKET)
    result = await simulate(client, admin_headers)
    assert result["replayed"] == 0 and result["skipped"] == 0


async def test_simulation_is_admin_only_and_validates(client, admin_headers):
    assert (await client.post("/api/v1/analytics/rules/simulate", json=CURRENT)).status_code == 403
    bad = {**CURRENT, "min_confidence": 1.5}
    assert (await client.post("/api/v1/analytics/rules/simulate", json=bad, headers=admin_headers)).status_code == 422


async def test_calibration_buckets(client, seeded, fake_jev):
    agree = await new_ticket(client, fake_jev, jev_response("replacement", confidence=0.97, item_damaged=0.9))
    await client.post(f"/api/v1/tickets/{agree}/approve", json={})
    disagree = await new_ticket(client, fake_jev, jev_response("replacement", confidence=0.96, item_damaged=0.9))
    await client.post(f"/api/v1/tickets/{disagree}/approve", json={"action": "refund"})
    await new_ticket(client, fake_jev, jev_response("technical_support", confidence=0.75))  # open
    await new_ticket(client, fake_jev, jev_response("technical_support", confidence=1.0))   # open, top edge

    body = (await client.get("/api/v1/analytics/calibration")).json()
    assert body["min_confidence"] == 0.7
    buckets = {b["label"]: b for b in body["buckets"]}
    assert buckets["0.95–1.00"] == {
        "label": "0.95–1.00", "min": 0.95, "max": 1.0, "decisions": 3, "closed_out": 2, "agreement_rate": 0.5,
    }
    assert buckets["0.70–0.80"]["decisions"] == 1
    assert buckets["0.70–0.80"]["agreement_rate"] is None
    assert sum(b["decisions"] for b in body["buckets"]) == 4
