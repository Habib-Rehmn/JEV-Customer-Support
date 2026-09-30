from app.services.jev_service import JevUnavailable
from app.services.openai_service import OpenAIError
from tests.conftest import jev_response
from tests.test_analysis import TICKET, events


async def test_reply_is_generated_after_analysis(client, seeded, fake_openai):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    reply = body["latest_ai_response"]
    assert reply["generated_text"] == "Hi Ali Khan, draft for replacement."
    assert reply["final_text"] == reply["generated_text"]
    assert reply["model"] == "fake-model"
    assert reply["approved"] is False
    assert fake_openai.calls[0]["order_number"] == "ORD-1"


async def test_escalated_ticket_gets_a_holding_reply(client, seeded, fake_jev, fake_openai):
    fake_jev.response = jev_response("billing", billing_dispute=0.97)
    await client.post("/api/v1/tickets", json=TICKET)
    # OpenAI only ever sees the permitted action, never Jev's raw recommendation.
    assert fake_openai.calls[0]["action"] == "human_escalation"


async def test_openai_failure_keeps_decision(client, seeded, fake_openai, session_factory):
    fake_openai.error = OpenAIError("OpenAI returned HTTP 503")
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]

    body = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()
    assert body["status"] == "WAITING_FOR_AGENT"
    assert body["latest_jev_decision"]["permitted_action"] == "replacement"
    assert body["latest_ai_response"] is None
    assert (await events(session_factory, ticket_id))[-1] == "openai_generation_failed"


async def test_no_reply_is_generated_when_jev_fails(client, seeded, fake_jev, fake_openai):
    fake_jev.error = JevUnavailable("down")
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    assert fake_openai.calls == []
    res = await client.post(f"/api/v1/tickets/{ticket_id}/generate-response")
    assert res.status_code == 409


async def test_regenerate_creates_a_new_reply(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    first = (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["latest_ai_response"]["id"]

    res = await client.post(f"/api/v1/tickets/{ticket_id}/generate-response")
    assert res.status_code == 201
    assert res.json()["id"] != first
    assert (await client.get(f"/api/v1/tickets/{ticket_id}")).json()["latest_ai_response"]["id"] == res.json()["id"]


async def test_regenerate_failure_returns_502(client, seeded, fake_openai):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    fake_openai.error = OpenAIError("down")
    assert (await client.post(f"/api/v1/tickets/{ticket_id}/generate-response")).status_code == 502


async def test_generate_for_missing_ticket_returns_404(client):
    assert (await client.post("/api/v1/tickets/999/generate-response")).status_code == 404
