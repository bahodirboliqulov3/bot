import pytest
from app.database.models.test import Question, TestStatus
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.scoring_service import ScoringService
from app.services.test_service import TestService


@pytest.mark.asyncio
async def test_quick_answers_parser_and_evaluation(db_session):
    # 1. Test text parser
    parsed = ScoringService.parse_quick_answers("1-A 2-C 3-b 4-D 5.a")
    assert parsed[1] == "A"
    assert parsed[2] == "C"
    assert parsed[3] == "B"
    assert parsed[4] == "D"
    assert parsed[5] == "A"

    # 2. Test quick evaluation against real test in DB
    user_repo = UserRepository(db_session)
    test_repo = TestRepository(db_session)
    test_service = TestService(db_session)
    scoring_service = ScoringService(db_session)

    user = await user_repo.create(
        telegram_id=987123456,
        first_name="Dilshod",
        last_name="Karimov",
        username="dilshod",
        phone_number="+998909998877",
        school="Litsiy",
        grade="11"
    )

    test = await test_service.create_test(
        title="Ingliz tili Grammar",
        subject_name="Ingliz tili",
        grade="11",
        author_id=user.id,
        status=TestStatus.ACTIVE
    )

    q1 = Question(text="Q1", option_a="is", option_b="are", option_c="am", option_d="be", correct_option="A", points=1.0)
    q2 = Question(text="Q2", option_a="do", option_b="does", option_c="did", option_d="done", correct_option="C", points=1.0)

    await test_repo.add_question_to_test(test.id, q1, 1)
    await test_repo.add_question_to_test(test.id, q2, 2)

    result, visual_grid = await scoring_service.evaluate_quick_submission(
        test_id=test.id,
        user_id=user.id,
        raw_answers="1-A 2-C"
    )

    assert result.correct_count == 2
    assert result.incorrect_count == 0
    assert result.percentage == 100.0
    assert visual_grid is not None
