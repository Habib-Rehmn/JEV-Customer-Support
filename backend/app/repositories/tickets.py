from __future__ import annotations

from sqlalchemy import case, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AIResponse, AuditLog, Customer, JevDecisionRecord, Order, Ticket
from app.models.enums import TicketPriority
from app.models.ticket import AWAITING_REPLY


_PRIORITY_RANK = case(
    {TicketPriority.URGENT: 0, TicketPriority.HIGH: 1, TicketPriority.NORMAL: 2, TicketPriority.LOW: 3},
    value=Ticket.priority,
    else_=4,
)
_AWAITING_FIRST = case((Ticket.status.in_(AWAITING_REPLY), 0), else_=1)
_ORDER = {
    "newest": (Ticket.id.desc(),),
    # Work queue: tickets still owed a reply, most urgent first, then whoever has waited longest.
    "urgent": (_AWAITING_FIRST, _PRIORITY_RANK, Ticket.created_at, Ticket.id),
}


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, ticket_id: int, with_relations: bool = False) -> Ticket | None:
        options = (
            [selectinload(Ticket.customer), selectinload(Ticket.order), selectinload(Ticket.jev_decisions),
             selectinload(Ticket.ai_responses)]
            if with_relations
            else []
        )
        return await self.session.get(Ticket, ticket_id, options=options, populate_existing=with_relations)

    async def list(
        self,
        *,
        status: str | None = None,
        customer_id: int | None = None,
        q: str | None = None,
        sort: str = "newest",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Ticket], int]:
        query = select(Ticket)
        if q:
            query = _search(query, q)
        if status:
            query = query.where(Ticket.status == status)
        if customer_id:
            query = query.where(Ticket.customer_id == customer_id)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.scalars(
            query.options(selectinload(Ticket.jev_decisions)).order_by(*_ORDER[sort]).limit(limit).offset(offset)
        )
        return list(result), total or 0

    async def add_decision(self, record: JevDecisionRecord) -> JevDecisionRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def add_response(self, response: AIResponse) -> AIResponse:
        self.session.add(response)
        await self.session.flush()
        return response

    async def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def list_events(self, ticket_id: int) -> list[AuditLog]:
        result = await self.session.scalars(
            select(AuditLog).where(AuditLog.ticket_id == ticket_id).order_by(AuditLog.id)
        )
        return list(result)

    async def log(self, ticket_id: int | None, event_type: str, **data) -> None:
        self.session.add(AuditLog(ticket_id=ticket_id, event_type=event_type, event_data=data))


def _search(query, q: str):
    """Case-insensitive match on ticket number, subject, message, customer name/email and order number.

    "#12" means ticket 12 only; a bare "12" matches ticket 12 or any text containing "12".
    """
    term = q.strip()
    number = term.removeprefix("#")
    is_number = number.isdigit() and len(number) <= 9  # stay inside the integer column range
    if term.startswith("#"):
        return query.where(Ticket.id == int(number)) if is_number else query.where(false())

    # Treat LIKE wildcards in the search text as literal characters.
    pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    conditions = [
        column.ilike(pattern, escape="\\")
        for column in (Ticket.subject, Ticket.message, Customer.name, Customer.email, Order.order_number)
    ]
    if is_number:
        conditions.append(Ticket.id == int(number))
    return (
        query.join(Customer, Customer.id == Ticket.customer_id)
        .outerjoin(Order, Order.id == Ticket.order_id)
        .where(or_(*conditions))
    )
