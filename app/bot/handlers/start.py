import html
import logging
from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.handlers.student.tests_list import send_test_to_student
from app.bot.keyboards.inline_keyboards import get_channel_subscription_keyboard
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.registration_state import RegistrationState
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.channel_service import ChannelService
from app.services.profanity_service import ProfanityService

logger = logging.getLogger(__name__)
router = Router(name="start")

REGIONS = [
    ["📍 Toshkent sh.", "📍 Toshkent vil."],
    ["📍 Samarqand", "📍 Farg‘ona"],
    ["📍 Andijon", "📍 Namangan"],
    ["📍 Buxoro", "📍 Xorazm"],
    ["📍 Qashqadaryo", "📍 Surxondaryo"],
    ["📍 Navoiy", "📍 Jizzax"],
    ["📍 Sirdaryo", "📍 Qoraqalpog‘iston"]
]

ROLES = [
    [InlineKeyboardButton(text="🎒 1-sinf", callback_data="role:1-sinf"), InlineKeyboardButton(text="🎒 2-sinf", callback_data="role:2-sinf")],
    [InlineKeyboardButton(text="🎒 3-sinf", callback_data="role:3-sinf"), InlineKeyboardButton(text="🎒 4-sinf", callback_data="role:4-sinf")],
    [InlineKeyboardButton(text="🎒 5-sinf", callback_data="role:5-sinf"), InlineKeyboardButton(text="🎒 6-sinf", callback_data="role:6-sinf")],
    [InlineKeyboardButton(text="🎒 7-sinf", callback_data="role:7-sinf"), InlineKeyboardButton(text="🎒 8-sinf", callback_data="role:8-sinf")],
    [InlineKeyboardButton(text="🎒 9-sinf", callback_data="role:9-sinf"), InlineKeyboardButton(text="🎓 10-sinf", callback_data="role:10-sinf")],
    [InlineKeyboardButton(text="🎓 11-sinf", callback_data="role:11-sinf"), InlineKeyboardButton(text="🏛 Abituriyent / Talaba", callback_data="role:Abituriyent")],
    [InlineKeyboardButton(text="👨🏫 O‘qituvchi / Repetitor", callback_data="role:O‘qituvchi")]
]


def get_regions_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for row in REGIONS:
        buttons.append([InlineKeyboardButton(text=r, callback_data=f"region:{r.replace('📍 ', '')}") for r in row])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_phone_registration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True
    )


@router.message(CommandStart())
async def start_command(message: Message, command: CommandObject, state: FSMContext, bot: Bot, session: AsyncSession):
    await state.clear()
    user_id = message.from_user.id
    auth_service = AuthService(session)
    user_repo = UserRepository(session)
    is_admin = await auth_service.is_admin(user_id)

    # 1. Check required channels (admins bypass)
    if not is_admin:
        channel_service = ChannelService(session)
        is_subbed, unsubs = await channel_service.check_user_subscriptions(bot, user_id)
        if not is_subbed and unsubs:
            await message.answer(
                "📢 Botdan foydalanish uchun quyidagi kanallarga a’zo bo‘ling:",
                reply_markup=get_channel_subscription_keyboard(unsubs),
                parse_mode="HTML"
            )
            return

    # Deep linking check: e.g. /start test_TEST101
    deep_test_code = None
    if command.args and command.args.startswith("test_"):
        deep_test_code = command.args.replace("test_", "").strip().upper()

    user = await user_repo.get_by_telegram_id(user_id)
    # If already fully registered (has phone and school)
    if user and user.phone_number and user.school and user.school != "Kiritilmagan":
        if deep_test_code:
            test_repo = TestRepository(session)
            test = await test_repo.get_by_code(deep_test_code)
            if test:
                await send_test_to_student(message, test, bot)
                return

        safe_fn = html.escape(user.first_name or "Foydalanuvchi")
        welcome_text = (
            f"⚡ <b>Xush kelibsiz, {safe_fn}!</b>\n\n"
            "╔══════════════════════╗\n"
            "║  🎯  TEST PLATFORMASI  ║\n"
            "╚══════════════════════╝\n\n"
            "🚀 <b>Tezkor test topshirish:</b>\n"
            "<blockquote>Test kodi + javoblarni bitta xabarda yuboring:\n"
            "<code>TEST-101 ABCDABCD...</code></blockquote>\n\n"
            "📌 <b>Menyudan bo'limni tanlang:</b>"
        )
        await message.answer(
            welcome_text,
            reply_markup=get_student_main_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )
        return

    # Start Interactive Onboarding for New or Incomplete User
    if deep_test_code:
        await state.update_data(pending_test_code=deep_test_code)

    raw_fn = message.from_user.first_name or "Foydalanuvchi"
    raw_ln = message.from_user.last_name or ""
    tg_name = f"{raw_fn} {raw_ln}".strip() or "Foydalanuvchi"

    # Check if Telegram account name itself contains profanity
    if ProfanityService.contains_profanity(tg_name):
        await state.set_state(RegistrationState.waiting_for_name)
        await message.answer(
            "🎉 <b>Xush kelibsiz!</b>\n\n"
            "╔══════════════════════╗\n"
            "║  🎯  TEST PLATFORMASI  ║\n"
            "╚══════════════════════╝\n\n"
            "📋 Profilingizni <b>30 soniyada</b> to'ldiring va testlarga kiring!\n\n"
            "<b>1️⃣ / 4</b>  ━━━━━░░░░░░  <i>25%</i>\n\n"
            "✏️ <b>Ism va Familiyangizni kiriting:</b>\n"
            "<i>(Masalan: Jasur Aliyev)</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(first_name=raw_fn, last_name=raw_ln)
    await state.set_state(RegistrationState.confirm_name)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Ha, {tg_name}", callback_data="name_confirm_yes")],
            [InlineKeyboardButton(text="✏️ Boshqa ism-familiya kiritish", callback_data="name_confirm_no")]
        ]
    )

    safe_tg_name = html.escape(tg_name)
    onboard_msg = (
        "🎉 <b>Xush kelibsiz!</b>\n\n"
        "╔══════════════════════╗\n"
        "║  🎯  TEST PLATFORMASI  ║\n"
        "╚══════════════════════╝\n\n"
        "📋 Profilingizni <b>30 soniyada</b> to'ldiring va testlarga kiring!\n\n"
        f"<b>1️⃣ / 4</b>  ━━━━━░░░░░░  <i>25%</i>\n\n"
        f"🙋 Ismingiz <b>{safe_tg_name}</b> — to'g'rimi?"
    )

    await message.answer(onboard_msg, reply_markup=kb, parse_mode="HTML")


