from pathlib import Path
import pytest
from app.database.models.result import Result
from app.database.models.test import Test
from app.database.models.user import User
from app.database.repositories.certificate_repo import CertificateRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.repositories.user_repo import UserRepository
from app.services.certificate_service import CertificateService


@pytest.mark.asyncio
async def test_certificate_issuance_and_pdf_generation(db_session):
    user_repo = UserRepository(db_session)
    test_repo = TestRepository(db_session)
    res_repo = ResultRepository(db_session)
    cert_service = CertificateService(db_session)

    user = await user_repo.create(
        telegram_id=333444555,
        first_name="Zafar",
        last_name="Yusupov",
        username="zafar",
        phone_number="+998901234567",
        school="Toshkent 2-IDUM",
        grade="10-A"
    )

    test = await test_repo.create(
        code="TEST-CERT1",
        title="Olimpiada Matematika",
        pass_percentage=70.0
    )

    res = await res_repo.create(
        attempt_id=1,
        user_id=user.id,
        test_id=test.id,
        correct_count=18,
        incorrect_count=2,
        unanswered_count=0,
        total_score=90.0,
        max_score=100.0,
        percentage=90.0,
        time_spent_seconds=900
    )

    cert = await cert_service.issue_certificate(res, user, test)
    assert cert.id is not None
    assert cert.certificate_number.startswith("CERT-")
    assert Path(cert.pdf_path).exists()
    assert Path(cert.pdf_path).stat().st_size > 0
