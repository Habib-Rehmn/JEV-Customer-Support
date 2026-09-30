from datetime import timedelta

from app.db.base import utcnow
from app.models import Ticket
from app.services.jev_service import JevUnavailable
from tests.conftest import jev_response
from tests.test_analysis import TICKET


async def new_ticket(client, fake_jev, response=None, error=None):
    fake_jev.response = response or jev_response("replacement", item_damaged=0.9)
    fake_jev.error = error
    return (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]


async def overview(client, **params):
    res = await client.get("/api/v1/analytics/overview", params=params)
    assert res.status_code == 200
    return res.json()


async def test_empty_overview(client):
    body = await overview(client)
    assert body["tickets"]["total"] == 0
    assert body["escalation_rate"] is None
    assert body["average_jev_confidence"] is None
    assert body["jev_human_agreement_rate"] is None
    assert body["by_category"] == {
        "refund": 0, "replacement": 0, "technical_support": 0, "billing": 0, "human_escalation": 0,
    }


async def test_overview_metrics(client, seeded, fake_jev):
    # A: replacement approved as-is (after an edit) -> agreement, no override, reply edited
    a = await new_ticket(client, fake_jev)
    await client.post(f"/api/v1/tickets/{a}/approve", json={"final_text": "Edited by agent"})

    # B: billing dispute escalated by rules, holding reply approved -> final human_escalation
    b = await new_ticket(client, fake_jev, jev_response("billing", billing_dispute=0.97))
    await client.post(f"/api/v1/tickets/{b}/approve", json={"next_status": "WAITING_FOR_CUSTOMER"})

    # C: replacement (confidence 0.8), agent overrides to refund
    c = await new_ticket(client, fake_jev, jev_response("replacement", confidence=0.8, item_damaged=0.9))
    await client.post(f"/api/v1/tickets/{c}/approve", json={"action": "refund"})

    # D: Jev failed
    await new_ticket(client, fake_jev, error=JevUnavailable("down"))

    # E: replacement, escalated by an agent, still open
    e = await new_ticket(client, fake_jev)
    await client.post(f"/api/v1/tickets/{e}/escalate", json={})

    body = await overview(client)
    assert body["tickets"] == {
        "total": 5, "open": 3, "escalated": 1, "resolved": 2, "jev_failed": 1, "overdue": 0,
        "analyzed": 4, "auto_routed": 3,
    }
    assert body["escalation_rate"] == 0.4                   # B (rules) + E (agent) of 5
    assert body["average_jev_confidence"] == 0.95           # (1 + 1 + 0.8 + 1) / 4
    assert body["by_category"]["replacement"] == 3
    assert body["by_category"]["billing"] == 1
    assert body["closed_out_with_decision"] == 3            # A, B, C
    assert body["human_override_rate"] == 0.3333            # C
    assert body["jev_human_agreement_rate"] == 0.3333       # A
    assert body["reply_edit_rate"] == 0.3333                # A of A, B, C


async def test_since_days_filters_old_tickets(client, seeded, fake_jev, session_factory):
    old = await new_ticket(client, fake_jev)
    await new_ticket(client, fake_jev)
    async with session_factory() as session:
        (await session.get(Ticket, old)).created_at = utcnow() - timedelta(days=60)
        await session.commit()

    assert (await overview(client))["tickets"]["total"] == 2
    assert (await overview(client, since_days=30))["tickets"]["total"] == 1


async def test_analytics_requires_login(anon_client):
    assert (await anon_client.get("/api/v1/analytics/overview")).status_code == 401