# Step 1: Name Confirmation
@router.callback_query(F.data == "name_confirm_yes")
async def name_confirmed_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RegistrationState.choose_region)
    try:
        await callback.message.edit_text(
            "<b>2️⃣ / 4</b>  ━━━━━━━━░░░  <i>50%</i>\n\n"
            "📍 <b>Qaysi viloyat yoki hududdansiz?</b>\n"
            "Quyidagi ro'yxatdan tanlang:",
            reply_markup=get_regions_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data == "name_confirm_no")
async def name_change_prompt_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RegistrationState.waiting_for_name)
    await callback.message.answer(
        "✏️ Ism va Familiyangizni kiriting:\n(Masalan: Jasur Aliyev)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(RegistrationState.waiting_for_name)
async def process_custom_name(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if ProfanityService.contains_profanity(raw_text) or len(raw_text) < 3:
        await message.answer(
            "⚠️ <b>Nomaqbul yoki noto'g'ri ism kiritildi!</b>\n\n"
            "Iltimos, o'zingizning haqiqiy va odobli ism-familiyangizni kiriting:\n"
            "<i>(Masalan: Jasur Aliyev)</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    parts = raw_text.split(maxsplit=1)
    fn = parts[0]
    ln = parts[1] if len(parts) > 1 else ""

    await state.update_data(first_name=fn, last_name=ln)
    await state.set_state(RegistrationState.choose_region)

    safe_name = html.escape(f"{fn} {ln}".strip())
    await message.answer(
        f"✅ Rahmat, <b>{safe_name}</b>!\n\n"
        "<b>2️⃣ / 4</b>  ━━━━━━━━░░░  <i>50%</i>\n\n"
        "📍 <b>Endi viloyatingizni tanlang:</b>",
        reply_markup=get_regions_keyboard(),
        parse_mode="HTML"
    )


# Step 2: Region Selection -> School Input
@router.callback_query(F.data.startswith("region:"))
async def region_chosen_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    region = callback.data.split(":")[1]
    await state.update_data(region=region)
    await state.set_state(RegistrationState.waiting_for_school)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"<b>3️⃣ / 4</b>  ━━━━━━━━━━░  <i>75%</i>\n\n"
        f"✅ Hudud: <b>{html.escape(region)}</b>\n\n"
        "🏫 <b>Ta'lim muassasangiz nomini kiriting:</b>\n"
        "<i>(Masalan: 15-maktab, Prezident maktabi, 1-Akademik litsey)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


# Step 3: School Input -> Role/Grade Selection
@router.message(RegistrationState.waiting_for_school)
async def process_school_input(message: Message, state: FSMContext):
    school_name = message.text.strip()
    if ProfanityService.contains_profanity(school_name) or len(school_name) < 2:
        await message.answer(
            "⚠️ <b>Nomaqbul yoki noto'g'ri muassasa nomi kiritildi!</b>\n\n"
            "Iltimos, ta'lim muassasangiz nomini to'g'ri kiriting:\n"
            "<i>(Masalan: 15-maktab, Prezident maktabi, 1-Akademik litsey)</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(school=school_name)
    await state.set_state(RegistrationState.choose_role)

    await message.answer(
        f"<b>4️⃣ / 4</b>  ━━━━━━━━━━━  <i>90%</i>\n\n"
        f"✅ Muassasa: <b>{html.escape(school_name)}</b>\n\n"
        "🎓 <b>Sinfingiz yoki faoliyat toifangizni tanlang:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=ROLES),
        parse_mode="HTML"
    )


# Step 4: Role Selection -> Phone Request
@router.callback_query(F.data.startswith("role:"))
async def role_chosen_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    role = callback.data.split(":")[1]
    await state.update_data(role=role)
    await state.set_state(RegistrationState.waiting_for_phone)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🏁 <b>Oxirgi qadam!</b>  ━━━━━━━━━━━  <i>95%</i>\n\n"
        f"✅ Toifa: <b>{html.escape(role)}</b>\n\n"
        "📱 <b>Telefon raqamingizni yuboring:</b>\n"
        "<i>«📞 Telefon raqamni yuborish» tugmasini bosing:</i>",
        reply_markup=get_phone_registration_keyboard(),
        parse_mode="HTML"
    )


# Step 5: Phone Contact or Text Input & Finish
@router.message(RegistrationState.waiting_for_phone, F.contact)
@router.message(F.contact)
async def process_phone_contact(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await finish_registration(message, state, phone, bot, session)


@router.message(RegistrationState.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    text = message.text.strip()
    # Accept phone number format
    cleaned_digits = "".join(ch for ch in text if ch.isdigit() or ch == '+')
    if len(cleaned_digits) < 7:
        await message.answer("❌ Iltimos, to‘g‘ri telefon raqam kiriting (masalan: +998901234567):", parse_mode="HTML")
        return
    if not cleaned_digits.startswith("+"):
        cleaned_digits = "+" + cleaned_digits
    await finish_registration(message, state, cleaned_digits, bot, session)


async def finish_registration(message: Message, state: FSMContext, phone: str, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    auth_service = AuthService(session)

    fn = data.get("first_name", message.from_user.first_name or "Foydalanuvchi")
    ln = data.get("last_name", message.from_user.last_name or "")
    region = data.get("region", "O‘zbekiston")
    school = data.get("school", "Kiritilmagan")
    role = data.get("role", "Umumiy")
    pending_code = data.get("pending_test_code")

    user = await auth_service.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=fn,
        last_name=ln,
        phone_number=phone,
        school=f"{region}, {school}" if school != "Kiritilmagan" else region,
        grade=role
    )
    await session.commit()

    await state.clear()
    is_admin = await auth_service.is_admin(user.telegram_id)

    safe_first_name = html.escape(user.first_name or "Foydalanuvchi")
    safe_region = html.escape(region)
    safe_school = html.escape(school)
    safe_role = html.escape(role)
    safe_phone = html.escape(phone)

    congrats_text = (
        f"🎊 <b>100% — Profil yaratildi!</b>\n\n"
        f"🌟 <b>Xush kelibsiz, {safe_first_name}!</b>\n\n"
        f"<blockquote>📍 Hudud: <b>{safe_region}</b>\n"
        f"🏫 Muassasa: <b>{safe_school}</b>\n"
        f"🎓 Toifa: <b>{safe_role}</b>\n"
        f"📞 Telefon: <code>{safe_phone}</code></blockquote>\n\n"
        "🚀 <b>Endi nima qilishingiz mumkin:</b>\n"
        "• 📝 Test ishlash — kodni yuboring\n"
        "• 🏆 Reytingda o'z o'rningizni ko'ring\n"
        "• 🎖 Sertifikat oling!\n\n"
        "<i>💡 Test boshlash: <code>TEST-101 ABCD...</code> yuboring</i>"
    )

    await message.answer(congrats_text, reply_markup=get_student_main_keyboard(is_admin=is_admin), parse_mode="HTML")

    # Send instant full notification to the Admin/Owner
    try:
        from app.config import settings
        if settings.OWNER_ID and settings.OWNER_ID != user.telegram_id:
            admin_notify_text = (
                f"👤 Yangi o‘quvchi to‘liq ro‘yxatdan o‘tdi!\n\n"
                f"🔹 Ism: {safe_first_name} {html.escape(ln)}\n"
                f"🆔 Telegram ID: {user.telegram_id}\n"
                f"🔗 Username: @{html.escape(message.from_user.username or 'yoq')}\n"
                f"📞 Telefon: {safe_phone}\n"
                f"📍 Hudud: {safe_region}\n"
                f"🏫 Muassasa: {safe_school}\n"
                f"🎓 Sinf/Toifa: {safe_role}\n"
            )
            await bot.send_message(chat_id=settings.OWNER_ID, text=admin_notify_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")

    if pending_code:
        test_repo = TestRepository(session)
        test = await test_repo.get_by_code(pending_code)
        if test:
            await send_test_to_student(message, test, bot)


@router.callback_query(F.data == "check_channel_subs")
async def check_channel_subs_callback(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    await callback.answer("✅ A’zolik tekshirilmoqda...")
    user_id = callback.from_user.id
    channel_service = ChannelService(session)
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(user_id)

    is_subbed, unsubs = await channel_service.check_user_subscriptions(bot, user_id)
    if not is_subbed and unsubs:
        await callback.answer("❌ Hali hamma kanallarga a’zo bo‘lmadingiz!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"👋 Xush kelibsiz, {callback.from_user.first_name}!\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang:",
        reply_markup=get_student_main_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
