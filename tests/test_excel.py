from pathlib import Path
import openpyxl
import pytest
from app.config import settings
from app.database.models.result import Result, TestAttempt
from app.database.models.user import User
from app.services.excel_service import ExcelService


def test_excel_import_parsing(tmp_path: Path):
    excel_path = tmp_path / "test_import.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Savollar"

    # Header
    ws.append(["question", "option_a", "option_b", "option_c", "option_d", "correct_answer", "points"])

    # Valid row
    ws.append(["O'zbekiston poytaxti qaysi?", "Samarqand", "Toshkent", "Buxoro", "Xiva", "B", 2.0])
    # Invalid correct_answer row
    ws.append(["Quyosh qayerdan chiqadi?", "G'arb", "Sharq", "Shimol", "Janub", "Z", 1.0])
    # Empty question row
    ws.append(["", "A", "B", "C", "D", "A", 1.0])

    wb.save(excel_path)
    wb.close()

    questions, errors = ExcelService.parse_questions_from_excel(excel_path)

    assert len(questions) == 1
    assert questions[0]["text"] == "O'zbekiston poytaxti qaysi?"
    assert questions[0]["correct_option"] == "B"
    assert questions[0]["points"] == 2.0

    assert len(errors) == 2
    assert "correct_answer noto'g'ri" in errors[0]
    assert "Savol matni kiritilmagan" in errors[1]


def test_excel_export():
    u = User(
        id=1,
        first_name="Anvar",
        last_name="Saidov",
        username="anvar_s",
        telegram_id=12345,
        phone_number="+998901112233",
        school="Litsiy",
        grade="10"
    )
    res = Result(
        id=1,
        user_id=1,
        test_id=1,
        correct_count=18,
        incorrect_count=2,
        unanswered_count=0,
        total_score=36.0,
        max_score=40.0,
        percentage=90.0,
        time_spent_seconds=1200
    )
    res.user = u
    res.attempt = TestAttempt(
        id=1,
        test_id=1,
        user_id=1,
        started_at=u.created_at,
        finished_at=u.created_at
    )

    path = ExcelService.export_results_to_excel([res], "Ona tili va Adabiyot")
    assert path.exists()

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) == 2
    assert rows[1][1] == "Anvar"
    assert rows[1][7] == "90.0%"
    wb.close()
