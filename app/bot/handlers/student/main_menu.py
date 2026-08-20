from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_student_main_keyboard
from app.bot.states.student_states import QuickCheckState, TestByCodeState
from app.database.repositories.certificate_repo import CertificateRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.scoring_service import ScoringService
from app.services.profanity_service import ProfanityService
import html

router = Router(name="student_main_menu")


async def send_or_edit_profile_ui(target: Message | CallbackQuery, text: str, kb: InlineKeyboardMarkup, bot: Bot, user_id: int):
    if isinstance(target, Message):
        try:
            photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
            if photos.total_count > 0:
                photo_file_id = photos.photos[0][-1].file_id
                await target.answer_photo(photo=photo_file_id, caption=text, reply_markup=kb, parse_mode="HTML")
                return
        except Exception:
            pass
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        try:
            if target.message.photo:
                await target.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


@router.message(StateFilter("*"), F.text.in_(["✅ Javobni tekshirish", "🔗 Test kodi", "🔗 Test kodi orqali kirish", "📝 Testlar"]))
async def enter_test_code_handler(message: Message, state: FSMContext):
    await state.set_state(TestByCodeState.waiting_for_code)
    await message.answer(
        "🔗 Test kodini kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


# 👤 Profilim bo'limi
from app.bot.states.registration_state import RegistrationState
from app.bot.states.student_states import ProfileEditState

PROF_REGIONS = [
    ["📍 Toshkent sh.", "📍 Toshkent vil."],
    ["📍 Samarqand", "📍 Farg‘ona"],
    ["📍 Andijon", "📍 Namangan"],
    ["📍 Buxoro", "📍 Xorazm"],
    ["📍 Qashqadaryo", "📍 Surxondaryo"],
    ["📍 Navoiy", "📍 Jizzax"],
    ["📍 Sirdaryo", "📍 Qoraqalpog‘iston"]
]

PROF_ROLES = [
    [InlineKeyboardButton(text="🎒 1-sinf", callback_data="prof_set_role:1-sinf"), InlineKeyboardButton(text="🎒 2-sinf", callback_data="prof_set_role:2-sinf")],
    [InlineKeyboardButton(text="🎒 3-sinf", callback_data="prof_set_role:3-sinf"), InlineKeyboardButton(text="🎒 4-sinf", callback_data="prof_set_role:4-sinf")],
    [InlineKeyboardButton(text="🎒 5-sinf", callback_data="prof_set_role:5-sinf"), InlineKeyboardButton(text="🎒 6-sinf", callback_data="prof_set_role:6-sinf")],
    [InlineKeyboardButton(text="🎒 7-sinf", callback_data="prof_set_role:7-sinf"), InlineKeyboardButton(text="🎒 8-sinf", callback_data="prof_set_role:8-sinf")],
    [InlineKeyboardButton(text="🎒 9-sinf", callback_data="prof_set_role:9-sinf"), InlineKeyboardButton(text="🎓 10-sinf", callback_data="prof_set_role:10-sinf")],
    [InlineKeyboardButton(text="🎓 11-sinf", callback_data="prof_set_role:11-sinf"), InlineKeyboardButton(text="🏛 Abituriyent / Talaba", callback_data="prof_set_role:Abituriyent")],
    [InlineKeyboardButton(text="👨🏫 O‘qituvchi / Repetitor", callback_data="prof_set_role:O‘qituvchi")],
    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="prof_edit_menu")]
]


