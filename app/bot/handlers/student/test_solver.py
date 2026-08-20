from datetime import datetime, timezone
import html
import logging
import urllib.parse
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.inline_keyboards import (
    get_quiz_finish_confirm_keyboard,
    get_quiz_overview_keyboard,
    get_quiz_question_keyboard,
    get_result_actions_keyboard,
)
from app.database.models.result import AttemptStatus
from app.database.models.test import Question, Test
from app.database.repositories.base_repo import BaseRepository
from app.database.repositories.result_repo import AttemptRepository, ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.scoring_service import ScoringService
from app.services.test_service import TestService

logger = logging.getLogger(__name__)
router = Router(name="student_test_solver")


async def render_question_card(
    session: AsyncSession,
    attempt_id: int,
    current_index: int,
    user_id: int
) -> tuple[str, str | None, any]:
    attempt_repo = AttemptRepository(session)
    test_repo = TestRepository(session)
    q_repo = BaseRepository(Question, session)

    attempt = await attempt_repo.get_by_id(attempt_id)
    if not attempt or attempt.status != AttemptStatus.IN_PROGRESS:
        raise ValueError("Attempt faol emas.")

    test = await test_repo.get_test_with_questions(attempt.test_id)
    question_ids = attempt.question_order
    total_questions = len(question_ids)

    if current_index < 1 or current_index > total_questions:
        current_index = 1

    current_q_id = question_ids[current_index - 1]
    question = await q_repo.get_by_id(current_q_id)

    answers = await attempt_repo.get_answers_for_attempt(attempt_id)
    answered_map = {ans.question_id: ans.selected_option for ans in answers}
    selected_option = answered_map.get(current_q_id)

    option_mapping = attempt.option_order.get(str(current_q_id), {"A": "A", "B": "B", "C": "C", "D": "D"})

    original_options_text = {
        "A": question.option_a,
        "B": question.option_b,
        "C": question.option_c,
        "D": question.option_d,
    }

    now = datetime.now(timezone.utc)
    elapsed_seconds = int((now - attempt.started_at).total_seconds())
    total_seconds = test.time_limit_minutes * 60
    remaining_seconds = max(0, total_seconds - elapsed_seconds)
    rem_min, rem_sec = divmod(remaining_seconds, 60)

    # Build progress bar for questions
    filled = int((current_index / total_questions) * 10)
    progress = "█" * filled + "░" * (10 - filled)
    answered_count = len(answered_map)

    # Time color indicator
    if remaining_seconds > total_seconds * 0.5:
        time_emoji = "🟢"
    elif remaining_seconds > total_seconds * 0.2:
        time_emoji = "🟡"
    else:
        time_emoji = "🔴"

    card_text = (
        f"⏱ {time_emoji} <b>{rem_min:02d}:{rem_sec:02d}</b> qoldi\n"
        f"📊 [{progress}] <b>{current_index}/{total_questions}</b> savol\n"
        f"✅ Javob berilgan: <b>{answered_count} ta</b>\n\n"
        f"❓ <b>{html.escape(question.text)}</b>\n\n"
        f"🔘 <b>A)</b> {html.escape(str(original_options_text.get(option_mapping.get('A', 'A'), '')))}\n"
        f"🔘 <b>B)</b> {html.escape(str(original_options_text.get(option_mapping.get('B', 'B'), '')))}\n"
        f"🔘 <b>C)</b> {html.escape(str(original_options_text.get(option_mapping.get('C', 'C'), '')))}\n"
        f"🔘 <b>D)</b> {html.escape(str(original_options_text.get(option_mapping.get('D', 'D'), '')))}\n"
    )

    kb = get_quiz_question_keyboard(
        attempt_id=attempt_id,
        current_index=current_index,
        total_questions=total_questions,
        selected_option=selected_option,
        allow_backtracking=test.allow_backtracking
    )

    return card_text, question.photo_file_id, kb


