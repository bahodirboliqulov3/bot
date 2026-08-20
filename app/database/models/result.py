from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .test import Test, Question


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class TestAttempt(Base, TimestampMixin):
    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, native_enum=False),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
        index=True
    )
    
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Anti-cheat state: question IDs in randomized order and randomized options mapping
    question_order: Mapped[List[int]] = mapped_column(JSON, default=list, nullable=False)
    option_order: Mapped[Dict[str, Dict[str, str]]] = mapped_column(JSON, default=dict, nullable=False) # e.g. {"1": {"A": "B", "B": "C", ...}}

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="test_attempts")
    test: Mapped["Test"] = relationship("Test", back_populates="attempts")
    student_answers: Mapped[List["StudentAnswer"]] = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")
    result: Mapped[Optional["Result"]] = relationship("Result", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    selected_option: Mapped[str] = mapped_column(String(4), nullable=False)  # 'A', 'B', 'C', 'D'
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    points_earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    attempt: Mapped["TestAttempt"] = relationship("TestAttempt", back_populates="student_answers")
    question: Mapped["Question"] = relationship("Question")


class Result(Base, TimestampMixin):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank_in_test: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    attempt: Mapped["TestAttempt"] = relationship("TestAttempt", back_populates="result")
    user: Mapped["User"] = relationship("User", back_populates="results")
    test: Mapped["Test"] = relationship("Test", back_populates="results")
    certificate: Mapped[Optional["Certificate"]] = relationship("Certificate", back_populates="result", uselist=False, cascade="all, delete-orphan")


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    certificate_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    score: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="certificates")
    test: Mapped["Test"] = relationship("Test", back_populates="certificates")
    result: Mapped["Result"] = relationship("Result", back_populates="certificate")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_type: Mapped[str] = mapped_column(String(64), nullable=False)  # first_test, perfect_score, top_rank, etc.
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="achievements")
