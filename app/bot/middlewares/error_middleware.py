from collections.abc import Awaitable, Callable
import logging
import traceback
from typing import Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Unhandled bot exception in {event.__class__.__name__}: {e}\n{traceback.format_exc()}")
            error_message = "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko‘ring."
            if isinstance(event, Message):
                try:
                    await event.answer(error_message)
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(error_message, show_alert=True)
                except Exception:
                    pass
            return None
