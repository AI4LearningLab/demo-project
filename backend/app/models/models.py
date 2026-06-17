"""
app/models/models.py
All ORM models in one file for easy Alembic discovery.
Each table maps to a concept from the architecture design.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    String, Float, Integer, Boolean, Text,
    DateTime, Date, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
# from pgvector.sqlalchemy import Vector  # disabled until pgvector installed

from app.models.base import Base


# ── helpers ──────────────────────────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.utcnow()


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # relationships
    knowledge_states: Mapped[list["KnowledgeState"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    struggle_entries: Mapped[list["StruggleMap"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["DebugSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sm2_schedules: Mapped[list["SM2Schedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    behavior_pattern: Mapped["BehaviorPattern"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


# ── Knowledge State ───────────────────────────────────────────────────────────
# One row per (user, concept, sub_skill) triple.
# mastery_score: 0.0–1.0 updated after every session.

class KnowledgeState(Base):
    __tablename__ = "knowledge_states"
    __table_args__ = (
        UniqueConstraint("user_id", "concept", "sub_skill"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    concept: Mapped[str] = mapped_column(String(100))    # e.g. "null_pointer"
    sub_skill: Mapped[str] = mapped_column(String(100))  # e.g. "fault_localization"
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    times_encountered: Mapped[int] = mapped_column(Integer, default=0)
    times_struggled: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="knowledge_states")


# ── Struggle Map ──────────────────────────────────────────────────────────────

class StruggleMap(Base):
    __tablename__ = "struggle_map"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    bug_type: Mapped[str] = mapped_column(String(100))       # e.g. "off_by_one"
    sub_skill: Mapped[str] = mapped_column(String(100))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    last_occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    resolved_eventually: Mapped[bool] = mapped_column(Boolean, default=False)
    hints_needed_last: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="struggle_entries")


# ── Debug Session ─────────────────────────────────────────────────────────────

class DebugSession(Base):
    __tablename__ = "debug_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    bug_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sub_skill_tested: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hints_given: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # short plain-text summary
    # 384-dim vector from all-MiniLM-L6-v2; change dim if you swap model
    # embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["SessionMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="SessionMessage.created_at")


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("debug_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["DebugSession"] = relationship(back_populates="messages")


# ── SM-2 Schedule ─────────────────────────────────────────────────────────────

class SM2Schedule(Base):
    __tablename__ = "sm2_schedules"
    __table_args__ = (
        UniqueConstraint("user_id", "concept"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    concept: Mapped[str] = mapped_column(String(100))
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    next_review_at: Mapped[date] = mapped_column(Date, default=date.today)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    last_quality: Mapped[int] = mapped_column(Integer, default=0)  # 0-5

    user: Mapped["User"] = relationship(back_populates="sm2_schedules")


# ── Behavior Pattern ──────────────────────────────────────────────────────────

class BehaviorPattern(Base):
    __tablename__ = "behavior_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    avg_hints_needed: Mapped[float] = mapped_column(Float, default=0.0)
    forms_hypothesis_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0–1
    reads_error_first_rate: Mapped[float] = mapped_column(Float, default=0.0)
    sessions_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="behavior_pattern")


# ── Content Library ───────────────────────────────────────────────────────────

class ContentItem(Base):
    """Buggy code exercises and quiz questions stored for reuse."""
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    item_type: Mapped[str] = mapped_column(String(50))    # "buggy_code" | "quiz_question"
    bug_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1–5
    language: Mapped[str] = mapped_column(String(50), default="python")
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)             # the code or question text
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
