import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminBlockUserState, AdminStudentSearchState
from app.database.models.user import User
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.user_repo import UserRepository
from app.services.excel_service import ExcelService

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

router = Router(name="admin_students_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(StateFilter("*"), F.text.in_(["👥 O‘quvchilar", "👥 O'quvchilar", "O‘quvchilar", "O'quvchilar"]))
async def list_students_menu(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    users = await user_repo.get_recent_users(limit=15)
    total_count = await user_repo.get_total_users_count()

    if not users:
        await message.answer("👥 O‘quvchilar ro‘yxati hozircha bo‘sh.")
        return

    text = f"👥 O‘quvchilar ro‘yxati (Jami: {total_count} ta):\n\n"
    for idx, u in enumerate(users, start=1):
        status = "🚫 Bloklangan" if u.is_blocked else "🟢 Faol"
        safe_name = html.escape(u.full_name or "Noma'lum")
        safe_username = f"@{html.escape(u.username)}" if u.username else "yo‘q"
        phone_str = f"📞 <code>{html.escape(u.phone_number)}</code>" if u.phone_number else "📞 —"
        meta_str = f"({html.escape(u.school or '')} | {html.escape(u.grade or '')})" if (u.school or u.grade) else ""
        
        text += (
            f"{idx}. {safe_name} | {safe_username}\n"
            f"   🆔 ID: <code>{u.telegram_id}</code> | {phone_str}\n"
            f"   📍 {meta_str} [{status}]\n\n"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔎 Qidirish (Ism/Tel/ID)", callback_data="adm_search_user"),
                InlineKeyboardButton(text="🚫 Bloklash/Ochish", callback_data="adm_block_prompt")
            ],
            [
                InlineKeyboardButton(text="📥 Excel (.xlsx) export", callback_data="adm_export_users_excel"),
                InlineKeyboardButton(text="📄 PDF ro‘yxat export", callback_data="adm_export_users_pdf")
            ]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "🔎 Qidirish")
@router.callback_query(F.data == "adm_search_user")
async def start_student_search(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AdminStudentSearchState.waiting_for_query)
    msg_text = (
        "🔎 O'quvchini qidirish:\n\n"
        "Ism, familiya, username, telefon raqam yoki Telegram ID kiriting:"
    )
    if isinstance(event, Message):
        await event.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        await event.answer()
        await event.message.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(AdminStudentSearchState.waiting_for_query)
async def process_student_search(message: Message, state: FSMContext, session: AsyncSession):
    query = message.text.strip()
    user_repo = UserRepository(session)

    # Check if numeric telegram id
    if query.isdigit():
        user = await user_repo.get_by_telegram_id(int(query))
        users = [user] if user else []
    else:
        users = await user_repo.search_users(query)

    if not users:
        await message.answer("❌ Hech qanday o'quvchi topilmadi. Qayta urinib ko'ring:", reply_markup=get_cancel_keyboard())
        return

    await state.clear()
    await message.answer(f"🔎 Qidiruv natijalari ({len(users)} ta):", parse_mode="HTML")

    for u in users:
        block_text = "🟢 Blokdan chiqarish" if u.is_blocked else "🚫 Bloklash"
        safe_phone = f"<code>{html.escape(u.phone_number)}</code>" if u.phone_number else "—"
        safe_name = html.escape(u.full_name) if u.full_name else "Noma'lum"
        safe_uname = html.escape(u.username) if u.username else "mavjud_emas"
        safe_sch = html.escape(u.school) if u.school else "—"
        safe_grd = html.escape(u.grade) if u.grade else "—"
        card = (
            f"👤 O'quvchi: {safe_name}\n"
            f"🆔 Telegram ID: <code>{u.telegram_id}</code>\n"
            f"🔗 Username: @{safe_uname}\n"
            f"📞 Telefon: {safe_phone}\n"
            f"🏫 Maktab: {safe_sch}\n"
            f"🎓 Sinf: {safe_grd}\n"
            f"🔒 Holati: {'🚫 Bloklangan' if u.is_blocked else '🟢 Faol'}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Natijalar tarixi", callback_data=f"adm_user_results:{u.id}")],
                [InlineKeyboardButton(text=block_text, callback_data=f"adm_toggle_block:{u.id}")]
            ]
        )
        await message.answer(card, reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "🚫 O‘quvchini bloklash")
