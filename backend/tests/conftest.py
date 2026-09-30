import json
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base, utcnow
from app.api.deps import get_session_factory
from app.db.session import get_session
from app.main import app
from app.models import Customer, Order
from app.services.jev_service import get_jev_service, parse_response

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeJev:
    """Stands in for BeatAPI. Returns the recorded real response unless told to fail."""

    def __init__(self):
        self.error: Exception | None = None
        self.contexts: list[dict] = []

    async def classify_ticket(self, context: dict):
        self.contexts.append(context)
        if self.error:
            raise self.error
        return parse_response(load_fixture("jev_replacement_response.json"))


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def seeded(session_factory):
    async with session_factory() as session:
        ali = Customer(name="Ali Khan", email="ali@example.com")
        sara = Customer(name="Sara Ahmed", email="sara@example.com")
        session.add_all([
            ali, sara,
            Order(customer=ali, order_number="ORD-1", total_amount=Decimal("89.99"),
                  status="delivered", delivered_at=utcnow()),
            Order(customer=sara, order_number="ORD-2", total_amount=Decimal("649.00"), status="delivered"),
        ])
        await session.commit()
        return {"ali": ali.id, "sara": sara.id}


@pytest.fixture
def fake_jev():
    return FakeJev()


@pytest.fixture
async def client(session_factory, fake_jev):
    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_jev_service] = lambda: fake_jev
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
