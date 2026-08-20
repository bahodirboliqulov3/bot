import html
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.user_repo import UserRepository

router = Router(name="student_guide_and_settings")


def get_guide_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Testni qanday ishlayman?", callback_data="faq:how_to_test")
            ],
            [
                InlineKeyboardButton(text="⚡ 1 soniyada javob tekshirish", callback_data="faq:quick_check")
            ],
            [
                InlineKeyboardButton(text="🏆 Reyting va Ballar tizimi", callback_data="faq:rating")
            ],
            [
                InlineKeyboardButton(text="👨🏫 O‘qituvchilar uchun qo‘llanma", callback_data="faq:teacher")
            ],
            [
                InlineKeyboardButton(text="📨 Adminga to‘g‘ridan-to‘g‘ri yozish", callback_data="student_support_prompt")
            ]
        ]
    )


@router.message(StateFilter("*"), F.text.in_(["📘 Qo‘llanma", "📘 Qo'llanma", "Qo‘llanma", "Qo'llanma", "ℹ️ Yordam", "ℹ️ Qo‘llanma va Yordam", "🆘 Yordam"]))
async def show_combined_guide_and_help(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "📘 BOTDAN FOYDALANISH QO‘LLANMASI 📚\n\n"
        "Platformamizdan to‘g‘ri, tezkor va samarali foydalanish uchun quyidagi mavzulardan birini tanlang:"
    )
    await message.answer(text, reply_markup=get_guide_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "faq:menu")
async def faq_menu_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📘 BOTDAN FOYDALANISH QO‘LLANMASI 📚\n\n"
        "Kerakli bo‘limni tanlang:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_guide_keyboard(), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "faq:how_to_test")
async def faq_how_to_test(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📝 Testni qanday ishlash kerak?\n\n"
        "1. «📝 Testlar» bo‘limiga kiring va faol testni tanlang.\n"
        "2. Agar sizda test kodi bo‘lsa (masalan: <code>TEST-101</code>), uni bitta xabarda yuboring.\n"
        "3. Test savollariga javob berib, «🏁 Testni yakunlash» tugmasini bosing.\n"
        "4. Natijangiz, xatolar tahlili va PDF hisobotingiz bir zumda ekranda chiqadi! 🚀"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Barcha savollar", callback_data="faq:menu")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "faq:quick_check")
async def faq_quick_check(callback: CallbackQuery):
    await callback.answer()
    text = (
        "⚡ 1 soniyada javob tekshirish siri:\n\n"
        "Hech qanday tugmani bosmasdan ham, botga to‘g‘ridan-to‘g‘ri yozib yuborishingiz mumkin:\n\n"
        "👉 <code>TEST-101 ABCDACBDABCD</code>\n"
        "yoki\n"
        "👉 <code>TEST-101 1a 2b 3c 4d 5a</code>\n\n"
        "Bot avtomatik tarzda testingizni hisoblab, to‘liq baho va xatolar ro‘yxatini chiqarib beradi! 🎯"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Barcha savollar", callback_data="faq:menu")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "faq:rating")
async def faq_rating(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🏆 Reyting va Ballar qanday hisoblanadi?\n\n"
        "• Har bir to‘g‘ri ishlangan test sizga ballar va reyting o‘rnini oshirish imkonini beradi.\n"
        "• «🏆 Reyting» bo‘limida umumiy TOP-10 talik hamda o‘z guruhingiz ichidagi o‘rningizni jonli kuzatib borishingiz mumkin! 🥇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Barcha savollar", callback_data="faq:menu")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "faq:teacher")
async def faq_teacher(callback: CallbackQuery):
    await callback.answer()
    text = (
        "👨🏫 O‘qituvchilar va Repetitorlar uchun:\n\n"
        "• O‘z o‘quvchilaringiz uchun tezkor test yaratish uchun <code>/fast_test</code> buyrug‘idan foydalaning:\n"
        "<code>/fast_test Matematika 10-sinf | ABCDABCD | 40</code>\n\n"
        "• Bot sizga test kodini beradi. O‘quvchilaringiz shu kod orqali javoblarni yuboradi va siz barcha natijalarni Excel (.xlsx) faylida yuklab olishingiz mumkin! 📊"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Barcha savollar", callback_data="faq:menu")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
