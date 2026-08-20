from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.result import Result, StudentAnswer, TestAttempt
from app.database.models.system import AuditLog, SystemSetting
from app.database.models.test import Question, Test, TestStatus
from app.database.models.user import User


class StatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_stats(self) -> Dict[str, Any]:
        users_count = (await self.session.execute(select(func.count(User.id)))).scalar_one() or 0
        tests_count = (await self.session.execute(select(func.count(Test.id)))).scalar_one() or 0
        active_tests_count = (await self.session.execute(select(func.count(Test.id)).where(Test.status == TestStatus.ACTIVE))).scalar_one() or 0
        attempts_count = (await self.session.execute(select(func.count(TestAttempt.id)))).scalar_one() or 0
        completed_results = (await self.session.execute(select(func.count(Result.id)))).scalar_one() or 0
        avg_score = (await self.session.execute(select(func.avg(Result.percentage)))).scalar_one() or 0.0

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_attempts = (
            await self.session.execute(
                select(func.count(TestAttempt.id)).where(TestAttempt.started_at >= today_start)
            )
        ).scalar_one() or 0

        return {
            "total_users": users_count,
            "total_tests": tests_count,
            "active_tests": active_tests_count,
            "total_attempts": attempts_count,
            "completed_results": completed_results,
            "average_percentage": round(float(avg_score), 2),
            "today_attempts": today_attempts,
        }

    async def get_most_taken_tests(self, limit: int = 5) -> List[dict]:
        stmt = (
            select(Test.title, Test.code, func.count(TestAttempt.id).label("attempt_count"))
            .join(TestAttempt, Test.id == TestAttempt.test_id)
            .group_by(Test.id)
            .order_by(func.count(TestAttempt.id).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [{"title": row[0], "code": row[1], "attempts": row[2]} for row in result.all()]

    async def get_hardest_questions(self, limit: int = 5) -> List[dict]:
        result = await self.session.execute(
            select(Question.text, StudentAnswer.is_correct)
            .join(StudentAnswer, Question.id == StudentAnswer.question_id)
        )
        rows = result.all()
        q_stats: Dict[str, Dict[str, int]] = {}
        for text, is_corr in rows:
            if text not in q_stats:
                q_stats[text] = {"total": 0, "correct": 0}
            q_stats[text]["total"] += 1
            if is_corr:
                q_stats[text]["correct"] += 1

        stats_list = []
        for text, counts in q_stats.items():
            acc = (counts["correct"] / counts["total"]) * 100 if counts["total"] > 0 else 0
            stats_list.append({"text": text, "total": counts["total"], "accuracy": round(acc, 1)})

        stats_list.sort(key=lambda x: x["accuracy"])
        return stats_list[:limit]

    async def log_audit(self, admin_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> AuditLog:
        log = AuditLog(admin_id=admin_id, action=action, details=details or {})
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_setting(self, key: str, default: str = "") -> str:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        return item.value if item else default

    async def set_setting(self, key: str, value: str, description: Optional[str] = None) -> SystemSetting:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            item.value = value
            if description:
                item.description = description
        else:
            item = SystemSetting(key=key, value=value, description=description)
            self.session.add(item)
        await self.session.flush()
        return item
