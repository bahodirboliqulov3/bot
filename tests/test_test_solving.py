import pytest
from app.database.models.test import Question, TestStatus
from app.database.repositories.result_repo import AttemptRepository, ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.scoring_service import ScoringService
from app.services.test_service import TestService


@pytest.mark.asyncio
async def test_test_creation_and_solving_flow(db_session):
    user_repo = UserRepository(db_session)
    test_repo = TestRepository(db_session)
    test_service = TestService(db_session)
    scoring_service = ScoringService(db_session)

    # 1. Create Student
    student = await user_repo.create(
        telegram_id=777111222,
        first_name="Jasur",
        last_name="Bekov",
        username="jasur",
        phone_number="+998901112233",
        school="Toshkent 15-maktab",
        grade="9-B"
    )

    # 2. Create Test
    test = await test_service.create_test(
        title="Matematika Asoslari",
        subject_name="Matematika",
        topic_name="Tenglamalar",
        grade="9",
        author_id=student.id,
        time_limit_minutes=30,
        status=TestStatus.ACTIVE
    )

    assert test.id is not None
    assert test.code.startswith("TEST-")

    # 3. Add 3 Questions
    q1 = Question(
        text="2x + 5 = 15 bo'lsa, x nechaga teng?",
        option_a="3",
        option_b="5",
        option_c="7",
        option_d="10",
        correct_option="B",
        points=2.0
    )
    q2 = Question(
        text="12 ning 25% qismi nechaga teng?",
        option_a="2",
        option_b="3",
        option_c="4",
        option_d="6",
        correct_option="B",
        points=2.0
    )
    q3 = Question(
        text="Qaysi son tub son?",
        option_a="9",
        option_b="15",
        option_c="17",
        option_d="21",
        correct_option="C",
        points=2.0
    )

    await test_repo.add_question_to_test(test.id, q1, 1)
    await test_repo.add_question_to_test(test.id, q2, 2)
    await test_repo.add_question_to_test(test.id, q3, 3)

    # Refresh test with questions
    test_with_q = await test_repo.get_test_with_questions(test.id)
    assert len(test_with_q.test_questions) == 3

    # 4. Start Attempt (Anti-cheat)
    can_start, msg = await test_service.validate_can_start_test(test_with_q, student.id)
    assert can_start is True

    attempt = await test_service.start_attempt(test_with_q, student.id)
    assert attempt.id is not None
    assert len(attempt.question_order) == 3

    attempt_repo = AttemptRepository(db_session)
    # Save answers: Q1 -> correct, Q2 -> correct, Q3 -> incorrect
    await attempt_repo.save_answer(attempt.id, q1.id, "B", is_correct=True, points_earned=2.0)
    await attempt_repo.save_answer(attempt.id, q2.id, "B", is_correct=True, points_earned=2.0)
    await attempt_repo.save_answer(attempt.id, q3.id, "A", is_correct=False, points_earned=0.0)

    # 5. Complete and Score Attempt
    result = await scoring_service.complete_attempt(attempt.id)
    assert result.correct_count == 2
    assert result.incorrect_count == 1
    assert result.unanswered_count == 0
    assert result.total_score == 4.0
    assert result.max_score == 6.0
    assert round(result.percentage, 1) == 66.7
