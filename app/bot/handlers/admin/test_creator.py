from datetime import datetime, timedelta, timezone
import html
import re
from typing import Optional, Tuple
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, InlineKeyboardButton, InlineKeyboardMarkup, Message, PhotoSize
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_admin_main_keyboard, get_cancel_keyboard
from app.bot.states.admin_states import AdminAddQuestionState, AdminCreateTestState
from app.database.models.test import Question, Test, TestStatus
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.scoring_service import ScoringService
from app.services.test_service import TestService

router = Router(name="admin_test_creator")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

UZB_TZ = timezone(timedelta(hours=5))

MONTHS_MAP = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentabr": 9, "sentyabr": 9, "oktabr": 10, "oktyabr": 10,
    "noyabr": 11, "dekabr": 12
}


def to_uzb_dt(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(UZB_TZ)


def format_schedule_display(start_dt: datetime | None, end_dt: datetime | None) -> str:
    if not start_dt and not end_dt:
        return "♾ Cheklovsiz (Doimiy faol)"

    st_uzb = to_uzb_dt(start_dt)
    et_uzb = to_uzb_dt(end_dt)

    if st_uzb and et_uzb:
        if st_uzb.date() == et_uzb.date():
            return f"📅 {st_uzb.strftime('%d.%m.%Y')} | {st_uzb.strftime('%H:%M')} — {et_uzb.strftime('%H:%M')}"
        else:
            return f"📅 {st_uzb.strftime('%d.%m.%Y %H:%M')} — {et_uzb.strftime('%d.%m.%Y %H:%M')}"
    elif et_uzb:
        return f"📅 {et_uzb.strftime('%d.%m.%Y')} soat {et_uzb.strftime('%H:%M')} gacha"
    elif st_uzb:
        return f"📅 {st_uzb.strftime('%d.%m.%Y %H:%M')} dan boshlanadi"
    return "♾ Cheklovsiz"


def parse_uzb_schedule(text: str) -> Tuple[Optional[datetime], Optional[datetime], TestStatus]:
    raw = text.strip().lower()
    now_uzb = datetime.now(UZB_TZ)
    now_utc = datetime.now(timezone.utc)
    current_year = now_uzb.year

    if raw in ["cheklovsiz", "cheksiz", "yo'q", "yoq", "skip", "o'tkazish", "otkazish", "-", "0"]:
        return None, None, TestStatus.ACTIVE

    clean = raw.replace("dan", "").replace("gacha", "").replace("vaqt", "").strip()

    for m_name, m_num in MONTHS_MAP.items():
        if m_name in clean:
            clean = re.sub(rf"(\d{{1,2}})[-\s]*{m_name}", rf"\1.{m_num:02d}", clean)

    if "ertaga" in clean:
        tom = now_uzb + timedelta(days=1)
        clean = clean.replace("ertaga", tom.strftime("%d.%m"))

    m_full = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})\s+(\d{1,2})[:.](\d{2})\s*[-–—to]+\s*(\d{1,2})[./](\d{1,2})[./](\d{4})\s+(\d{1,2})[:.](\d{2})", clean)
    if m_full:
        d1, mo1, y1, h1, min1, d2, mo2, y2, h2, min2 = map(int, m_full.groups())
        st_uzb = datetime(y1, mo1, d1, h1, min1, 0, tzinfo=UZB_TZ)
        et_uzb = datetime(y2, mo2, d2, h2, min2, 0, tzinfo=UZB_TZ)
        st_utc = st_uzb.astimezone(timezone.utc)
        et_utc = et_uzb.astimezone(timezone.utc)
        status = TestStatus.SCHEDULED if st_utc > now_utc else TestStatus.ACTIVE
        return st_utc, et_utc, status

    m_short_two = re.search(r"(\d{1,2})[./](\d{1,2})\s+(\d{1,2})[:.](\d{2})\s*[-–—to]+\s*(\d{1,2})[./](\d{1,2})\s+(\d{1,2})[:.](\d{2})", clean)
    if m_short_two:
        d1, mo1, h1, min1, d2, mo2, h2, min2 = map(int, m_short_two.groups())
        st_uzb = datetime(current_year, mo1, d1, h1, min1, 0, tzinfo=UZB_TZ)
        et_uzb = datetime(current_year, mo2, d2, h2, min2, 0, tzinfo=UZB_TZ)
        st_utc = st_uzb.astimezone(timezone.utc)
        et_utc = et_uzb.astimezone(timezone.utc)
        status = TestStatus.SCHEDULED if st_utc > now_utc else TestStatus.ACTIVE
        return st_utc, et_utc, status

    m_date_timerange = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\s+(\d{1,2})[:.](\d{2})\s*[-–—to]+\s*(\d{1,2})[:.](\d{2})", clean)
    if m_date_timerange:
        d, mo, y, h1, min1, h2, min2 = m_date_timerange.groups()
        year = int(y) if y else current_year
        st_uzb = datetime(year, int(mo), int(d), int(h1), int(min1), 0, tzinfo=UZB_TZ)
        et_uzb = datetime(year, int(mo), int(d), int(h2), int(min2), 0, tzinfo=UZB_TZ)
        if et_uzb < st_uzb:
            et_uzb += timedelta(days=1)
        st_utc = st_uzb.astimezone(timezone.utc)
        et_utc = et_uzb.astimezone(timezone.utc)
        status = TestStatus.SCHEDULED if st_utc > now_utc else TestStatus.ACTIVE
        return st_utc, et_utc, status

    m_single_date = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\s+(\d{1,2})[:.](\d{2})", clean)
    if m_single_date:
        d, mo, y, h, min_val = m_single_date.groups()
        year = int(y) if y else current_year
        et_uzb = datetime(year, int(mo), int(d), int(h), int(min_val), 0, tzinfo=UZB_TZ)
        et_utc = et_uzb.astimezone(timezone.utc)
        return None, et_utc, TestStatus.ACTIVE

    m_same_day = re.search(r"(\d{1,2})[:.](\d{2})\s*[-–—to]+\s*(\d{1,2})[:.](\d{2})", clean)
    if m_same_day:
        h1, min1, h2, min2 = map(int, m_same_day.groups())
        st_uzb = now_uzb.replace(hour=h1, minute=min1, second=0, microsecond=0)
        et_uzb = now_uzb.replace(hour=h2, minute=min2, second=0, microsecond=0)
        if et_uzb < st_uzb:
            et_uzb += timedelta(days=1)
        st_utc = st_uzb.astimezone(timezone.utc)
        et_utc = et_uzb.astimezone(timezone.utc)
        status = TestStatus.SCHEDULED if st_utc > now_utc else TestStatus.ACTIVE
        return st_utc, et_utc, status

    m_time_only = re.match(r"^(\d{1,2})[:.](\d{2})$", clean)
    if m_time_only:
        h, min_val = map(int, m_time_only.groups())
        target_uzb = now_uzb.replace(hour=h, minute=min_val, second=0, microsecond=0)
        if target_uzb < now_uzb:
            target_uzb += timedelta(days=1)
        et_utc = target_uzb.astimezone(timezone.utc)
        return None, et_utc, TestStatus.ACTIVE

    if "soat" in clean or "hour" in clean:
        nums = re.findall(r"\d+", clean)
        hrs = int(nums[0]) if nums else 1
        return None, (now_uzb + timedelta(hours=hrs)).astimezone(timezone.utc), TestStatus.ACTIVE
    if "kun" in clean or "day" in clean:
        nums = re.findall(r"\d+", clean)
        days = int(nums[0]) if nums else 1
        return None, (now_uzb + timedelta(days=days)).astimezone(timezone.utc), TestStatus.ACTIVE

    return None, None, TestStatus.ACTIVE


