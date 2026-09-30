from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models import Ticket
from app.models.enums import SupportAction


def _days_since(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    if moment.tzinfo is None:  # SQLite drops tzinfo; values are stored as UTC.
        moment = moment.replace(tzinfo=timezone.utc)
    return (utcnow() - moment).days


class ContextBuilder:
    """Gathers the customer/order facts Jev (and later the rules engine) decide on."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def build(self, ticket: Ticket) -> dict:
        customer, order = ticket.customer, ticket.order
        other_tickets = select(Ticket).where(Ticket.customer_id == customer.id, Ticket.id != ticket.id)
        refunds = other_tickets.where(Ticket.final_action == SupportAction.REFUND)

        previous_tickets = await self._count(other_tickets)
        previous_refunds = await self._count(refunds)
        refunds_last_30_days = await self._count(
            refunds.where(Ticket.resolved_at >= utcnow() - timedelta(days=30))
        )

        return {
            "customer_message": {"subject": ticket.subject, "body": ticket.message},
            "order": {
                "found": order is not None,
                "order_number": order.order_number if order else None,
                "status": order.status if order else None,
                "amount": float(order.total_amount) if order else None,
                "age_days": _days_since(order.created_at) if order else None,
                "days_since_delivery": _days_since(order.delivered_at) if order else None,
            },
            "customer": {
                "account_age_days": _days_since(customer.created_at),
                "previous_tickets": previous_tickets,
                "previous_refunds": previous_refunds,
                "refunds_last_30_days": refunds_last_30_days,
            },
        }

    async def _count(self, query) -> int:
        return await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
