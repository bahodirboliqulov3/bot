import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.handlers.student.test_solver import show_test_result
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.student_states import QuickCheckState
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.scoring_service import ScoringService

router = Router(name="student_quick_check")


# 1. Direct one-line test answer checker: "TEST-101 abcdacbd..." or "test-8a92 1a 2b 3c"
@router.message(F.text.regexp(r"(?i)^(TEST-[A-Z0-9]+|[A-Z0-9_\-]{3,16})\s+([\w\s\-:.,]+)$"))
async def direct_code_and_answers_handler(message: Message, session: AsyncSession):
    text = message.text.strip()
    parsed_pair = ScoringService.parse_direct_code_and_answers(text)
    if not parsed_pair:
        return

    test_code, raw_answers = parsed_pair
    test_repo = TestRepository(session)
    test = await test_repo.get_by_code(test_code)

    if not test:
        await message.answer(
            f"🙈 <b>{html.escape(test_code)}</b> kodli test topilmadi!\n\n"
            "💡 <i>Test kodini to'g'ri kiritdingizmi? Masalan:</i>\n"
            f"<code>{html.escape(test_code)} ABCDABCD...</code>",
            parse_mode="HTML"
        )
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(
            "👋 Avval ro'yxatdan o'ting!\n\n"
            "👉 /start — bosib profilingizni yarating",
            parse_mode="HTML"
        )
        return

    scoring_service = ScoringService(session)
    try:
        res, visual_grid = await scoring_service.evaluate_quick_submission(
            test_id=test.id,
            user_id=user.id,
            raw_answers=raw_answers
        )
        auth_service = AuthService(session)
        is_admin = await auth_service.is_admin(message.from_user.id)

        await message.answer(
            f"⚡ <b>\"{html.escape(test.title)}\"</b> — javoblar tekshirildi!",
            reply_markup=get_student_main_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )
        await show_test_result(message, res, session, visual_breakdown=visual_grid)
    except ValueError as e:
        await message.answer(
            f"⚠️ <b>Xato:</b> {html.escape(str(e))}\n\n"
            f"📝 <i>To'g'ri format:</i> <code>{test.code} ABCDABCD...</code>",
            parse_mode="HTML"
        )


@router.message(F.text == "✅ Javobni tekshirish")
async def start_quick_check_menu(message: Message, state: FSMContext):
    await state.set_state(QuickCheckState.waiting_for_test_code)
    await message.answer(
        "✅ <b>Javoblarni tekshirish</b>\n\n"
        "Test kodini kiriting (masalan: <code>TEST-101</code>):\n\n"
        "💡 <b>Maslahat:</b> Bitta xabarda kod va javoblarni to‘g‘ridan-to‘g‘ri yuborishingiz mumkin:\n"
        "<code>TEST-101 ABCDACBD...</code> <i>(nusxalash uchun bosing)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(QuickCheckState.waiting_for_test_code)
async def process_quick_check_test_code(message: Message, state: FSMContext, session: AsyncSession):
    code = message.text.strip().upper()

    # Check if user sent direct code + answers in this step as well
    parsed_pair = ScoringService.parse_direct_code_and_answers(code)
    if parsed_pair:
        await state.clear()
        await direct_code_and_answers_handler(message, session)
        return

    test_repo = TestRepository(session)
    test = await test_repo.get_by_code(code)

    if not test:
        await message.answer("⛔ Ushbu kodli test topilmadi. Qaytadan kiriting yoki bekor qiling:")
        return

    await state.update_data(test_id=test.id)
    await state.set_state(QuickCheckState.waiting_for_answers)

    q_count = test.total_questions if test.total_questions > 0 else len(test.test_questions)
    info_msg = (
        f"📝 <b>Test topildi:</b> {html.escape(test.title)} ({q_count} ta savol)\n\n"
        "Endi javoblaringizni quyidagi formatlardan birida yuboring:\n"
        "• Ketma-ket harflar: <code>ABCDACBD...</code>\n"
        "• Yoki raqamlangan: <code>1-A 2-B 3-C 4-D...</code>"
    )

    if test.file_id:
        if test.file_type == "photo":
            try:
                await message.answer_photo(photo=test.file_id, caption=info_msg, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
                return
            except Exception:
                pass
        else:
            try:
                await message.answer_document(document=test.file_id, caption=info_msg, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
                return
            except Exception:
                pass

    await message.answer(info_msg, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(QuickCheckState.waiting_for_answers, F.text)
async def process_quick_check_text_answers(message: Message, state: FSMContext, session: AsyncSession):
    raw_text = message.text.strip()
    data = await state.get_data()
    test_id = data.get("test_id")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    scoring_service = ScoringService(session)

    try:
        res, visual_grid = await scoring_service.evaluate_quick_submission(
            test_id=test_id,
            user_id=user.id,
            raw_answers=raw_text
        )
        await state.clear()
        auth_service = AuthService(session)
        is_admin = await auth_service.is_admin(message.from_user.id)

        await message.answer("✅ Javoblaringiz muvaffaqiyatli tekshirildi!", reply_markup=get_student_main_keyboard(is_admin=is_admin))
        await show_test_result(message, res, session, visual_breakdown=visual_grid)
    except ValueError as e:
        await message.answer(f"❌ {html.escape(str(e))}\nIltimos, javoblarni to‘g‘ri formatda yuboring (Masalan: ABCDACBD... yoki 1-A 2-B 3-C):", parse_mode="HTML")