def build_test_created_preview(test: Test, start_dt: Optional[datetime], end_dt: Optional[datetime], status: TestStatus, bot_username: str) -> str:
    share_link = f"https://t.me/{bot_username}?start=test_{test.code}"
    file_badge = "✅ Mavjud" if test.file_id else "Yo'q"
    sched_info = format_schedule_display(start_dt, end_dt)

    channel_post_template = (
        f"📝 \"{test.title}\" testi boshlandi!\n\n"
        f"🔑 Test kodi: {test.code}\n"
        f"❓ Savollar soni: {test.total_questions} ta\n"
        f"⏱ Test ishlash vaqti: {test.time_limit_minutes} daqiqa\n\n"
        f"👉 Javoblarni @{bot_username} ga quyidagi tartibda yuboring:\n"
        f"{test.code} abcdabcd...\n\n"
        f"🔗 1-bosishda testni ochish:\n"
        f"{share_link}"
    )

    return (
        f"🎉 <b>Yangi Test Muvaffaqiyatli Yaratildi!</b>\n\n"
        f"📝 <b>Nomi:</b> {html.escape(test.title)}\n"
        f"🔑 <b>Test kodi:</b> <code>{test.code}</code> <i>(nusxalash uchun bosing)</i>\n"
        f"❓ <b>Savollar soni:</b> {test.total_questions} ta\n"
        f"🔑 <b>Kalitlar:</b> <code>{test.answer_key}</code> <i>(nusxalash uchun bosing)</i>\n"
        f"⏱ <b>Test ishlash vaqti:</b> {test.time_limit_minutes} daqiqa\n"
        f"⏰ <b>Faollik muddati:</b> {sched_info}\n"
        f"📎 <b>Test fayli:</b> {file_badge}\n"
        f"🟢 <b>Holati:</b> {'Jadval bo‘yicha' if status == TestStatus.SCHEDULED else 'Faol'}\n\n"
        f"🔗 <b>O‘quvchilar uchun to‘g‘ridan-to‘g‘ri havola:</b>\n"
        f"<code>{share_link}</code> <i>(nusxalash uchun bosing)</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>Kanalga tashlash uchun tayyor e'lon (nusxalash uchun ustiga bosing):</b>\n"
        f"<code>{html.escape(channel_post_template)}</code>"
    )


