from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminAddAdminState
from app.config import settings
from app.database.repositories.user_repo import AdminRepository
from app.services.auth_service import AuthService

router = Router(name="admin_admins_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "👑 Adminlar")
async def list_admins_handler(message: Message, session: AsyncSession):
    admin_repo = AdminRepository(session)
    admins = await admin_repo.get_all_admins()

    text = "👑 Tizim Adminlari ro‘yxati:\n\n"
    text += f"🌟 Asosiy Boshqaruvchi (Owner): <code>{settings.OWNER_ID}</code>\n\n"

    for a in admins:
        text += f"🔹 {a.full_name} | ID: <code>{a.telegram_id}</code> (Qo'shilgan: {a.created_at.strftime('%d.%m.%Y')})\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi admin qo‘shish", callback_data="adm_add_admin")],
            [InlineKeyboardButton(text="➖ Adminni o‘chirish", callback_data="adm_del_admin_prompt")]
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "adm_add_admin")
async def start_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminAddAdminState.waiting_for_telegram_id)
    await callback.answer()
    await callback.message.answer(
        "➕ Yangi adminning Telegram ID sini kiriting:\n(Masalan: 987654321)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminAddAdminState.waiting_for_telegram_id)
async def process_admin_tg_id(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Telegram ID faqat raqamlardan iborat bo‘lishi kerak:")
        return

    await state.update_data(tg_id=int(val))
    await state.set_state(AdminAddAdminState.waiting_for_full_name)
    await message.answer("Adminning to‘liq ismi-sharifini kiriting:", reply_markup=get_cancel_keyboard())


@router.message(AdminAddAdminState.waiting_for_full_name)
async def process_admin_full_name(message: Message, state: FSMContext, session: AsyncSession):
    full_name = message.text.strip()
    data = await state.get_data()
    tg_id = data["tg_id"]

    auth_service = AuthService(session)
    await auth_service.add_admin(
        telegram_id=tg_id,
        full_name=full_name,
        added_by=message.from_user.id
    )

    await state.clear()
    await message.answer(f"✅ {full_name} ({tg_id}) admin sifatida muvaffaqiyatli qo‘shildi!", parse_mode="HTML")


@router.callback_query(F.data == "adm_del_admin_prompt")
async def delete_admin_prompt(callback: CallbackQuery, session: AsyncSession):
    admin_repo = AdminRepository(session)
    admins = await admin_repo.get_all_admins()

    if not admins:
        await callback.answer("Qo'shilgan qo'shimcha adminlar yo'q.", show_alert=True)
        return

    buttons = []
    for a in admins:
        safe_aname = (a.full_name or "Admin").replace("<", "&lt;").replace(">", "&gt;")
        buttons.append([InlineKeyboardButton(text=f"🗑 {safe_aname} ({a.telegram_id})", callback_data=f"adm_del_admin:{a.telegram_id}")])

    await callback.answer()
    await callback.message.answer("O'chirmoqchi bo'lgan adminni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_del_admin:"))
async def delete_admin_callback(callback: CallbackQuery, session: AsyncSession):
    target_id = int(callback.data.split(":")[1])
    auth_service = AuthService(session)

    try:
        await auth_service.remove_admin(target_id)
        await callback.answer("Admin muvaffaqiyatli o‘chirildi.")
        try:
            await callback.message.delete()
        except Exception:
            pass
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
