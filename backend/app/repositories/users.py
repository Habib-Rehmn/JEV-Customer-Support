from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    async def list(self) -> list[User]:
        return list(await self.session.scalars(select(User).order_by(User.id)))

    async def names(self, user_ids: set[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        rows = await self.session.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
        return {user_id: name for user_id, name in rows}

    async def count_admins(self) -> int:
        return await self.session.scalar(select(func.count()).where(User.role == UserRole.ADMIN)) or 0

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