# ⚡ Fast Quick Creator: /fast_test Nomi | Kalitlar | Vaqt
@router.message(Command("fast_test", "tezkor_test"))
async def fast_test_creator_command(message: Message, session: AsyncSession):
    raw_args = message.text.replace("/fast_test", "").replace("/tezkor_test", "").strip()
    if not raw_args or "|" not in raw_args:
        await message.answer(
            "⚡ <b>Tezkor Test Yaratish (3 soniyada!):</b>\n\n"
            "Format:\n"
            "<code>/fast_test &lt;Test Nomi&gt; | &lt;Kalitlar&gt; | &lt;Vaqt(daqiqa)&gt;</code>\n\n"
            "Misol:\n"
            "<code>/fast_test Fizika 9-sinf ChSB | ABCDACBDABCD | 45</code>",
            parse_mode="HTML"
        )
        return

    parts = [p.strip() for p in raw_args.split("|")]
    title = parts[0]
    raw_keys = parts[1] if len(parts) > 1 else ""
    try:
        minutes = int(parts[2]) if len(parts) > 2 else 30
    except ValueError:
        minutes = 30

    parsed = ScoringService.parse_quick_answers(raw_keys)
    if not parsed:
        await message.answer("❌ Kalitlar aniqlanmadi. Iltimos, <code>ABCDACBD...</code> yoki <code>1-A 2-B 3-C</code> formatida yozing.", parse_mode="HTML")
        return

    key_str = "".join(parsed[i] for i in sorted(parsed.keys()))
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    test_service = TestService(session)

    test = await test_service.create_test(
        title=title,
        answer_key=key_str,
        total_questions=len(parsed),
        author_id=user.id if user else None,
        time_limit_minutes=minutes,
        status=TestStatus.ACTIVE
    )

    try:
        bot_user = await message.bot.get_me()
        bot_username = bot_user.username
    except Exception:
        bot_username = "tekshiruv2_bot"

    preview = build_test_created_preview(test, None, None, TestStatus.ACTIVE, bot_username)
    await message.answer(preview, parse_mode="HTML")


