"""
tests/unit/test_prompt_transformer.py
Tests for prompt transformation logic — no LLM or DB needed.
"""
import pytest
from app.services.context.context_builder import UserContext
from app.services.prompt.prompt_transformer import PromptTransformer


def make_context(
    struggles=None,
    mastery=None,
    behavior=None,
    similar_sessions=None,
    prerequisite_reminders=None,
    due_reviews=None,
) -> UserContext:
    return UserContext(
        user_id="test-user",
        struggles=struggles or [],
        mastery=mastery or [],
        behavior=behavior,
        similar_sessions=similar_sessions or [],
        prerequisite_reminders=prerequisite_reminders or [],
        due_reviews=due_reviews or [],
    )


class TestPromptTransformer:
    transformer = PromptTransformer()

    def test_output_is_non_empty_string(self):
        context = make_context()
        prompt = self.transformer.build(context)
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_socratic_rules_always_present(self):
        context = make_context()
        prompt = self.transformer.build(context)
        assert "Never give the answer directly" in prompt

    def test_hint_level_0_asks_to_explain(self):
        context = make_context()
        prompt = self.transformer.build(context, hint_level=0)
        assert "explain" in prompt.lower()

    def test_hint_level_3_gives_concrete_hint(self):
        context = make_context()
        prompt = self.transformer.build(context, hint_level=3)
        assert "stuck" in prompt.lower() or "hint" in prompt.lower()

    def test_struggle_included_in_persona(self):
        context = make_context(
            struggles=[{"bug_type": "null_pointer", "sub_skill": "fault_localization", "count": 3, "last_occurred": "2024-01-01"}]
        )
        prompt = self.transformer.build(context)
        assert "null_pointer" in prompt

    def test_weak_concepts_included(self):
        context = make_context(
            mastery=[{"concept": "recursion", "sub_skill": "hypothesis", "score": 0.2}]
        )
        prompt = self.transformer.build(context)
        assert "recursion" in prompt

    def test_prerequisite_reminders_included(self):
        context = make_context(prerequisite_reminders=["Quick reminder: you covered 'pointers'"])
        prompt = self.transformer.build(context)
        assert "pointers" in prompt

    def test_due_reviews_included(self):
        context = make_context(due_reviews=["recursion", "scope"])
        prompt = self.transformer.build(context)
        assert "recursion" in prompt
        assert "scope" in prompt

    def test_similar_sessions_section_when_present(self):
        context = make_context(
            similar_sessions=[{
                "bug_type": "off_by_one", "hints_given": 2,
                "summary": "Array loop bug", "similarity": 0.85
            }]
        )
        prompt = self.transformer.build(context)
        assert "off_by_one" in prompt or "past sessions" in prompt.lower()

    def test_no_similar_sessions_section_when_empty(self):
        context = make_context(similar_sessions=[])
        prompt = self.transformer.build(context)
        assert "Relevant past sessions" not in prompt
