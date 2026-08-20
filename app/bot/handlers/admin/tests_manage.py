import html
from datetime import datetime, timedelta, timezone
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminScheduleState, AdminSetPasswordState
from app.database.models.test import Test, TestStatus
from app.database.repositories.channel_repo import ChannelRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.services.scoring_service import ScoringService
from app.services.test_service import TestService

router = Router(name="admin_tests_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


UZB_TZ = timezone(timedelta(hours=5))


def to_uzb_dt(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UZB_TZ)


def format_admin_test_card(t: Test) -> str:
    status_icon = "🟢 Faol" if t.status == TestStatus.ACTIVE else "🟡 Qoralama" if t.status == TestStatus.DRAFT else "🕒 Jadval" if t.status == TestStatus.SCHEDULED else "🔴 Yopilgan"
    st_uzb = to_uzb_dt(t.start_time)
    et_uzb = to_uzb_dt(t.end_time)
    start_str = st_uzb.strftime("%d.%m.%Y %H:%M") if st_uzb else "-"
    end_str = et_uzb.strftime("%d.%m.%Y %H:%M") if et_uzb else "-"
    pass_str = t.password or "Yo'q"
    attempts_str = "Faqat 1 marta 🔒" if (t.max_attempts and t.max_attempts == 1) else "Cheksiz 🔓"
    q_count = t.total_questions if t.total_questions > 0 else (len(t.test_questions) if t.test_questions else 0)
    safe_title = html.escape(t.title or "Test")
    safe_code = html.escape(t.code or "")

    return (
        f"📝 <b>{safe_title}</b> (ID: <code>{t.id}</code>)\n\n"
        f"🔑 <b>Test kodi:</b> <code>{safe_code}</code>\n"
        f"❓ <b>Savollar soni:</b> {q_count} ta\n"
        f"📊 <b>Holati:</b> {status_icon}\n"
        f"🔒 <b>Qayta topshirish:</b> {attempts_str}\n"
        f"🔐 <b>Parol:</b> {html.escape(pass_str)}\n"
        f"📅 <b>Boshlanish:</b> {start_str} | <b>Tugash:</b> {end_str}\n"
        f"⏱ <b>Vaqt:</b> {t.time_limit_minutes} daqiqa"
    )


def get_admin_test_keyboard(test: Test, page: int = 1) -> InlineKeyboardMarkup:
    attempts_btn_text = "🔓 Qayta topshirish: Cheksiz qilish" if (test.max_attempts and test.max_attempts == 1) else "🔒 Qayta topshirish: 1 marta qilish"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Natijalarni e'lon qilish", callback_data=f"adm_pub_res:{test.id}"),
                InlineKeyboardButton(text="📥 Excel yuklash", callback_data=f"adm_import_xl:{test.id}")
            ],
            [
                InlineKeyboardButton(text=attempts_btn_text, callback_data=f"adm_toggle_att:{test.id}:{page}")
            ],
            [
                InlineKeyboardButton(text="🔄 Nusxalash", callback_data=f"adm_clone:{test.id}"),
                InlineKeyboardButton(text="⏰ Jadval", callback_data=f"adm_sched:{test.id}"),
                InlineKeyboardButton(text="🔐 Parol", callback_data=f"adm_pass:{test.id}")
            ],
            [
                InlineKeyboardButton(text="🟢 Faol qilish", callback_data=f"adm_set_status:{test.id}:active"),
                InlineKeyboardButton(text="⛔ Yopish", callback_data=f"adm_set_status:{test.id}:finished"),
                InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"adm_del:{test.id}")
            ],
            [
                InlineKeyboardButton(text="◀️ Barcha testlar ro‘yxatiga qaytish", callback_data=f"adm_tests_page:{page}")
            ]
        ]
    )