# 1. Start Test Creation: Nomini kiritish
@router.message(F.text.in_(["➕ Yangi test", "➕ Test yaratish"]))
async def start_admin_create_test(message: Message, state: FSMContext):
    await state.set_state(AdminCreateTestState.waiting_for_title)
    await message.answer(
        "➕ <b>Yangi Test Yaratish</b>\n\n"
        "1️⃣ <b>Test nomini kiriting:</b>\n"
        "(Masalan: <code>Matematika 10-sinf ChSB</code> yoki <code>IELTS Reading Mock 1</code>)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminCreateTestState.waiting_for_title)
async def process_test_title(message: Message, state: FSMContext):
    if message.text in ["❌ Bekor qilish", "🏠 Bosh menyu"]:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    title = message.text.strip()
    if len(title) < 2:
        await message.answer("❌ Test nomi juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(title=title)
    await state.set_state(AdminCreateTestState.waiting_for_code)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Avtomatik kod generatsiya qilish", callback_data="adm_auto_code")]
        ]
    )

    await message.answer(
        "2️⃣ <b>Test kodini kiriting:</b>\n"
        "(Masalan: <code>TEST-101</code>, <code>MATEM-9</code>, <code>CHSB-2026</code>)\n\n"
        "Yoki avtomatik kod olish uchun tugmani bosing:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_auto_code")
async def auto_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🎲 Avtomatik kod tanlandi")
    auto_code = TestService.generate_test_code()
    await state.update_data(code=auto_code)
    await state.set_state(AdminCreateTestState.waiting_for_file)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Faylsiz davom etish", callback_data="adm_skip_file")]
        ]
    )

    await callback.message.answer(
        f"✅ Test kodi: <code>{auto_code}</code>\n\n"
        "3️⃣ <b>Test faylini (PDF yoki Rasm) yuboring:</b>\n"
        "O‘quvchilar test kodini kiritganda ushbu fayl ularga yuboriladi.",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.message(AdminCreateTestState.waiting_for_code)
async def process_custom_code(message: Message, state: FSMContext):
    if message.text in ["❌ Bekor qilish", "🏠 Bosh menyu"]:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    code = message.text.strip().upper()
    await state.update_data(code=code)
    await state.set_state(AdminCreateTestState.waiting_for_file)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Faylsiz davom etish", callback_data="adm_skip_file")]
        ]
    )

    await message.answer(
        f"✅ Test kodi: <code>{code}</code>\n\n"
        "3️⃣ <b>Test faylini (PDF yoki Rasm) yuboring:</b>\n"
        "O‘quvchilar test kodini kiritganda ushbu fayl ularga yuboriladi.",
        reply_markup=kb,
        parse_mode="HTML"
    )


