from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.repositories.user_repo import AdminRepository


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        user_id = event.from_user.id if event.from_user else 0
        if user_id == settings.OWNER_ID:
            return True
        admin_repo = AdminRepository(session)
        return await admin_repo.is_admin(user_id, settings.OWNER_ID)
