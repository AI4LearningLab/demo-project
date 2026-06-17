"""
app/services/context/context_builder.py

Retrieves and assembles the user's learning context.
This is the RAG layer: pulls structured data (mastery, struggles)
AND semantic data (similar past sessions via pgvector).
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import (
    KnowledgeState, StruggleMap, BehaviorPattern, SM2Schedule
)
from app.services.llm.embedding_service import embedding_service
from app.core.logging import get_logger

logger = get_logger(__name__)

# Prerequisite map: bug_type → list of concepts the student must understand
PREREQUISITE_MAP: dict[str, list[str]] = {
    "null_pointer":    ["pointers", "memory_references", "object_initialization"],
    "stack_overflow":  ["recursion", "call_stack", "base_case"],
    "off_by_one":      ["array_indexing", "loop_bounds", "zero_indexing"],
    "scope_error":     ["variable_scope", "namespaces", "closures"],
    "type_error":      ["data_types", "type_casting", "dynamic_typing"],
    "memory_leak":     ["heap_memory", "garbage_collection", "pointers"],
    "race_condition":  ["concurrency", "threads", "shared_state"],
}

MASTERY_WEAK_THRESHOLD = 0.5
REMINDER_STALE_DAYS = 7


class UserContext:
    """Snapshot of everything the system knows about a user right now."""
    def __init__(
        self,
        user_id: str,
        mastery: list[dict],
        struggles: list[dict],
        behavior: dict | None,
        similar_sessions: list[dict],
        prerequisite_reminders: list[str],
        due_reviews: list[str],
    ) -> None:
        self.user_id = user_id
        self.mastery = mastery
        self.struggles = struggles
        self.behavior = behavior
        self.similar_sessions = similar_sessions
        self.prerequisite_reminders = prerequisite_reminders
        self.due_reviews = due_reviews


class ContextBuilder:
    """
    Given a user_id and the current student query,
    fetch all relevant context and return a UserContext object.
    """

    async def build(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        detected_bug_type: str | None = None,
    ) -> UserContext:
        logger.debug("context.building", user_id=user_id, bug_type=detected_bug_type)

        mastery      = await self._get_weak_mastery(db, user_id)
        struggles    = await self._get_top_struggles(db, user_id)
        behavior     = await self._get_behavior(db, user_id)
        similar      = await embedding_service.find_similar_sessions(db, user_id, query)
        prereqs      = await self._check_prerequisites(db, user_id, detected_bug_type)
        due_reviews  = await self._get_due_reviews(db, user_id)

        return UserContext(
            user_id=user_id,
            mastery=mastery,
            struggles=struggles,
            behavior=behavior,
            similar_sessions=similar,
            prerequisite_reminders=prereqs,
            due_reviews=due_reviews,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    async def _get_weak_mastery(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(KnowledgeState)
            .where(
                and_(
                    KnowledgeState.user_id == user_id,
                    KnowledgeState.mastery_score < MASTERY_WEAK_THRESHOLD,
                )
            )
            .order_by(KnowledgeState.mastery_score.asc())
            .limit(5)
        )
        return [
            {"concept": ks.concept, "sub_skill": ks.sub_skill, "score": ks.mastery_score}
            for ks in result.scalars().all()
        ]

    async def _get_top_struggles(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(StruggleMap)
            .where(StruggleMap.user_id == user_id)
            .order_by(StruggleMap.occurrence_count.desc())
            .limit(5)
        )
        return [
            {
                "bug_type": s.bug_type,
                "sub_skill": s.sub_skill,
                "count": s.occurrence_count,
                "last_occurred": s.last_occurred_at.isoformat(),
            }
            for s in result.scalars().all()
        ]

    async def _get_behavior(self, db: AsyncSession, user_id: str) -> dict | None:
        result = await db.execute(
            select(BehaviorPattern).where(BehaviorPattern.user_id == user_id)
        )
        bp = result.scalar_one_or_none()
        if bp is None:
            return None
        return {
            "avg_hints_needed": bp.avg_hints_needed,
            "forms_hypothesis_rate": bp.forms_hypothesis_rate,
            "reads_error_first_rate": bp.reads_error_first_rate,
        }

    async def _check_prerequisites(
        self,
        db: AsyncSession,
        user_id: str,
        bug_type: str | None,
    ) -> list[str]:
        """
        Return reminder strings for any prerequisite concepts that are:
        - weak (mastery < threshold) AND
        - not seen recently (last_seen > REMINDER_STALE_DAYS days ago)
        """
        if bug_type is None or bug_type not in PREREQUISITE_MAP:
            return []

        prereqs = PREREQUISITE_MAP[bug_type]
        stale_cutoff = datetime.utcnow() - timedelta(days=REMINDER_STALE_DAYS)

        result = await db.execute(
            select(KnowledgeState).where(
                and_(
                    KnowledgeState.user_id == user_id,
                    KnowledgeState.concept.in_(prereqs),
                    KnowledgeState.mastery_score < MASTERY_WEAK_THRESHOLD,
                )
            )
        )
        weak = result.scalars().all()

        reminders = []
        for ks in weak:
            is_stale = ks.last_seen_at is None or ks.last_seen_at < stale_cutoff
            if is_stale:
                reminders.append(
                    f"Quick reminder: you covered '{ks.concept}' "
                    f"{'recently' if ks.last_seen_at else 'before'} "
                    f"— it's a prerequisite for the current bug."
                )
        return reminders

    async def _get_due_reviews(self, db: AsyncSession, user_id: str) -> list[str]:
        from datetime import date
        result = await db.execute(
            select(SM2Schedule).where(
                and_(
                    SM2Schedule.user_id == user_id,
                    SM2Schedule.next_review_at <= date.today(),
                )
            )
        )
        return [s.concept for s in result.scalars().all()]


context_builder = ContextBuilder()
