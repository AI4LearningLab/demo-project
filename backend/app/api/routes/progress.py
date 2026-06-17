"""app/api/routes/progress.py"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import User, KnowledgeState, StruggleMap, SM2Schedule, DebugSession
from app.schemas.schemas import ProgressSummary, KnowledgeStateOut, StruggleEntryOut, SM2ScheduleOut
from app.core.auth import get_current_user
from datetime import date

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/summary", response_model=ProgressSummary)
async def get_progress_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id

    # Total sessions
    total = await db.execute(
        select(func.count()).select_from(DebugSession).where(DebugSession.user_id == uid)
    )
    total_sessions = total.scalar() or 0

    # Avg hints (simplified)
    avg_hints_result = await db.execute(
        select(func.avg(DebugSession.hints_given)).where(DebugSession.user_id == uid)
    )
    avg_hints = float(avg_hints_result.scalar() or 0)

    # Top struggles
    struggles_result = await db.execute(
        select(StruggleMap)
        .where(StruggleMap.user_id == uid)
        .order_by(StruggleMap.occurrence_count.desc())
        .limit(5)
    )
    struggles = [StruggleEntryOut.model_validate(s) for s in struggles_result.scalars().all()]

    # Knowledge states
    ks_result = await db.execute(
        select(KnowledgeState).where(KnowledgeState.user_id == uid)
    )
    knowledge_states = [KnowledgeStateOut.model_validate(ks) for ks in ks_result.scalars().all()]

    # Upcoming reviews
    reviews_result = await db.execute(
        select(SM2Schedule)
        .where(SM2Schedule.user_id == uid, SM2Schedule.next_review_at <= date.today())
        .limit(10)
    )
    upcoming = [SM2ScheduleOut.model_validate(r) for r in reviews_result.scalars().all()]

    return ProgressSummary(
        total_sessions=total_sessions,
        avg_hints_per_session=round(avg_hints, 2),
        top_struggles=struggles,
        knowledge_states=knowledge_states,
        upcoming_reviews=upcoming,
    )
