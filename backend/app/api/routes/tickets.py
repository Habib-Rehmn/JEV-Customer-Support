from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.api.deps import (
    AdminUser,
    CurrentUser,
    JevServiceDep,
    OpenAIServiceDep,
    SessionFactoryDep,
    TicketServiceDep,
    get_current_user,
)
from app.models.enums import TicketStatus
from app.schemas.response import AIResponseRead
from app.schemas.ticket import (
    ApproveRequest,
    EscalateRequest,
    ResolveRequest,
    ResponseEdit,
    TicketCreate,
    TicketDetail,
    TicketEvent,
    TicketList,
    TicketRead,
    TicketUpdate,
)
from app.services.ticket_service import analyze_ticket_job

# Customers submit tickets without logging in; everything else is for support agents.
public_router = APIRouter(prefix="/tickets", tags=["tickets"])
router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(get_current_user)])


@public_router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
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
    q: str | None = Query(None, max_length=200, description="Search ticket #, subject, message, customer, order"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = await service.list(status=status, q=q, limit=limit, offset=offset)
    return TicketList(items=items, total=total)


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: int, service: TicketServiceDep):
    return await service.get(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(ticket_id: int, data: TicketUpdate, service: TicketServiceDep, admin: AdminUser):
    """Raw field changes, for admins correcting data. Agents use the action endpoints."""
    return await service.update(ticket_id, data, user_id=admin.id)


@router.get("/{ticket_id}/events", response_model=list[TicketEvent])
async def ticket_events(ticket_id: int, service: TicketServiceDep):
    return await service.events(ticket_id)


@router.post("/{ticket_id}/analyze", response_model=TicketRead, status_code=status.HTTP_202_ACCEPTED)
async def analyze_ticket(
    ticket_id: int,
    service: TicketServiceDep,
    background: BackgroundTasks,
    session_factory: SessionFactoryDep,
    jev: JevServiceDep,
    openai: OpenAIServiceDep,
):
    ticket = await service.start_analysis(ticket_id)
    background.add_task(analyze_ticket_job, ticket.id, session_factory, jev, openai)
    return ticket


@router.post("/{ticket_id}/generate-response", response_model=AIResponseRead, status_code=status.HTTP_201_CREATED)
async def generate_response(
    ticket_id: int, service: TicketServiceDep, openai: OpenAIServiceDep, user: CurrentUser
):
    return await service.generate_response(ticket_id, openai, user_id=user.id)


@router.put("/{ticket_id}/response", response_model=AIResponseRead)
async def edit_response(ticket_id: int, data: ResponseEdit, service: TicketServiceDep, user: CurrentUser):
    return await service.edit_response(ticket_id, data.final_text, user_id=user.id)


@router.post("/{ticket_id}/approve", response_model=TicketRead)
async def approve_ticket(ticket_id: int, data: ApproveRequest, service: TicketServiceDep, user: CurrentUser):
    return await service.approve(
        ticket_id, final_text=data.final_text, action=data.action, next_status=data.next_status, user_id=user.id
    )


@router.post("/{ticket_id}/escalate", response_model=TicketRead)
async def escalate_ticket(ticket_id: int, data: EscalateRequest, service: TicketServiceDep, user: CurrentUser):
    return await service.escalate(ticket_id, data.reason, user_id=user.id)


@router.post("/{ticket_id}/resolve", response_model=TicketRead)
async def resolve_ticket(ticket_id: int, data: ResolveRequest, service: TicketServiceDep, user: CurrentUser):
    return await service.resolve(ticket_id, data.final_action, data.note, user_id=user.id)