@router.callback_query(F.data.startswith("start_test:"))
async def handle_start_test_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("🚀 Test yuklanmoqda...")
    test_id = int(callback.data.split(":")[1])
    test_repo = TestRepository(session)
    user_repo = UserRepository(session)
    test_service = TestService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Iltimos, avval ro'yxatdan o'ting (/start).")
        return

    test = await test_repo.get_test_with_questions(test_id)
    if not test:
        await callback.message.answer("Test topilmadi.")
        return

    can_start, msg = await test_service.validate_can_start_test(test, user.id)
    if not can_start:
        await callback.message.answer(msg)
        return

    attempt = await test_service.start_attempt(test, user.id)

    card_text, photo_file_id, kb = await render_question_card(
        session=session,
        attempt_id=attempt.id,
        current_index=1,
        user_id=user.id
    )

    if photo_file_id:
        try:
            await callback.message.answer_photo(photo=photo_file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass

    await callback.message.answer(card_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("ans:"))
async def handle_answer_option_callback(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    attempt_id = int(parts[1])
    current_index = int(parts[2])
    chosen_label = parts[3]

    # Instant UI feedback
    await callback.answer(f"✅ {chosen_label}")

    attempt_repo = AttemptRepository(session)
    test_repo = TestRepository(session)
    q_repo = BaseRepository(Question, session)

    attempt = await attempt_repo.get_by_id(attempt_id)
    if not attempt or attempt.status != AttemptStatus.IN_PROGRESS:
        return

    test = await test_repo.get_test_with_questions(attempt.test_id)
    now = datetime.now(timezone.utc)
    elapsed_seconds = int((now - attempt.started_at).total_seconds())
    if elapsed_seconds > (test.time_limit_minutes * 60 + 30):
        scoring_service = ScoringService(session)
        res = await scoring_service.complete_attempt(attempt_id)
        await show_test_result(callback.message, res, session)
        return

    current_q_id = attempt.question_order[current_index - 1]
    question = await q_repo.get_by_id(current_q_id)

    option_mapping = attempt.option_order.get(str(current_q_id), {"A": "A", "B": "B", "C": "C", "D": "D"})
    actual_selected_option = option_mapping.get(chosen_label, chosen_label)

    is_correct = (actual_selected_option.upper() == question.correct_option.upper())
    points_earned = question.points if is_correct else 0.0

    await attempt_repo.save_answer(
        attempt_id=attempt.id,
        question_id=current_q_id,
        selected_option=chosen_label,
        is_correct=is_correct,
        points_earned=points_earned
    )

    next_index = current_index + 1 if current_index < len(attempt.question_order) else current_index

    card_text, photo_file_id, kb = await render_question_card(
        session=session,
        attempt_id=attempt.id,
        current_index=next_index,
        user_id=callback.from_user.id
    )

    try:
        await callback.message.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("nav:"))
async def handle_navigation_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    parts = callback.data.split(":")
    attempt_id = int(parts[1])
    target_index = int(parts[2])

    card_text, photo_file_id, kb = await render_question_card(
        session=session,
        attempt_id=attempt_id,
        current_index=target_index,
        user_id=callback.from_user.id
    )
    try:
        await callback.message.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("overview:"))
