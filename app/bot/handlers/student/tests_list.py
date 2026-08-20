import html
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.inline_keyboards import get_test_item_keyboard
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.student_states import QuickCheckState, TestByCodeState
from app.database.models.test import Test, TestStatus
from app.database.repositories.test_repo import SubjectRepository, TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.test_service import TestService

router = Router(name="student_tests_list")


def format_test_card(test: Test, is_saved: bool = False) -> str:
    subj_name = test.subject.name if test.subject else "Umumiy"
    q_count = test.total_questions if test.total_questions > 0 else (len(test.test_questions) if test.test_questions else 0)
    start_str = test.start_time.strftime("%d.%m.%Y %H:%M") if test.start_time else "Ixtiyoriy"
    end_str = test.end_time.strftime("%d.%m.%Y %H:%M") if test.end_time else "Cheklanmagan"
    pass_mark = test.pass_percentage

    saved_indicator = " ⭐ (Saqlangan)" if is_saved else ""
    file_info = "📎 Test fayli (PDF/Rasm) biriktirilgan" if test.file_id else ""

    safe_title = html.escape(test.title or "Test")
    safe_subj = html.escape(subj_name)
    safe_code = html.escape(test.code or "")

    text = (
        f"📝 <b>{safe_title}</b>{saved_indicator}\n\n"
        f"📌 <b>Fan:</b> {safe_subj}\n"
        f"❓ <b>Savollar soni:</b> {q_count} ta\n"
        f"⏱ <b>Ajratilgan vaqt:</b> {test.time_limit_minutes} daqiqa\n"
        f"🏆 <b>Maksimal ball:</b> {test.max_points}\n"
        f"🎯 <b>O‘tish bali:</b> {pass_mark}%\n"
        f"📅 <b>Boshlanish:</b> {start_str} | <b>Tugash:</b> {end_str}\n"
        f"🔑 <b>Test kodi:</b> <code>{safe_code}</code> <i>(nusxalash uchun bosing)</i>\n\n"
        f"👉 <b>Tezkor javob yuborish:</b>\n"
        f"<code>{safe_code} ABCDACBD...</code> <i>(nusxalash uchun bosing)</i>\n"
    )
    if file_info:
        text += f"\n{file_info}\n"
    return text


def get_test_action_keyboard(test: Test, back_page: int = 1) -> InlineKeyboardMarkup:
    buttons = []
    if test.file_id:
        buttons.append([InlineKeyboardButton(text="📥 Test faylini yuklab olish", callback_data=f"get_test_file:{test.id}")])
    buttons.append([InlineKeyboardButton(text="✅ Javoblarni yuborish", callback_data=f"submit_ans_prompt:{test.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Ro‘yxatga qaytish", callback_data=f"std_tests_page:{back_page}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_student_tests_page(tests: list[Test], page: int = 1, page_size: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    total_tests = len(tests)
    total_pages = max(1, (total_tests + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    current_page_tests = tests[start_idx:start_idx + page_size]

    text = f"📝 Mavjud Faol Testlar (Jami: {total_tests} ta):\n\n"
    buttons = []

    for idx, t in enumerate(current_page_tests, start=start_idx + 1):
        subj_name = t.subject.name if t.subject else "Umumiy"
        q_count = t.total_questions if t.total_questions > 0 else (len(t.test_questions) if t.test_questions else 0)
        safe_title = html.escape(t.title or "Test")
        safe_code = html.escape(t.code or "")

        text += (
            f"{idx}. {safe_title} ({safe_code})\n"
            f"   📌 Fan: {html.escape(subj_name)} | ❓ {q_count} ta savol | ⏱ {t.time_limit_minutes} daq\n\n"
        )
        short_name = (t.title[:18] + "..") if len(t.title or "") > 18 else (t.title or "Test")
        buttons.append([InlineKeyboardButton(text=f"👉 {idx}. {short_name} ({t.code})", callback_data=f"std_open_test:{t.id}:{page}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"std_tests_page:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"std_tests_page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(StateFilter("*"), F.text == "📝 Testlar")
async def list_available_tests(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    test_repo = TestRepository(session)
    tests = await test_repo.get_active_tests(limit=50)

    if not tests:
        await message.answer("📝 Hozircha faol testlar mavjud emas.\n\n💡 Yangi test kodini olganingizda, uni «🔗 Test kodi» bo‘limi orqali kiritishingiz mumkin.", parse_mode="HTML")
        return

    text, kb = build_student_tests_page(tests, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("std_tests_page:"))
async def student_tests_page_callback(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    tests = await test_repo.get_active_tests(limit=50)

    if not tests:
        await callback.answer("Faol testlar mavjud emas.", show_alert=True)
        return

    text, kb = build_student_tests_page(tests, page=page)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("std_open_test:"))
async def student_open_test_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    test_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    card_text = format_test_card(test)
    kb = get_test_action_keyboard(test, back_page=page)

    await callback.answer()
    try:
        await callback.message.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Test by Code Handlers
@router.message(TestByCodeState.waiting_for_code)
async def process_test_code_input(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    code = message.text.strip().upper()
    test_repo = TestRepository(session)
    test = await test_repo.get_by_code(code)

    if not test:
        await message.answer("⛔ Bu test mavjud emas yoki yakunlangan. Qaytadan kiriting:")
        return

    if test.password:
        await state.update_data(test_id=test.id)
        await state.set_state(TestByCodeState.waiting_for_password)
        await message.answer("🔐 Test parolini kiriting:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
        return

    await state.clear()
    await send_test_to_student(message, test, bot)


@router.message(TestByCodeState.waiting_for_password)
async def process_test_password_input(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    password = message.text.strip()
    data = await state.get_data()
    test_id = data.get("test_id")

    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test or test.password != password:
        await message.answer("❌ Parol noto'g'ri. Qaytadan kiriting:", reply_markup=get_cancel_keyboard())
        return

    await state.clear()
    await send_test_to_student(message, test, bot)


async def send_test_to_student(message: Message, test: Test, bot: Bot):
    card_text = format_test_card(test)
    kb = get_test_action_keyboard(test)

    if test.file_id:
        if test.file_type == "document":
            try:
                await message.answer_document(document=test.file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                pass
        elif test.file_type == "photo":
            try:
                await message.answer_photo(photo=test.file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                pass

    await message.answer(card_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("get_test_file:"))
async def get_test_file_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test or not test.file_id:
        await callback.answer("Fayl biriktirilmagan.", show_alert=True)
        return

    await callback.answer("Fayl yuklanmoqda...")
    if test.file_type == "document":
        await callback.message.answer_document(document=test.file_id, caption=f"📄 {test.title} savollari.")
    elif test.file_type == "photo":
        await callback.message.answer_photo(photo=test.file_id, caption=f"📷 {test.title} savollari.")


@router.callback_query(F.data.startswith("submit_ans_prompt:"))
async def submit_answer_prompt_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    await state.update_data(test_id=test.id)
    await state.set_state(QuickCheckState.waiting_for_answers)
    await callback.answer()

    q_count = test.total_questions if test.total_questions > 0 else len(test.test_questions)
    await callback.message.answer(
        f"📝 \"{test.title}\" ({q_count} ta savol)\n\n"
        "Javoblaringizni quyidagi formatlardan birida yuboring:\n"
        "• Ketma-ket: ABCDACBD...\n"
        "• Yoki: 1-A 2-B 3-C 4-D ...",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
