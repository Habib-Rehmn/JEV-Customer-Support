from datetime import timedelta

import pytest

from app.db.base import utcnow
from app.models import Ticket
from app.models.enums import TicketPriority as P
from app.services.jev_service import QUESTIONS, parse_response
from app.services.ticket_service import priority_for
from tests.conftest import jev_response, load_fixture
from tests.test_analysis import TICKET


def test_real_urgency_response_parses():
    body = load_fixture("jev_replacement_response.json")
    body["answers"]["urgency"] = load_fixture("jev_urgency_response.json")["answers"]["urgency"]
    assert parse_response(body).urgency == 3.0


def test_urgency_question_has_four_levels_lowest_first():
    criteria = QUESTIONS["urgency"]["criteria"]
    assert len(criteria) == 4
    assert criteria[0].startswith("Low") and criteria[-1].startswith("Urgent")


@pytest.mark.parametrize("score", [None, "high", -0.5, 3.5, float("nan"), True])
def test_bad_urgency_is_unknown_not_a_failure(score):
    body = jev_response("refund", urgency=None)
    if score is not None:
        body["answers"]["urgency"] = {"type": "score", "score": score}
    decision = parse_response(body)
    assert decision.urgency is None
    assert decision.action == "refund"


@pytest.mark.parametrize("urgency,escalated,expected", [
    (0.0, False, P.LOW),
    (1.4, False, P.NORMAL),
    (1.6, False, P.HIGH),
    (3.0, False, P.URGENT),
    (None, False, P.NORMAL),
    (0.0, True, P.HIGH),       # escalations are never below HIGH
    (None, True, P.HIGH),
    (3.0, True, P.URGENT),
])
def test_priority_from_urgency(urgency, escalated, expected):
    assert priority_for(urgency, escalated=escalated) == expected


async def test_analysis_sets_priority_and_due_time(client, seeded, fake_jev):
    fake_jev.response = jev_response("replacement", item_damaged=0.9, urgency=3)
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["priority"] == "URGENT"
    assert body["latest_jev_decision"]["urgency_score"] == 3
    assert body["response_due_at"] is not None
    assert body["overdue"] is False


async def test_no_due_time_once_replied(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"next_status": "WAITING_FOR_CUSTOMER"})
    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["response_due_at"] is None
    assert body["overdue"] is False


async def age(session_factory, ticket_id, hours):
    async with session_factory() as session:
        (await session.get(Ticket, ticket_id)).created_at = utcnow() - timedelta(hours=hours)
        await session.commit()


async def test_overdue_after_target(client, seeded, fake_jev, session_factory):
    fake_jev.response = jev_response("technical_support", urgency=2)  # HIGH: 4h target
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await age(session_factory, ticket_id, 5)

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["overdue"] is True
    assert (await client.get("/api/v1/analytics/overview")).json()["tickets"]["overdue"] == 1


async def test_urgent_sort_puts_priority_then_oldest_first(client, seeded, fake_jev, session_factory):
    ids = {}
    for name, urgency in [("normal_old", 1), ("urgent", 3), ("low", 0), ("normal_new", 1)]:
        fake_jev.response = jev_response("technical_support", urgency=urgency)
        ids[name] = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await age(session_factory, ids["normal_old"], 10)

    items = (await client.get("/api/v1/tickets", params={"sort": "urgent"})).json()["items"]
    assert [t["id"] for t in items] == [ids["urgent"], ids["normal_old"], ids["normal_new"], ids["low"]]
    newest = (await client.get("/api/v1/tickets")).json()["items"]
    assert newest[0]["id"] == ids["normal_new"]


async def test_unknown_sort_is_rejected(client):
    assert (await client.get("/api/v1/tickets", params={"sort": "random"})).status_code == 422


async def test_urgent_sort_puts_tickets_owed_a_reply_first(client, seeded, fake_jev):
    fake_jev.response = jev_response("technical_support", urgency=3)
    done = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.post(f"/api/v1/tickets/{done}/resolve", json={"final_action": "technical_support"})
    fake_jev.response = jev_response("technical_support", urgency=0)
    waiting = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    items = (await client.get("/api/v1/tickets", params={"sort": "urgent"})).json()["items"]
    assert [t["id"] for t in items] == [waiting, done]  # a low-priority open ticket beats a resolved urgent one
