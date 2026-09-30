async def test_customer_endpoints(client, seeded):
    ali = seeded["ali"]
    assert len((await client.get("/api/v1/customers")).json()) == 2
    assert (await client.get(f"/api/v1/customers/{ali}")).json()["email"] == "ali@example.com"

    orders = (await client.get(f"/api/v1/customers/{ali}/orders")).json()
    assert [o["order_number"] for o in orders] == ["ORD-1"]

    await client.post("/api/v1/tickets", json={
        "customer_name": "Ali Khan", "email": "ali@example.com", "subject": "Hi", "message": "Question",
    })
    assert (await client.get(f"/api/v1/customers/{ali}/tickets")).json()["total"] == 1


async def test_missing_customer_returns_404(client):
    assert (await client.get("/api/v1/customers/999")).status_code == 404
    assert (await client.get("/api/v1/customers/999/orders")).status_code == 404
