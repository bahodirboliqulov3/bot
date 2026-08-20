from pathlib import Path
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.bot.keyboards.reply_keyboards import get_cancel_keyboard, get_admin_main_keyboard
from app.bot.states.admin_states import AdminExcelImportState
from app.config import settings
from app.database.models.test import Question, TestStatus
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.excel_service import ExcelService
import html

router = Router(name="admin_excel_handler")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text.in_(["📁 Excel boshqaruvi", "📥 Excel import", "📤 Excel eksport"]))
async def admin_excel_main_menu(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Savollarni yuklash (Excel Import)", callback_data="adm_xl_import_start")],
            [InlineKeyboardButton(text="📄 Namuna shablonni yuklab olish (.xlsx)", callback_data="adm_xl_download_template")],
            [InlineKeyboardButton(text="📤 Test natijalarini yuklab olish (Excel)", callback_data="adm_xl_export_start")],
            [InlineKeyboardButton(text="👥 Barcha o'quvchilarni yuklab olish (.xlsx)", callback_data="adm_export_users_excel")],
            [InlineKeyboardButton(text="📑 Barcha o'quvchilar ro'yxati (.pdf)", callback_data="adm_export_users_pdf")]
        ]
    )
    await message.answer(
        "📁 <b>Excel & Hujjatlar Boshqaruvi:</b>\n\n"
        "Kerakli amaliyotni tanlang:\n\n"
        "• <b>Savollarni yuklash:</b> Excel fayl orqali testga savollarni bir zumda qo'shish\n"
        "• <b>Namuna shablon:</b> Savollar qanday tartibda to'ldirilishi kerakligini ko'rsatuvchi tayyor fayl\n"
        "• <b>Natijalarni eksport:</b> Har bir test bo'yicha o'quvchilar ballari va javoblari\n"
        "• <b>O'quvchilar bazasi:</b> Barcha foydalanuvchilar to'liq ro'yxati",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_xl_download_template")
async def download_excel_template_callback(callback: CallbackQuery):
    await callback.answer("📄 Shablon tayyorlanmoqda...")
    template_path = ExcelService.generate_sample_questions_template()

    caption = (
        "📄 <b>Savollar kiritish uchun Namuna Shablon (.xlsx)</b>\n\n"
        "<b>Ustunlar tartibi:</b>\n"
        "1. <b>Savol matni:</b> Savol mazmuni\n"
        "2. <b>A, B, C, D variantlari:</b> Javob variantlari\n"
        "3. <b>To'g'ri javob:</b> A, B, C yoki D\n"
        "4. <b>Ball:</b> Savol uchun beriladigan ball (standart 1.0)\n\n"
        "<i>💡 Faylni to'ldirib, «📥 Savollarni yuklash» bo'limi orqali testga biriktiring!</i>"
    )
    await callback.message.answer_document(
        document=FSInputFile(path=str(template_path), filename="Savollar_Namuna_Shablon.xlsx"),
        caption=caption,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_xl_import_start")
async def admin_excel_import_menu(callback: CallbackQuery, session: AsyncSession):
    test_repo = TestRepository(session)
    tests = await test_repo.get_all(limit=25)

    if not tests:
        await callback.answer("Testlar topilmadi. Avval yangi test yarating.", show_alert=True)
        return

    buttons = []
    for t in tests:
        buttons.append([InlineKeyboardButton(text=f"📝 {t.title} ({t.code})", callback_data=f"adm_import_xl:{t.id}")])

    await callback.answer()
    await callback.message.answer(
        "📥 <b>Qaysi testga Excel orqali savollarni yuklamoqchisiz?</b>\n\n"
        "Kerakli testni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_import_xl:"))
async def ask_for_excel_file(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)
    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    await state.update_data(excel_test_id=test_id)
    await state.set_state(AdminExcelImportState.waiting_for_file)
    await callback.answer()

    await callback.message.answer(
        f"📥 <b>«{html.escape(test.title)}»</b> ({test.code}) testi uchun Excel (.xlsx) faylni yuboring:\n\n"
        "<b>Ustunlar:</b> <code>Savol | A | B | C | D | To'g'ri javob | Ball</code>\n\n"
        "<i>💡 Agar shablon bo'lmasa, avval bosh menyudan namuna shablonni yuklab oling.</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(AdminExcelImportState.waiting_for_file, F.document)
async def process_uploaded_excel(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    doc = message.document
    if not (doc.file_name.endswith(".xlsx") or doc.file_name.endswith(".xls")):
        await message.answer("❌ Iltimos, faqat <b>.xlsx</b> formatidagi Excel fayl yuboring!", parse_mode="HTML")
        return

    data = await state.get_data()
    test_id = data.get("excel_test_id")
    test_repo = TestRepository(session)
    test = await test_repo.get_by_id(test_id)

    if not test:
        await message.answer("❌ Test topilmadi.")
        await state.clear()
        return

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_info = await bot.get_file(doc.file_id)
    download_path = settings.UPLOAD_DIR / f"upload_{test_id}_{doc.file_name}"
    await bot.download_file(file_info.file_path, destination=download_path)

    questions, errors = ExcelService.parse_questions_from_excel(download_path)

    if errors:
        error_report = "⚠️ <b>Faylda quyidagi xatoliklar aniqlandi:</b>\n\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_report += f"\n... va yana {len(errors) - 10} ta xato."
        await message.answer(error_report, parse_mode="HTML")
        if not questions:
            return

    if not questions:
        await message.answer("❌ Faylda yaroqli savollar topilmadi. Shablon bo'yicha to'ldirganingizga ishonch hosil qiling.")
        return

    # Add questions
    for idx, q_data in enumerate(questions, start=1):
        q = Question(
            text=q_data["text"],
            option_a=q_data["option_a"],
            option_b=q_data["option_b"],
            option_c=q_data["option_c"],
            option_d=q_data["option_d"],
            correct_option=q_data["correct_option"],
            points=q_data["points"]
        )
        await test_repo.add_question_to_test(test_id=test.id, question=q, order_index=idx)

    # Commit to DB so questions are saved permanently
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Muvaffaqiyatli import qilindi!</b>\n\n"
        f"📝 Test: <b>{html.escape(test.title)}</b>\n"
        f"❓ Yuklangan savollar: <b>{len(questions)} ta</b>\n"
        f"🔑 Test kodi: <code>{test.code}</code>\n\n"
        f"Savollar testga to'liq biriktirildi!",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_xl_export_start")
async def admin_excel_export_menu(callback: CallbackQuery, session: AsyncSession):
    test_repo = TestRepository(session)
    tests = await test_repo.get_all(limit=25)

    if not tests:
        await callback.answer("Eksport qilish uchun testlar mavjud emas.", show_alert=True)
        return

    buttons = []
    for t in tests:
        buttons.append([InlineKeyboardButton(text=f"📊 {t.title} ({t.code})", callback_data=f"adm_export_xl:{t.id}")])

    await callback.answer()
    await callback.message.answer(
        "📤 <b>Qaysi test natijalarini Excel formatida yuklab olmoqchisiz?</b>\n\n"
        "Kerakli testni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_export_xl:"))
async def handle_excel_export(callback: CallbackQuery, session: AsyncSession):
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    result_repo = ResultRepository(session)

    test = await test_repo.get_by_id(test_id)
    if not test:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    results = await result_repo.get_test_results(test_id)
    if not results:
        await callback.answer("Ushbu test bo'yicha hali natijalar mavjud emas.", show_alert=True)
        return

    await callback.answer("📤 Excel fayl tayyorlanmoqda...")
    excel_path = ExcelService.export_results_to_excel(results, test.title)

    await callback.message.answer_document(
        document=FSInputFile(path=str(excel_path), filename=f"Natijalar_{test.code}.xlsx"),
        caption=f"📊 <b>{html.escape(test.title)}</b> testi bo'yicha o'quvchilar natijalari ({len(results)} ta).",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_export_users_excel")
async def export_users_excel_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("👥 Foydalanuvchilar ro'yxati tayyorlanmoqda...")
    user_repo = UserRepository(session)
    users = await user_repo.get_all(limit=10000)

    if not users:
        await callback.message.answer("Foydalanuvchilar topilmadi.")
        return

    excel_path = ExcelService.export_users_to_excel(users)
    await callback.message.answer_document(
        document=FSInputFile(path=str(excel_path), filename="Barcha_Foydalanuvchilar.xlsx"),
        caption=f"👥 <b>Barcha foydalanuvchilar ro'yxati (Jami: {len(users)} ta)</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm_export_users_pdf")
async def export_users_pdf_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("📑 PDF hujjat tayyorlanmoqda...")
    user_repo = UserRepository(session)
    users = await user_repo.get_all(limit=5000)

    if not users:
        await callback.message.answer("Foydalanuvchilar topilmadi.")
        return

    pdf_path = ExcelService.export_users_to_pdf(users)
    await callback.message.answer_document(
        document=FSInputFile(path=str(pdf_path), filename="Foydalanuvchilar_Royxati.pdf"),
        caption=f"📑 <b>Foydalanuvchilar ro'yxati (Jami: {len(users)} ta)</b>",
        parse_mode="HTML"
    )

