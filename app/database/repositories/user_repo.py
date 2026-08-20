from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.user import Admin, BlockedUser, User
from .base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        search_pattern = f"%{query}%"
        stmt = select(User).where(
            or_(
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.phone_number.ilike(search_pattern),
                User.school.ilike(search_pattern),
            )
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_users(self, limit: int = 20) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_users_count(self) -> int:
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_all_active_users(self) -> List[User]:
        stmt = select(User).where(User.is_blocked.is_(False))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_blocked(self, user_id: int, is_blocked: bool, blocked_by: int, reason: Optional[str] = None) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.is_blocked = is_blocked
            if is_blocked:
                # Add blocked record
                stmt = select(BlockedUser).where(BlockedUser.telegram_id == user.telegram_id)
                existing = (await self.session.execute(stmt)).scalar_one_or_none()
                if not existing:
                    blocked_entry = BlockedUser(telegram_id=user.telegram_id, reason=reason, blocked_by=blocked_by)
                    self.session.add(blocked_entry)
            else:
                # Remove blocked record
                stmt = select(BlockedUser).where(BlockedUser.telegram_id == user.telegram_id)
                existing = (await self.session.execute(stmt)).scalar_one_or_none()
                if existing:
                    await self.session.delete(existing)
            await self.session.flush()


class AdminRepository(BaseRepository[Admin]):
    def __init__(self, session: AsyncSession):
        super().__init__(Admin, session)

    async def is_admin(self, telegram_id: int, owner_id: int) -> bool:
        if telegram_id == owner_id:
            return True
        stmt = select(Admin).where(Admin.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        stmt = select(Admin).where(Admin.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_admins(self) -> List[Admin]:
        stmt = select(Admin).order_by(Admin.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_telegram_id(self, telegram_id: int) -> bool:
        admin = await self.get_by_telegram_id(telegram_id)
        if admin:
            await self.session.delete(admin)
            await self.session.flush()
            return True
        return False
