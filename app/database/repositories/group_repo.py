from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.group import Group, GroupMember
from app.database.models.user import User
from .base_repo import BaseRepository


class GroupRepository(BaseRepository[Group]):
    def __init__(self, session: AsyncSession):
        super().__init__(Group, session)

    async def get_by_name(self, name: str) -> Optional[Group]:
        stmt = select(Group).where(Group.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_groups_with_member_count(self) -> List[tuple[Group, int]]:
        stmt = (
            select(Group, func.count(GroupMember.id).label("member_count"))
            .outerjoin(GroupMember, Group.id == GroupMember.group_id)
            .group_by(Group.id)
            .order_by(Group.name)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_group_members(self, group_id: int) -> List[User]:
        stmt = (
            select(User)
            .join(GroupMember, User.id == GroupMember.user_id)
            .where(GroupMember.group_id == group_id)
            .order_by(User.first_name, User.last_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_member(self, group_id: int, user_id: int) -> GroupMember:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
        membership = GroupMember(group_id=group_id, user_id=user_id)
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def remove_member(self, group_id: int, user_id: int) -> bool:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return True
        return False

    async def is_member(self, group_id: int, user_id: int) -> bool:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_groups(self, user_id: int) -> List[Group]:
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(GroupMember.user_id == user_id)
            .order_by(Group.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
