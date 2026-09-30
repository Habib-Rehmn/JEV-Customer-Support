TICKET = {
    "customer_name": "Ali Khan",
    "email": "ali@example.com",
    "order_number": "ORD-1",
    "subject": "Damaged product",
    "message": "My headphones arrived broken. Can you replace them?",
}


async def test_create_ticket_links_existing_customer_and_order(client, seeded):
    res = await client.post("/api/v1/tickets", json=TICKET)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ANALYZING"
    assert body["customer_id"] == seeded["ali"]
    assert body["order_id"] is not None


async def test_create_ticket_ignores_order_owned_by_someone_else(client, seeded):
    res = await client.post("/api/v1/tickets", json={**TICKET, "order_number": "ORD-2"})
    assert res.status_code == 201
    assert res.json()["order_id"] is None


async def test_create_ticket_creates_new_customer(client, seeded):
    res = await client.post("/api/v1/tickets", json={**TICKET, "email": "new@example.com", "order_number": None})
    assert res.status_code == 201
    assert res.json()["customer_id"] not in seeded.values()


async def test_create_ticket_validates_input(client):
    res = await client.post("/api/v1/tickets", json={**TICKET, "email": "not-an-email"})
    assert res.status_code == 422


async def test_get_ticket_includes_customer_and_order(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    res = await client.get(f"/api/v1/tickets/{ticket_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["customer"]["email"] == "ali@example.com"
    assert body["order"]["order_number"] == "ORD-1"


async def test_get_missing_ticket_returns_404(client):
    assert (await client.get("/api/v1/tickets/999")).status_code == 404


async def test_list_tickets_filters_by_status(client, seeded):
    first = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    await client.post("/api/v1/tickets", json=TICKET)
    await client.patch(f"/api/v1/tickets/{first}", json={"status": "ESCALATED"})

    all_tickets = (await client.get("/api/v1/tickets")).json()
    escalated = (await client.get("/api/v1/tickets", params={"status": "ESCALATED"})).json()
    assert all_tickets["total"] == 2
    assert escalated["total"] == 1
    assert escalated["items"][0]["id"] == first


async def test_resolving_ticket_sets_resolved_at(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    res = await client.patch(
        f"/api/v1/tickets/{ticket_id}", json={"status": "RESOLVED", "final_action": "replacement"}
    )
    assert res.status_code == 200
    assert res.json()["resolved_at"] is not None
    assert res.json()["final_action"] == "replacement"


async def test_update_rejects_unknown_status(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    res = await client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "DONE"})
    assert res.status_code == 422
