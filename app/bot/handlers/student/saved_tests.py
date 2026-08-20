from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.handlers.student.tests_list import format_test_card
from app.bot.keyboards.inline_keyboards import get_test_item_keyboard
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository

router = Router(name="student_saved_tests")


@router.message(F.text == "🔖 Saqlangan testlar")
async def list_saved_tests(message: Message, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    test_repo = TestRepository(session)
    saved = await test_repo.get_saved_tests(user.id)

    if not saved:
        await message.answer("🔖 Sizda hozircha saqlangan testlar mavjud emas.")
        return

    await message.answer(f"🔖 Saqlangan testlar ({len(saved)} ta):", parse_mode="HTML")

    for t in saved:
        await message.answer(
            format_test_card(t, is_saved=True),
            reply_markup=get_test_item_keyboard(t.id, is_saved=True),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("toggle_save:"))
async def toggle_save_test_callback(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    test_repo = TestRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    is_saved = await test_repo.toggle_save_test(user.id, test_id)
    if is_saved:
        await callback.answer("⭐ Test saqlanganlarga qo'shildi!")
    else:
        await callback.answer("🗑 Test saqlanganlardan o'chirildi.")

    test = await test_repo.get_test_with_questions(test_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=get_test_item_keyboard(test.id, is_saved=is_saved))
    except Exception:
        pass
