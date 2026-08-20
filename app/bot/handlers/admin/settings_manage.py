from datetime import datetime
from pathlib import Path
import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.config import settings
from app.database.repositories.channel_repo import ChannelRepository
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.stats_repo import StatsRepository
from app.database.repositories.support_repo import SupportRepository
from app.database.repositories.user_repo import AdminRepository

router = Router(name="admin_settings_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


async def build_settings_dashboard(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
    stats_repo = StatsRepository(session)
    anti_cheat_strict = await stats_repo.get_setting("anti_cheat_strict", "true")

    anticheat_status = "🟢 Faol" if anti_cheat_strict == "true" else "🔴 No-faol"

    text = (
        "⚙️ Admin Boshqaruv Markazi va Sozlamalar:\n\n"
        f"🛡 Anti-Cheat (Variantlar aralashtirish): {anticheat_status}\n\n"
        "Quyidagi boshqaruv bo‘limlaridan birini tanlang:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="adm_nav_channels"),
                InlineKeyboardButton(text="👑 Adminlar", callback_data="adm_nav_admins")
            ],
            [
                InlineKeyboardButton(text="👥 Guruhlar", callback_data="adm_nav_groups"),
                InlineKeyboardButton(text="📁 Excel boshqaruvi", callback_data="adm_nav_excel")
            ],
            [
                InlineKeyboardButton(text="📨 Murojaatlar", callback_data="adm_nav_support"),
                InlineKeyboardButton(text="💾 Baza zaxirasi (Backup)", callback_data="adm_backup_db")
            ],
            [
                InlineKeyboardButton(text=f"🛡 Anti-Cheat: {anticheat_status}", callback_data="toggle_sys_anticheat")
            ]
        ]
    )
    return text, kb


@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Boshqaruv & Sozlamalar"]))
async def show_admin_system_settings(message: Message, session: AsyncSession):
    text, kb = await build_settings_dashboard(session)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "adm_nav_settings_main")
async def nav_settings_main_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    text, kb = await build_settings_dashboard(session)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "toggle_sys_anticheat")
async def toggle_sys_anticheat_callback(callback: CallbackQuery, session: AsyncSession):
    stats_repo = StatsRepository(session)
    current = await stats_repo.get_setting("anti_cheat_strict", "true")
    new_val = "false" if current == "true" else "true"
    await stats_repo.set_setting("anti_cheat_strict", new_val)
    await callback.answer(f"Anti-cheat: {'Faollashtirildi' if new_val == 'true' else 'O‘chirildi'}!")

    text, kb = await build_settings_dashboard(session)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Channels view
