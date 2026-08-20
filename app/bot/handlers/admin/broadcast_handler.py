from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminBroadcastState
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.test_repo import TestRepository
from app.services.broadcast_service import BroadcastService

router = Router(name="admin_broadcast_handler")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


from aiogram.filters import StateFilter

@router.message(StateFilter("*"), F.text.in_(["📢 Xabar yuborish", "Xabar yuborish", "Xabarnoma", "📢 Xabarnoma"]))
async def broadcast_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Barcha o‘quvchilarga", callback_data="adm_bcast_target:all")],
            [InlineKeyboardButton(text="👥 Ma'lum bir guruhga", callback_data="adm_bcast_target:group")],
            [InlineKeyboardButton(text="📝 Test qatnashchilariga", callback_data="adm_bcast_target:test")]
        ]
    )
    await message.answer("📢 Kimlarga xabar yubormoqchisiz?", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_bcast_target:"))
async def select_broadcast_target(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    target = callback.data.split(":")[1]
    await state.update_data(target_type=target)
    await callback.answer()

    if target == "all":
        await state.set_state(AdminBroadcastState.waiting_for_message)
        await callback.message.answer(
            "✍️ Yubormoqchi bo‘lgan xabaringiz matnini kiriting:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    elif target == "group":
        group_repo = GroupRepository(session)
        groups = await group_repo.get_all()
        buttons = []
        for g in groups:
            buttons.append([InlineKeyboardButton(text=f"👥 {g.name}", callback_data=f"adm_bcast_id:{g.id}")])
        await callback.message.answer(
            "Qaysi guruhga xabar yuborasiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    elif target == "test":
        test_repo = TestRepository(session)
        tests = await test_repo.get_all(limit=10)
        buttons = []
        for t in tests:
            buttons.append([InlineKeyboardButton(text=f"📝 {t.title}", callback_data=f"adm_bcast_id:{t.id}")])
        await callback.message.answer(
            "Qaysi test qatnashchilariga xabar yuborasiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )


@router.callback_query(F.data.startswith("adm_bcast_id:"))
async def select_target_id(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split(":")[1])
    await state.update_data(target_id=target_id)
    await state.set_state(AdminBroadcastState.waiting_for_message)
    await callback.answer()
    await callback.message.answer(
        "✍️ Yubormoqchi bo‘lgan xabaringiz matnini kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminBroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(bcast_text=text)
    await state.set_state(AdminBroadcastState.waiting_for_confirmation)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, yuborilsin", callback_data="adm_confirm_bcast"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
            ]
        ]
    )

    await message.answer(
        f"⚠️ Yuborishni tasdiqlaysizmi?\n\n"
        f"📝 Xabar matni:\n{text}",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_confirm_bcast", AdminBroadcastState.waiting_for_confirmation)
async def execute_broadcast_callback(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    text = data.get("bcast_text")

    await callback.answer("🚀 Xabar yuborish boshlandi!")
    await callback.message.edit_text("⏳ Xabarlar tarqatilmoqda, iltimos kuting...")

    bcast_service = BroadcastService(session)
    result = await bcast_service.execute_broadcast(
        bot=bot,
        admin_id=callback.from_user.id,
        target_type=target_type,
        message_text=text,
        target_id=target_id
    )

    await state.clear()
    await callback.message.answer(
        f"✅ Xabar tarqatish yakunlandi!\n\n"
        f"📊 Jami foydalanuvchilar: {result.total_count} ta\n"
        f"✅ Muvaffaqiyatli yetkazildi: {result.success_count} ta\n"
        f"❌ Xatolik yuz bergan: {result.failed_count} ta",
        parse_mode="HTML"
    )
