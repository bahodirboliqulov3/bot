import html
from pathlib import Path
import urllib.parse
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models.result import Certificate
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.certificate_repo import CertificateRepository
from app.database.repositories.user_repo import UserRepository
from app.services.certificate_service import CertificateService

router = Router(name="student_certificates")


@router.message(StateFilter("*"), F.text.in_(["📜 Sertifikatlarim", "📜 Sertifikatlar", "🎉 Sertifikatlar", "Sertifikatlarim"]))
async def list_student_certificates(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    cert_repo = CertificateRepository(session)
    certs = await cert_repo.get_user_certificates(user.id)

    if not certs:
        empty_text = (
            "📜 Sizda hozircha sertifikatlar mavjud emas.\n\n"
            "💡 Qanday qilib sertifikat olish mumkin?\n"
            "• Testlarni muvaffaqiyatli topshiring (o‘tish foizi odatda 70% dan yuqori);\n"
            "• Natijangiz chiqqan zahoti sizga QR-kodli rasmiy PDF Sertifikat taqdim etiladi!\n\n"
            "Test topshirish uchun «✅ Javobni tekshirish» tugmasini bosing! 🚀"
        )
        await message.answer(empty_text, parse_mode="HTML")
        return

    header_text = (
        f"🎖 Sizning rasmiy sertifikatlaringiz ({len(certs)} ta):\n"
        "Quyidagi ro‘yxatdan kerakli sertifikatni yuklab olishingiz yoki ulashishingiz mumkin:"
    )
    await message.answer(header_text, parse_mode="HTML")

    for idx, cert in enumerate(certs, start=1):
        test_title = html.escape(cert.test.title if cert.test else "Umumiy Test")
        issued_str = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else "20.08.2026"
        cert_num = cert.certificate_number

        share_text = f"Men «{test_title}» testida {cert.percentage}% natija bilan rasmiy Sertifikat oldim! 🎓📜\nTest platformasi: @tekshiruv2_bot"
        share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote(share_text)}"

        text = (
            f"📜 {idx}. {test_title}\n"
            f"🔹 Natija: {cert.percentage:.1f}% ({cert.score:.1f} ball)\n"
            f"🔹 Sertifikat ID: <code>{cert_num}</code>\n"
            f"📅 Berilgan sana: {issued_str}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 PDF yuklab olish", callback_data=f"download_cert:{cert.id}"),
                    InlineKeyboardButton(text="📲 Do‘stlarga ulashish", url=share_url)
                ]
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("download_cert:"))
async def download_cert_file_callback(callback: CallbackQuery, session: AsyncSession):
    cert_id = int(callback.data.split(":")[1])
    cert_repo = CertificateRepository(session)
    user_repo = UserRepository(session)

    cert = await cert_repo.get_certificate_with_details(cert_id)
    if not cert:
        await callback.answer("Sertifikat topilmadi.", show_alert=True)
        return

    # Check if file exists, if not generate it on the fly
    pdf_file_path = Path(cert.pdf_path) if cert.pdf_path else (settings.CERTIFICATE_DIR / f"{cert.certificate_number}.pdf")
    if not pdf_file_path.exists():
        user = cert.user or await user_repo.get_by_id(cert.user_id)
        test_title = cert.test.title if cert.test else "Fan testi"
        max_score = cert.test.max_points if cert.test else 100.0
        date_str = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else datetime.now().strftime("%d.%m.%Y")
        pdf_file_path.parent.mkdir(parents=True, exist_ok=True)
        CertificateService._generate_certificate_pdf(
            output_path=pdf_file_path,
            cert_number=cert.certificate_number,
            full_name=user.full_name if user else "O‘quvchi",
            school=user.school if user else "",
            grade=user.grade if user else "",
            test_title=test_title,
            score=cert.score,
            max_score=max_score,
            percentage=cert.percentage,
            date_str=date_str
        )
        cert.pdf_path = str(pdf_file_path)
        await session.commit()

    await callback.answer("📥 Sertifikat yuborilmoqda...")
    safe_title = html.escape(cert.test.title if cert.test else "Test")
    await callback.message.answer_document(
        document=FSInputFile(path=str(pdf_file_path), filename=f"Sertifikat_{cert.certificate_number}.pdf"),
        caption=(
            f"🎓 Tabriklaymiz! Sizning rasmiy sertifikatingiz:\n\n"
            f"📝 Test: {safe_title}\n"
            f"📊 Natija: {cert.percentage:.1f}%\n"
            f"📜 Seriya: <code>{cert.certificate_number}</code>"
        ),
        parse_mode="HTML"
    )