def render_profile_card(user, results: list, certs: list) -> tuple[str, InlineKeyboardMarkup]:
    tests_taken = len(results)
    avg_score = (sum(r.percentage for r in results) / tests_taken) if tests_taken > 0 else 0

    rank_title, badge, next_hint = ScoringService.get_user_rank_title(tests_taken, avg_score)

    safe_name = html.escape(user.full_name or "Foydalanuvchi")
    safe_username = html.escape(user.username or "yo‘q")
    safe_school = html.escape(user.school or "Kiritilmagan")
    safe_grade = html.escape(user.grade or "Umumiy")
    safe_phone = html.escape(user.phone_number or "Kiritilmagan")
    phone_display = f"<code>{safe_phone}</code>" if user.phone_number else "Kiritilmagan"

    # Progress bar toward next rank
    rank_levels = [0, 3, 10, 25, 50]
    next_lvl = next((l for l in rank_levels if l > tests_taken), 50)
    prev_lvl = max((l for l in rank_levels if l <= tests_taken), default=0)
    span = max(next_lvl - prev_lvl, 1)
    done = tests_taken - prev_lvl
    bar_filled = min(10, int(done / span * 10))
    rank_bar = "█" * bar_filled + "░" * (10 - bar_filled)

    profile_text = (
        f"╔══════════════════════╗\n"
        f"║   👤  FOYDALANUVCHI   ║\n"
        f"╚══════════════════════╝\n\n"
        f"🌟 <b>{safe_name}</b>\n"
        f"🔹 ID: <code>{user.telegram_id}</code>  |  @{safe_username}\n"
        f"📞 Tel: {phone_display}\n"
        f"🏫 {safe_school}  •  🎓 {safe_grade}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎖 Unvon: {badge} <b>{rank_title}</b>\n"
        f"📈 [{rank_bar}] {tests_taken}/{next_lvl} test\n"
        f"<i>💡 {next_hint}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Ishlangan testlar: <b>{tests_taken} ta</b>\n"
        f"• O'rtacha natija: <b>{avg_score:.1f}%</b>\n"
        f"• Sertifikatlar: <b>{len(certs)} ta</b>\n"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="prof_edit_menu"),
                InlineKeyboardButton(text="🔄 Qayta ro‘yxatdan o‘tish", callback_data="prof_restart_reg")
            ]
        ]
    )
    return profile_text, kb




@router.message(StateFilter("*"), F.text.in_(["👤 Profilim", "👤 Profil", "Profilim", "Profil"]))
async def my_profile_handler(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)

    profile_text, kb = render_profile_card(user, results, certs)
    await send_or_edit_profile_ui(message, profile_text, kb, bot, message.from_user.id)


@router.callback_query(F.data == "prof_view")
async def prof_view_callback(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)

    profile_text, kb = render_profile_card(user, results, certs)
    await callback.answer()
    await send_or_edit_profile_ui(callback, profile_text, kb, bot, callback.from_user.id)


@router.callback_query(F.data.in_(["prof_edit_menu", "edit_school_grade"]))
async def prof_edit_menu_callback(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Ism-Familiya", callback_data="prof_edit_name"),
                InlineKeyboardButton(text="📍 Viloyat / Hudud", callback_data="prof_edit_region")
            ],
            [
                InlineKeyboardButton(text="🏫 Maktab / Muassasa", callback_data="prof_edit_school"),
                InlineKeyboardButton(text="🎓 Sinf / Toifa", callback_data="prof_edit_grade")
            ],
            [
                InlineKeyboardButton(text="📞 Telefon raqam", callback_data="prof_edit_phone")
            ],
            [
                InlineKeyboardButton(text="◀️ Profilga qaytish", callback_data="prof_view")
            ]
        ]
    )
    edit_text = "✏️ Profilning qaysi ma’lumotini o‘zgartirmoqchisiz?\nQuyidagilardan birini tanlang:"
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=edit_text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(edit_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# Edit Name
@router.callback_query(F.data == "prof_edit_name")
async def prof_edit_name_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditState.waiting_for_name)
    await callback.answer()
    await callback.message.answer(
        "✏️ Yangi Ism va Familiyangizni kiriting:\n(Masalan: Jasur Aliyev)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(ProfileEditState.waiting_for_name)
async def process_profile_new_name(message: Message, state: FSMContext, session: AsyncSession):
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

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user:
        user.first_name = fn
        user.last_name = ln
        await session.commit()

    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)

    await message.answer("✅ Ism-familiyangiz muvaffaqiyatli yangilandi!", reply_markup=get_student_main_keyboard(is_admin=is_admin))
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)
    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)
    text, kb = render_profile_card(user, results, certs)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# Edit Region
@router.callback_query(F.data == "prof_edit_region")
async def prof_edit_region_callback(callback: CallbackQuery):
    await callback.answer()
    buttons = []
    for row in PROF_REGIONS:
        buttons.append([InlineKeyboardButton(text=r, callback_data=f"prof_set_reg:{r.replace('📍 ', '')}") for r in row])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="prof_edit_menu")])

    text_msg = "📍 Viloyat yoki hududingizni tanlang:"
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text_msg, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("prof_set_reg:"))
async def prof_set_region_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    region = callback.data.split(":")[1]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if user:
        current_school = user.school or ""
        # Keep school name if existing
        if ", " in current_school:
            parts = current_school.split(", ", 1)
            user.school = f"{region}, {parts[1]}"
        else:
            user.school = region
        await session.commit()

    await callback.answer("📍 Hudud yangilandi!")
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)
    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)
    text, kb = render_profile_card(user, results, certs)
    await send_or_edit_profile_ui(callback, text, kb, bot, callback.from_user.id)


