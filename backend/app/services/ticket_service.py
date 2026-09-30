from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import utcnow
from app.models import Customer, Ticket
from app.models.enums import TicketStatus
from app.repositories.customers import CustomerRepository
from app.repositories.orders import OrderRepository
from app.repositories.tickets import TicketRepository
from app.schemas.ticket import TicketCreate, TicketUpdate

logger = get_logger(__name__)


class TicketNotFound(Exception):
    pass


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customers = CustomerRepository(session)
        self.orders = OrderRepository(session)
        self.tickets = TicketRepository(session)

    async def create(self, data: TicketCreate) -> Ticket:
        customer = await self.customers.get_by_email(data.email)
        if customer is None:
            customer = await self.customers.add(Customer(name=data.customer_name, email=data.email))

        # Only link an order that belongs to this customer; anything else is treated as unknown.
        order = await self.orders.get_by_number(data.order_number) if data.order_number else None
        if order is not None and order.customer_id != customer.id:
            order = None

        ticket = await self.tickets.add(Ticket(
            customer_id=customer.id,
            order_id=order.id if order else None,
            subject=data.subject,
            message=data.message,
        ))
        await self.tickets.log(
            ticket.id, "ticket_created",
            submitted_order_number=data.order_number, order_found=order is not None,
        )
        await self.session.commit()
        logger.info("ticket_created id=%s order_found=%s", ticket.id, order is not None)
        return ticket

    async def get(self, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get(ticket_id, with_relations=True)
        if ticket is None:
            raise TicketNotFound(ticket_id)
        return ticket

    async def list(self, **filters) -> tuple[list[Ticket], int]:
        return await self.tickets.list(**filters)

    async def update(self, ticket_id: int, data: TicketUpdate) -> Ticket:
        ticket = await self.get(ticket_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in changes.items():
            setattr(ticket, field, value)
        if changes.get("status") == TicketStatus.RESOLVED:
            ticket.resolved_at = utcnow()
        await self.tickets.log(ticket.id, "ticket_updated", **{k: str(v) for k, v in changes.items()})
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