# 3. Test fayli (PDF yoki Rasm yoki Skip)
@router.message(AdminCreateTestState.waiting_for_file, F.document)
async def process_test_document(message: Message, state: FSMContext):
    file_id = message.document.file_id
    await state.update_data(file_id=file_id, file_type="document")
    await state.set_state(AdminCreateTestState.waiting_for_answer_key)
    await message.answer(
        "✅ Test PDF fayli qabul qilindi!\n\n"
        "4️⃣ <b>Javoblar kalitini kiriting:</b>\n"
        "Formatlar:\n"
        "• Harflar ketma-ketligi: <code>ABCDACBD...</code>\n"
        "• Yoki raqamlangan: <code>1-A 2-B 3-C 4-D ...</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminCreateTestState.waiting_for_file, F.photo)
async def process_test_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(file_id=file_id, file_type="photo")
    await state.set_state(AdminCreateTestState.waiting_for_answer_key)
    await message.answer(
        "✅ Test rasmi qabul qilindi!\n\n"
        "4️⃣ <b>Javoblar kalitini kiriting:</b>\n"
        "Formatlar:\n"
        "• Harflar ketma-ketligi: <code>ABCDACBD...</code>\n"
        "• Yoki raqamlangan: <code>1-A 2-B 3-C 4-D ...</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_skip_file")
async def skip_file_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Fayl o'tkazib yuborildi")
    await state.update_data(file_id=None, file_type=None)
    await state.set_state(AdminCreateTestState.waiting_for_answer_key)
    await callback.message.answer(
        "4️⃣ <b>Javoblar kalitini kiriting:</b>\n"
        "Formatlar:\n"
        "• Harflar ketma-ketligi: <code>ABCDACBD...</code>\n"
        "• Yoki raqamlangan: <code>1-A 2-B 3-C 4-D ...</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


# 4. Kalitlarni qabul qilish
@router.message(AdminCreateTestState.waiting_for_answer_key)
async def process_answer_key(message: Message, state: FSMContext):
    if message.text in ["❌ Bekor qilish", "🏠 Bosh menyu"]:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    raw_key = message.text.strip()
    parsed = ScoringService.parse_quick_answers(raw_key)

    if not parsed:
        await message.answer("❌ Kalitlar aniqlanmadi. Iltimos, <code>ABCDACBD...</code> yoki <code>1-A 2-B 3-C</code> formatida kiriting:", parse_mode="HTML")
        return

    key_str = "".join(parsed[i] for i in sorted(parsed.keys()))
    total_q = len(parsed)

    await state.update_data(answer_key=key_str, total_questions=total_q)
    await state.set_state(AdminCreateTestState.waiting_for_time_limit)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏱ 15 daqiqa", callback_data="adm_timer:15"),
                InlineKeyboardButton(text="⏱ 30 daqiqa", callback_data="adm_timer:30")
            ],
            [
                InlineKeyboardButton(text="⏱ 45 daqiqa", callback_data="adm_timer:45"),
                InlineKeyboardButton(text="⏱ 60 daqiqa", callback_data="adm_timer:60")
            ]
        ]
    )

    await message.answer(
        f"✅ <b>{total_q} ta savol kaliti saqlandi:</b> <code>{key_str}</code>\n\n"
        "5️⃣ <b>Testni yechish uchun vaqtni belgilang:</b>\n"
        "(Tugmani bosing yoki o‘zingiz daqiqa sonini yozing, masalan: <code>40</code>):",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_timer:"))
async def timer_button_callback(callback: CallbackQuery, state: FSMContext):
    mins = int(callback.data.split(":")[1])
    await callback.answer(f"⏱ {mins} daqiqa tanlandi")
    await state.update_data(time_limit=mins)
    await state.set_state(AdminCreateTestState.waiting_for_schedule)
    await ask_schedule_step(callback.message, mins)


# 5. Vaqt chegarasi (matn orqali)
@router.message(AdminCreateTestState.waiting_for_time_limit)
async def process_test_time_limit(message: Message, state: FSMContext):
    if message.text in ["❌ Bekor qilish", "🏠 Bosh menyu"]:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    try:
        minutes = int(message.text.strip())
        if minutes <= 0:
            minutes = 30
    except ValueError:
        minutes = 30

    await state.update_data(time_limit=minutes)
    await state.set_state(AdminCreateTestState.waiting_for_schedule)
    await ask_schedule_step(message, minutes)


async def ask_schedule_step(target: Message, minutes: int):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾ Cheklovsiz (Doimiy faol)", callback_data="adm_sched_dur:unlimited")],
            [
                InlineKeyboardButton(text="⏱ 1 soat", callback_data="adm_sched_dur:1h"),
                InlineKeyboardButton(text="⏱ 2 soat", callback_data="adm_sched_dur:2h"),
                InlineKeyboardButton(text="⏱ 3 soat", callback_data="adm_sched_dur:3h")
            ],
            [
                InlineKeyboardButton(text="🌙 Bugun 22:00 gacha", callback_data="adm_sched_dur:today_22"),
                InlineKeyboardButton(text="📅 Ertaga 20:00 gacha", callback_data="adm_sched_dur:tomorrow_20")
            ],
            [
                InlineKeyboardButton(text="🗓 3 kun faol", callback_data="adm_sched_dur:3d"),
                InlineKeyboardButton(text="🗓 7 kun faol", callback_data="adm_sched_dur:7d")
            ]
        ]
    )

    text = (
        f"⏱ Test ishlash vaqti: <b>{minutes} daqiqa</b> belgilandi.\n\n"
        "6️⃣ <b>Test qachongacha faol bo‘lsin (Faollik muddati)?</b>\n\n"
        "Tugmalardan birini bosing yoki o‘zingiz yozing:\n\n"
        "💡 <b>Kiritish namunalari:</b>\n"
        "• <code>25.08.2026 09:00 - 25.08.2026 18:00</code> (to‘liq sana va soat)\n"
        "• <code>25.08 14:00 - 18:00</code> (sana va soat oralig‘i)\n"
        "• <code>Ertaga 19:00 - 21:00</code>\n"
        "• <code>25-avgust 20:00</code>\n"
        "• <code>19:00 - 20:00</code> (bugun uchun)\n"
        "• <code>cheklovsiz</code> (doimiy ochiq)"
    )
    await target.answer(text, reply_markup=kb, parse_mode="HTML")


