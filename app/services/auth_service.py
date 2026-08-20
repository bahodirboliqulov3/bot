import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models.user import Admin, User
from app.database.repositories.user_repo import AdminRepository, UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.admin_repo = AdminRepository(session)

    async def is_admin(self, telegram_id: int) -> bool:
        if telegram_id == settings.OWNER_ID:
            return True
        return await self.admin_repo.is_admin(telegram_id, settings.OWNER_ID)

    async def register_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: str,
        username: Optional[str],
        phone_number: Optional[str],
        school: str,
        grade: str
    ) -> User:
        return await self.get_or_create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            phone_number=phone_number or "",
            school=school,
            grade=grade
        )

    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: str,
        username: Optional[str],
        phone_number: str,
        school: str,
        grade: str
    ) -> User:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.phone_number = phone_number or ""
            user.school = school
            user.grade = grade
            await self.session.flush()
            return user
        else:
            return await self.user_repo.create(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                phone_number=phone_number or "",
                school=school,
                grade=grade,
                is_blocked=False,
                notifications_enabled=True
            )

    async def is_user_registered(self, telegram_id: int) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user is not None

    async def is_user_blocked(self, telegram_id: int) -> bool:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user and user.is_blocked:
            return True
        return False

    async def add_admin(self, telegram_id: int, full_name: str, added_by: int) -> Admin:
        existing = await self.admin_repo.get_by_telegram_id(telegram_id)
        if existing:
            return existing
        return await self.admin_repo.create(
            telegram_id=telegram_id,
            full_name=full_name,
            added_by=added_by
        )

    async def remove_admin(self, telegram_id: int) -> bool:
        if telegram_id == settings.OWNER_ID:
            raise ValueError("Asosiy Owner adminni o'chirib bo'lmaydi!")
        return await self.admin_repo.delete_by_telegram_id(telegram_id)
