from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    async def list(self) -> list[User]:
        return list(await self.session.scalars(select(User).order_by(User.id)))

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
