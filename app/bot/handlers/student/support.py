from datetime import datetime, timezone
import html
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.student_states import StudentSupportState
from app.config import settings
from app.database.models.system import SupportTicket, SupportTicketStatus
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.user_repo import AdminRepository, UserRepository
from app.services.auth_service import AuthService
from app.services.profanity_service import ProfanityService

router = Router(name="student_support")


@router.message(F.text == "👨💼 Admin bilan bog‘lanish")
@router.callback_query(F.data == "student_support_prompt")
async def student_contact_admin_handler(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(StudentSupportState.waiting_for_message)
    msg_text = (
        "📨 Admin bilan bog‘lanish:\n\n"
        "Savolingiz, taklifingiz yoki muammoni batafsil yozib yuboring.\n"
        "Adminlarimiz tez orada sizga javob berishadi."
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        await event.answer(msg_text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(StudentSupportState.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    text = message.text.strip()
    if ProfanityService.contains_profanity(text):
        await message.answer(
            "⚠️ <b>Nomaqbul yoki haqoratomuz so'zlar aniqlandi!</b>\n\n"
            "Iltimos, adminga murojaatingizni odobli va tushunarli tarzda yozing.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    if len(text) < 5:
        await message.answer("❌ Iltimos, xabarni to‘liqroq yozing:")
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    ticket_repo = BaseRepository(SupportTicket, session)
    ticket = await ticket_repo.create(
        user_id=user.id,
        message_text=text,
        status=SupportTicketStatus.NEW
    )

    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)
    await message.answer(
        "✅ Murojaatingiz adminga yuborildi!\n"
        "Javob kelishi bilanoq sizga bildirishnoma yuboramiz.",
        reply_markup=get_student_main_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

    # Notify admins
    admin_repo = AdminRepository(session)
    admins = await admin_repo.get_all_admins()
    admin_ids = {a.telegram_id for a in admins}
    admin_ids.add(settings.OWNER_ID)

    safe_user_name = html.escape(user.full_name or "O'quvchi")
    safe_uname = html.escape(user.username or "mavjud_emas")
    safe_sch = html.escape(user.school or "—")
    safe_grd = html.escape(user.grade or "—")
    safe_text = html.escape(text)

    admin_msg = (
        f"📩 <b>Yangi Murojaat #{ticket.id}</b>\n\n"
        f"👤 O‘quvchi: {safe_user_name}\n"
        f"🔗 Username: @{safe_uname}\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"🏫 Maktab/Sinf: {safe_sch} ({safe_grd})\n"
        f"📅 Vaqt: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"💬 <b>Xabar:</b>\n{safe_text}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Javob yozish", callback_data=f"reply_ticket:{ticket.id}")]
        ]
    )

    for a_id in admin_ids:
        try:
            await bot.send_message(chat_id=a_id, text=admin_msg, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
