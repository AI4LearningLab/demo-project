"""
app/services/reminder/sm2.py

SM-2 spaced repetition algorithm (Wozniak, 1987).
Implemented from scratch — no library dependency.
This is a research contribution: we apply SM-2 specifically to
debugging sub-skill concepts rather than vocabulary flashcards.

Quality scale (0–5):
  0 — complete blackout
  1 — wrong, correct answer remembered after seeing it
  2 — wrong, but correct answer seemed easy once seen
  3 — correct, but required significant effort
  4 — correct, after slight hesitation
  5 — perfect recall
"""
from datetime import date, timedelta
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import SM2Schedule
from app.core.logging import get_logger

logger = get_logger(__name__)

MIN_EASE_FACTOR = 1.3
INITIAL_EASE_FACTOR = 2.5


@dataclass
class SM2Result:
    interval_days: int
    ease_factor: float
    next_review_at: date
    repetitions: int


def calculate_sm2(
    quality: int,           # 0–5 (see module docstring)
    interval_days: int,
    ease_factor: float,
    repetitions: int,
) -> SM2Result:
    """
    Pure function — takes current SM-2 state and quality score,
    returns the updated state. No side effects.
    """
    if quality < 3:
        # Student failed → reset to beginning
        new_interval = 1
        new_repetitions = 0
    elif repetitions == 0:
        new_interval = 1
        new_repetitions = 1
    elif repetitions == 1:
        new_interval = 3
        new_repetitions = 2
    else:
        new_interval = round(interval_days * ease_factor)
        new_repetitions = repetitions + 1

    # Ease factor update (standard SM-2 formula)
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(MIN_EASE_FACTOR, new_ef)

    return SM2Result(
        interval_days=new_interval,
        ease_factor=round(new_ef, 3),
        next_review_at=date.today() + timedelta(days=new_interval),
        repetitions=new_repetitions,
    )


class SM2Service:
    """Handles database reads/writes for SM-2 schedules."""

    async def record_review(
        self,
        db: AsyncSession,
        user_id: str,
        concept: str,
        quality: int,
    ) -> SM2Result:
        """
        Update (or create) the SM-2 schedule entry for (user, concept)
        after a review/quiz interaction.
        """
        result = await db.execute(
            select(SM2Schedule).where(
                and_(SM2Schedule.user_id == user_id, SM2Schedule.concept == concept)
            )
        )
        schedule = result.scalar_one_or_none()

        if schedule is None:
            # First time seeing this concept
            sm2_result = calculate_sm2(quality, 1, INITIAL_EASE_FACTOR, 0)
            schedule = SM2Schedule(
                user_id=user_id,
                concept=concept,
                interval_days=sm2_result.interval_days,
                ease_factor=sm2_result.ease_factor,
                next_review_at=sm2_result.next_review_at,
                repetitions=sm2_result.repetitions,
                last_quality=quality,
            )
            db.add(schedule)
        else:
            sm2_result = calculate_sm2(
                quality, schedule.interval_days, schedule.ease_factor, schedule.repetitions
            )
            schedule.interval_days = sm2_result.interval_days
            schedule.ease_factor = sm2_result.ease_factor
            schedule.next_review_at = sm2_result.next_review_at
            schedule.repetitions = sm2_result.repetitions
            schedule.last_quality = quality

        await db.flush()
        logger.info(
            "sm2.updated",
            user=user_id,
            concept=concept,
            quality=quality,
            next_review=sm2_result.next_review_at.isoformat(),
        )
        return sm2_result

    async def get_due_today(self, db: AsyncSession, user_id: str) -> list[SM2Schedule]:
        result = await db.execute(
            select(SM2Schedule).where(
                and_(
                    SM2Schedule.user_id == user_id,
                    SM2Schedule.next_review_at <= date.today(),
                )
            )
        )
        return result.scalars().all()


sm2_service = SM2Service()
