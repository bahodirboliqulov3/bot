import asyncio
import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.system import Broadcast, BroadcastStatus
from app.database.models.user import User
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class BroadcastService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.group_repo = GroupRepository(session)
        self.result_repo = ResultRepository(session)
        self.broadcast_repo = BaseRepository(Broadcast, session)

    async def get_target_users(self, target_type: str, target_id: Optional[int] = None) -> List[User]:
        if target_type == "all":
            return await self.user_repo.get_all_active_users()
        elif target_type == "group" and target_id:
            return await self.group_repo.get_group_members(target_id)
        elif target_type == "test" and target_id:
            results = await self.result_repo.get_test_results(target_id)
            users_dict = {}
            for r in results:
                if r.user and not r.user.is_blocked:
                    users_dict[r.user.id] = r.user
            return list(users_dict.values())
        return []

    async def execute_broadcast(
        self,
        bot: Bot,
        admin_id: int,
        target_type: str,
        message_text: str,
        target_id: Optional[int] = None
    ) -> Broadcast:
        users = await self.get_target_users(target_type, target_id)

        broadcast = await self.broadcast_repo.create(
            admin_id=admin_id,
            target_type=target_type,
            target_id=target_id,
            message_text=message_text,
            total_count=len(users),
            success_count=0,
            failed_count=0,
            status=BroadcastStatus.SENDING
        )

        success = 0
        failed = 0

        # Send in batches of 25 with 1 second pause to respect Telegram limits
        batch_size = 25
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            for user in batch:
                if not user.notifications_enabled and target_type == "all":
                    continue
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=message_text)
                    success += 1
                except TelegramForbiddenError:
                    # User blocked the bot
                    failed += 1
                except TelegramAPIError as e:
                    logger.warning(f"Failed to send broadcast to {user.telegram_id}: {e}")
                    failed += 1
                except Exception as e:
                    logger.error(f"Unexpected error broadcasting to {user.telegram_id}: {e}")
                    failed += 1
            await asyncio.sleep(1.0)

        broadcast.success_count = success
        broadcast.failed_count = failed
        broadcast.status = BroadcastStatus.COMPLETED
        await self.session.flush()

        return broadcast
