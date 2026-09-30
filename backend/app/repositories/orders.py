from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_number(self, order_number: str) -> Order | None:
        return await self.session.scalar(select(Order).where(Order.order_number == order_number))

    async def list_for_customer(self, customer_id: int) -> list[Order]:
        result = await self.session.scalars(
            select(Order).where(Order.customer_id == customer_id).order_by(Order.created_at.desc())
        )
        return list(result)
