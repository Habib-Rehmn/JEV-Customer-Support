from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer


class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, customer_id: int) -> Customer | None:
        return await self.session.get(Customer, customer_id)

    async def get_by_email(self, email: str) -> Customer | None:
        return await self.session.scalar(select(Customer).where(func.lower(Customer.email) == email.lower()))

    async def list(self, limit: int, offset: int) -> list[Customer]:
        result = await self.session.scalars(select(Customer).order_by(Customer.id).limit(limit).offset(offset))
        return list(result)

    async def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        await self.session.flush()
        return customer
