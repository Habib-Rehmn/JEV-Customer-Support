from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import decode_access_token
from app.db.session import SessionLocal, get_session
from app.models import User
from app.models.enums import UserRole
from app.repositories.users import UserRepository
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


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> User:
    user_id = decode_access_token(credentials.credentials) if credentials else None
    user = await UserRepository(session).get(user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
