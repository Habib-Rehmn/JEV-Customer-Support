import pytest

from tests.test_analysis import TICKET

SARA = {
    "customer_name": "Sara Ahmed",
    "email": "sara@example.com",
    "order_number": "ORD-2",
    "subject": "Charged twice",
    "message": "I see two charges of 100% the same amount on my card.",
}


async def search(client, q, **params):
    res = await client.get("/api/v1/tickets", params={"q": q, **params})
    assert res.status_code == 200
    return [t["id"] for t in res.json()["items"]]


@pytest.fixture
async def two_tickets(client, seeded):
    ali = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    sara = (await client.post("/api/v1/tickets", json=SARA)).json()["id"]
    return ali, sara


@pytest.mark.parametrize("q,who", [
    ("damaged", "ali"),            # subject, case-insensitive
    ("HEADPHONES", "ali"),         # message
    ("sara ahmed", "sara"),        # customer name
    ("ali@example", "ali"),        # customer email
    ("ord-2", "sara"),             # order number
])
async def test_search_fields(client, two_tickets, q, who):
    ali, sara = two_tickets
    assert await search(client, q) == [ali if who == "ali" else sara]


async def test_hash_number_matches_ticket_number_only(client, two_tickets):
    ali, sara = two_tickets
    assert await search(client, f"#{sara}") == [sara]
    assert await search(client, f"#{ali}") == [ali]
    assert await search(client, "#abc") == []


async def test_bare_number_matches_ticket_number_or_text(client, two_tickets):
    ali, sara = two_tickets
    # Ticket #1 by number, plus Sara's ticket because its message contains "100%".
    assert sorted(await search(client, str(ali))) == sorted([ali, sara])


async def test_huge_number_does_not_break(client, two_tickets):
    assert await search(client, "99999999999999999999") == []
    assert await search(client, "#99999999999999999999") == []


async def test_wildcards_are_literal(client, two_tickets):
    _, sara = two_tickets
    assert await search(client, "100%") == [sara]
    assert await search(client, "%") == [sara]      # only Sara's text contains a literal %
    assert await search(client, "_") == []


async def test_search_combines_with_status(client, two_tickets):
    ali, sara = two_tickets
    await client.post(f"/api/v1/tickets/{sara}/escalate", json={})
    assert await search(client, "example.com", status="ESCALATED") == [sara]
    assert sorted(await search(client, "example.com")) == sorted([ali, sara])


async def test_search_total_counts_matches(client, two_tickets):
    res = await client.get("/api/v1/tickets", params={"q": "sara"})
    assert res.json()["total"] == 1
