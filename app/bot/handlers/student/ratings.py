import html
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.group import GroupMember
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.user_repo import UserRepository
from app.services.excel_service import ExcelService

router = Router(name="student_ratings")


def format_paginated_leaderboard(all_students: list[dict], user_id: int, page: int = 1, page_size: int = 10) -> tuple[str, InlineKeyboardMarkup]:
    total_count = len(all_students)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    current_page = all_students[start_idx:start_idx + page_size]

    user_pos = None
    for idx, s in enumerate(all_students, start=1):
        if s["user_id"] == user_id:
            user_pos = (idx, s["total_score"], s["avg_percentage"])
            break

    text = "🏆 <b>PLATFORMA REYTINGI</b> 🌟\n\n"
    if user_pos:
        # mini progress in top 10%?
        top_pct = round((user_pos[0] / total_count) * 100) if total_count else 100
        text += (
            f"┌─────────────────────┐\n"
            f"│  📍 Sizning o'rningiz: <b>{user_pos[0]}-o'rin</b>\n"
            f"│  🎯 Ball: <b>{user_pos[1]}</b>  ({user_pos[2]:.1f}%)\n"
            f"│  👥 Top <b>{top_pct}%</b> da (jami {total_count} ta)\n"
            f"└─────────────────────┘\n\n"
        )
    else:
        text += f"<i>ℹ️ Siz hali reytingda yo'qsiz — birinchi testni ishlang!</i>\n\n"

    text += f"<b>🏅 {start_idx + 1}–{min(start_idx + len(current_page), total_count)} o'rinlar:</b>\n\n"

    if not current_page:
        text += "Hozircha reytingda qatnashchilar yo'q.\n"
    else:
        for idx, s in enumerate(current_page, start=start_idx + 1):
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"<b>{idx}.</b>"
            safe_student = html.escape(f"{s['first_name']} {s['last_name']}".strip() or "Noma'lum")
            safe_school = html.escape(s['school'] or 'Kiritilmagan')
            safe_grade = html.escape(s['grade'] or 'Umumiy')
            is_me = " 👈 <b>(Siz)</b>" if s["user_id"] == user_id else ""
            pct = s['avg_percentage']
            if pct >= 90:
                star = "⭐⭐⭐"
            elif pct >= 70:
                star = "⭐⭐"
            else:
                star = "⭐"
            text += f"{medal} <b>{safe_student}</b>{is_me}\n"
            text += f"   🏫 {safe_school} • 🎯 <b>{s['total_score']}</b> ball {star}\n\n"

    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"ratings:page:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"ratings:page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="📄 PDF reyting", callback_data="ratings:pdf_export"),
        InlineKeyboardButton(text="👥 Guruhlarim", callback_data="ratings:my_groups")
    ])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"ratings:page:{page}")])

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(StateFilter("*"), F.text == "🏆 Reyting")
async def show_ratings_menu(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    result_repo = ResultRepository(session)
    all_students = await result_repo.get_global_leaderboard(limit=1000)

    text, kb = format_paginated_leaderboard(all_students, user.id, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("ratings:page:"))
async def ratings_page_callback(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[2])
    await callback.answer()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    result_repo = ResultRepository(session)
    all_students = await result_repo.get_global_leaderboard(limit=1000)

    user_id = user.id if user else 0
    text, kb = format_paginated_leaderboard(all_students, user_id, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "ratings:refresh_global")
async def refresh_global_rating(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("🔄 Reyting yangilandi!")
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    result_repo = ResultRepository(session)
    all_students = await result_repo.get_global_leaderboard(limit=1000)

    user_id = user.id if user else 0
    text, kb = format_paginated_leaderboard(all_students, user_id, page=1)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "ratings:pdf_export")
async def export_leaderboard_pdf_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("📄 PDF reyting tayyorlanmoqda...")
    result_repo = ResultRepository(session)
    all_students = await result_repo.get_global_leaderboard(limit=2000)

    if not all_students:
        await callback.message.answer("Hozircha reytingda ishtirokchilar yo‘q.")
        return

    pdf_path = ExcelService.export_leaderboard_to_pdf(all_students)
    await callback.message.answer_document(
        document=FSInputFile(path=str(pdf_path), filename="Umumiy_Reyting.pdf"),
        caption=f"🏆 <b>Platformaning barcha ishtirokchilari reytingi (Jami: {len(all_students)} ta)</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "ratings:my_groups")
async def show_my_groups_rating(callback: CallbackQuery, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.")
        return

    group_repo = GroupRepository(session)
    result_repo = ResultRepository(session)

    user_groups = await group_repo.get_user_groups(user.id)
    if not user_groups:
        await callback.answer("ℹ️ Siz hali birorta ham guruhga a’zo emassiz.", show_alert=True)
        return

    await callback.answer()
    for g in user_groups:
        leaderboard = await result_repo.get_group_leaderboard(g.id, limit=50)
        safe_gname = html.escape(g.name)
        text = f"👥 <b>{safe_gname}</b> guruhi reytingi:\n\n"
        if not leaderboard:
            text += "Ushbu guruhda hali natijalar yo‘q."
        else:
            for idx, s in enumerate(leaderboard, start=1):
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
                safe_student = html.escape(f"{s['first_name']} {s['last_name']}".strip() or "Noma'lum")
                text += f"{medal} <b>{safe_student}</b> | 🏆 Ball: <b>{s['total_score']}</b> ({s['avg_percentage']:.1f}%)\n"

        await callback.message.answer(text, parse_mode="HTML")
