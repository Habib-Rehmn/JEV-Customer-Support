"""Load demo customers and orders. Safe to run more than once.

    docker compose exec backend python -m scripts.seed
"""
import asyncio
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import Customer, Order

# (name, email, account_age_days, [(order_number, amount, status, age_days)])
CUSTOMERS = [
    ("Ali Khan", "ali@example.com", 430, [("ORD-10342", "89.99", "delivered", 4)]),
    ("Sara Ahmed", "sara@example.com", 120, [("ORD-10343", "649.00", "delivered", 10)]),
    ("John Smith", "john@example.com", 800, [
        ("ORD-10344", "25.50", "delivered", 45),
        ("ORD-10345", "140.00", "shipped", 2),
    ]),
    ("Maria Lopez", "maria@example.com", 15, [("ORD-10346", "59.99", "processing", 1)]),
]


async def seed() -> None:
    now = utcnow()
    async with SessionLocal() as session:
        for name, email, account_age, orders in CUSTOMERS:
            if await session.scalar(select(Customer).where(Customer.email == email)):
                continue
            customer = Customer(name=name, email=email, created_at=now - timedelta(days=account_age))
            session.add(customer)
            for number, amount, status, age in orders:
                created = now - timedelta(days=age + 3)
                session.add(Order(
                    customer=customer,
                    order_number=number,
                    total_amount=Decimal(amount),
                    status=status,
                    created_at=created,
                    delivered_at=now - timedelta(days=age) if status == "delivered" else None,
                ))
        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