@router.callback_query(F.data == "adm_nav_channels")
async def nav_channels_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    channel_repo = ChannelRepository(session)
    channels = await channel_repo.get_all()

    text = f"📢 Majburiy a’zolik kanallari ({len(channels)} ta):\n\n"
    if not channels:
        text += "Hozircha majburiy kanallar qo‘shilmagan.\n\n"
    else:
        for idx, ch in enumerate(channels, start=1):
            st = "🟢 Faol" if ch.is_active else "🔴 O‘chirilgan"
            safe_title = html.escape(ch.title)
            safe_id = html.escape(str(ch.channel_id))
            text += f"{idx}. {safe_title} ({safe_id}) — {st}\n   🔗 {html.escape(ch.invite_link)}\n\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi kanal qo‘shish", callback_data="adm_add_channel"),
                InlineKeyboardButton(text="❌ O‘chirish", callback_data="adm_del_channel_prompt")
            ],
            [
                InlineKeyboardButton(text="◀️ Sozlamalarga qaytish", callback_data="adm_nav_settings_main")
            ]
        ]
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Admins view
@router.callback_query(F.data == "adm_nav_admins")
async def nav_admins_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    admin_repo = AdminRepository(session)
    admins = await admin_repo.get_all_admins()

    text = "👑 Tizim Adminlari ro‘yxati:\n\n"
    text += f"🌟 Bosh Administrator (Owner): {settings.OWNER_ID}\n\n"

    if admins:
        text += "📋 Qo‘shimcha adminlar:\n"
        for idx, a in enumerate(admins, start=1):
            safe_admin = html.escape(a.full_name or "Admin")
            date_str = a.created_at.strftime('%d.%m.%Y') if a.created_at else ""
            text += f"{idx}. {safe_admin} | ID: {a.telegram_id} (📅 {date_str})\n"
    else:
        text += "Qo‘shimcha adminlar mavjud emas.\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi admin qo‘shish", callback_data="adm_add_admin"),
                InlineKeyboardButton(text="➖ Adminni o‘chirish", callback_data="adm_del_admin_prompt")
            ],
            [
                InlineKeyboardButton(text="◀️ Sozlamalarga qaytish", callback_data="adm_nav_settings_main")
            ]
        ]
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Groups view
@router.callback_query(F.data == "adm_nav_groups")
async def nav_groups_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    group_repo = GroupRepository(session)
    groups = await group_repo.get_all_groups_with_member_count()

    text = f"👥 Tizimdagi guruhlar va sinflar ({len(groups)} ta):\n\n"
    if not groups:
        text += "Hozircha guruhlar yaratilmagan.\n\n"
    else:
        for idx, (g, count) in enumerate(groups, start=1):
            safe_gname = html.escape(g.name)
            text += f"{idx}. {safe_gname} — 👤 {count} nafar o‘quvchi\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi guruh yaratish", callback_data="adm_create_group"),
                InlineKeyboardButton(text="👥 Guruhlarni ko‘rish", callback_data="adm_view_group_prompt")
            ],
            [
                InlineKeyboardButton(text="◀️ Sozlamalarga qaytish", callback_data="adm_nav_settings_main")
            ]
        ]
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Excel view
@router.callback_query(F.data == "adm_nav_excel")
async def nav_excel_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📁 EXCEL (.XLSX) BOSHQARUV MARKAZI 📊\n\n"
        "Quyidagi amallardan birini tanlang:\n"
        "• Import: Excel fayl orqali test savollarini avtomatik yaratish.\n"
        "• Eksport: O‘quvchilar natijalari va test hisobotlarini Excel formatida yuklab olish."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Savollarni Exceldan yuklash", callback_data="adm_xl_import_start"),
                InlineKeyboardButton(text="📤 Natijalarni Excelga yuklash", callback_data="adm_xl_export_start")
            ],
            [
                InlineKeyboardButton(text="◀️ Sozlamalarga qaytish", callback_data="adm_nav_settings_main")
            ]
        ]
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


from app.database.models.system import SupportTicketStatus


# Support view
@router.callback_query(F.data == "adm_nav_support")
async def nav_support_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    sup_repo = SupportRepository(session)
    tickets = await sup_repo.get_tickets(limit=10)

    text = f"📨 O‘quvchilar murojaatlari (Jami: {len(tickets)} ta):\n\n"
    buttons = []

    if not tickets:
        text += "🎉 Hozircha yangi murojaatlar yo‘q!\n"
    else:
        for t in tickets:
            safe_uname = html.escape(t.user.full_name if t.user else "Foydalanuvchi")
            safe_msg = html.escape(t.message_text[:50]) + ("..." if len(t.message_text) > 50 else "")
            st_badge = "🆕 Yangi" if t.status == SupportTicketStatus.NEW else "✅ Javob berilgan"
            text += f"🔹 #{t.id} {safe_uname} ({st_badge}):\n   «{safe_msg}»\n\n"
            if t.status == SupportTicketStatus.NEW:
                buttons.append([InlineKeyboardButton(text=f"✍️ #{t.id} ga javob berish", callback_data=f"reply_ticket:{t.id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Sozlamalarga qaytish", callback_data="adm_nav_settings_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "adm_backup_db")
async def backup_database_callback(callback: CallbackQuery):
    await callback.answer("💾 Baza zaxiralanmoqda...")
    db_file = Path("storage/test_platform.db")
    if not db_file.exists():
        for alt in [Path("test_platform.db"), Path("storage/data/test_platform.db")]:
            if alt.exists():
                db_file = alt
                break

    if db_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await callback.message.answer_document(
            document=FSInputFile(path=str(db_file), filename=f"backup_database_{timestamp}.db"),
            caption=f"💾 <b>Ma'lumotlar bazasi zaxirasi (Backup)</b>\n📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("⚠️ Baza fayli topilmadi.")
