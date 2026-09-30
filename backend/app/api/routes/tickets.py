from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import JevServiceDep, OpenAIServiceDep, SessionFactoryDep, TicketServiceDep
from app.models.enums import TicketStatus
from app.schemas.response import AIResponseRead
from app.schemas.ticket import TicketCreate, TicketDetail, TicketList, TicketRead, TicketUpdate
from app.services.ticket_service import (
    NoDecisionYet,
    ResponseGenerationFailed,
    TicketNotAnalyzable,
    TicketNotFound,
    analyze_ticket_job,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    service: TicketServiceDep,
    background: BackgroundTasks,
    session_factory: SessionFactoryDep,
    jev: JevServiceDep,
    openai: OpenAIServiceDep,
):
    ticket = await service.create(data)
    ticket = await service.start_analysis(ticket.id)
    background.add_task(analyze_ticket_job, ticket.id, session_factory, jev, openai)
    return ticket


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


@router.post("/{ticket_id}/analyze", response_model=TicketRead, status_code=status.HTTP_202_ACCEPTED)
async def analyze_ticket(
    ticket_id: int,
    service: TicketServiceDep,
    background: BackgroundTasks,
    session_factory: SessionFactoryDep,
    jev: JevServiceDep,
    openai: OpenAIServiceDep,
):
    try:
        ticket = await service.start_analysis(ticket_id)
    except TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    except TicketNotAnalyzable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ticket in status {exc} cannot be analyzed")
    background.add_task(analyze_ticket_job, ticket.id, session_factory, jev, openai)
    return ticket


@router.post("/{ticket_id}/generate-response", response_model=AIResponseRead, status_code=status.HTTP_201_CREATED)
async def generate_response(ticket_id: int, service: TicketServiceDep, openai: OpenAIServiceDep):
    try:
        return await service.generate_response(ticket_id, openai)
    except TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    except NoDecisionYet:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ticket has no permitted action yet; analyze it first")
    except ResponseGenerationFailed:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Reply generation failed; try again or write the reply manually"
        )
