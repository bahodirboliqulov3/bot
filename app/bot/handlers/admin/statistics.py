import html
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.database.repositories.stats_repo import StatsRepository
from app.services.stats_service import StatsService

router = Router(name="admin_statistics")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(StateFilter("*"), F.text.in_(["📊 Statistika", "📊 Statistika va Natijalar", "📈 Statistika", "📊 Natijalar", "Statistika"]))
async def show_admin_statistics(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    stats_service = StatsService(session)
    stats_repo = StatsRepository(session)

    dashboard = await stats_service.get_dashboard_stats()
    top_tests = await stats_repo.get_most_taken_tests(limit=3)
    hard_questions = await stats_repo.get_hardest_questions(limit=3)

    text = (
        "📊 PLATFORMA STATISTIKASI VA ASOSIY KO‘RSATKICHLAR\n\n"
        f"👥 Jami o‘quvchilar: {dashboard['total_users']} ta\n"
        f"📝 Jami testlar: {dashboard['total_tests']} ta (Faol: {dashboard['active_tests']} ta)\n"
        f"🔄 Jami urinishlar: {dashboard['total_attempts']} ta\n"
        f"📊 Tugallangan testlar: {dashboard['completed_results']} ta\n"
        f"🎯 O‘rtacha o‘zlashtirish: {dashboard['average_percentage']}%\n"
        f"📅 Bugungi urinishlar: {dashboard['today_attempts']} ta\n\n"
    )

    if top_tests:
        text += "🔥 Eng ko‘p ishlangan testlar:\n"
        for t in top_tests:
            safe_t = html.escape(t['title'])
            safe_c = html.escape(t['code'])
            text += f"🔹 {safe_t} ({safe_c}) — {t['attempts']} marta\n"
        text += "\n"

    if hard_questions:
        text += "⚠️ Eng ko‘p xato qilingan savollar:\n"
        for q in hard_questions:
            q_short = q["text"][:35] + "..." if len(q["text"]) > 35 else q["text"]
            text += f"▫️ \"{html.escape(q_short)}\" — {q['accuracy']}% to'g'ri ({q['total']} javob)\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm_refresh_stats")]
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "adm_refresh_stats")
async def refresh_admin_stats(callback: CallbackQuery, session: AsyncSession):
    stats_service = StatsService(session)
    stats_repo = StatsRepository(session)

    dashboard = await stats_service.get_dashboard_stats()
    top_tests = await stats_repo.get_most_taken_tests(limit=3)
    hard_questions = await stats_repo.get_hardest_questions(limit=3)

    text = (
        "📊 PLATFORMA STATISTIKASI VA ASOSIY KO‘RSATKICHLAR\n\n"
        f"👥 Jami o‘quvchilar: {dashboard['total_users']} ta\n"
        f"📝 Jami testlar: {dashboard['total_tests']} ta (Faol: {dashboard['active_tests']} ta)\n"
        f"🔄 Jami urinishlar: {dashboard['total_attempts']} ta\n"
        f"📊 Tugallangan testlar: {dashboard['completed_results']} ta\n"
        f"🎯 O‘rtacha o‘zlashtirish: {dashboard['average_percentage']}%\n"
        f"📅 Bugungi urinishlar: {dashboard['today_attempts']} ta\n\n"
    )

    if top_tests:
        text += "🔥 Eng ko‘p ishlangan testlar:\n"
        for t in top_tests:
            safe_t = html.escape(t['title'])
            safe_c = html.escape(t['code'])
            text += f"🔹 {safe_t} ({safe_c}) — {t['attempts']} marta\n"
        text += "\n"

    if hard_questions:
        text += "⚠️ Eng ko‘p xato qilingan savollar:\n"
        for q in hard_questions:
            q_short = q["text"][:35] + "..." if len(q["text"]) > 35 else q["text"]
            text += f"▫️ \"{html.escape(q_short)}\" — {q['accuracy']}% to'g'ri ({q['total']} javob)\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm_refresh_stats")]
        ]
    )

    await callback.answer("Statistika yangilandi!")
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