async def handle_overview_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    attempt_id = int(callback.data.split(":")[1])
    attempt_repo = AttemptRepository(session)
    attempt = await attempt_repo.get_by_id(attempt_id)

    if not attempt:
        return

    answers = await attempt_repo.get_answers_for_attempt(attempt_id)
    answered_q_ids = {ans.question_id for ans in answers}
    answered_indices = set()
    for idx, q_id in enumerate(attempt.question_order, start=1):
        if q_id in answered_q_ids:
            answered_indices.add(idx)

    kb = get_quiz_overview_keyboard(
        attempt_id=attempt_id,
        total_questions=len(attempt.question_order),
        answered_indices=answered_indices
    )
    await callback.message.edit_text(
        f"📋 Savollar xaritasi ({len(answered_indices)} / {len(attempt.question_order)} belgilandi):\n"
        "Kerakli savol raqamini tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("finish_confirm:"))
async def handle_finish_confirm_callback(callback: CallbackQuery):
    await callback.answer()
    attempt_id = int(callback.data.split(":")[1])
    kb = get_quiz_finish_confirm_keyboard(attempt_id=attempt_id)
    await callback.message.edit_text(
        "⚠️ Testni yakunlashni xohlaysizmi?\n\n"
        "Yakunlaganingizdan keyin javoblarni o‘zgartirib bo‘lmaydi.",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("finish_test:"))
async def handle_finish_test_callback(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("✅ Natija hisoblanmoqda...")
    attempt_id = int(callback.data.split(":")[1])
    scoring_service = ScoringService(session)
    try:
        res = await scoring_service.complete_attempt(attempt_id)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_test_result(callback.message, res, session)
    except Exception as e:
        logger.error(f"Error completing test attempt: {e}")
        await callback.message.answer("❌ Xatolik yuz berdi.")


async def show_test_result(message: Message, result, session: AsyncSession, visual_breakdown: str = ""):
    test_repo = TestRepository(session)
    scoring_service = ScoringService(session)

    test = await test_repo.get_by_id(result.test_id)
    raw_test_title = test.title if test else "Test"
    test_title = html.escape(raw_test_title)
    safe_code = html.escape(test.code or "") if test else ""

    minutes, seconds = divmod(result.time_spent_seconds, 60)
    progress_bar = scoring_service.get_progress_bar(result.percentage)
    grade_label, motivational_quote, celebration_banner = scoring_service.get_grade_info(result.percentage)
    rank, total_p = await scoring_service.get_test_rank(result.test_id, result.id)

    result_text = (
        f"{celebration_banner}\n\n"
        f"🎯 <b>TEST NATIJASI</b>\n\n"
        f"📝 Test: <b>{test_title}</b>\n"
        f"🔑 Test kodi: <code>{safe_code}</code>\n"
        f"📊 Ko‘rsatkich: {progress_bar} <b>{result.percentage}%</b>\n"
        f"🎖 Baho: <b>{html.escape(grade_label)}</b>\n"
        f"🏆 O‘rin: <b>{rank}-o‘rin</b> (Jami {total_p} ta ishtirokchidan)\n\n"
        f"✅ To‘g‘ri javoblar: <b>{result.correct_count} ta</b>\n"
        f"❌ Xatolar: <b>{result.incorrect_count} ta</b>\n"
        f"⚪ Belgilanmagan: <b>{result.unanswered_count} ta</b>\n"
        f"🏅 To‘plangan ball: <b>{result.total_score} / {result.max_score}</b>\n"
        f"⏱ Sarflangan vaqt: <b>{minutes:02d}:{seconds:02d}</b>\n\n"
        f"💬 <i>{html.escape(motivational_quote)}</i>\n\n"
    )

    if visual_breakdown:
        result_text += f"<pre>{html.escape(visual_breakdown)}</pre>\n"

    share_msg = (
        f"🎯 Men «{raw_test_title}» testida {result.percentage}% natija to‘pladim!\n"
        f"✅ To‘g‘ri: {result.correct_count} ta | ❌ Xato: {result.incorrect_count} ta\n"
        f"🏆 Ball: {result.total_score} / {result.max_score}\n\n"
        f"Siz ham bilimingizni sinab ko‘ring: @tekshiruv2_bot"
    )
    share_url = f"https://t.me/share/url?url=https://t.me/tekshiruv2_bot&text={urllib.parse.quote(share_msg)}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔎 Xatolarni ko‘rish", callback_data=f"view_mistakes:{result.id}"),
                InlineKeyboardButton(text="📄 PDF hisobot", callback_data=f"pdf_result:{result.id}")
            ],
            [
                InlineKeyboardButton(text="📤 Ulashish", url=share_url)
            ]
        ]
    )

    await message.answer(result_text, reply_markup=kb, parse_mode="HTML")
