from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.certificate_repo import CertificateRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.stats_repo import StatsRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.stats_repo = StatsRepository(session)
        self.user_repo = UserRepository(session)
        self.test_repo = TestRepository(session)
        self.result_repo = ResultRepository(session)
        self.cert_repo = CertificateRepository(session)

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        return await self.stats_repo.get_system_stats()

    async def get_student_achievements_and_stats(self, user_id: int) -> Dict[str, Any]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {}

        results = await self.result_repo.get_user_results(user_id)
        certs = await self.cert_repo.get_user_certificates(user_id)

        total_tests = len(results)
        if total_tests > 0:
            avg_score = sum(r.percentage for r in results) / total_tests
            best_score = max(r.percentage for r in results)
        else:
            avg_score = 0.0
            best_score = 0.0

        # Calculate rank
        leaderboard = await self.result_repo.get_global_leaderboard(limit=500)
        user_rank = None
        for idx, entry in enumerate(leaderboard, start=1):
            if entry["user_id"] == user_id:
                user_rank = idx
                break

        return {
            "total_tests": total_tests,
            "avg_percentage": round(avg_score, 1),
            "best_percentage": round(best_score, 1),
            "certificate_count": len(certs),
            "user_rank": user_rank or "Top 500 dan tashqarida",
        }
