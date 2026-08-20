from datetime import datetime, timezone
from pathlib import Path
import random
import string
from typing import Optional
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models.result import Certificate, Result, TestAttempt
from app.database.models.test import Test
from app.database.models.user import User
from app.database.repositories.certificate_repo import CertificateRepository


class CertificateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cert_repo = CertificateRepository(session)

    @staticmethod
    def generate_certificate_number() -> str:
        year = datetime.now().year
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"CERT-{year}-{suffix}"

    async def issue_certificate(self, result: Result, user: User, test: Test) -> Certificate:
        # Check if certificate already exists for this result
        existing = await self.cert_repo.get_by_result_id(result.id)
        if existing:
            # If PDF file missing on disk, regenerate it
            pdf_path = Path(existing.pdf_path) if existing.pdf_path else (settings.CERTIFICATE_DIR / f"{existing.certificate_number}.pdf")
            if not pdf_path.exists():
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                date_str = result.created_at.strftime("%d.%m.%Y") if result.created_at else datetime.now().strftime("%d.%m.%Y")
                self._generate_certificate_pdf(
                    output_path=pdf_path,
                    cert_number=existing.certificate_number,
                    full_name=user.full_name,
                    school=user.school,
                    grade=user.grade,
                    test_title=test.title,
                    score=result.total_score,
                    max_score=result.max_score,
                    percentage=result.percentage,
                    date_str=date_str
                )
                existing.pdf_path = str(pdf_path)
                await self.session.commit()
            return existing

        cert_number = self.generate_certificate_number()
        while await self.cert_repo.get_by_number(cert_number):
            cert_number = self.generate_certificate_number()

        pdf_path = settings.CERTIFICATE_DIR / f"{cert_number}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        date_str = result.created_at.strftime("%d.%m.%Y") if result.created_at else datetime.now().strftime("%d.%m.%Y")
        
        self._generate_certificate_pdf(
            output_path=pdf_path,
            cert_number=cert_number,
            full_name=user.full_name,
            school=user.school,
            grade=user.grade,
            test_title=test.title,
            score=result.total_score,
            max_score=result.max_score,
            percentage=result.percentage,
            date_str=date_str
        )

        cert = await self.cert_repo.create(
            certificate_number=cert_number,
            user_id=user.id,
            test_id=test.id,
            result_id=result.id,
            score=result.total_score,
            percentage=result.percentage,
            pdf_path=str(pdf_path),
            issued_at=datetime.now(timezone.utc)
        )
        await self.session.commit()
        return cert

    @staticmethod
    def _generate_certificate_pdf(
        output_path: Path,
        cert_number: str,
        full_name: str,
        school: str,
        grade: str,
        test_title: str,
        score: float,
        max_score: float,
        percentage: float,
        date_str: str
    ) -> None:
        c = canvas.Canvas(str(output_path), pagesize=landscape(A4))
        width, height = landscape(A4)  # 841.89 x 595.27

        # 1. Warm Ivory Background Fill
        c.setFillColor(colors.HexColor("#FDFBF7"))
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # 2. Outer Deep Navy Border
        c.setStrokeColor(colors.HexColor("#0B1B3D"))
        c.setLineWidth(6)
        c.rect(20, 20, width - 40, height - 40)

        # 3. Inner Rich Gold Accent Border
        c.setStrokeColor(colors.HexColor("#C59B27"))
        c.setLineWidth(2)
        c.rect(28, 28, width - 56, height - 56)

        # 4. Thin Hairline Inner Border
        c.setStrokeColor(colors.HexColor("#E2D3A8"))
        c.setLineWidth(0.8)
        c.rect(34, 34, width - 68, height - 68)

        # 5. Corner Ornaments (Vector gold circles with navy rings)
        for (cx, cy) in [(34, 34), (width - 34, 34), (34, height - 34), (width - 34, height - 34)]:
            c.setFillColor(colors.HexColor("#C59B27"))
            c.circle(cx, cy, 4, stroke=0, fill=1)
            c.setStrokeColor(colors.HexColor("#0B1B3D"))
            c.setLineWidth(1)
            c.circle(cx, cy, 7, stroke=1, fill=0)

        # 6. Top Institution / Brand Header (Clean typography, no broken emojis)
        c.setFillColor(colors.HexColor("#8C6B16"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, height - 65, "TELEGRAM TEST PLATFORMASI")

        c.setFillColor(colors.HexColor("#A08030"))
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, height - 79, "ONLINE ASSESSMENT & TESTING PLATFORM")

        # Decorative top line with diamond
        c.setStrokeColor(colors.HexColor("#C59B27"))
        c.setLineWidth(1)
        c.line(width / 2 - 180, height - 88, width / 2 + 180, height - 88)
        c.setFillColor(colors.HexColor("#C59B27"))
        p = c.beginPath()
        p.moveTo(width / 2, height - 84)
        p.lineTo(width / 2 + 4, height - 88)
        p.lineTo(width / 2, height - 92)
        p.lineTo(width / 2 - 4, height - 88)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

        # 7. Main Title: SERTIFIKAT
        c.setFillColor(colors.HexColor("#0B1B3D"))
        c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(width / 2, height - 130, "SERTIFIKAT")

        c.setFillColor(colors.HexColor("#9E7A1C"))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, height - 148, "CERTIFICATE OF EXCELLENCE & ACHIEVEMENT")

        # 8. Introductory Text
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica-Oblique", 11)
        c.drawCentredString(width / 2, height - 180, "Ushbu sertifikat munosib bilim va a'lo natija ko'rsatganligi uchun taqdim etiladi:")

        # 9. Recipient Full Name
        c.setFillColor(colors.HexColor("#0B1B3D"))
        c.setFont("Helvetica-Bold", 24)
        clean_name = full_name.upper().strip()
        c.drawCentredString(width / 2, height - 216, clean_name)

        # Gold Underline with center diamond
        name_w = max(260, min(500, len(clean_name) * 15))
        c.setStrokeColor(colors.HexColor("#C59B27"))
        c.setLineWidth(1.5)
        c.line((width - name_w) / 2, height - 224, (width + name_w) / 2, height - 224)
        p = c.beginPath()
        p.moveTo(width / 2, height - 221)
        p.lineTo(width / 2 + 3, height - 224)
        p.lineTo(width / 2, height - 227)
        p.lineTo(width / 2 - 3, height - 224)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

        # 10. School & Grade info (Clean separator, no emojis)
        safe_school = (school or "Ta'lim muassasasi").strip()
        safe_grade = (grade or "Umumiy").strip()
        c.setFillColor(colors.HexColor("#2D3748"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, height - 248, f"{safe_school}   |   {safe_grade}")

        # 11. Test Subject info
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 275, f"«{test_title}» fani bo'yicha tashkil etilgan bilimlar sinovidan muvaffaqiyatli o'tdi")

        # 12. Score & Distinction Badge Card
        card_w = 460
        card_h = 60
        card_x = (width - card_w) / 2
        card_y = height - 355

        c.setFillColor(colors.HexColor("#FFFDF5"))
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(1.5)
        c.roundRect(card_x, card_y, card_w, card_h, 8, fill=1, stroke=1)

        c.setStrokeColor(colors.HexColor("#F1E2B8"))
        c.setLineWidth(0.8)
        c.roundRect(card_x + 3, card_y + 3, card_w - 6, card_h - 6, 6, fill=0, stroke=1)

        if percentage >= 90:
            grade_label = "A'LO DARAJA (WITH DISTINCTION)"
            star_str = "★ ★ ★"
        elif percentage >= 75:
            grade_label = "YAXSHI NATIJA (ADVANCED)"
            star_str = "★ ★"
        else:
            grade_label = "QONIQARLI NATIJA (STANDARD)"
            star_str = "★"

        c.setFillColor(colors.HexColor("#7A5308"))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, card_y + 36, f"{star_str}   NATIJA: {percentage:.1f}%  —  {grade_label}   {star_str}")

        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, card_y + 16, f"To'plangan ball: {score:.1f} / {max_score:.1f} ball")

        # 13. Verification Section (Bottom Footer)
        # Left: Verification QR Code
        try:
            qr_content = f"https://t.me/tekshiruv2_bot?start=cert_{cert_number}\nVERIFIED: {cert_number}\nNomzod: {clean_name}\nNatija: {percentage}%\nFan: {test_title}\nSana: {date_str}"
            qr_widget = QrCodeWidget(qr_content)
            qr_size = 68
            qr_widget.barWidth = qr_size
            qr_widget.barHeight = qr_size
            d = Drawing(qr_size, qr_size)
            d.add(qr_widget)
            renderPDF.draw(d, c, 52, 54)

            c.setFillColor(colors.HexColor("#718096"))
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(52 + qr_size / 2, 44, "HAQIQIYLIKNI TEKSHIRISH")
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(52 + qr_size / 2, 35, "QR-KODNI SKANERLANG")
        except Exception:
            pass

        # Center: Official Gold Seal
        seal_x = width / 2
        seal_y = 86

        c.setStrokeColor(colors.HexColor("#C59B27"))
        c.setFillColor(colors.HexColor("#FFFDF5"))
        c.setLineWidth(2)
        c.circle(seal_x, seal_y, 34, stroke=1, fill=1)

        c.setStrokeColor(colors.HexColor("#8C6B16"))
        c.setLineWidth(1)
        c.circle(seal_x, seal_y, 29, stroke=1, fill=0)

        c.setFillColor(colors.HexColor("#8C6B16"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(seal_x, seal_y + 15, "★ ★ ★")
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(seal_x, seal_y + 4, "RASMIY MUHR")
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(seal_x, seal_y - 6, "TEST PLATFORMASI")
        c.setFont("Helvetica", 6)
        c.drawCentredString(seal_x, seal_y - 16, "TASDIQLANGAN")

        # Right: Signature, Date, and Unique Serial ID
        right_x = width - 52
        c.setFillColor(colors.HexColor("#0B1B3D"))
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(right_x, 102, "A. Rahmonov")

        c.setStrokeColor(colors.HexColor("#A0AEC0"))
        c.setLineWidth(1)
        c.line(right_x - 140, 96, right_x, 96)

        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 8.5)
        c.drawRightString(right_x, 83, "Platforma Rahbari  /  Director")

        c.setFillColor(colors.HexColor("#718096"))
        c.setFont("Helvetica", 8)
        c.drawRightString(right_x, 69, f"Berilgan sana: {date_str}")

        c.setFillColor(colors.HexColor("#8C6B16"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(right_x, 55, f"Seriya: {cert_number}")

        c.save()


    def generate_result_pdf(
        self,
        result: Result,
        user: User,
        test: Test,
        answers: list,
        attempt: Optional[TestAttempt] = None
    ) -> Path:
        pdf_path = settings.EXCEL_DIR / f"result_{result.id}_{user.id}.pdf"
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        styles = getSampleStyleSheet()
        elements = []

        # Styles
        brand_style = ParagraphStyle(
            'BrandStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor("#C59B27"),
            alignment=1,
            spaceAfter=4
        )
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=colors.HexColor("#0B1B3D"),
            alignment=1,
            spaceAfter=15
        )
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.HexColor("#4A5568")
        )
        val_style = ParagraphStyle(
            'ValStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#1A202C")
        )
        th_style = ParagraphStyle(
            'THStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.whitesmoke,
            alignment=1
        )
        td_center = ParagraphStyle(
            'TDCenter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            alignment=1
        )
        td_left = ParagraphStyle(
            'TDLeft',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            alignment=0
        )
        td_correct = ParagraphStyle(
            'TDCorrect',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            textColor=colors.HexColor("#22543D"),
            alignment=1
        )
        td_incorrect = ParagraphStyle(
            'TDIncorrect',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            textColor=colors.HexColor("#742A2A"),
            alignment=1
        )

        # Header
        elements.append(Paragraph("TELEGRAM TEST PLATFORMASI", brand_style))
        elements.append(Paragraph(f"Test Natijasi: {test.title}", title_style))

        full_name = user.full_name if user else "Foydalanuvchi"
        school_grade = f"{user.school} ({user.grade})" if user and (user.school or user.grade) else "Belgilanmagan"
        date_str = result.created_at.strftime("%d.%m.%Y %H:%M") if result.created_at else datetime.now().strftime("%d.%m.%Y %H:%M")
        time_str = f"{result.time_spent_seconds // 60} daqiqa" if result.time_spent_seconds else "1 daqiqa"

        # Information Card Table (All wrapped in Paragraph to prevent overlap)
        info_data = [
            [
                Paragraph("Foydalanuvchi:", label_style),
                Paragraph(full_name, val_style),
                Paragraph("Sana:", label_style),
                Paragraph(date_str, val_style)
            ],
            [
                Paragraph("Muassasa / Sinf:", label_style),
                Paragraph(school_grade, val_style),
                Paragraph("Sarflangan vaqt:", label_style),
                Paragraph(time_str, val_style)
            ],
            [
                Paragraph("To'g'ri javoblar:", label_style),
                Paragraph(f"<b>{result.correct_count} ta</b>", val_style),
                Paragraph("Noto'g'ri javoblar:", label_style),
                Paragraph(f"<b>{result.incorrect_count} ta</b>", val_style)
            ],
            [
                Paragraph("Jami to'plangan ball:", label_style),
                Paragraph(f"<b>{result.total_score:.1f} / {result.max_score:.1f}</b>", val_style),
                Paragraph("O'zlashtirish:", label_style),
                Paragraph(f"<b>{result.percentage:.1f}%</b>", val_style)
            ]
        ]
        info_table = Table(info_data, colWidths=[105, 175, 105, 150])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0"))
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 16))

        # Answers breakdown table
        table_data = [[
            Paragraph("T/r", th_style),
            Paragraph("Savol", th_style),
            Paragraph("Tanlangan", th_style),
            Paragraph("To'g'ri", th_style),
            Paragraph("Holat", th_style),
            Paragraph("Ball", th_style)
        ]]

        if answers:
            for idx, sa in enumerate(answers, start=1):
                is_correct = sa.is_correct
                status_p = Paragraph("To'g'ri", td_correct) if is_correct else Paragraph("Noto'g'ri", td_incorrect)
                q_text = (sa.question.text[:45] + '...') if (sa.question and len(sa.question.text) > 45) else (sa.question.text if sa.question else f"Savol {idx}")
                correct_opt = sa.question.correct_option if sa.question else "-"
                table_data.append([
                    Paragraph(str(idx), td_center),
                    Paragraph(q_text, td_left),
                    Paragraph(sa.selected_option, td_center),
                    Paragraph(correct_opt, td_center),
                    status_p,
                    Paragraph(f"{sa.points_earned:.1f}", td_center)
                ])
        elif attempt and attempt.option_order:
            user_answers = attempt.option_order.get("user_answers", {})
            correct_keys = attempt.option_order.get("correct_keys", {})
            if not correct_keys and test.answer_key:
                from app.services.scoring_service import ScoringService
                correct_keys = {str(k): v for k, v in ScoringService.parse_quick_answers(test.answer_key).items()}

            point_per_q = round(result.max_score / len(correct_keys), 2) if correct_keys else 1.0
            for idx_str, corr_opt in sorted(correct_keys.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                u_opt = user_answers.get(str(idx_str), "-")
                is_correct = (u_opt.upper() == corr_opt.upper())
                status_p = Paragraph("To'g'ri", td_correct) if is_correct else Paragraph("Noto'g'ri", td_incorrect)
                pts = point_per_q if is_correct else 0.0
                table_data.append([
                    Paragraph(str(idx_str), td_center),
                    Paragraph(f"Savol {idx_str}", td_left),
                    Paragraph(u_opt, td_center),
                    Paragraph(corr_opt, td_center),
                    status_p,
                    Paragraph(f"{pts:.1f}", td_center)
                ])

        ans_table = Table(table_data, colWidths=[35, 230, 65, 65, 80, 60])
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0B1B3D")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0"))
        ]
        # Alternating row colors
        for i in range(1, len(table_data)):
            bg = colors.HexColor("#F8FAFC") if i % 2 == 0 else colors.white
            table_styles.append(('BACKGROUND', (0, i), (-1, i), bg))

        ans_table.setStyle(TableStyle(table_styles))
        elements.append(ans_table)

        doc.build(elements)
        return pdf_path
