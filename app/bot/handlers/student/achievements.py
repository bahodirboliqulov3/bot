import html
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.result_repo import AchievementRepository
from app.database.repositories.user_repo import UserRepository
from app.services.stats_service import StatsService

router = Router(name="student_achievements")


@router.message(F.text == "🏅 Yutuqlarim")
async def show_my_achievements(message: Message, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    stats_service = StatsService(session)
    stats = await stats_service.get_student_achievements_and_stats(user.id)

    ach_repo = AchievementRepository(session)
    badges = await ach_repo.get_user_achievements(user.id)

    text = (
        f"🏅 <b>{html.escape(user.full_name or 'Foydalanuvchi')}</b> — Shaxsiy Natijalar va Yutuqlar\n\n"
        f"📝 Jami ishlangan testlar: <b>{stats.get('total_tests', 0)} ta</b>\n"
        f"📊 O'rtacha natija: <b>{stats.get('avg_percentage', 0.0)}%</b>\n"
        f"🎯 Eng yaxshi natija: <b>{stats.get('best_percentage', 0.0)}%</b>\n"
        f"🎉 Sertifikatlar soni: <b>{stats.get('certificate_count', 0)} ta</b>\n"
        f"🏆 Umumiy reytingdagi o'rin: <b>#{stats.get('user_rank', '-')}</b>\n\n"
        f"🎖 Qo'lga kiritilgan nishonlar ({len(badges)} ta):\n"
    )

    if not badges:
        text += "▫️ Hozircha maxsus nishonlar yo‘q. Testlarda faol qatnashib, yangi nishonlarni oching!"
    else:
        for b in badges:
            text += f"🔹 {b.title}\n   {b.description}\n"

    await message.answer(text, parse_mode="HTML")
