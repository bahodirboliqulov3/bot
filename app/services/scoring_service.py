from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.result import Achievement, AttemptStatus, Result, StudentAnswer, TestAttempt
from app.database.models.test import Question, Test
from app.database.repositories.result_repo import AchievementRepository, AttemptRepository, ResultRepository
from app.database.repositories.test_repo import TestRepository

logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.result_repo = ResultRepository(session)
        self.attempt_repo = AttemptRepository(session)
        self.test_repo = TestRepository(session)
        self.achievement_repo = AchievementRepository(session)

    @staticmethod
    def parse_quick_answers(text: str) -> Dict[int, str]:
        cleaned = text.strip()
        if re.fullmatch(r"[A-Da-d]+", cleaned):
            return {idx: char.upper() for idx, char in enumerate(cleaned, start=1)}

        pattern = r"(\d+)[\s\-:.\)]*([A-Da-d])"
        matches = re.findall(pattern, cleaned)
        answers: Dict[int, str] = {}
        for q_num, ans in matches:
            answers[int(q_num)] = ans.upper()
        return answers

    @staticmethod
    def parse_direct_code_and_answers(text: str) -> Optional[Tuple[str, str]]:
        match = re.match(r"^(TEST-[A-Z0-9]+|[A-Z0-9_\-]{3,16})\s+([\w\s\-:.,]+)$", text.strip(), re.IGNORECASE)
        if match:
            return match.group(1).upper(), match.group(2).strip()
        return None

    @staticmethod
    def get_progress_bar(percentage: float, total_blocks: int = 10) -> str:
        filled_blocks = int(round((percentage / 100) * total_blocks))
        filled_blocks = max(0, min(total_blocks, filled_blocks))
        empty_blocks = total_blocks - filled_blocks
        return "🟩" * filled_blocks + "⬜" * empty_blocks

    @staticmethod
    def get_user_rank_title(tests_count: int, avg_percentage: float = 0.0) -> Tuple[str, str, str]:
        if tests_count >= 50 and avg_percentage >= 80:
            return "👑 Professor / Daho", "👑", "Siz eng oliy darajadasiz! 🏆"
        elif tests_count >= 25:
            return "🎓 Ekspert / Akademik", "🎓", f"Keyingi daraja: 👑 Professor ({50 - tests_count} ta test qoldi)"
        elif tests_count >= 10:
            return "⚡ Bilimdon", "⚡", f"Keyingi daraja: 🎓 Ekspert ({25 - tests_count} ta test qoldi)"
        elif tests_count >= 3:
            return "📚 Izlanuvchi", "📚", f"Keyingi daraja: ⚡ Bilimdon ({10 - tests_count} ta test qoldi)"
        else:
            return "🌱 Boshlovchi", "🌱", f"Keyingi daraja: 📚 Izlanuvchi ({3 - tests_count} ta test qoldi)"

    @staticmethod
    def get_grade_info(percentage: float) -> Tuple[str, str, str]:
        if percentage == 100:
            return (
                "⭐️⭐️⭐️⭐️⭐️ 5+ (Mutlaq Daho)",
                "🔥 Qoyilmaqom! Barcha savollarga 100% to‘g‘ri javob berdingiz!",
                "🎉🥳🔥 <b>DAHOSIZ! 100% REKORD NATIJA!</b>\nSiz hech qanday xatosiz mutlaq g‘olib bo‘ldingiz! 🏆"
            )
        elif percentage >= 90:
            return (
                "⭐️⭐️⭐️⭐️⭐️ 5 (A'lo)",
                "🔥 Haqiqiy bilimdon natijasi! Juda yuqori daraja!",
                "🌟 <b>A'LO DARAJA!</b> Zo‘r natija ko‘rsatdingiz! 🚀"
            )
        elif percentage >= 75:
            return (
                "⭐️⭐️⭐️⭐️ 4 (Yaxshi)",
                "👍 Zo‘r natija! Ozgina mashq qilsangiz, 100% ga chiqasiz!",
                "👏 <b>YAXSHI HARAKAT!</b> Bilimingiz mustahkam! 💪"
            )
        elif percentage >= 55:
            return (
                "⭐️⭐️⭐️ 3 (Qoniqarli)",
                "💪 Yomon emas, ammo siz bundan ham yaxshiroq qila olasiz!",
                "💡 <b>HARAKATDA BARAKAT!</b> Xatolar ustida ishlab, qayta topshiring! 📈"
            )
        else:
            return (
                "⭐️⭐️ 2 (Qayta tayyorgarlik)",
                "💪 Tushkunlikka tushmang! Har bir xato — bu yangi bilim demakdir!",
                "🌱 <b>TUSHKUNLIKKA TUSHMANNG!</b> Keyingi safar albatta yuqori ball olasiz! 💪✨"
            )

    @staticmethod
    def build_visual_breakdown(correct_keys: Dict[int, str], user_answers: Dict[int, str]) -> str:
        total_q = len(correct_keys)
        if total_q == 0:
            return ""

        rows_count = (total_q + 2) // 3
        text_lines = ["\n📊 <b>Javoblar Tahlili:</b>"]

        for r in range(rows_count):
            col_items = []
            for col in range(3):
                q_num = r + 1 + (col * rows_count)
                if q_num <= total_q:
                    corr = correct_keys.get(q_num, "-")
                    user_ans = user_answers.get(q_num, "—")
                    if user_ans == corr:
                        badge = f"<b>{q_num}</b>.🟢{corr}"
                    elif user_ans == "—":
                        badge = f"<b>{q_num}</b>.⚪({corr})"
                    else:
                        badge = f"<b>{q_num}</b>.🔴{user_ans}({corr})"
                    col_items.append(f"{badge:<14}")
            text_lines.append("  |  ".join(col_items))

        return "\n".join(text_lines)

    async def get_test_rank(self, test_id: int, user_result_id: int) -> Tuple[int, int]:
        results = await self.result_repo.get_test_results(test_id)
        total_participants = len(results)
        rank = 1
        for idx, r in enumerate(results, start=1):
            if r.id == user_result_id:
                rank = idx
                break
        return rank, total_participants

    async def generate_channel_leaderboard_text(self, test_id: int, limit: int = 20) -> str:
        test = await self.test_repo.get_by_id(test_id)
        if not test:
            return "Test topilmadi."

        results = await self.result_repo.get_test_results(test_id)
        if not results:
            return f"📢 <b>\"{test.title}\"</b> testi bo‘yicha hali qatnashchilar yo‘q."

        total_participants = len(results)
        avg_score = sum(r.percentage for r in results) / total_participants
        pass_count = sum(1 for r in results if r.percentage >= test.pass_percentage)

        text = (
            f"🏆 <b>\"{test.title}\" TESTI CHEMPIONLARI</b>\n"
            f"🔑 Test kodi: <code>{test.code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for idx, r in enumerate(results[:limit], start=1):
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            elif idx <= 10:
                medal = f"<b>{idx}.</b> 🎖"
            else:
                medal = f"<b>{idx}.</b>"

            user_name = r.user.full_name if r.user else "O'quvchi"
            region = f"({r.user.school})" if (r.user and r.user.school and r.user.school != "O‘zbekiston") else ""
            minutes, seconds = divmod(r.time_spent_seconds, 60)
            time_str = f"{minutes}m {seconds}s" if r.time_spent_seconds > 0 else ""

            text += f"{medal} <b>{user_name}</b> {region}\n"
            text += f"   └ 📊 <b>{r.percentage}%</b> ({r.correct_count}/{r.correct_count + r.incorrect_count + r.unanswered_count} ta) • {time_str}\n\n"

        text += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Jami ishtirokchilar:</b> {total_participants} nafar\n"
            f"📈 <b>O‘rtacha ko‘rsatkich:</b> {avg_score:.1f}%\n"
            f"🎉 <b>Sertifikat egalari:</b> {pass_count} nafar\n"
            f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🤖 <i>Testni bot orqali tekshirish: @tekshiruv2_bot</i>"
        )
        return text

    async def complete_attempt(self, attempt_id: int) -> Result:
        attempt = await self.attempt_repo.get_by_id(attempt_id)
        if not attempt:
            raise ValueError("Attempt topilmadi")

        test = await self.test_repo.get_test_with_questions(attempt.test_id)
        if not test:
            raise ValueError("Test topilmadi")

        now = datetime.now(timezone.utc)
        attempt.finished_at = now
        started = attempt.started_at.replace(tzinfo=timezone.utc) if attempt.started_at.tzinfo is None else attempt.started_at
        time_spent = int((now - started).total_seconds())
        attempt.time_spent_seconds = max(1, time_spent)
        attempt.status = AttemptStatus.COMPLETED

        student_answers = await self.attempt_repo.get_answers_for_attempt(attempt_id)
        answer_map = {ans.question_id: ans for ans in student_answers}

        total_questions = len(test.test_questions) if test.test_questions else test.total_questions
        correct_count = 0
        incorrect_count = 0
        total_score = 0.0
        max_possible_score = sum(tq.question.points for tq in test.test_questions) if test.test_questions else test.max_points

        for tq in test.test_questions:
            q = tq.question
            if q.id in answer_map:
                ans = answer_map[q.id]
                if ans.is_correct:
                    correct_count += 1
                    total_score += q.points
                else:
                    incorrect_count += 1

        unanswered_count = max(0, total_questions - (correct_count + incorrect_count))
        percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0.0
        percentage = round(percentage, 2)

        existing_result = await self.result_repo.get_by_attempt_id(attempt_id)
        if existing_result:
            existing_result.correct_count = correct_count
            existing_result.incorrect_count = incorrect_count
            existing_result.unanswered_count = unanswered_count
            existing_result.total_score = round(total_score, 2)
            existing_result.max_score = round(max_possible_score, 2)
            existing_result.percentage = percentage
            existing_result.time_spent_seconds = attempt.time_spent_seconds
            res = existing_result
        else:
            res = await self.result_repo.create(
                attempt_id=attempt.id,
                user_id=attempt.user_id,
                test_id=test.id,
                correct_count=correct_count,
                incorrect_count=incorrect_count,
                unanswered_count=unanswered_count,
                total_score=round(total_score, 2),
                max_score=round(max_possible_score, 2),
                percentage=percentage,
                time_spent_seconds=attempt.time_spent_seconds
            )

        await self._check_achievements(attempt.user_id, res)
        await self._auto_issue_certificate(attempt.user_id, test, res)
        return res

    async def evaluate_quick_submission(
        self,
        test_id: int,
        user_id: int,
        raw_answers: str
    ) -> Tuple[Result, str]:
        from app.database.models.test import TestStatus

        test = await self.test_repo.get_test_with_questions(test_id)
        if not test:
            raise ValueError("Test topilmadi")

        now_utc = datetime.now(timezone.utc)

        # 1. Start time check
        if test.start_time:
            st = test.start_time.replace(tzinfo=timezone.utc) if test.start_time.tzinfo is None else test.start_time
            if now_utc < st:
                raise ValueError(f"⏳ Ushbu test hali boshlanmadi. Boshlanish vaqti: {test.start_time.strftime('%d.%m.%Y %H:%M')}")

        # 2. Expiration and Completed status check
        if test.status in [TestStatus.FINISHED, TestStatus.ARCHIVED]:
            raise ValueError("⛔ Ushbu test yakunlangan! Belgilangan vaqt tugaganligi sababli yangi javoblar qabul qilinmaydi.")

        if test.end_time:
            et = test.end_time.replace(tzinfo=timezone.utc) if test.end_time.tzinfo is None else test.end_time
            if now_utc > et:
                test.status = TestStatus.FINISHED
                await self.session.commit()
                raise ValueError("⛔ Ushbu testning belgilangan vaqti tugagan! Test yakunlandi va yangi javoblar qabul qilinmaydi.")

        # 3. Check Attempts Limit (Feature 5)
        if test.max_attempts and test.max_attempts > 0:
            user_results = await self.result_repo.get_user_results(user_id)
            user_test_results = [r for r in user_results if r.test_id == test.id]
            if len(user_test_results) >= test.max_attempts:
                prev = user_test_results[0]
                raise ValueError(
                    f"⚠️ Siz ushbu testni allaqachon topshirgansiz!\n"
                    f"🔒 Qoidalarga ko‘ra, ushbu testda faqat {test.max_attempts} marta qatnashish mumkin.\n\n"
                    f"📊 Sizning rasmiy natijangiz: {prev.percentage}% ({prev.correct_count} ta to‘g‘ri)."
                )

        parsed = self.parse_quick_answers(raw_answers)
        if not parsed:
            raise ValueError("Javoblar aniqlanmadi. Format: `1-A 2-B 3-C` yoki `ABCDACBD...`")

        if test.answer_key:
            correct_keys = self.parse_quick_answers(test.answer_key)
            total_questions = len(correct_keys)
            correct_count = 0
            incorrect_count = 0

            for idx, correct_opt in correct_keys.items():
                user_opt = parsed.get(idx)
                if user_opt:
                    if user_opt == correct_opt:
                        correct_count += 1
                    else:
                        incorrect_count += 1

            unanswered = max(0, total_questions - (correct_count + incorrect_count))
            percentage = round((correct_count / total_questions * 100), 2) if total_questions > 0 else 0.0
            point_per_q = test.max_points / total_questions if total_questions > 0 else 1.0
            total_score = round(correct_count * point_per_q, 2)

            attempt = await self.attempt_repo.create(
                test_id=test.id,
                user_id=user_id,
                attempt_number=1,
                status=AttemptStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                time_spent_seconds=60,
                question_order=list(correct_keys.keys()),
                option_order={
                    "user_answers": {str(k): v for k, v in parsed.items()},
                    "correct_keys": {str(k): v for k, v in correct_keys.items()}
                }
            )

            res = await self.result_repo.create(
                attempt_id=attempt.id,
                user_id=user_id,
                test_id=test.id,
                correct_count=correct_count,
                incorrect_count=incorrect_count,
                unanswered_count=unanswered,
                total_score=total_score,
                max_score=test.max_points,
                percentage=percentage,
                time_spent_seconds=attempt.time_spent_seconds
            )

            await self._check_achievements(user_id, res)
            await self._auto_issue_certificate(user_id, test, res)

            visual_grid = self.build_visual_breakdown(correct_keys, parsed)
            return res, visual_grid

        else:
            correct_keys = {}
            for idx, tq in enumerate(test.test_questions, start=1):
                correct_keys[idx] = tq.question.correct_option.upper()

            attempt = await self.attempt_repo.create(
                test_id=test.id,
                user_id=user_id,
                attempt_number=1,
                status=AttemptStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc),
                question_order=[tq.question.id for tq in test.test_questions],
                option_order={
                    "user_answers": {str(k): v for k, v in parsed.items()},
                    "correct_keys": {str(k): v for k, v in correct_keys.items()}
                }
            )

            for idx, tq in enumerate(test.test_questions, start=1):
                q = tq.question
                user_ans = parsed.get(idx)
                if user_ans:
                    is_correct = (user_ans.upper() == q.correct_option.upper())
                    pts = q.points if is_correct else 0.0
                    await self.attempt_repo.save_answer(
                        attempt_id=attempt.id,
                        question_id=q.id,
                        selected_option=user_ans.upper(),
                        is_correct=is_correct,
                        points_earned=pts
                    )

            res = await self.complete_attempt(attempt.id)
            visual_grid = self.build_visual_breakdown(correct_keys, parsed)
            return res, visual_grid

    async def _auto_issue_certificate(self, user_id: int, test: Test, result: Result) -> None:
        if result.percentage >= test.pass_percentage:
            try:
                from app.services.certificate_service import CertificateService
                from app.database.repositories.user_repo import UserRepository
                user_repo = UserRepository(self.session)
                user = await user_repo.get_by_id(user_id)
                if user:
                    cert_service = CertificateService(self.session)
                    await cert_service.issue_certificate(result, user, test)
            except Exception as e:
                logger.error(f"Error auto-issuing certificate: {e}")

    async def _check_achievements(self, user_id: int, result: Result) -> None:
        if not await self.achievement_repo.has_badge(user_id, "first_test"):
            await self.achievement_repo.create(
                user_id=user_id,
                badge_type="first_test",
                title="🚀 Birinchi qadam",
                description="Platformada birinchi testni muvaffaqiyatli topshirdingiz!"
            )

        if result.percentage >= 100.0 and not await self.achievement_repo.has_badge(user_id, "perfect_score"):
            await self.achievement_repo.create(
                user_id=user_id,
                badge_type="perfect_score",
                title="🎯 100% Natija",
                description="Testdan maksimal 100% natija qayd etdingiz!"
            )
