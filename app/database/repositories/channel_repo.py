from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.system import RequiredChannel
from .base_repo import BaseRepository


class ChannelRepository(BaseRepository[RequiredChannel]):
    def __init__(self, session: AsyncSession):
        super().__init__(RequiredChannel, session)

    async def get_active_channels(self) -> List[RequiredChannel]:
        stmt = select(RequiredChannel).where(RequiredChannel.is_active.is_(True)).order_by(RequiredChannel.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_channel_id(self, channel_id: str) -> Optional[RequiredChannel]:
        stmt = select(RequiredChannel).where(RequiredChannel.channel_id == channel_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
