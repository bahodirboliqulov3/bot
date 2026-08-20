from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminChannelState
from app.database.models.system import RequiredChannel
from app.database.repositories.channel_repo import ChannelRepository

router = Router(name="admin_channels_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "📢 Majburiy kanallar")
async def list_required_channels_handler(message: Message, session: AsyncSession):
    channel_repo = ChannelRepository(session)
    channels = await channel_repo.get_all()

    text = f"📢 Majburiy kanallar ro‘yxati ({len(channels)} ta):\n\n"
    for ch in channels:
        status_icon = "🟢 Faol" if ch.is_active else "🔴 O'chirilgan"
        text += f"🔹 <b>{ch.title}</b> (<code>{ch.channel_id}</code>) — {status_icon}\n   🔗 <code>{ch.invite_link}</code>\n\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi kanal qo‘shish", callback_data="adm_add_channel")],
            [InlineKeyboardButton(text="❌ Kanalni o‘chirish", callback_data="adm_del_channel_prompt")]
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "adm_add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminChannelState.waiting_for_title)
    await callback.answer()
    await callback.message.answer(
        "➕ Kanal nomini kiriting:\n(Masalan: Rasmiy Yangiliklar)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminChannelState.waiting_for_title)
async def process_channel_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminChannelState.waiting_for_channel_id)
    await message.answer(
        "Kanal ID yoki @username kiriting:\n(Masalan: -1001234567890 yoki @mening_kanalim):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminChannelState.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    await state.update_data(channel_id=message.text.strip())
    await state.set_state(AdminChannelState.waiting_for_invite_link)
    await message.answer(
        "Kanalga a'zo bo'lish havolasini (link) kiriting:\n(Masalan: https://t.me/mening_kanalim):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminChannelState.waiting_for_invite_link)
async def process_channel_link(message: Message, state: FSMContext, session: AsyncSession):
    link = message.text.strip()
    data = await state.get_data()

    channel_repo = ChannelRepository(session)
    await channel_repo.create(
        title=data["title"],
        channel_id=data["channel_id"],
        invite_link=link,
        is_active=True
    )

    await state.clear()
    await message.answer(f"✅ \"{data['title']}\" kanali muvaffaqiyatli qo'shildi!", parse_mode="HTML")


@router.callback_query(F.data == "adm_del_channel_prompt")
async def delete_channel_prompt(callback: CallbackQuery, session: AsyncSession):
    channel_repo = ChannelRepository(session)
    channels = await channel_repo.get_all()
    if not channels:
        await callback.answer("Kanallar mavjud emas.", show_alert=True)
        return

    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"🗑 {ch.title}", callback_data=f"adm_del_ch:{ch.id}")])

    await callback.answer()
    await callback.message.answer(
        "O'chirmoqchi bo'lgan kanalni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("adm_del_ch:"))
async def delete_channel_callback(callback: CallbackQuery, session: AsyncSession):
    ch_id = int(callback.data.split(":")[1])
    channel_repo = ChannelRepository(session)
    await channel_repo.delete(ch_id)
    await callback.answer("🗑 Kanal o'chirildi!")
    try:
        await callback.message.delete()
    except Exception:
        pass
