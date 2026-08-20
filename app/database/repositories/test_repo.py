from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.test import Question, SavedTest, Subject, Test, TestQuestion, TestStatus, Topic
from .base_repo import BaseRepository


class TestRepository(BaseRepository[Test]):
    def __init__(self, session: AsyncSession):
        super().__init__(Test, session)

    async def get_by_code(self, code: str) -> Optional[Test]:
        stmt = (
            select(Test)
            .where(Test.code == code.upper().strip())
            .options(
                selectinload(Test.subject),
                selectinload(Test.topic),
                selectinload(Test.test_questions).selectinload(TestQuestion.question)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_test_with_questions(self, test_id: int) -> Optional[Test]:
        stmt = (
            select(Test)
            .where(Test.id == test_id)
            .options(
                selectinload(Test.subject),
                selectinload(Test.topic),
                selectinload(Test.test_questions).selectinload(TestQuestion.question)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_tests(self, limit: int = 20) -> List[Test]:
        stmt = (
            select(Test)
            .order_by(Test.created_at.desc())
            .options(selectinload(Test.subject), selectinload(Test.topic), selectinload(Test.test_questions))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_tests(
        self,
        subject_id: Optional[int] = None,
        grade: Optional[str] = None,
        topic_id: Optional[int] = None,
        status: Optional[TestStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Test]:
        stmt = (
            select(Test)
            .options(selectinload(Test.subject), selectinload(Test.topic), selectinload(Test.test_questions))
        )
        if status:
            stmt = stmt.where(Test.status == status)
        else:
            stmt = stmt.where(Test.status.in_([TestStatus.ACTIVE, TestStatus.SCHEDULED]))
            
        if subject_id:
            stmt = stmt.where(Test.subject_id == subject_id)
        if grade:
            stmt = stmt.where(Test.grade == grade)
        if topic_id:
            stmt = stmt.where(Test.topic_id == topic_id)
            
        stmt = stmt.order_by(Test.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tests_by_author(self, author_id: int) -> List[Test]:
        stmt = (
            select(Test)
            .where(Test.author_id == author_id)
            .options(selectinload(Test.subject), selectinload(Test.test_questions))
            .order_by(Test.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_question_to_test(self, test_id: int, question: Question, order_index: int = 0) -> TestQuestion:
        self.session.add(question)
        await self.session.flush()
        
        test_q = TestQuestion(test_id=test_id, question_id=question.id, order_index=order_index)
        self.session.add(test_q)
        await self.session.flush()
        return test_q

    async def add_existing_question_to_test(self, test_id: int, question_id: int, order_index: int = 0) -> TestQuestion:
        test_q = TestQuestion(test_id=test_id, question_id=question_id, order_index=order_index)
        self.session.add(test_q)
        await self.session.flush()
        return test_q

    async def toggle_save_test(self, user_id: int, test_id: int) -> bool:
        """Returns True if saved, False if unsaved"""
        stmt = select(SavedTest).where(SavedTest.user_id == user_id, SavedTest.test_id == test_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return False
        else:
            saved = SavedTest(user_id=user_id, test_id=test_id)
            self.session.add(saved)
            await self.session.flush()
            return True

    async def get_saved_tests(self, user_id: int) -> List[Test]:
        stmt = (
            select(Test)
            .join(SavedTest, Test.id == SavedTest.test_id)
            .where(SavedTest.user_id == user_id)
            .options(selectinload(Test.subject), selectinload(Test.test_questions))
            .order_by(SavedTest.saved_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def is_test_saved(self, user_id: int, test_id: int) -> bool:
        stmt = select(SavedTest).where(SavedTest.user_id == user_id, SavedTest.test_id == test_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class SubjectRepository(BaseRepository[Subject]):
    def __init__(self, session: AsyncSession):
        super().__init__(Subject, session)

    async def get_or_create(self, name: str) -> Subject:
        clean_name = name.strip()
        stmt = select(Subject).where(Subject.name.ilike(clean_name))
        result = await self.session.execute(stmt)
        subj = result.scalar_one_or_none()
        if not subj:
            subj = Subject(name=clean_name)
            self.session.add(subj)
            await self.session.flush()
            await self.session.refresh(subj)
        return subj

    async def get_all_with_topics(self) -> List[Subject]:
        stmt = select(Subject).options(selectinload(Subject.topics)).order_by(Subject.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TopicRepository(BaseRepository[Topic]):
    def __init__(self, session: AsyncSession):
        super().__init__(Topic, session)

    async def get_or_create(self, subject_id: int, name: str) -> Topic:
        clean_name = name.strip()
        stmt = select(Topic).where(Topic.subject_id == subject_id, Topic.name.ilike(clean_name))
        result = await self.session.execute(stmt)
        top = result.scalar_one_or_none()
        if not top:
            top = Topic(subject_id=subject_id, name=clean_name)
            self.session.add(top)
            await self.session.flush()
            await self.session.refresh(top)
        return top

    async def get_by_subject(self, subject_id: int) -> List[Topic]:
        stmt = select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
