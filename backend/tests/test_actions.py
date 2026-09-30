from app.services.jev_service import JevUnavailable
from app.services.openai_service import OpenAIError
from tests.conftest import jev_response
from tests.test_analysis import TICKET, events


async def create(client):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    return ticket_id, (await client.get(f"/api/v1/tickets/{ticket_id}")).json()


# Approve

async def test_approve_sends_reply_and_resolves_with_permitted_action(client, seeded, session_factory):
    ticket_id, _ = await create(client)

    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["final_action"] == "replacement"
    assert res.json()["resolved_at"] is not None

    reply = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["latest_ai_response"]
    assert reply["approved"] is True
    assert reply["sent_at"] is not None
    assert (await events(session_factory, ticket_id))[-2:] == ["ticket_approved", "ticket_resolved"]


async def test_approve_with_edited_text(client, seeded):
    ticket_id, before = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"final_text": "Hi Ali, edited."})
    assert res.status_code == 200

    reply = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["latest_ai_response"]
    assert reply["id"] == before["latest_ai_response"]["id"]
    assert reply["final_text"] == "Hi Ali, edited."
    assert reply["generated_text"] == before["latest_ai_response"]["generated_text"]


async def test_approve_can_wait_for_customer(client, seeded):
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"next_status": "WAITING_FOR_CUSTOMER"})
    assert res.json()["status"] == "WAITING_FOR_CUSTOMER"
    assert res.json()["resolved_at"] is None


async def test_approve_rejects_other_next_status(client, seeded):
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"next_status": "CLOSED"})
    assert res.status_code == 422


async def test_agent_can_override_action(client, seeded, session_factory):
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"action": "refund"})
    assert res.json()["final_action"] == "refund"


async def test_escalated_ticket_needs_no_extra_input_to_approve_holding_reply(client, seeded, fake_jev):
    fake_jev.response = jev_response("billing", billing_dispute=0.97)
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"next_status": "WAITING_FOR_CUSTOMER"})
    assert res.status_code == 200
    assert res.json()["final_action"] == "human_escalation"


async def test_approve_without_reply_is_rejected(client, seeded, fake_openai):
    fake_openai.error = OpenAIError("down")
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})
    assert res.status_code == 409
    assert "no reply" in res.json()["detail"]


async def test_jev_failed_ticket_needs_manual_action_and_reply(client, seeded, fake_jev):
    fake_jev.error = JevUnavailable("down")
    ticket_id, _ = await create(client)

    assert (await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={"final_text": "Hi"})).status_code == 409
    res = await client.post(
        f"/api/v1/tickets/{ticket_id}/approve", json={"final_text": "Hi Ali, we're on it.", "action": "replacement"}
    )
    assert res.status_code == 200
    assert res.json()["final_action"] == "replacement"


async def test_resolved_ticket_cannot_be_approved_again(client, seeded):
    ticket_id, _ = await create(client)
    await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})
    res = await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})
    assert res.status_code == 409


async def test_approve_missing_ticket_returns_404(client):
    assert (await client.post("/api/v1/tickets/999/approve", json={})).status_code == 404


# Edit

async def test_edit_updates_draft_without_approving(client, seeded):
    ticket_id, before = await create(client)
    res = await client.put(f"/api/v1/tickets/{ticket_id}/response", json={"final_text": "Draft v2"})
    assert res.status_code == 200
    assert res.json()["id"] == before["latest_ai_response"]["id"]
    assert res.json()["final_text"] == "Draft v2"
    assert res.json()["approved"] is False
    assert (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["status"] == "WAITING_FOR_AGENT"


async def test_edit_creates_manual_reply_when_openai_failed(client, seeded, fake_openai):
    fake_openai.error = OpenAIError("down")
    ticket_id, _ = await create(client)
    res = await client.put(f"/api/v1/tickets/{ticket_id}/response", json={"final_text": "Written by hand"})
    assert res.status_code == 200
    assert res.json()["generated_text"] is None
    assert res.json()["model"] is None
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})).status_code == 200


async def test_edit_rejects_empty_text(client, seeded):
    ticket_id, _ = await create(client)
    assert (await client.put(f"/api/v1/tickets/{ticket_id}/response", json={"final_text": ""})).status_code == 422


# Escalate

async def test_agent_escalation(client, seeded, session_factory):
    ticket_id, _ = await create(client)
    res = await client.post(f"/api/v1/tickets/{ticket_id}/escalate", json={"reason": "Customer is a VIP"})
    assert res.status_code == 200
    assert res.json()["status"] == "ESCALATED"
    assert res.json()["priority"] == "HIGH"
    assert (await events(session_factory, ticket_id))[-1] == "ticket_escalated"


async def test_cannot_escalate_twice(client, seeded):
    ticket_id, _ = await create(client)
    await client.post(f"/api/v1/tickets/{ticket_id}/escalate", json={})
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/escalate", json={})).status_code == 409


# Resolve

async def test_resolve_without_reply(client, seeded):
    ticket_id, _ = await create(client)
    res = await client.post(
        f"/api/v1/tickets/{ticket_id}/resolve", json={"final_action": "refund", "note": "Handled by phone"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["final_action"] == "refund"


async def test_resolve_requires_final_action(client, seeded):
    ticket_id, _ = await create(client)
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/resolve", json={})).status_code == 422


async def test_cannot_resolve_twice(client, seeded):
    ticket_id, _ = await create(client)
    await client.post(f"/api/v1/tickets/{ticket_id}/resolve", json={"final_action": "refund"})
    res = await client.post(f"/api/v1/tickets/{ticket_id}/resolve", json={"final_action": "refund"})
    assert res.status_code == 409
