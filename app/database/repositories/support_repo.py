from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.system import SupportTicket, SupportTicketStatus
from .base_repo import BaseRepository


class SupportRepository(BaseRepository[SupportTicket]):
    def __init__(self, session: AsyncSession):
        super().__init__(SupportTicket, session)

    async def get_ticket_with_user(self, ticket_id: int) -> Optional[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .options(selectinload(SupportTicket.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tickets(self, status: Optional[SupportTicketStatus] = None, limit: int = 50, offset: int = 0) -> List[SupportTicket]:
        stmt = select(SupportTicket).options(selectinload(SupportTicket.user))
        if status:
            stmt = stmt.where(SupportTicket.status == status)
        stmt = stmt.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def answer_ticket(self, ticket_id: int, admin_id: int, response_text: str) -> Optional[SupportTicket]:
        ticket = await self.get_ticket_with_user(ticket_id)
        if ticket:
            ticket.admin_response = response_text
            ticket.answered_by = admin_id
            ticket.status = SupportTicketStatus.ANSWERED
            ticket.answered_at = datetime.now(timezone.utc)
            await self.session.flush()
        return ticket
