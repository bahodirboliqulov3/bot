import html
from pathlib import Path
import re
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.inline_keyboards import get_result_actions_keyboard
from app.database.models.result import Result
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.result_repo import AttemptRepository, ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.certificate_service import CertificateService
from app.services.scoring_service import ScoringService

router = Router(name="student_results")


def get_dashboard_progress_bar(percentage: float) -> str:
    filled = min(10, max(0, int(percentage / 10)))
    return "🟩" * filled + "⬜" * (10 - filled)


def get_grade_emoji(percentage: float) -> str:
    if percentage >= 90:
        return "🥇"
    elif percentage >= 80:
        return "🥈"
    elif percentage >= 60:
        return "🥉"
    elif percentage >= 40:
        return "⚠️"
    else:
        return "❌"


def build_results_dashboard(results: list[Result], user_name: str, page: int = 1, page_size: int = 5) -> tuple[str, InlineKeyboardMarkup]:
    total_tests = len(results)
    avg_score = (sum(r.percentage for r in results) / total_tests) if total_tests > 0 else 0
    max_score_test = max(results, key=lambda r: r.percentage) if results else None
    passed_count = sum(1 for r in results if r.percentage >= (r.test.pass_percentage if r.test else 60))

    total_pages = max(1, (total_tests + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    current_page_results = results[start_idx:start_idx + page_size]

    p_bar = get_dashboard_progress_bar(avg_score)
    safe_user_name = html.escape(user_name or "O‘quvchi")

    text = (
        f"📊 MENING NATIJALAR MARKAZIM 🎓\n\n"
        f"👤 O‘quvchi: {safe_user_name}\n"
        f"📈 Jami ishlangan: {total_tests} ta test\n"
        f"🏆 O‘rtacha ko‘rsatkich: {avg_score:.1f}%\n"
        f"   └ {p_bar}\n"
        f"🎉 Muvaffaqiyatli testlar: {passed_count} ta\n"
    )
    if max_score_test:
        max_title = html.escape(max_score_test.test.title if max_score_test.test else "Test")
        text += f"🌟 Eng yuqori natija: {max_score_test.percentage}% ({max_title})\n"

    text += f"\n──────────────────────────\n"
    text += f"📋 So‘nggi ishlangan testlar ({page}/{total_pages}-sahifa):\n\n"

    buttons = []
    for idx, r in enumerate(current_page_results, start=start_idx + 1):
        medal = get_grade_emoji(r.percentage)
        test_title = html.escape(r.test.title if r.test else "Test")
        raw_title = r.test.title if r.test else "Test"
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else ""

        text += (
            f"{idx}. {medal} {test_title}\n"
            f"   └ 📊 {r.percentage}% | Ball: {r.total_score}/{r.max_score} | 📅 {date_str}\n\n"
        )
        short_title = (raw_title[:16] + "..") if len(raw_title) > 16 else raw_title
        btn_label = f"🔎 {idx}. {short_title} ({r.percentage}%)"
        buttons.append([InlineKeyboardButton(text=btn_label, callback_data=f"res_view:{r.id}:{page}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"res_page:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"res_page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


def format_single_result_view(r: Result, page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    import urllib.parse
    raw_test_title = r.test.title if r.test else "Test"
    test_title = html.escape(raw_test_title)
    date_str = r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else ""
    minutes, seconds = divmod(r.time_spent_seconds, 60)
    p_bar = get_dashboard_progress_bar(r.percentage)

    safe_code = html.escape(r.test.code or "") if r.test else ""

    card_text = (
        f"🎯 TEST NATIJASI TAHLILI\n\n"
        f"📝 Test: {test_title}\n"
        f"🔑 Test kodi: <code>{safe_code}</code>\n"
        f"📅 Topshirilgan vaqt: {date_str}\n"
        f"📊 Ko‘rsatkich: {p_bar} {r.percentage}%\n\n"
        f"✅ To‘g‘ri javoblar: {r.correct_count} ta\n"
        f"❌ Xatolar soni: {r.incorrect_count} ta\n"
        f"⚪ Belgilanmagan: {r.unanswered_count} ta\n"
        f"🏆 To‘plangan ball: {r.total_score} / {r.max_score}\n"
        f"⏱ Sarflangan vaqt: {minutes:02d}:{seconds:02d}\n"
    )

    share_msg = (
        f"🎯 Men «{raw_test_title}» testida {r.percentage}% natija to‘pladim!\n"
        f"✅ To‘g‘ri: {r.correct_count} ta | ❌ Xato: {r.incorrect_count} ta\n"
        f"🏆 Ball: {r.total_score} / {r.max_score}\n\n"
        f"Siz ham bilimingizni sinab ko‘ring: @tekshiruv2_bot"
    )
    share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote(share_msg)}"

    buttons = [
        [
            InlineKeyboardButton(text="🔎 Xatolarni ko‘rish", callback_data=f"view_mistakes:{r.id}"),
            InlineKeyboardButton(text="📄 PDF natija", callback_data=f"pdf_result:{r.id}")
        ],
        [
            InlineKeyboardButton(text="📤 Ulashish", url=share_url),
            InlineKeyboardButton(text="◀️ Natijalar ro‘yxati", callback_data=f"res_page:{page}")
        ]
    ]

    return card_text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(StateFilter("*"), F.text == "📊 Natijalarim")
async def list_my_results_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        return

    result_repo = ResultRepository(session)
    results = await result_repo.get_user_results(user.id, limit=50)

    if not results:
        await message.answer(
            "📊 Sizda hali ishlangan test natijalari mavjud emas.\n\n"
            "💡 «📝 Testlar» bo‘limidan birorta testni tanlang yoki botga test kodini yuborib birinchi testingizni ishlang!",
            parse_mode="HTML"
        )
        return

    text, kb = build_results_dashboard(results, user_name=user.full_name, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("res_page:"))
async def results_page_callback(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.")
        return

    result_repo = ResultRepository(session)
    results = await result_repo.get_user_results(user.id, limit=50)

    if not results:
        await callback.answer("Natijalar mavjud emas.", show_alert=True)
        return

    text, kb = build_results_dashboard(results, user_name=user.full_name, page=page)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("res_view:"))
async def result_view_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    result_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    res_repo = ResultRepository(session)
    res = await res_repo.get_result_with_details(result_id)

    if not res:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return

    text, kb = format_single_result_view(res, page=page)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("view_mistakes:"))
async def view_mistakes_callback(callback: CallbackQuery, session: AsyncSession):
    result_id = int(callback.data.split(":")[1])
    res_repo = ResultRepository(session)
    attempt_repo = AttemptRepository(session)
    test_repo = TestRepository(session)

    res = await res_repo.get_result_with_details(result_id)
    if not res:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return

    test = res.test or await test_repo.get_by_id(res.test_id)
    answers = await attempt_repo.get_answers_for_attempt(res.attempt_id)

    await callback.answer()

    if answers:
        mistakes = [ans for ans in answers if not ans.is_correct]
        if not mistakes and res.incorrect_count == 0 and res.unanswered_count == 0:
            await callback.message.answer("🎉 Tabriklaymiz! Siz bu testda birorta ham xato qilmadingiz!")
            return

        text = f"🔎 Xatolar tahlili ({len(mistakes)} ta xato):\n\n"
        for idx, m in enumerate(mistakes, start=1):
            q = m.question
            q_text = html.escape(q.text if q else f"Savol {idx}")
            corr_opt = html.escape(q.correct_option if q else "-")
            sel_opt = html.escape(m.selected_option or "Belgilanmagan")
            text += (
                f"{idx}. Savol: {q_text}\n"
                f"❌ Sizning javobingiz: {sel_opt}\n"
                f"✅ To'g'ri javob: {corr_opt}\n"
            )
            if q and q.explanation:
                text += f"💡 Izoh: {html.escape(q.explanation)}\n"
            text += "\n"
    else:
        attempt = await attempt_repo.get_by_id(res.attempt_id)
        user_answers = {}
        correct_keys = {}
        if attempt and attempt.option_order and isinstance(attempt.option_order, dict):
            user_answers = attempt.option_order.get("user_answers", {})
            correct_keys = attempt.option_order.get("correct_keys", {})

        if not correct_keys and test and test.answer_key:
            correct_keys = {str(k): v for k, v in ScoringService.parse_quick_answers(test.answer_key).items()}

        mistakes = []
        for idx_str, corr_opt in sorted(correct_keys.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            u_opt = user_answers.get(str(idx_str))
            if not u_opt or u_opt.upper() != corr_opt.upper():
                mistakes.append((idx_str, u_opt or "(Belgilanmagan)", corr_opt))

        if not mistakes and res.incorrect_count == 0 and res.unanswered_count == 0:
            await callback.message.answer("🎉 Tabriklaymiz! Siz bu testda birorta ham xato qilmadingiz!")
            return

        text = f"🔎 Xatolar tahlili ({len(mistakes)} ta xato):\n\n"
        for num, u_opt, corr_opt in mistakes:
            text += (
                f"{num}-savol:\n"
                f"❌ Sizning javobingiz: {html.escape(u_opt)}\n"
                f"✅ To'g'ri javob: {html.escape(corr_opt)}\n\n"
            )

    if len(text) > 4000:
        for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
            await callback.message.answer(chunk, parse_mode="HTML")
    else:
        await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("pdf_result:"))
async def download_result_pdf_callback(callback: CallbackQuery, session: AsyncSession):
    result_id = int(callback.data.split(":")[1])
    res_repo = ResultRepository(session)
    test_repo = TestRepository(session)
    user_repo = UserRepository(session)
    attempt_repo = AttemptRepository(session)

    res = await res_repo.get_result_with_details(result_id)
    if not res:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return

    user = res.user or await user_repo.get_by_id(res.user_id)
    test = res.test or await test_repo.get_by_id(res.test_id)
    attempt = await attempt_repo.get_by_id(res.attempt_id)
    answers = await attempt_repo.get_answers_for_attempt(res.attempt_id)

    cert_service = CertificateService(session)
    pdf_path = cert_service.generate_result_pdf(res, user, test, answers, attempt=attempt)

    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', test.title if test else "Test")[:25]
    safe_user = re.sub(r'[^a-zA-Z0-9_\-]', '_', user.full_name if user else "Foydalanuvchi")[:25]
    safe_filename = f"Natija_{safe_title}_{safe_user}.pdf"

    await callback.answer("📄 PDF tayyorlanmoqda...")
    await callback.message.answer_document(
        document=FSInputFile(path=pdf_path, filename=safe_filename),
        caption=f"📄 {html.escape(test.title if test else 'Test')} bo‘yicha to‘liq test natijangiz.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("get_cert:"))
async def get_certificate_callback(callback: CallbackQuery, session: AsyncSession):
    result_id = int(callback.data.split(":")[1])
    res_repo = ResultRepository(session)
    test_repo = TestRepository(session)
    user_repo = UserRepository(session)

    res = await res_repo.get_result_with_details(result_id)
    if not res:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return

    test = res.test or await test_repo.get_by_id(res.test_id)
    user = res.user or await user_repo.get_by_id(res.user_id)

    if res.percentage < test.pass_percentage:
        await callback.answer(
            f"⛔ Sertifikat olish uchun kamida {test.pass_percentage}% to'plash kerak. (Sizda: {res.percentage}%)",
            show_alert=True
        )
        return

    cert_service = CertificateService(session)
    cert = await cert_service.issue_certificate(res, user, test)

    safe_user_name = html.escape(user.full_name if user else "Foydalanuvchi")
    safe_test_title = html.escape(test.title if test else "Test")

    await callback.answer("🎉 Sertifikat yuklanmoqda!")
    await callback.message.answer_document(
        document=FSInputFile(path=cert.pdf_path, filename=f"Sertifikat_{cert.certificate_number}.pdf"),
        caption=(
            f"🎉 Tabriklaymiz, {safe_user_name}!\n\n"
            f"Siz \"{safe_test_title}\" fan testini a'lo darajada topshirib, maxsus sertifikatga ega bo'ldingiz.\n"
            f"🔑 Sertifikat raqami: <code>{cert.certificate_number}</code>"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("share_result:"))
async def share_result_callback(callback: CallbackQuery, session: AsyncSession):
    import urllib.parse
    result_id = int(callback.data.split(":")[1])
    res_repo = ResultRepository(session)
    res = await res_repo.get_result_with_details(result_id)

    if not res:
        await callback.answer("Natija topilmadi.", show_alert=True)
        return

    test_title = res.test.title if res.test else "Test"
    user_name = res.user.full_name if res.user else "O'quvchi"

    raw_text = (
        f"🎯 Men «{test_title}» testida qatnashdim!\n"
        f"✅ To‘g‘ri javoblar: {res.correct_count} ta\n"
        f"📊 Natija: {res.percentage}%\n"
        f"🏆 Ball: {res.total_score} / {res.max_score}\n\n"
        f"Siz ham o‘z bilimingizni sinab ko‘ring: @tekshiruv2_bot"
    )
    share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote(raw_text)}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Do‘stlarga / Guruhga yuborish", url=share_url)]
        ]
    )

    await callback.answer("📤 Ulashish tayyor!")
    await callback.message.answer(
        f"📤 Natijangizni ulashish uchun quyidagi tugmani bosing:\n\n<blockquote>{html.escape(raw_text)}</blockquote>",
        reply_markup=kb,
        parse_mode="HTML"
    )

