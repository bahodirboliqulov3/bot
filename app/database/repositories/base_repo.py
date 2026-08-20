from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, item_id: int) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == item_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, item_id: int, **kwargs: Any) -> Optional[ModelType]:
        stmt = update(self.model).where(self.model.id == item_id).values(**kwargs).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, item_id: int) -> bool:
        stmt = delete(self.model).where(self.model.id == item_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