def build_admin_tests_page(tests: list[Test], page: int = 1, page_size: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    total_tests = len(tests)
    total_pages = max(1, (total_tests + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    current_page_tests = tests[start_idx:start_idx + page_size]

    text = f"📝 <b>Testlar Boshqaruvi</b> (Jami: {total_tests} ta):\n\n"
    buttons = []

    for idx, t in enumerate(current_page_tests, start=start_idx + 1):
        status_icon = "🟢" if t.status == TestStatus.ACTIVE else "🟡" if t.status == TestStatus.DRAFT else "🕒" if t.status == TestStatus.SCHEDULED else "🔴"
        safe_title = html.escape(t.title or "Test")
        safe_code = html.escape(t.code or "")
        q_count = t.total_questions if t.total_questions > 0 else (len(t.test_questions) if t.test_questions else 0)

        text += (
            f"{idx}. {status_icon} <b>{safe_title}</b> (<code>{safe_code}</code>)\n"
            f"   ❓ {q_count} ta savol | ⏱ {t.time_limit_minutes} daq | ID: {t.id}\n\n"
        )
        short_name = (t.title[:18] + "..") if len(t.title or "") > 18 else (t.title or "Test")
        buttons.append([InlineKeyboardButton(text=f"⚙️ {idx}. {short_name} ({t.code})", callback_data=f"adm_open_test:{t.id}:{page}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"adm_tests_page:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"adm_tests_page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(StateFilter("*"), F.text.in_(["📝 Testlar boshqaruvi", "Testlar boshqaruvi"]))
async def list_admin_tests_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    test_repo = TestRepository(session)
    tests = await test_repo.get_recent_tests(limit=50)

    if not tests:
        await message.answer("Bazada hozircha testlar mavjud emas. '➕ Yangi test' tugmasi orqali test yarating.")
        return

    text, kb = build_admin_tests_page(tests, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_tests_page:"))
async def admin_tests_page_callback(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    tests = await test_repo.get_recent_tests(limit=50)

    if not tests:
        await callback.answer("Bazada testlar mavjud emas.", show_alert=True)
        return

    text, kb = build_admin_tests_page(tests, page=page)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_open_test:"))
async def admin_open_test_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    test_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    card = format_admin_test_card(test)
    kb = get_admin_test_keyboard(test, page=page)

    await callback.answer()
    try:
        await callback.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Feature 5: Toggle Max Attempts (1 marta vs Cheksiz)
@router.callback_query(F.data.startswith("adm_toggle_att:"))
async def toggle_attempts_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    test_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    if test.max_attempts and test.max_attempts == 1:
        test.max_attempts = 0  # Unlimited
        msg = "🔓 Ushbu test uchun cheksiz topshirish yoqildi!"
    else:
        test.max_attempts = 1  # 1 attempt only
        msg = "🔒 Ushbu test uchun faqat 1 marta topshirish cheklovi o‘rnatildi!"

    await session.commit()
    await callback.answer(msg, show_alert=True)

    card = format_admin_test_card(test)
    kb = get_admin_test_keyboard(test, page=page)
    try:
        await callback.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Feature 3: Leaderboard Channel Report Generator
@router.callback_query(F.data.startswith("adm_pub_res:"))
async def publish_test_results_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    scoring_service = ScoringService(session)
    channel_repo = ChannelRepository(session)

    leaderboard_text = await scoring_service.generate_channel_leaderboard_text(test_id, limit=20)
    channels = await channel_repo.get_active_channels()

    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch.title} ga yuborish", callback_data=f"send_res_ch:{test_id}:{ch.channel_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Ortga", callback_data=f"adm_open_test:{test_id}:1")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.answer()
    await callback.message.answer(leaderboard_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("send_res_ch:"))
async def send_results_to_channel(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    parts = callback.data.split(":")
    test_id = int(parts[1])
    channel_target = parts[2]

    scoring_service = ScoringService(session)
    leaderboard_text = await scoring_service.generate_channel_leaderboard_text(test_id, limit=25)

    try:
        chat_id = channel_target
        if not (chat_id.startswith("@") or chat_id.startswith("-100")) and chat_id.isdigit():
            chat_id = int(chat_id)
        await bot.send_message(chat_id=chat_id, text=leaderboard_text, parse_mode="HTML")
        await callback.answer("✅ Natijalar kanalga muvaffaqiyatli e'lon qilindi!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: Bot ushbu kanalda admin bo'lishi kerak.", show_alert=True)


@router.callback_query(F.data.startswith("adm_set_status:"))
async def change_status_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    test_id = int(parts[1])
    new_status = parts[2]

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if test:
        test.status = TestStatus(new_status)
        await session.commit()
        status_name = "Faol" if new_status == "active" else "Yopilgan"
        await callback.answer(f"✅ Test holati: {status_name}")
        card = format_admin_test_card(test)
        kb = get_admin_test_keyboard(test)
        try:
            await callback.message.edit_text(card, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data.startswith("adm_del:"))
async def delete_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    await test_repo.delete_by_id(test_id)
    await session.commit()
    await callback.answer("🗑 Test muvaffaqiyatli o'chirildi.", show_alert=True)

    tests = await test_repo.get_recent_tests(limit=50)
    text, kb = build_admin_tests_page(tests, page=1)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_clone:"))
async def clone_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_service = TestService(session)
    cloned = await test_service.duplicate_test(test_id)
    await session.commit()
    if cloned:
        await callback.answer(f"✅ Nusxa yaratildi: {cloned.code}", show_alert=True)
    else:
        await callback.answer("Nusxalashda xatolik yuz berdi.", show_alert=True)

    test_repo = TestRepository(session)
    tests = await test_repo.get_recent_tests(limit=50)
    text, kb = build_admin_tests_page(tests, page=1)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_pass:"))
async def start_set_password(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await state.update_data(target_test_id=test_id)
    await state.set_state(AdminSetPasswordState.waiting_for_password)
    await callback.answer()
    await callback.message.answer(
        "🔐 <b>Test uchun yangi parol kiriting:</b>\n"
        "(Parolni o‘chirish uchun <code>0</code> yoki <code>yo'q</code> deb yozing)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminSetPasswordState.waiting_for_password)
async def process_password_input(message: Message, state: FSMContext, session: AsyncSession):
    pw = message.text.strip()
    data = await state.get_data()
    test_id = data.get("target_test_id")

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if test:
        if pw in ["0", "yoq", "yo'q", "none"]:
            test.password = None
            msg = "🔓 Test paroli olib tashlandi."
        else:
            test.password = pw
            msg = f"🔐 Test paroli <code>{html.escape(pw)}</code> qilib o‘rnatildi."
        await session.commit()
        await state.clear()
        await message.answer(msg, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_sched:"))
async def start_schedule_test(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await state.update_data(target_test_id=test_id)
    await state.set_state(AdminScheduleState.waiting_for_dates)
    await callback.answer()
    await callback.message.answer(
        "⏰ <b>Testning boshlanish va tugash vaqtini kiriting:</b>\n\n"
        "Format: <code>DD.MM.YYYY HH:MM - DD.MM.YYYY HH:MM</code>\n"
        "Misol: <code>21.08.2026 09:00 - 21.08.2026 21:00</code>\n\n"
        "(Cheklovni olib tashlash uchun <code>0</code> deb yozing)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminScheduleState.waiting_for_dates)
async def process_schedule_dates(message: Message, state: FSMContext, session: AsyncSession):
    raw = message.text.strip()
    data = await state.get_data()
    test_id = data.get("target_test_id")

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if not test:
        await state.clear()
        await message.answer("Test topilmadi.")
        return

    if raw == "0":
        test.start_time = None
        test.end_time = None
        test.status = TestStatus.ACTIVE
        await session.commit()
        await state.clear()
        await message.answer("✅ Vaqt cheklovlari olib tashlandi, test doimiy faol!")
        return

    try:
        parts = raw.split("-")
        st_parsed = datetime.strptime(parts[0].strip(), "%d.%m.%Y %H:%M").replace(tzinfo=UZB_TZ)
        et_parsed = datetime.strptime(parts[1].strip(), "%d.%m.%Y %H:%M").replace(tzinfo=UZB_TZ)

        test.start_time = st_parsed.astimezone(timezone.utc)
        test.end_time = et_parsed.astimezone(timezone.utc)
        test.status = TestStatus.SCHEDULED
        await session.commit()
        await state.clear()
        await message.answer(f"⏰ Test jadvali saqlandi: {raw}", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Noto'g'ri format. Iltimos: <code>DD.MM.YYYY HH:MM - DD.MM.YYYY HH:MM</code> ko'rinishida kiriting:")
