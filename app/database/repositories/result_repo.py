from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.result import Achievement, AttemptStatus, Result, StudentAnswer, TestAttempt
from app.database.models.test import Test
from app.database.models.user import User
from .base_repo import BaseRepository


class ResultRepository(BaseRepository[Result]):
    def __init__(self, session: AsyncSession):
        super().__init__(Result, session)

    async def get_by_attempt_id(self, attempt_id: int) -> Optional[Result]:
        stmt = (
            select(Result)
            .where(Result.attempt_id == attempt_id)
            .options(
                selectinload(Result.user),
                selectinload(Result.test),
                selectinload(Result.certificate)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_result_with_details(self, result_id: int) -> Optional[Result]:
        stmt = (
            select(Result)
            .where(Result.id == result_id)
            .options(
                selectinload(Result.user),
                selectinload(Result.test),
                selectinload(Result.certificate)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_results(self, user_id: int, limit: int = 50) -> List[Result]:
        stmt = (
            select(Result)
            .where(Result.user_id == user_id)
            .options(selectinload(Result.test), selectinload(Result.certificate))
            .order_by(Result.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_test_results(self, test_id: int, limit: int = 5000) -> List[Result]:
        stmt = (
            select(Result)
            .where(Result.test_id == test_id)
            .options(
                selectinload(Result.user),
                selectinload(Result.attempt)
            )
            .order_by(Result.percentage.desc(), Result.time_spent_seconds.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_global_leaderboard(self, limit: int = 50) -> List[dict]:
        # Top students based on average score & tests completed
        stmt = (
            select(
                User.id.label("user_id"),
                User.first_name,
                User.last_name,
                User.school,
                User.grade,
                func.count(Result.id).label("tests_taken"),
                func.avg(Result.percentage).label("avg_percentage"),
                func.sum(Result.total_score).label("total_score")
            )
            .join(Result, User.id == Result.user_id)
            .group_by(User.id)
            .order_by(desc("total_score"), desc("avg_percentage"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "user_id": row.user_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "school": row.school,
                "grade": row.grade,
                "tests_taken": row.tests_taken,
                "avg_percentage": float(row.avg_percentage or 0.0),
                "total_score": float(row.total_score or 0.0),
            }
            for row in result.all()
        ]

    async def get_group_leaderboard(self, group_id: int, limit: int = 50) -> List[dict]:
        from app.database.models.group import GroupMember

        stmt = (
            select(
                User.id.label("user_id"),
                User.first_name,
                User.last_name,
                func.count(Result.id).label("tests_taken"),
                func.avg(Result.percentage).label("avg_percentage"),
                func.sum(Result.total_score).label("total_score")
            )
            .join(GroupMember, User.id == GroupMember.user_id)
            .outerjoin(Result, User.id == Result.user_id)
            .where(GroupMember.group_id == group_id)
            .group_by(User.id)
            .order_by(desc("total_score"), desc("avg_percentage"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "user_id": row.user_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "tests_taken": row.tests_taken or 0,
                "avg_percentage": float(row.avg_percentage or 0.0),
                "total_score": float(row.total_score or 0.0),
            }
            for row in result.all()
        ]


class AttemptRepository(BaseRepository[TestAttempt]):
    def __init__(self, session: AsyncSession):
        super().__init__(TestAttempt, session)

    async def get_user_attempt_count(self, user_id: int, test_id: int) -> int:
        stmt = select(func.count(TestAttempt.id)).where(
            TestAttempt.user_id == user_id,
            TestAttempt.test_id == test_id,
            TestAttempt.status != AttemptStatus.CANCELLED
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_active_attempt(self, user_id: int, test_id: Optional[int] = None) -> Optional[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.status == AttemptStatus.IN_PROGRESS
            )
            .options(
                selectinload(TestAttempt.test),
                selectinload(TestAttempt.student_answers)
            )
        )
        if test_id:
            stmt = stmt.where(TestAttempt.test_id == test_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_answer(self, attempt_id: int, question_id: int, selected_option: str, is_correct: bool, points_earned: float) -> StudentAnswer:
        stmt = select(StudentAnswer).where(
            StudentAnswer.attempt_id == attempt_id,
            StudentAnswer.question_id == question_id
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.selected_option = selected_option
            existing.is_correct = is_correct
            existing.points_earned = points_earned
            existing.answered_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing
        else:
            ans = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option=selected_option,
                is_correct=is_correct,
                points_earned=points_earned
            )
            self.session.add(ans)
            await self.session.flush()
            return ans

    async def get_answers_for_attempt(self, attempt_id: int) -> List[StudentAnswer]:
        stmt = (
            select(StudentAnswer)
            .where(StudentAnswer.attempt_id == attempt_id)
            .options(selectinload(StudentAnswer.question))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AchievementRepository(BaseRepository[Achievement]):
    def __init__(self, session: AsyncSession):
        super().__init__(Achievement, session)

    async def get_user_achievements(self, user_id: int) -> List[Achievement]:
        stmt = select(Achievement).where(Achievement.user_id == user_id).order_by(Achievement.unlocked_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_badge(self, user_id: int, badge_type: str) -> bool:
        stmt = select(Achievement).where(Achievement.user_id == user_id, Achievement.badge_type == badge_type)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
