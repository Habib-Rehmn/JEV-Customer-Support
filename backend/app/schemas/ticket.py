from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import SupportAction, TicketPriority, TicketStatus
from app.schemas.customer import CustomerRead
from app.schemas.jev import JevDecisionRead
from app.schemas.order import OrderRead
from app.schemas.response import AIResponseRead


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    order_number: str | None = Field(default=None, max_length=50)
    subject: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=10_000)


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    final_action: SupportAction | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_id: int | None
    subject: str
    message: str
    status: TicketStatus
    priority: TicketPriority
    final_action: SupportAction | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketListItem(TicketRead):
    current_action: SupportAction | None


class TicketDetail(TicketRead):
    customer: CustomerRead
    order: OrderRead | None
    latest_jev_decision: JevDecisionRead | None
    latest_ai_response: AIResponseRead | None


class TicketList(BaseModel):
    items: list[TicketListItem]
    total: int


class ResponseEdit(BaseModel):
    final_text: str = Field(min_length=1, max_length=10_000)


class ApproveRequest(BaseModel):
    final_text: str | None = Field(default=None, min_length=1, max_length=10_000)
    action: SupportAction | None = None  # defaults to the rules' permitted action
    next_status: Literal[TicketStatus.RESOLVED, TicketStatus.WAITING_FOR_CUSTOMER] = TicketStatus.RESOLVED


class EscalateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1_000)


class ResolveRequest(BaseModel):
    final_action: SupportAction
    note: str | None = Field(default=None, max_length=1_000)