# Edit School
@router.callback_query(F.data == "prof_edit_school")
async def prof_edit_school_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditState.waiting_for_school)
    await callback.answer()
    await callback.message.answer(
        "🏫 Maktab yoki ta’lim muassasangiz nomini kiriting:\n(Masalan: 15-maktab yoki 1-IDUM)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(ProfileEditState.waiting_for_school)
async def process_profile_new_school(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
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

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user:
        user.school = school_name
        await session.commit()

    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)

    await message.answer("✅ Ta’lim muassasangiz muvaffaqiyatli saqlandi!", reply_markup=get_student_main_keyboard(is_admin=is_admin))
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)
    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)
    text, kb = render_profile_card(user, results, certs)
    await send_or_edit_profile_ui(message, text, kb, bot, message.from_user.id)


# Edit Grade / Role
@router.callback_query(F.data == "prof_edit_grade")
async def prof_edit_grade_callback(callback: CallbackQuery):
    await callback.answer()
    text_msg = "🎓 Sinfingiz yoki toifangizni tanlang:"
    kb = InlineKeyboardMarkup(inline_keyboard=PROF_ROLES)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text_msg, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("prof_set_role:"))
async def prof_set_role_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    role = callback.data.split(":")[1]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if user:
        user.grade = role
        await session.commit()

    await callback.answer("🎓 Sinf/Toifa yangilandi!")
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)
    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)
    text, kb = render_profile_card(user, results, certs)
    await send_or_edit_profile_ui(callback, text, kb, bot, callback.from_user.id)


# Edit Phone
@router.callback_query(F.data == "prof_edit_phone")
async def prof_edit_phone_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditState.waiting_for_phone)
    await callback.answer()
    from app.bot.keyboards.reply_keyboards import get_phone_request_keyboard
    await callback.message.answer(
        "📱 Telefon raqamingizni yuboring:\nQuyidagi tugmani bosing yoki raqamingizni yozing (+998901234567):",
        reply_markup=get_phone_request_keyboard(),
        parse_mode="HTML"
    )


@router.message(ProfileEditState.waiting_for_phone, F.contact)
@router.message(ProfileEditState.waiting_for_phone, F.text)
async def process_profile_new_phone(message: Message, state: FSMContext, session: AsyncSession):
    phone = message.contact.phone_number if message.contact else message.text.strip()
    if not phone.startswith("+") and phone.isdigit():
        phone = "+" + phone

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user:
        user.phone_number = phone
        await session.commit()

    await state.clear()
    auth_service = AuthService(session)
    is_admin = await auth_service.is_admin(message.from_user.id)

    await message.answer("✅ Telefon raqamingiz saqlandi!", reply_markup=get_student_main_keyboard(is_admin=is_admin))
    result_repo = ResultRepository(session)
    cert_repo = CertificateRepository(session)
    results = await result_repo.get_user_results(user.id)
    certs = await cert_repo.get_user_certificates(user.id)
    text, kb = render_profile_card(user, results, certs)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# Restart Full Onboarding
@router.callback_query(F.data == "prof_restart_reg")
async def prof_restart_registration_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    raw_fn = callback.from_user.first_name or "Foydalanuvchi"
    raw_ln = callback.from_user.last_name or ""
    tg_name = f"{raw_fn} {raw_ln}".strip() or "Foydalanuvchi"
    await state.update_data(first_name=raw_fn, last_name=raw_ln)
    await state.set_state(RegistrationState.confirm_name)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Ha, {tg_name}", callback_data="name_confirm_yes")],
            [InlineKeyboardButton(text="✏️ Boshqa ism-familiya kiritish", callback_data="name_confirm_no")]
        ]
    )

    safe_tg_name = html.escape(tg_name)
    try:
        await callback.message.edit_text(
            f"🔄 Qayta ro‘yxatdan o‘tish:\n\n1️⃣ Ism-familiyangiz: {safe_tg_name} to‘g‘rimi?",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception:
        pass
