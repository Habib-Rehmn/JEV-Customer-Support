from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep, get_current_user
from app.repositories.customers import CustomerRepository
from app.repositories.orders import OrderRepository
from app.repositories.tickets import TicketRepository
from app.schemas.customer import CustomerRead
from app.schemas.order import OrderRead
from app.schemas.ticket import TicketList

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


async def _get_customer_or_404(session: SessionDep, customer_id: int):
    customer = await CustomerRepository(session).get(customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.get("", response_model=list[CustomerRead])
async def list_customers(session: SessionDep, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return await CustomerRepository(session).list(limit, offset)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, session: SessionDep):
    return await _get_customer_or_404(session, customer_id)


@router.get("/{customer_id}/tickets", response_model=TicketList)
async def get_customer_tickets(customer_id: int, session: SessionDep):
    await _get_customer_or_404(session, customer_id)
    items, total = await TicketRepository(session).list(customer_id=customer_id, limit=200)
    return TicketList(items=items, total=total)


@router.get("/{customer_id}/orders", response_model=list[OrderRead])
async def get_customer_orders(customer_id: int, session: SessionDep):
    await _get_customer_or_404(session, customer_id)
    return await OrderRepository(session).list_for_customer(customer_id)
