"""
tests/unit/test_sm2.py
Tests for the SM-2 algorithm — pure function, no DB or LLM needed.
Run with: pytest tests/unit/test_sm2.py -v
"""
import pytest
from datetime import date, timedelta
from app.services.reminder.sm2 import calculate_sm2, MIN_EASE_FACTOR


class TestCalculateSM2:

    def test_failure_resets_interval(self):
        result = calculate_sm2(quality=0, interval_days=7, ease_factor=2.5, repetitions=3)
        assert result.interval_days == 1
        assert result.repetitions == 0

    def test_quality_below_3_resets(self):
        for q in [0, 1, 2]:
            result = calculate_sm2(quality=q, interval_days=10, ease_factor=2.5, repetitions=5)
            assert result.interval_days == 1
            assert result.repetitions == 0

    def test_first_success_gives_interval_1(self):
        result = calculate_sm2(quality=4, interval_days=1, ease_factor=2.5, repetitions=0)
        assert result.interval_days == 1
        assert result.repetitions == 1

    def test_second_success_gives_interval_3(self):
        result = calculate_sm2(quality=4, interval_days=1, ease_factor=2.5, repetitions=1)
        assert result.interval_days == 3
        assert result.repetitions == 2

    def test_third_success_multiplies_by_ef(self):
        result = calculate_sm2(quality=5, interval_days=3, ease_factor=2.5, repetitions=2)
        assert result.interval_days == round(3 * 2.5)

    def test_ease_factor_never_below_minimum(self):
        result = calculate_sm2(quality=0, interval_days=1, ease_factor=MIN_EASE_FACTOR, repetitions=1)
        assert result.ease_factor >= MIN_EASE_FACTOR

    def test_perfect_quality_increases_ef(self):
        result = calculate_sm2(quality=5, interval_days=3, ease_factor=2.5, repetitions=2)
        assert result.ease_factor > 2.5

    def test_next_review_date_is_in_future(self):
        result = calculate_sm2(quality=4, interval_days=3, ease_factor=2.5, repetitions=2)
        assert result.next_review_at > date.today()

    def test_next_review_matches_interval(self):
        result = calculate_sm2(quality=4, interval_days=3, ease_factor=2.5, repetitions=2)
        expected = date.today() + timedelta(days=result.interval_days)
        assert result.next_review_at == expected
