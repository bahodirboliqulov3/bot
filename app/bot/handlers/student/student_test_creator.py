from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.student_states import StudentCreateTestState
from app.database.models.test import Question, Test, TestStatus
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.test_service import TestService

router = Router(name="student_test_creator")


@router.message(F.text == "✍️ Test yaratish")
async def start_student_test_creation(message: Message, state: FSMContext):
    await state.set_state(StudentCreateTestState.waiting_for_title)
    await message.answer(
        "✍️ Yangi test yaratish:\n\n"
        "Test nomini kiriting:\n(Masalan: Matematika 9-sinf ChSB)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(StudentCreateTestState.waiting_for_title)
async def process_test_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("❌ Nomi juda qisqa. Qaytadan kiriting:")
        return
    await state.update_data(title=title)
    await state.set_state(StudentCreateTestState.waiting_for_subject)
    await message.answer("Fan nomini kiriting:\n(Masalan: Fizika, Ingliz tili)", reply_markup=get_cancel_keyboard())


@router.message(StudentCreateTestState.waiting_for_subject)
async def process_test_subject(message: Message, state: FSMContext):
    subj = message.text.strip()
    await state.update_data(subject=subj)
    await state.set_state(StudentCreateTestState.waiting_for_grade)
    await message.answer("Qaysi sinf/bosqich uchun? (Masalan: 9-sinf yoki Umumiy):", reply_markup=get_cancel_keyboard())


@router.message(StudentCreateTestState.waiting_for_grade)
async def process_test_grade(message: Message, state: FSMContext):
    grade = message.text.strip()
    await state.update_data(grade=grade)
    await state.set_state(StudentCreateTestState.waiting_for_time_limit)
    await message.answer("Test uchun vaqt chegarasi (daqiqada, masalan: 20):", reply_markup=get_cancel_keyboard())


@router.message(StudentCreateTestState.waiting_for_time_limit)
async def process_test_time_limit(message: Message, state: FSMContext, session: AsyncSession):
    try:
        minutes = int(message.text.strip())
        if minutes <= 0:
            minutes = 20
    except ValueError:
        minutes = 20

    data = await state.get_data()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    test_service = TestService(session)

    test = await test_service.create_test(
        title=data.get("title"),
        subject_name=data.get("subject"),
        grade=data.get("grade"),
        author_id=user.id,
        time_limit_minutes=minutes,
        status=TestStatus.DRAFT
    )

    await state.update_data(test_id=test.id, questions_added=0)
    await state.set_state(StudentCreateTestState.waiting_for_question_text)
    await message.answer(
        f"✅ Test asosi yaratildi!\n🔑 Test kodi: {test.code}\n\n"
        "Endi 1-savol matnini kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(StudentCreateTestState.waiting_for_question_text)
async def process_question_text(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(current_q_text=text)
    await state.set_state(StudentCreateTestState.waiting_for_option_a)
    await message.answer("🅰️ A variant matnini kiriting:", parse_mode="HTML")


@router.message(StudentCreateTestState.waiting_for_option_a)
async def process_option_a(message: Message, state: FSMContext):
    await state.update_data(opt_a=message.text.strip())
    await state.set_state(StudentCreateTestState.waiting_for_option_b)
    await message.answer("🅱️ B variant matnini kiriting:", parse_mode="HTML")


@router.message(StudentCreateTestState.waiting_for_option_b)
async def process_option_b(message: Message, state: FSMContext):
    await state.update_data(opt_b=message.text.strip())
    await state.set_state(StudentCreateTestState.waiting_for_option_c)
    await message.answer("🅲 C variant matnini kiriting:", parse_mode="HTML")


@router.message(StudentCreateTestState.waiting_for_option_c)
async def process_option_c(message: Message, state: FSMContext):
    await state.update_data(opt_c=message.text.strip())
    await state.set_state(StudentCreateTestState.waiting_for_option_d)
    await message.answer("🅳 D variant matnini kiriting:", parse_mode="HTML")


@router.message(StudentCreateTestState.waiting_for_option_d)
async def process_option_d(message: Message, state: FSMContext):
    await state.update_data(opt_d=message.text.strip())
    await state.set_state(StudentCreateTestState.waiting_for_correct_option)
    await message.answer(
        "✅ To‘g‘ri javobni tanlang (A, B, C yoki D):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="A", callback_data="stud_correct:A"),
                    InlineKeyboardButton(text="B", callback_data="stud_correct:B"),
                    InlineKeyboardButton(text="C", callback_data="stud_correct:C"),
                    InlineKeyboardButton(text="D", callback_data="stud_correct:D"),
                ]
            ]
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stud_correct:"))
async def process_correct_option_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    correct_opt = callback.data.split(":")[1]
    data = await state.get_data()

    test_id = data.get("test_id")
    q_count = data.get("questions_added", 0) + 1

    question = Question(
        text=data.get("current_q_text"),
        option_a=data.get("opt_a"),
        option_b=data.get("opt_b"),
        option_c=data.get("opt_c"),
        option_d=data.get("opt_d"),
        correct_option=correct_opt,
        points=1.0
    )

    test_repo = TestRepository(session)
    await test_repo.add_question_to_test(test_id=test_id, question=question, order_index=q_count)

    await state.update_data(questions_added=q_count)
    await callback.answer(f"✅ {q_count}-savol saqlandi!")

    # Prompt for next question or publish test
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yana savol qo‘shish", callback_data=f"stud_add_more:{test_id}")],
            [InlineKeyboardButton(text="🚀 Testni faollashtirish (Tugatish)", callback_data=f"stud_activate:{test_id}")]
        ]
    )
    await callback.message.edit_text(
        f"✅ {q_count}-savol muvaffaqiyatli saqlandi!\n\nNima qilishni xohlaysiz?",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stud_add_more:"))
async def add_more_questions_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StudentCreateTestState.waiting_for_question_text)
    await callback.answer()
    await callback.message.answer("Yangi savol matnini kiriting:", reply_markup=get_cancel_keyboard())


