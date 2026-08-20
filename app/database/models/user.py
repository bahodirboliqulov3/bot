from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .group import GroupMember
    from .result import Certificate, Result, TestAttempt, Achievement
    from .test import SavedTest, Test
    from .system import SupportTicket


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    school: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    group_memberships: Mapped[List["GroupMember"]] = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    test_attempts: Mapped[List["TestAttempt"]] = relationship("TestAttempt", back_populates="user", cascade="all, delete-orphan")
    results: Mapped[List["Result"]] = relationship("Result", back_populates="user", cascade="all, delete-orphan")
    certificates: Mapped[List["Certificate"]] = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    saved_tests: Mapped[List["SavedTest"]] = relationship("SavedTest", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["Achievement"]] = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    created_tests: Mapped[List["Test"]] = relationship("Test", back_populates="author", foreign_keys="Test.author_id")
    support_tickets: Mapped[List["SupportTicket"]] = relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        ln = self.last_name or ""
        return f"{self.first_name} {ln}".strip()


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class BlockedUser(Base):
    __tablename__ = "blocked_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    blocked_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
