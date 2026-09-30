from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import UserCreate

logger = get_logger(__name__)

# Compared against when the email is unknown, so response time doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


class InvalidCredentials(Exception):
    pass


class EmailTaken(Exception):
    pass


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def login(self, email: str, password: str) -> tuple[str, User]:
        user = await self.users.get_by_email(email)
        valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if user is None or not valid:
            logger.info("login_failed email=%s", email)
            raise InvalidCredentials()
        logger.info("login_succeeded user=%s", user.id)
        return create_access_token(user.id, user.role), user

    async def create_user(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise EmailTaken(data.email)
        user = await self.users.add(User(
            name=data.name, email=data.email.lower(), password_hash=hash_password(data.password), role=data.role,
        ))
        await self.session.commit()
        return user
