from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_admin_main_keyboard, get_student_main_keyboard
from app.services.auth_service import AuthService

router = Router(name="admin_menu")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(StateFilter("*"), Command("admin"))
@router.message(StateFilter("*"), F.text.in_(["👨💼 Admin Paneli", "Admin Paneli", "/admin"]))
async def open_admin_panel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👨💼 Admin Boshqaruv Paneliga xush kelibsiz!\n\n"
        "Kerakli boshqaruv bo‘limini tanlang:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(StateFilter("*"), F.text.in_(["🏠 O‘quvchi rejimi", "🏠 O'quvchi rejimi", "O‘quvchi rejimi", "O'quvchi rejimi", "🏠 Bosh menyu (O'quvchi rejimi)"]))
async def switch_to_student_mode_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)
    await message.answer(
        "🏠 O‘quvchi rejimiga o‘tdingiz.",
        reply_markup=get_student_main_keyboard(is_admin=is_admin)
    )
