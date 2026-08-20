import html
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_admin_main_keyboard
from app.bot.states.admin_states import AdminGroupState
from app.database.models.group import Group
from app.database.repositories.group_repo import GroupRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.user_repo import UserRepository

router = Router(name="admin_groups_manage")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "👥 Guruhlar")
async def list_groups_handler(message: Message, session: AsyncSession):
    group_repo = GroupRepository(session)
    groups = await group_repo.get_all_groups_with_member_count()

    text = f"👥 Guruhlar ro‘yxati ({len(groups)} ta):\n\n"
    if not groups:
        text += "Hozircha guruhlar yaratilmagan.\n"
    else:
        for idx, (g, count) in enumerate(groups, start=1):
            safe_name = html.escape(g.name)
            text += f"🔹 {idx}. {safe_name} — 👤 {count} ta o‘quvchi (ID: <code>{g.id}</code>)\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi guruh yaratish", callback_data="adm_create_group")],
            [InlineKeyboardButton(text="👥 Guruh a'zolarini ko'rish", callback_data="adm_view_group_prompt")]
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.in_(["adm_create_group", "adm_add_group"]))
async def start_create_group_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminGroupState.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        "➕ Yangi guruh yoki sinf nomini kiriting:\n"
        "(Masalan: 9-A sinf yoki Fizika Olimpiada guruhi)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminGroupState.waiting_for_name)
async def process_group_name(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text.strip()
    group_repo = GroupRepository(session)

    existing = await group_repo.get_by_name(name)
    if existing:
        await message.answer("❌ Bu nomdagi guruh allaqachon mavjud. Boshqa nom kiriting:")
        return

    group = await group_repo.create(name=name, created_by=message.from_user.id)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ «{html.escape(group.name)}» guruhi muvaffaqiyatli yaratildi!\n"
        f"Guruh ID: {group.id}",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_view_group_prompt")
async def view_group_prompt_callback(callback: CallbackQuery, session: AsyncSession):
    group_repo = GroupRepository(session)
    groups = await group_repo.get_all_groups_with_member_count()
    if not groups:
        await callback.answer("Guruhlar mavjud emas. Avval guruh yarating.", show_alert=True)
        return

    buttons = []
    for g, count in groups:
        buttons.append([InlineKeyboardButton(text=f"👥 {g.name} ({count} ta)", callback_data=f"adm_view_group:{g.id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="adm_nav_settings_main")])

    await callback.answer()
    try:
        await callback.message.edit_text(
            "👥 Qaysi guruhni ko‘rmoqchisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_view_group:"))
async def view_group_details_callback(callback: CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split(":")[1])
    group_repo = GroupRepository(session)

    group = await group_repo.get_by_id(group_id)
    if not group:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return

    members = await group_repo.get_group_members(group_id)

    safe_gname = html.escape(group.name)
    text = f"👥 Guruh: {safe_gname}\n"
    text += f"📊 A’zolar soni: {len(members)} ta\n\n"

    if not members:
        text += "Guruhda hozircha a’zolar yo‘q.\n"
    else:
        for idx, m in enumerate(members[:20], start=1):
            safe_uname = html.escape(m.full_name or "O‘quvchi")
            safe_un = f"@{m.username}" if m.username else f"ID: {m.telegram_id}"
            text += f"{idx}. {safe_uname} ({safe_un})\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ O‘quvchi qo‘shish", callback_data=f"adm_add_member:{group.id}")],
            [InlineKeyboardButton(text="🗑 Guruhni o‘chirish", callback_data=f"adm_del_group:{group.id}")],
            [InlineKeyboardButton(text="◀️ Guruhlar ro‘yxati", callback_data="adm_view_group_prompt")]
        ]
    )

    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_add_member:"))
async def add_member_prompt(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split(":")[1])
    await state.update_data(target_group_id=group_id)
    await state.set_state(AdminGroupState.waiting_for_student_id_to_add)
    await callback.answer()
    await callback.message.answer(
        "➕ Guruhga qo‘shmoqchi bo‘lgan o‘quvchining Telegram ID yoki telefon raqamini kiriting:\n"
        "(Masalan: 8420258761 yoki +998901234567)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminGroupState.waiting_for_student_id_to_add)
async def process_add_member_id(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    data = await state.get_data()
    group_id = data.get("target_group_id")

    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)

    user = None
    if val.isdigit():
        user = await user_repo.get_by_telegram_id(int(val))
        if not user:
            user = await user_repo.get_by_id(int(val))
    elif val.startswith("+") or val.startswith("998"):
        user = await user_repo.get_by_phone(val)

    if not user:
        await message.answer("❌ O‘quvchi topilmadi. Qaytadan kiriting (yoki Bekor qilishni bosing):", reply_markup=get_cancel_keyboard())
        return

    await group_repo.add_member(group_id=group_id, user_id=user.id)
    await session.commit()
    await state.clear()
    safe_name = html.escape(user.full_name or "O‘quvchi")
    await message.answer(
        f"✅ {safe_name} guruhga muvaffaqiyatli qo‘shildi!",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_del_group:"))
async def delete_group_callback(callback: CallbackQuery, session: AsyncSession):
    group_id = int(callback.data.split(":")[1])
    group_repo = GroupRepository(session)
    await group_repo.delete(group_id)
    await session.commit()
    await callback.answer("🗑 Guruh o‘chirildi!", show_alert=True)
    await view_group_prompt_callback(callback, session)
