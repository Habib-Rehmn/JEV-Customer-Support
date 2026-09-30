from sqlalchemy import select

from app.models import AuditLog, Ticket
from app.services.jev_service import JevUnavailable
from tests.conftest import jev_response

TICKET = {
    "customer_name": "Ali Khan",
    "email": "ali@example.com",
    "order_number": "ORD-1",
    "subject": "Damaged product",
    "message": "My headphones arrived broken. Can you replace them?",
}


async def events(session_factory, ticket_id):
    async with session_factory() as session:
        rows = await session.scalars(select(AuditLog.event_type).where(AuditLog.ticket_id == ticket_id))
        return list(rows)


async def test_new_ticket_is_analyzed_automatically(client, seeded, session_factory):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["status"] == "WAITING_FOR_AGENT"
    decision = body["latest_jev_decision"]
    assert decision["selected_action"] == "replacement"
    assert decision["replacement_probability"] == 1
    assert decision["item_damaged_probability"] == 0.92
    # Damaged $89.99 item delivered today: replacement permitted without extra approval.
    assert decision["permitted_action"] == "replacement"
    assert decision["requires_approval"] is False
    assert await events(session_factory, ticket_id) == [
        "ticket_created", "jev_request_started", "jev_request_completed", "rule_triggered",
    ]


async def test_rules_escalate_billing_dispute(client, seeded, fake_jev, session_factory):
    fake_jev.response = jev_response("billing", billing_dispute=0.97)
    ticket_id = (await client.post("/api/v1/tickets", json={**TICKET, "subject": "Charged twice"})).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["status"] == "ESCALATED"
    assert body["priority"] == "HIGH"
    decision = body["latest_jev_decision"]
    assert decision["selected_action"] == "billing"
    assert decision["permitted_action"] == "human_escalation"
    assert decision["rule_hits"][0]["rule"] == "billing_dispute"
    assert (await events(session_factory, ticket_id))[-2:] == ["rule_triggered", "ticket_escalated"]


async def test_rules_escalate_refund_for_unknown_order(client, seeded, fake_jev):
    fake_jev.response = jev_response("refund")
    ticket_id = (await client.post("/api/v1/tickets", json={**TICKET, "order_number": "ORD-404"})).json()["id"]
    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["status"] == "ESCALATED"
    assert body["latest_jev_decision"]["rule_hits"][0]["rule"] == "unknown_order"


async def test_context_sent_to_jev(client, seeded, fake_jev):
    await client.post("/api/v1/tickets", json=TICKET)
    context = fake_jev.contexts[0]
    assert context["customer_message"]["body"] == TICKET["message"]
    assert context["order"] == {
        "found": True, "order_number": "ORD-1", "status": "delivered", "amount": 89.99,
        "age_days": 0, "days_since_delivery": 0,
    }
    assert context["customer"]["previous_tickets"] == 0


async def test_unknown_order_is_reported_in_context(client, seeded, fake_jev):
    await client.post("/api/v1/tickets", json={**TICKET, "order_number": "ORD-404"})
    assert fake_jev.contexts[0]["order"]["found"] is False


async def test_context_counts_previous_refunds(client, seeded, fake_jev):
    first = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.patch(f"/api/v1/tickets/{first}", json={"status": "RESOLVED", "final_action": "refund"})
    await client.post("/api/v1/tickets", json=TICKET)

    customer = fake_jev.contexts[1]["customer"]
    assert customer["previous_tickets"] == 1
    assert customer["previous_refunds"] == 1
    assert customer["refunds_last_30_days"] == 1


async def test_jev_failure_marks_ticket_and_keeps_it(client, seeded, fake_jev, session_factory):
    fake_jev.error = JevUnavailable("BeatAPI returned HTTP 503")
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["status"] == "JEV_FAILED"
    assert body["latest_jev_decision"] is None
    assert (await events(session_factory, ticket_id))[-1] == "jev_request_failed"


async def test_unexpected_error_also_marks_jev_failed(client, seeded, fake_jev):
    fake_jev.error = RuntimeError("bug")
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    assert (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["status"] == "JEV_FAILED"


async def test_failed_ticket_can_be_reanalyzed(client, seeded, fake_jev):
    fake_jev.error = JevUnavailable("down")
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    fake_jev.error = None
    res = await client.post(f"/api/v1/tickets/{ticket_id}/analyze")
    assert res.status_code == 202
    assert res.json()["status"] == "ANALYZING"
    assert (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["status"] == "WAITING_FOR_AGENT"


async def test_resolved_ticket_cannot_be_analyzed(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "RESOLVED"})
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/analyze")).status_code == 409


async def test_ticket_in_progress_cannot_be_analyzed_twice(client, seeded, session_factory):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    async with session_factory() as session:
        (await session.get(Ticket, ticket_id)).status = "ANALYZING"
        await session.commit()
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/analyze")).status_code == 409


async def test_analyze_missing_ticket_returns_404(client):
    assert (await client.post("/api/v1/tickets/999/analyze")).status_code == 404
