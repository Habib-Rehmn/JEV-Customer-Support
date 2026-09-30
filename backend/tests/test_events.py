from tests.test_analysis import TICKET


async def test_timeline_records_the_whole_flow_with_actor_names(client, seeded, users):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.put(f"/api/v1/tickets/{ticket_id}/response", json={"final_text": "Edited"})
    await client.post(f"/api/v1/tickets/{ticket_id}/approve", json={})

    res = await client.get(f"/api/v1/tickets/{ticket_id}/events")
    assert res.status_code == 200
    events = res.json()
    assert [e["event_type"] for e in events] == [
        "ticket_created",
        "jev_request_started",
        "jev_request_completed",
        "rule_triggered",
        "openai_generation_started",
        "openai_generation_completed",
        "response_edited",
        "ticket_approved",
        "ticket_resolved",
    ]
    by_type = {e["event_type"]: e for e in events}
    assert by_type["ticket_created"]["actor"] is None
    assert by_type["response_edited"]["actor"] == "Agent Amy"
    assert by_type["ticket_approved"]["actor"] == "Agent Amy"
    assert by_type["jev_request_completed"]["data"]["action"] == "replacement"
    assert by_type["jev_request_started"]["data"]["context"]["order"]["order_number"] == "ORD-1"


async def test_admin_patch_is_attributed(client, seeded, admin_headers):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.patch(f"/api/v1/tickets/{ticket_id}", json={"priority": "URGENT"}, headers=admin_headers)
    last = (await client.get(f"/api/v1/tickets/{ticket_id}/events")).json()[-1]
    assert last["event_type"] == "ticket_updated"
    assert last["actor"] == "Admin Ann"
    assert last["data"]["changes"] == {"priority": "URGENT"}


async def test_events_for_missing_ticket_returns_404(client):
    assert (await client.get("/api/v1/tickets/999/events")).status_code == 404


async def test_events_require_login(anon_client):
    assert (await anon_client.get("/api/v1/tickets/1/events")).status_code == 401
