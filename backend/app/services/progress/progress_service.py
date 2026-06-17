"""
app/services/progress/progress_service.py

Updates the student's knowledge state, struggle map, and behavior pattern
at the end of every debug session.

Outcome enum → mastery delta:
  solved_no_hints    +0.10
  solved_with_hints  +0.05
  failed_after_hints -0.10
  repeated_mistake   -0.15
"""
from datetime import datetime
from enum import StrEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import KnowledgeState, StruggleMap, BehaviorPattern
from app.core.logging import get_logger

logger = get_logger(__name__)

MASTERY_DELTA: dict[str, float] = {
    "solved_no_hints":    +0.10,
    "solved_with_hints":  +0.05,
    "failed_after_hints": -0.10,
    "repeated_mistake":   -0.15,
}


class SessionOutcome(StrEnum):
    SOLVED_NO_HINTS    = "solved_no_hints"
    SOLVED_WITH_HINTS  = "solved_with_hints"
    FAILED_AFTER_HINTS = "failed_after_hints"
    REPEATED_MISTAKE   = "repeated_mistake"


def _determine_outcome(
    resolved: bool,
    hints_given: int,
    is_recurring_bug: bool,
) -> SessionOutcome:
    """Derive outcome from session metrics."""
    if is_recurring_bug and not resolved:
        return SessionOutcome.REPEATED_MISTAKE
    if resolved and hints_given == 0:
        return SessionOutcome.SOLVED_NO_HINTS
    if resolved:
        return SessionOutcome.SOLVED_WITH_HINTS
    return SessionOutcome.FAILED_AFTER_HINTS


class ProgressService:

    async def update_after_session(
        self,
        db: AsyncSession,
        user_id: str,
        concept: str,
        sub_skill: str,
        bug_type: str,
        resolved: bool,
        hints_given: int,
        formed_hypothesis: bool,
        read_error_first: bool,
    ) -> dict:
        """
        Called when a debug session ends.
        Updates knowledge state, struggle map, and behavior pattern.
        Returns a summary dict for logging / response.
        """
        is_recurring = await self._is_recurring(db, user_id, bug_type)
        outcome = _determine_outcome(resolved, hints_given, is_recurring)
        delta = MASTERY_DELTA[outcome]

        mastery = await self._upsert_knowledge_state(
            db, user_id, concept, sub_skill, delta, resolved
        )
        await self._upsert_struggle(
            db, user_id, bug_type, sub_skill, resolved, hints_given
        )
        await self._update_behavior(
            db, user_id, hints_given, formed_hypothesis, read_error_first
        )

        logger.info(
            "progress.updated",
            user=user_id,
            concept=concept,
            outcome=outcome,
            new_mastery=mastery,
        )
        return {"outcome": outcome, "mastery_score": mastery, "delta": delta}

    # ── private ───────────────────────────────────────────────────────────────

    async def _upsert_knowledge_state(
        self,
        db: AsyncSession,
        user_id: str,
        concept: str,
        sub_skill: str,
        delta: float,
        resolved: bool,
    ) -> float:
        result = await db.execute(
            select(KnowledgeState).where(
                and_(
                    KnowledgeState.user_id == user_id,
                    KnowledgeState.concept == concept,
                    KnowledgeState.sub_skill == sub_skill,
                )
            )
        )
        ks = result.scalar_one_or_none()

        if ks is None:
            new_score = max(0.0, min(1.0, 0.0 + delta))
            ks = KnowledgeState(
                user_id=user_id,
                concept=concept,
                sub_skill=sub_skill,
                mastery_score=new_score,
                times_encountered=1,
                times_struggled=0 if resolved else 1,
                last_seen_at=datetime.utcnow(),
            )
            db.add(ks)
        else:
            ks.mastery_score = max(0.0, min(1.0, ks.mastery_score + delta))
            ks.times_encountered += 1
            if not resolved:
                ks.times_struggled += 1
            ks.last_seen_at = datetime.utcnow()

        await db.flush()
        return ks.mastery_score

    async def _upsert_struggle(
        self,
        db: AsyncSession,
        user_id: str,
        bug_type: str,
        sub_skill: str,
        resolved: bool,
        hints_given: int,
    ) -> None:
        result = await db.execute(
            select(StruggleMap).where(
                and_(
                    StruggleMap.user_id == user_id,
                    StruggleMap.bug_type == bug_type,
                )
            )
        )
        sm = result.scalar_one_or_none()

        if sm is None:
            if not resolved:
                db.add(StruggleMap(
                    user_id=user_id,
                    bug_type=bug_type,
                    sub_skill=sub_skill,
                    occurrence_count=1,
                    last_occurred_at=datetime.utcnow(),
                    resolved_eventually=False,
                    hints_needed_last=hints_given,
                ))
        else:
            if not resolved:
                sm.occurrence_count += 1
                sm.last_occurred_at = datetime.utcnow()
                sm.hints_needed_last = hints_given
            else:
                sm.resolved_eventually = True

        await db.flush()

    async def _update_behavior(
        self,
        db: AsyncSession,
        user_id: str,
        hints_given: int,
        formed_hypothesis: bool,
        read_error_first: bool,
    ) -> None:
        result = await db.execute(
            select(BehaviorPattern).where(BehaviorPattern.user_id == user_id)
        )
        bp = result.scalar_one_or_none()

        if bp is None:
            bp = BehaviorPattern(
                user_id=user_id,
                avg_hints_needed=float(hints_given),
                forms_hypothesis_rate=1.0 if formed_hypothesis else 0.0,
                reads_error_first_rate=1.0 if read_error_first else 0.0,
                sessions_evaluated=1,
            )
            db.add(bp)
        else:
            n = bp.sessions_evaluated
            bp.avg_hints_needed = (bp.avg_hints_needed * n + hints_given) / (n + 1)
            bp.forms_hypothesis_rate = (
                bp.forms_hypothesis_rate * n + (1.0 if formed_hypothesis else 0.0)
            ) / (n + 1)
            bp.reads_error_first_rate = (
                bp.reads_error_first_rate * n + (1.0 if read_error_first else 0.0)
            ) / (n + 1)
            bp.sessions_evaluated += 1

        await db.flush()

    async def _is_recurring(
        self, db: AsyncSession, user_id: str, bug_type: str
    ) -> bool:
        result = await db.execute(
            select(StruggleMap).where(
                and_(
                    StruggleMap.user_id == user_id,
                    StruggleMap.bug_type == bug_type,
                )
            )
        )
        sm = result.scalar_one_or_none()
        return sm is not None and sm.occurrence_count >= 2


progress_service = ProgressService()
