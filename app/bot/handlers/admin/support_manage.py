import html
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard
from app.bot.states.admin_states import AdminSupportResponseState
from app.database.models.system import SupportTicketStatus
from app.database.repositories.support_repo import SupportRepository
from app.database.repositories.user_repo import UserRepository

router = Router(name="admin_support_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "📨 Murojaatlar")
async def list_support_tickets(message: Message, session: AsyncSession):
    support_repo = SupportRepository(session)
    tickets = await support_repo.get_tickets(limit=10)

    if not tickets:
        await message.answer("🎉 Hozircha yangi murojaatlar mavjud emas.", parse_mode="HTML")
        return

    await message.answer(f"📨 So‘nggi murojaatlar ro‘yxati ({len(tickets)} ta):", parse_mode="HTML")

    for t in tickets:
        user = t.user
        status_icon = "🆕 Yangi" if t.status == SupportTicketStatus.NEW else "✅ Javob berilgan"
        safe_student = html.escape(user.full_name if user else "Foydalanuvchi")
        safe_msg = html.escape(t.message_text)
        card = (
            f"📩 Murojaat #{t.id} ({status_icon})\n"
            f"👤 O‘quvchi: {safe_student}\n"
            f"📅 Vaqt: {t.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"💬 Xabar: {safe_msg}\n"
        )
        if t.admin_response:
            safe_resp = html.escape(t.admin_response)
            card += f"💡 Javob: {safe_resp}\n"

        buttons = []
        if t.status == SupportTicketStatus.NEW:
            buttons.append([InlineKeyboardButton(text="✍️ Javob yozish", callback_data=f"reply_ticket:{t.id}")])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        await message.answer(card, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("reply_ticket:"))
async def reply_ticket_prompt(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split(":")[1])
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(AdminSupportResponseState.waiting_for_response)
    await callback.answer()
    await callback.message.answer(
        f"✍️ #{ticket_id}-sonli murojaatga javobingizni yozing:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminSupportResponseState.waiting_for_response)
async def process_ticket_response(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    response_text = message.text.strip()
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")

    support_repo = SupportRepository(session)
    ticket = await support_repo.answer_ticket(
        ticket_id=ticket_id,
        admin_id=message.from_user.id,
        response_text=response_text
    )

    await state.clear()
    await message.answer(f"✅ #{ticket_id}-sonli murojaatga javob yuborildi!", parse_mode="HTML")

    # Notify student
    if ticket and ticket.user:
        try:
            safe_q = html.escape(ticket.message_text)
            safe_a = html.escape(response_text)
            student_msg = (
                f"👨💼 Admin javobi (Murojaat #{ticket.id}):\n\n"
                f"💬 Sizning savolingiz:\n«{safe_q}»\n\n"
                f"✅ Admin javobi:\n{safe_a}"
            )
            await bot.send_message(chat_id=ticket.user.telegram_id, text=student_msg, parse_mode="HTML")
        except Exception:
            pass
