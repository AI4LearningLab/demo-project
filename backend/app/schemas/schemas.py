"""
app/schemas/schemas.py
Pydantic v2 schemas — separate from ORM models.
Input schemas validate incoming data; output schemas control what gets serialised.
"""
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    display_name: str | None
    created_at: datetime


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """Single message sent from the frontend."""
    content: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None   # None → start new session


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    reminders: list[str] = []       # any prerequisite reminders injected
    hint_level: int = 0             # 0 = no hints given yet this session


# ── Knowledge State ───────────────────────────────────────────────────────────

class KnowledgeStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    concept: str
    sub_skill: str
    mastery_score: float
    times_encountered: int
    times_struggled: int
    last_seen_at: datetime | None


# ── Struggle Map ──────────────────────────────────────────────────────────────

class StruggleEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bug_type: str
    sub_skill: str
    occurrence_count: int
    last_occurred_at: datetime
    resolved_eventually: bool


# ── SM-2 Schedule ─────────────────────────────────────────────────────────────

class SM2ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    concept: str
    interval_days: int
    ease_factor: float
    next_review_at: date
    repetitions: int


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuizRequest(BaseModel):
    topic: str | None = None   # None → auto-select from weak areas


class QuizQuestion(BaseModel):
    question: str
    options: list[str] | None = None
    correct_answer: str | None = None   # omitted when sending to user


class QuizResult(BaseModel):
    question: str
    user_answer: str
    correct: bool
    explanation: str


class QuizSubmit(BaseModel):
    session_id: str
    answers: list[dict]   # [{question, answer}]


# ── Progress Dashboard ────────────────────────────────────────────────────────

class ProgressSummary(BaseModel):
    total_sessions: int
    avg_hints_per_session: float
    top_struggles: list[StruggleEntryOut]
    knowledge_states: list[KnowledgeStateOut]
    upcoming_reviews: list[SM2ScheduleOut]
