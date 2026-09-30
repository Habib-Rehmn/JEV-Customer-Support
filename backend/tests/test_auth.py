import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token
from tests.conftest import PASSWORD
from tests.test_analysis import TICKET


async def login(client, email, password=PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_login_returns_token_and_user(anon_client, users):
    res = await login(anon_client, "agent@example.com")
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "AGENT"
    assert "password_hash" not in body["user"]

    me = await anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["email"] == "agent@example.com"


async def test_login_email_is_case_insensitive(anon_client, users):
    assert (await login(anon_client, "Agent@Example.com")).status_code == 200


@pytest.mark.parametrize("email,password", [
    ("agent@example.com", "wrong-password"),
    ("nobody@example.com", PASSWORD),
])
async def test_bad_credentials_are_rejected_with_same_message(anon_client, users, email, password):
    res = await login(anon_client, email, password)
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


async def test_customers_can_submit_tickets_without_logging_in(anon_client, seeded):
    assert (await anon_client.post("/api/v1/tickets", json=TICKET)).status_code == 201


@pytest.mark.parametrize("method,path", [
    ("get", "/api/v1/tickets"),
    ("get", "/api/v1/tickets/1"),
    ("post", "/api/v1/tickets/1/analyze"),
    ("post", "/api/v1/tickets/1/generate-response"),
    ("post", "/api/v1/tickets/1/approve"),
    ("post", "/api/v1/tickets/1/escalate"),
    ("post", "/api/v1/tickets/1/resolve"),
    ("put", "/api/v1/tickets/1/response"),
    ("patch", "/api/v1/tickets/1"),
    ("get", "/api/v1/customers"),
    ("get", "/api/v1/customers/1/orders"),
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/users"),
])
async def test_agent_endpoints_require_login(anon_client, method, path):
    res = await anon_client.request(method, path, json={})
    assert res.status_code == 401


async def test_invalid_and_expired_tokens_are_rejected(anon_client, users):
    bad = {"Authorization": "Bearer not-a-token"}
    assert (await anon_client.get("/api/v1/auth/me", headers=bad)).status_code == 401

    expired = jwt.encode({"sub": str(users["agent"]), "exp": 0}, settings.jwt_secret, algorithm="HS256")
    res = await anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401

    forged = jwt.encode({"sub": str(users["admin"])}, "some-other-secret", algorithm="HS256")
    res = await anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


async def test_token_for_deleted_user_is_rejected(anon_client):
    token = create_access_token(12345, "ADMIN")
    res = await anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_agent_cannot_use_admin_endpoints(client, seeded):
    ticket_id = (await client.post("/api/v1/tickets", json=TICKET)).json()["id"]
    assert (await client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "CLOSED"})).status_code == 403
    assert (await client.get("/api/v1/users")).status_code == 403
    new_user = {"name": "X", "email": "x@example.com", "password": "password123"}
    assert (await client.post("/api/v1/users", json=new_user)).status_code == 403


async def test_admin_can_create_agent_who_can_then_log_in(anon_client, users, admin_headers):
    new_user = {"name": "New Agent", "email": "new@example.com", "password": "password123"}
    res = await anon_client.post("/api/v1/users", json=new_user, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["role"] == "AGENT"

    assert (await anon_client.post("/api/v1/users", json=new_user, headers=admin_headers)).status_code == 409
    assert (await login(anon_client, "new@example.com", "password123")).status_code == 200
    listed = (await anon_client.get("/api/v1/users", headers=admin_headers)).json()
    assert {u["email"] for u in listed} == {"agent@example.com", "admin@example.com", "new@example.com"}


async def test_short_password_is_rejected(anon_client, users, admin_headers):
    res = await anon_client.post(
        "/api/v1/users", json={"name": "X", "email": "x@example.com", "password": "short"}, headers=admin_headers
    )
    assert res.status_code == 422
