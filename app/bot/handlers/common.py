from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.reply_keyboards import get_student_main_keyboard
from app.services.auth_service import AuthService

router = Router(name="common")


@router.message(F.text.in_(["❌ Bekor qilish", "/cancel"]))
async def cancel_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)
    await message.answer(
        "❌ Amaliyot bekor qilindi.",
        reply_markup=get_student_main_keyboard(is_admin=is_admin)
    )


@router.message(F.text.in_(["🏠 Bosh menyu", "/menu"]))
async def main_menu_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)
    await message.answer(
        "🏠 Asosiy menyudasiz. Kerakli bo‘limni tanlang:",
        reply_markup=get_student_main_keyboard(is_admin=is_admin)
    )


@router.callback_query(F.data == "cancel")
async def cancel_callback_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    await callback.message.delete()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(callback.from_user.id)
    await callback.message.answer(
        "❌ Amaliyot bekor qilindi.",
        reply_markup=get_student_main_keyboard(is_admin=is_admin)
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()