@router.callback_query(F.data.startswith("stud_activate:"))
async def activate_created_test_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if test:
        test.status = TestStatus.ACTIVE
        await session.flush()

    await state.clear()
    await callback.answer("🚀 Test faollashtirildi!")
    await callback.message.edit_text(
        f"🎉 Test muvaffaqiyatli nashr qilindi!\n\n"
        f"📝 Nomi: {test.title}\n"
        f"🔑 Test kodi: <code>{test.code}</code>\n\n"
        f"Ushbu kodni do‘stlaringizga ulashib, test yechishlarini so‘rashingiz mumkin.",
        parse_mode="HTML"
    )


# Section 16: Mening testlarim
@router.message(F.text == "📚 Mening testlarim")
async def list_my_created_tests(message: Message, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    test_repo = TestRepository(session)
    tests = await test_repo.get_tests_by_author(user.id)

    if not tests:
        await message.answer(
            "📚 Siz hali birorta ham test yaratmagansiz.\n"
            "'✍️ Test yaratish' bo'limi orqali yangi test tuzishingiz mumkin."
        )
        return

    await message.answer(f"📚 Siz yaratgan testlar ({len(tests)} ta):", parse_mode="HTML")

    for t in tests:
        status_badge = "🟢 Faol" if t.status == TestStatus.ACTIVE else "🟡 Qoralama" if t.status == TestStatus.DRAFT else "🔴 Tugagan"
        card = (
            f"📝 {t.title}\n"
            f"🔑 Kod: {t.code}\n"
            f"❓ Savollar: {len(t.test_questions)} ta\n"
            f"📊 Holati: {status_badge}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Nusxalash", callback_data=f"clone_test:{t.id}"),
                    InlineKeyboardButton(text="📤 Ulashish", callback_data=f"share_my_test:{t.id}")
                ],
                [
                    InlineKeyboardButton(text="⛔ Yopish", callback_data=f"close_test:{t.id}"),
                    InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"delete_test:{t.id}")
                ]
            ]
        )
        await message.answer(card, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("clone_test:"))
async def clone_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_service = TestService(session)
    cloned = await test_service.duplicate_test(test_id)
    await callback.answer("✅ Testdan nusxa yaratildi!")
    await callback.message.answer(f"✅ Yangi nusxa kodi: <code>{cloned.code}</code>", parse_mode="HTML")


@router.callback_query(F.data.startswith("close_test:"))
async def close_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if test:
        test.status = TestStatus.FINISHED
        await session.flush()
        await callback.answer("⛔ Test yopildi!")
        await callback.message.edit_text(f"⛔ {test.title} testi yakunlandi.", parse_mode="HTML")


@router.callback_query(F.data.startswith("delete_test:"))
async def delete_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    await test_repo.delete(test_id)
    await callback.answer("🗑 Test o‘chirildi!")
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("share_my_test:"))
async def share_my_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if test:
        await callback.answer()
        await callback.message.answer(
            f"📢 \"{test.title}\" testiga taklif!\n\n"
            f"Testni ishlash uchun quyidagi kodni botga yuboring:\n"
            f"🔑 Test kodi: <code>{test.code}</code>",
            parse_mode="HTML"
        )