@router.callback_query(F.data == "adm_block_prompt")
async def block_user_prompt(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AdminBlockUserState.waiting_for_user_id)
    msg_text = "🚫 Bloklash/blokdan ochish uchun o'quvchi Telegram ID yoki tizim ID sini kiriting:"
    if isinstance(event, Message):
        await event.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        await event.answer()
        await event.message.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(AdminBlockUserState.waiting_for_user_id)
async def process_block_input(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    user_repo = UserRepository(session)

    user = None
    if val.isdigit():
        user = await user_repo.get_by_telegram_id(int(val))
        if not user:
            user = await user_repo.get_by_id(int(val))

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Qaytadan kiriting:", reply_markup=get_cancel_keyboard())
        return

    # Toggle block
    new_blocked = not user.is_blocked
    await user_repo.set_blocked(
        user_id=user.id,
        is_blocked=new_blocked,
        blocked_by=message.from_user.id,
        reason="Admin qarori"
    )

    await state.clear()
    safe_fn = html.escape(user.full_name or "Foydalanuvchi")
    status_str = "bloklandi 🚫" if new_blocked else "blokdan ochildi 🟢"
    await message.answer(f"✅ <b>{safe_fn}</b> muvaffaqiyatli {status_str}!", parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_toggle_block:"))
async def toggle_block_callback(callback: CallbackQuery, session: AsyncSession):
    user_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    new_blocked = not user.is_blocked
    await user_repo.set_blocked(
        user_id=user.id,
        is_blocked=new_blocked,
        blocked_by=callback.from_user.id
    )

    status_str = "bloklandi" if new_blocked else "blokdan ochildi"
    await callback.answer(f"Foydalanuvchi {status_str}!")
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_user_results:"))
async def view_user_results_history(callback: CallbackQuery, session: AsyncSession):
    user_id = int(callback.data.split(":")[1])
    result_repo = ResultRepository(session)
    user_repo = UserRepository(session)

    user = await user_repo.get_by_id(user_id)
    results = await result_repo.get_user_results(user_id, limit=5)

    await callback.answer()
    safe_fn = html.escape(user.full_name or "Foydalanuvchi") if user else "Foydalanuvchi"
    if not results:
        await callback.message.answer(f"👤 <b>{safe_fn}</b> da ishlangan test natijalari yo'q.", parse_mode="HTML")
        return

    text = f"📊 <b>{safe_fn}</b> — Natijalar tarixi:\n\n"
    for r in results:
        test_title = r.test.title if r.test else "Test"
        text += (
            f"📝 {test_title} ({r.created_at.strftime('%d.%m.%Y')})\n"
            f"   Natija: {r.percentage}% | Ball: {r.total_score}/{r.max_score} | To'g'ri: {r.correct_count}\n"
        )

    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "adm_export_users_excel")
async def export_users_excel_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("📥 Excel fayl tayyorlanmoqda...")
    user_repo = UserRepository(session)
    users = await user_repo.get_all(limit=5000)

    if not users:
        await callback.message.answer("Bazada o‘quvchilar mavjud emas.")
        return

    excel_path = ExcelService.export_users_to_excel(users)
    await callback.message.answer_document(
        document=FSInputFile(path=str(excel_path), filename="Barcha_oquvchilar.xlsx"),
        caption=f"📁 Jami <b>{len(users)} ta</b> o‘quvchining to‘liq Excel jadvali.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_export_users_pdf")
async def export_users_pdf_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("📄 PDF ro‘yxat tayyorlanmoqda...")
    user_repo = UserRepository(session)
    users = await user_repo.get_all(limit=5000)

    if not users:
        await callback.message.answer("Bazada o‘quvchilar mavjud emas.")
        return

    pdf_path = ExcelService.export_users_to_pdf(users)
    await callback.message.answer_document(
        document=FSInputFile(path=str(pdf_path), filename="Barcha_oquvchilar_royxati.pdf"),
        caption=f"📄 Jami <b>{len(users)} ta</b> o‘quvchining to‘liq rasmiy PDF ro‘yxati.",
        parse_mode="HTML"
    )