# 6. Boshlanish va tugash vaqti / Tugmalar orqali
@router.callback_query(F.data.startswith("adm_sched_dur:") | (F.data == "adm_sched_skip"))
async def schedule_duration_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    dur_code = callback.data.split(":")[1] if ":" in callback.data else "unlimited"
    await callback.answer("✅ Test saqlanmoqda...")
    data = await state.get_data()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    test_service = TestService(session)

    now_uzb = datetime.now(UZB_TZ)
    start_dt = None
    end_dt = None
    status = TestStatus.ACTIVE

    if dur_code == "unlimited":
        start_dt = None
        end_dt = None
    elif dur_code == "1h":
        end_uzb = now_uzb + timedelta(hours=1)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "2h":
        end_uzb = now_uzb + timedelta(hours=2)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "3h":
        end_uzb = now_uzb + timedelta(hours=3)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "today_22":
        end_uzb = now_uzb.replace(hour=22, minute=0, second=0, microsecond=0)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "tomorrow_20":
        end_uzb = (now_uzb + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "3d":
        end_uzb = now_uzb + timedelta(days=3)
        end_dt = end_uzb.astimezone(timezone.utc)
    elif dur_code == "7d":
        end_uzb = now_uzb + timedelta(days=7)
        end_dt = end_uzb.astimezone(timezone.utc)

    title = data.get("title", "Yangi Test")
    test = await test_service.create_test(
        title=title,
        code=data.get("code"),
        file_id=data.get("file_id"),
        file_type=data.get("file_type"),
        answer_key=data.get("answer_key"),
        total_questions=data.get("total_questions", 0),
        author_id=user.id if user else None,
        time_limit_minutes=data.get("time_limit", 30),
        start_time=start_dt,
        end_time=end_dt,
        status=status
    )

    await state.clear()

    try:
        bot_user = await callback.bot.get_me()
        bot_username = bot_user.username
    except Exception:
        bot_username = "tekshiruv2_bot"

    preview = build_test_created_preview(test, start_dt, end_dt, status, bot_username)

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(preview, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


# 6. Muddat (matn orqali kiritilganda)
@router.message(AdminCreateTestState.waiting_for_schedule)
async def process_schedule_input(message: Message, state: FSMContext, session: AsyncSession):
    if message.text in ["❌ Bekor qilish", "🏠 Bosh menyu"]:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    data = await state.get_data()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    test_service = TestService(session)

    start_dt, end_dt, status = parse_uzb_schedule(message.text)

    title = data.get("title", "Yangi Test")
    test = await test_service.create_test(
        title=title,
        code=data.get("code"),
        file_id=data.get("file_id"),
        file_type=data.get("file_type"),
        answer_key=data.get("answer_key"),
        total_questions=data.get("total_questions", 0),
        author_id=user.id if user else None,
        time_limit_minutes=data.get("time_limit", 30),
        start_time=start_dt,
        end_time=end_dt,
        status=status
    )

    await state.clear()

    try:
        bot_user = await message.bot.get_me()
        bot_username = bot_user.username
    except Exception:
        bot_username = "tekshiruv2_bot"

    preview = build_test_created_preview(test, start_dt, end_dt, status, bot_username)
    await message.answer(preview, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
