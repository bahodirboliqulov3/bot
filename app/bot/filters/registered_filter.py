from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.user_repo import UserRepository


class IsRegisteredFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        user_id = event.from_user.id if event.from_user else 0
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        return user is not None
