from collections.abc import Awaitable, Callable
import time
from typing import Any, Dict, Set
from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.services.auth_service import AuthService
from app.services.channel_service import ChannelService


class RequiredChannelMiddleware(BaseMiddleware):
    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl = cache_ttl_seconds
        self.cached_verified_users: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Ignore non-message/callback events
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = data.get("event_from_user")
        bot: Bot = data.get("bot")
        session: AsyncSession = data.get("session")

        if not user or not bot or not session:
            return await handler(event, data)

        # Allow /start command or channel check callback to pass through
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data in ["check_channel_subs", "cancel"]:
            return await handler(event, data)

        # Instant Cache Check for verified users
        now = time.time()
        cached_time = self.cached_verified_users.get(user.id, 0.0)
        if now - cached_time < self.cache_ttl:
            return await handler(event, data)

        # Allow Admins to bypass channel checks
        auth_service = AuthService(session)
        if await auth_service.is_admin(user.id):
            self.cached_verified_users[user.id] = now
            return await handler(event, data)

        channel_service = ChannelService(session)
        is_subbed, unsubs = await channel_service.check_user_subscriptions(bot, user.id)

        if not is_subbed and unsubs:
            buttons = []
            for ch in unsubs:
                buttons.append([InlineKeyboardButton(text=f"📢 {ch.title}", url=ch.invite_link)])
            buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_channel_subs")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)

            msg_text = "📢 Botdan foydalanish uchun quyidagi kanallarga a’zo bo‘ling:"
            if isinstance(event, Message):
                await event.answer(msg_text, reply_markup=kb, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.message.answer(msg_text, reply_markup=kb, parse_mode="HTML")
                await event.answer()
            return

        # Cache successful verification
        self.cached_verified_users[user.id] = now
        return await handler(event, data)
