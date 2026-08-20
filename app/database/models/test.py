from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .result import TestAttempt, Result, Certificate


class TestStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    FINISHED = "finished"
    ARCHIVED = "archived"


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    tests: Mapped[List["Test"]] = relationship("Test", back_populates="subject")


class Topic(Base):
    __tablename__ = "topics"
    table_args = (
        UniqueConstraint("subject_id", "name", name="uq_subject_topic"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="topics")
    tests: Mapped[List["Test"]] = relationship("Test", back_populates="topic")


class Test(Base, TimestampMixin):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    grade: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # PDF / Photo test questions file
    file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 'document', 'photo'
    
    # Answer key string (e.g. "ABCDACBD...")
    answer_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Explanation / Solution attachment (video link or PDF file)
    explanation_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    explanation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_points: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    pass_percentage: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    password: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_backtracking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus, native_enum=False),
        default=TestStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    author: Mapped[Optional["User"]] = relationship("User", back_populates="created_tests", foreign_keys=[author_id])
    subject: Mapped[Optional["Subject"]] = relationship("Subject", back_populates="tests")
    topic: Mapped[Optional["Topic"]] = relationship("Topic", back_populates="tests")
    test_questions: Mapped[List["TestQuestion"]] = relationship("TestQuestion", back_populates="test", cascade="all, delete-orphan", order_by="TestQuestion.order_index")
    attempts: Mapped[List["TestAttempt"]] = relationship("TestAttempt", back_populates="test", cascade="all, delete-orphan")
    results: Mapped[List["Result"]] = relationship("Result", back_populates="test", cascade="all, delete-orphan")
    certificates: Mapped[List["Certificate"]] = relationship("Certificate", back_populates="test", cascade="all, delete-orphan")
    saved_by: Mapped[List["SavedTest"]] = relationship("SavedTest", back_populates="test", cascade="all, delete-orphan")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    
    correct_option: Mapped[str] = mapped_column(String(4), nullable=False)  # 'A', 'B', 'C', 'D'
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    test_questions: Mapped[List["TestQuestion"]] = relationship("TestQuestion", back_populates="question", cascade="all, delete-orphan")


class TestQuestion(Base):
    __tablename__ = "test_questions"
    table_args = (
        UniqueConstraint("test_id", "question_id", name="uq_test_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    test: Mapped["Test"] = relationship("Test", back_populates="test_questions")
    question: Mapped["Question"] = relationship("Question", back_populates="test_questions")


class SavedTest(Base):
    __tablename__ = "saved_tests"
    table_args = (
        UniqueConstraint("user_id", "test_id", name="uq_user_saved_test"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="saved_tests")
    test: Mapped["Test"] = relationship("Test", back_populates="saved_by")
