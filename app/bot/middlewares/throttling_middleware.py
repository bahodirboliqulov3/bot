import time
from collections.abc import Awaitable, Callable
from typing import Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.35, warning_cooldown: float = 2.0):
        self.rate_limit = rate_limit
        self.warning_cooldown = warning_cooldown
        self.user_timestamps: Dict[int, float] = {}
        self.warning_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        now = time.time()
        last_time = self.user_timestamps.get(user.id, 0.0)
        time_passed = now - last_time

        # If user exceeds rate limit (anti-flood trigger)
        if time_passed < self.rate_limit:
            last_warn = self.warning_timestamps.get(user.id, 0.0)
            # Only warn once every `warning_cooldown` seconds to avoid spamming the user
            if now - last_warn > self.warning_cooldown:
                self.warning_timestamps[user.id] = now
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Iltimos, shoshilmang! Tugmalarni ketma-ket juda tez bosmang.", show_alert=False)
                    except Exception:
                        pass
                elif isinstance(event, Message):
                    try:
                        await event.answer("⚠️ <b>Iltimos, shoshilmang!</b> Buyruqlarni ketma-ket juda tez yubormang.", parse_mode="HTML")
                    except Exception:
                        pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:
                    pass
            return

        self.user_timestamps[user.id] = now
        return await handler(event, data)
