from datetime import datetime, timezone
import random
import string
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.result import AttemptStatus, TestAttempt
from app.database.models.test import Question, Test, TestQuestion, TestStatus
from app.database.repositories.result_repo import AttemptRepository
from app.database.repositories.test_repo import SubjectRepository, TestRepository, TopicRepository


class TestService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.test_repo = TestRepository(session)
        self.subject_repo = SubjectRepository(session)
        self.topic_repo = TopicRepository(session)
        self.attempt_repo = AttemptRepository(session)

    @staticmethod
    def generate_test_code(prefix: str = "TEST-") -> str:
        random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"{prefix}{random_suffix}"

    async def create_test(
        self,
        title: str,
        code: Optional[str] = None,
        file_id: Optional[str] = None,
        file_type: Optional[str] = None,
        answer_key: Optional[str] = None,
        total_questions: int = 0,
        subject_name: Optional[str] = None,
        topic_name: Optional[str] = None,
        grade: Optional[str] = None,
        author_id: Optional[int] = None,
        time_limit_minutes: int = 30,
        max_points: float = 100.0,
        pass_percentage: float = 60.0,
        max_attempts: int = 1,
        password: Optional[str] = None,
        shuffle_questions: bool = True,
        shuffle_options: bool = True,
        allow_backtracking: bool = True,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: TestStatus = TestStatus.ACTIVE
    ) -> Test:
        if code:
            test_code = code.strip().upper()
            existing = await self.test_repo.get_by_code(test_code)
            if existing:
                test_code = self.generate_test_code()
        else:
            test_code = self.generate_test_code()
            while await self.test_repo.get_by_code(test_code):
                test_code = self.generate_test_code()

        subject_id = None
        if subject_name:
            subject = await self.subject_repo.get_or_create(subject_name)
            subject_id = subject.id

        topic_id = None
        if subject_id and topic_name:
            topic = await self.topic_repo.get_or_create(subject_id, topic_name)
            topic_id = topic.id

        test = await self.test_repo.create(
            code=test_code,
            title=title,
            file_id=file_id,
            file_type=file_type,
            answer_key=answer_key.strip().upper() if answer_key else None,
            total_questions=total_questions,
            subject_id=subject_id,
            topic_id=topic_id,
            grade=grade,
            author_id=author_id,
            time_limit_minutes=time_limit_minutes,
            max_points=max_points,
            pass_percentage=pass_percentage,
            max_attempts=max_attempts,
            password=password.strip() if password else None,
            shuffle_questions=shuffle_questions,
            shuffle_options=shuffle_options,
            allow_backtracking=allow_backtracking,
            start_time=start_time,
            end_time=end_time,
            status=status
        )
        return test

    async def duplicate_test(self, original_test_id: int, new_author_id: Optional[int] = None) -> Optional[Test]:
        original = await self.test_repo.get_test_with_questions(original_test_id)
        if not original:
            return None

        new_test = await self.create_test(
            title=f"{original.title} (Nusxa)",
            file_id=original.file_id,
            file_type=original.file_type,
            answer_key=original.answer_key,
            total_questions=original.total_questions,
            subject_name=original.subject.name if original.subject else None,
            topic_name=original.topic.name if original.topic else None,
            grade=original.grade,
            author_id=new_author_id or original.author_id,
            time_limit_minutes=original.time_limit_minutes,
            max_points=original.max_points,
            pass_percentage=original.pass_percentage,
            max_attempts=original.max_attempts,
            password=original.password,
            shuffle_questions=original.shuffle_questions,
            shuffle_options=original.shuffle_options,
            allow_backtracking=original.allow_backtracking,
            start_time=original.start_time,
            end_time=original.end_time,
            status=TestStatus.DRAFT
        )

        for tq in original.test_questions:
            await self.test_repo.add_existing_question_to_test(
                test_id=new_test.id,
                question_id=tq.question_id,
                order_index=tq.order_index
            )

        return new_test

    async def validate_can_start_test(self, test: Test, user_id: int, password: Optional[str] = None) -> Tuple[bool, str]:
        # 1. Status check
        if test.status != TestStatus.ACTIVE:
            if test.status == TestStatus.DRAFT:
                return False, "⛔ Bu test hali qoralama (draft) holatida."
            elif test.status == TestStatus.SCHEDULED:
                return False, "⏳ Test hali boshlanmagan yoki rejalashtirilgan vaqtda emas."
            else:
                return False, "⛔ Bu test mavjud emas yoki yakunlangan."

        # 2. Time window check
        now = datetime.now(timezone.utc)
        if test.start_time and now < test.start_time:
            return False, f"⏳ Test {test.start_time.strftime('%d.%m.%Y %H:%M')} da boshlanadi."
        if test.end_time and now > test.end_time:
            return False, "⛔ Test yakunlangan (vaqti o'tib ketgan)."

        # 3. Password check
        if test.password:
            if not password or password.strip() != test.password:
                return False, "🔐 Test paroli noto'g'ri."

        # 4. Max attempts check
        attempt_count = await self.attempt_repo.get_user_attempt_count(user_id, test.id)
        if attempt_count >= test.max_attempts:
            return False, f"⛔ Siz ushbu testni maksimal {test.max_attempts} marta topshirgansiz."

        # 5. Check if questions or answer_key exist
        if not test.test_questions and not test.answer_key:
            return False, "⛔ Ushbu testda hali savollar yoki javoblar kaliti mavjud emas."

        return True, "OK"

    async def start_attempt(self, test: Test, user_id: int) -> TestAttempt:
        active = await self.attempt_repo.get_active_attempt(user_id, test.id)
        if active:
            return active

        question_ids = [tq.question_id for tq in test.test_questions]
        if test.shuffle_questions:
            random.shuffle(question_ids)

        option_order: Dict[str, Dict[str, str]] = {}
        for q_id in question_ids:
            if test.shuffle_options:
                original_options = ["A", "B", "C", "D"]
                shuffled = original_options.copy()
                random.shuffle(shuffled)
                mapping = {display: orig for display, orig in zip(original_options, shuffled)}
                option_order[str(q_id)] = mapping
            else:
                option_order[str(q_id)] = {"A": "A", "B": "B", "C": "C", "D": "D"}

        attempt_count = await self.attempt_repo.get_user_attempt_count(user_id, test.id)
        
        attempt = await self.attempt_repo.create(
            test_id=test.id,
            user_id=user_id,
            attempt_number=attempt_count + 1,
            status=AttemptStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            question_order=question_ids,
            option_order=option_order
        )
        return attempt
