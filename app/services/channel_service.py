import logging
from typing import List, Tuple
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.system import RequiredChannel
from app.database.repositories.channel_repo import ChannelRepository

logger = logging.getLogger(__name__)


class ChannelService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.channel_repo = ChannelRepository(session)

    async def get_required_channels(self) -> List[RequiredChannel]:
        return await self.channel_repo.get_active_channels()

    async def check_user_subscriptions(self, bot: Bot, telegram_id: int) -> Tuple[bool, List[RequiredChannel]]:
        """
        Returns (is_all_subscribed, list_of_unsubscribed_channels)
        """
        channels = await self.get_required_channels()
        if not channels:
            return True, []

        unsubscribed: List[RequiredChannel] = []
        for channel in channels:
            try:
                chat_id = channel.channel_id
                if not (chat_id.startswith("@") or chat_id.startswith("-100")):
                    if chat_id.isdigit():
                        chat_id = int(chat_id)
                member = await bot.get_chat_member(chat_id=chat_id, user_id=telegram_id)
                if member.status in ["left", "kicked"]:
                    unsubscribed.append(channel)
            except Exception as e:
                logger.warning(f"Error checking membership for user {telegram_id} in channel {channel.channel_id}: {e}")
                # If bot cannot check or bot is not admin in channel, don't rigidly block or handle gracefully
                unsubscribed.append(channel)

        return len(unsubscribed) == 0, unsubscribed
