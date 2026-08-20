from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.result import Certificate
from .base_repo import BaseRepository


class CertificateRepository(BaseRepository[Certificate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Certificate, session)

    async def get_by_number(self, certificate_number: str) -> Optional[Certificate]:
        stmt = (
            select(Certificate)
            .where(Certificate.certificate_number == certificate_number.strip())
            .options(selectinload(Certificate.user), selectinload(Certificate.test))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_result_id(self, result_id: int) -> Optional[Certificate]:
        stmt = (
            select(Certificate)
            .where(Certificate.result_id == result_id)
            .options(selectinload(Certificate.user), selectinload(Certificate.test))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_certificate_with_details(self, cert_id: int) -> Optional[Certificate]:
        stmt = (
            select(Certificate)
            .where(Certificate.id == cert_id)
            .options(selectinload(Certificate.user), selectinload(Certificate.test))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_certificates(self, user_id: int) -> List[Certificate]:
        stmt = (
            select(Certificate)
            .where(Certificate.user_id == user_id)
            .options(selectinload(Certificate.test))
            .order_by(Certificate.issued_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_certificates(self, limit: int = 100, offset: int = 0) -> List[Certificate]:
        stmt = (
            select(Certificate)
            .options(selectinload(Certificate.user), selectinload(Certificate.test))
            .order_by(Certificate.issued_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
