from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import SessionLocal, get_session
from app.services.jev_service import JevService, get_jev_service
from app.services.openai_service import OpenAIService, get_openai_service
from app.services.ticket_service import TicketService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_session_factory() -> async_sessionmaker:
    return SessionLocal


SessionFactoryDep = Annotated[async_sessionmaker, Depends(get_session_factory)]
JevServiceDep = Annotated[JevService, Depends(get_jev_service)]
OpenAIServiceDep = Annotated[OpenAIService, Depends(get_openai_service)]


def get_ticket_service(session: SessionDep) -> TicketService:
    return TicketService(session)


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
