from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuditLog, Ticket


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, ticket_id: int, with_relations: bool = False) -> Ticket | None:
        options = [selectinload(Ticket.customer), selectinload(Ticket.order)] if with_relations else []
        return await self.session.get(Ticket, ticket_id, options=options)

    async def list(
        self, *, status: str | None = None, customer_id: int | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[Ticket], int]:
        query = select(Ticket)
        if status:
            query = query.where(Ticket.status == status)
        if customer_id:
            query = query.where(Ticket.customer_id == customer_id)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.scalars(query.order_by(Ticket.id.desc()).limit(limit).offset(offset))
        return list(result), total or 0

    async def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def log(self, ticket_id: int | None, event_type: str, **data) -> None:
        self.session.add(AuditLog(ticket_id=ticket_id, event_type=event_type, event_data=data))
