from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import TicketServiceDep
from app.models.enums import TicketStatus
from app.schemas.ticket import TicketCreate, TicketDetail, TicketList, TicketRead, TicketUpdate
from app.services.ticket_service import TicketNotFound

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(data: TicketCreate, service: TicketServiceDep):
    return await service.create(data)


@router.get("", response_model=TicketList)
async def list_tickets(
    service: TicketServiceDep,
    status: TicketStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = await service.list(status=status, limit=limit, offset=offset)
    return TicketList(items=items, total=total)


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: int, service: TicketServiceDep):
    try:
        return await service.get(ticket_id)
    except TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(ticket_id: int, data: TicketUpdate, service: TicketServiceDep):
    try:
        return await service.update(ticket_id, data)
    except TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
