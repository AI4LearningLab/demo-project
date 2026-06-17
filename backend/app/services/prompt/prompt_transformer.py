"""
app/services/prompt/prompt_transformer.py

THE CORE RESEARCH CONTRIBUTION.

Takes raw student input + UserContext and produces a fully-transformed
system prompt that instructs the LLM to behave as a Socratic debugging tutor
personalised to this specific student's history and weak areas.

Three-layer transformation:
  Layer 1 — Persona injection   (who the student is)
  Layer 2 — Behavioural rules   (how the LLM must respond)
  Layer 3 — History targeting   (student-specific context)
"""
from app.services.context.context_builder import UserContext
from app.core.logging import get_logger

logger = get_logger(__name__)


class PromptTransformer:
    """
    Transforms a plain student question into a context-enriched Socratic prompt.

    Usage:
        transformer = PromptTransformer()
        system_prompt = transformer.build(context, hint_level=0)
    """

    def build(self, context: UserContext, hint_level: int = 0) -> str:
        """
        Assemble the final system prompt from all three layers.

        Args:
            context:    UserContext produced by ContextBuilder.
            hint_level: How many hints already given this session (0 = fresh start).

        Returns:
            A multi-section system prompt string ready to send to the LLM.
        """
        parts = [
            self._layer_1_persona(context),
            self._layer_2_behaviour(hint_level),
            self._layer_3_history(context),
        ]

        if context.prerequisite_reminders:
            parts.append(self._prerequisite_block(context.prerequisite_reminders))

        if context.due_reviews:
            parts.append(self._review_nudge(context.due_reviews))

        prompt = "\n\n".join(filter(None, parts))
        logger.debug("prompt.built", user_id=context.user_id, layers=len(parts))
        return prompt

    # ── Layer 1: Persona ──────────────────────────────────────────────────────

    def _layer_1_persona(self, context: UserContext) -> str:
        lines = ["## Student profile"]

        if context.behavior:
            b = context.behavior
            avg = b["avg_hints_needed"]
            hyp = b["forms_hypothesis_rate"]
            err = b["reads_error_first_rate"]
            lines.append(
                f"- Needs on average {avg:.1f} hints to resolve a bug."
            )
            if hyp < 0.4:
                lines.append("- Rarely forms a hypothesis before testing — guide them to do so.")
            if err < 0.4:
                lines.append("- Often skips reading the error message — ask them to read it first.")
        else:
            lines.append("- New student — no behavioural data yet. Start with open questions.")

        if context.struggles:
            top = context.struggles[0]
            lines.append(
                f"- Recurring struggle: '{top['bug_type']}' ({top['count']} times). "
                "Be alert to this pattern."
            )

        if context.mastery:
            weak_concepts = ", ".join(m["concept"] for m in context.mastery[:3])
            lines.append(f"- Weak areas: {weak_concepts}.")

        return "\n".join(lines)

    # ── Layer 2: Behavioural rules ─────────────────────────────────────────────

    def _layer_2_behaviour(self, hint_level: int) -> str:
        base = (
            "## Your role\n"
            "You are a Socratic debugging tutor. Your goal is to develop the student's "
            "debugging skill — NOT to fix their bug for them.\n\n"
            "Rules you must always follow:\n"
            "1. Never give the answer directly.\n"
            "2. Ask exactly ONE guiding question at a time.\n"
            "3. If the student answers correctly, affirm briefly and ask the next question.\n"
            "4. Guide through: (a) reading the error, (b) forming a hypothesis, "
            "(c) narrowing the location, (d) testing the fix.\n"
            "5. Keep responses short — 2-4 sentences maximum unless giving a code example.\n"
            "6. Never use condescending language."
        )

        if hint_level == 0:
            hint_guidance = (
                "\nThe student is just starting. Begin by asking them to explain "
                "what they think the code is supposed to do."
            )
        elif hint_level == 1:
            hint_guidance = (
                "\nOne hint already given. Ask them to read the error message carefully "
                "and identify the line number."
            )
        elif hint_level == 2:
            hint_guidance = (
                "\nTwo hints given. Ask them to form a testable hypothesis: "
                "'What do you think is causing this?'"
            )
        else:
            hint_guidance = (
                f"\n{hint_level} hints given. The student is stuck. "
                "Give one small concrete hint (not the answer) about where to look next."
            )

        return base + hint_guidance

    # ── Layer 3: History targeting ─────────────────────────────────────────────

    def _layer_3_history(self, context: UserContext) -> str:
        if not context.similar_sessions:
            return ""

        lines = ["## Relevant past sessions (from this student's history)"]
        for s in context.similar_sessions[:2]:   # top 2 most similar
            similarity_pct = int(s.get("similarity", 0) * 100)
            lines.append(
                f"- [{similarity_pct}% match] Bug: {s.get('bug_type', 'unknown')} | "
                f"Hints needed: {s.get('hints_given', '?')} | "
                f"Summary: {s.get('summary', 'no summary')}"
            )

        lines.append(
            "Use this history to adapt your questions. "
            "If this looks like a recurring bug type, gently note the pattern."
        )
        return "\n".join(lines)

    # ── Prerequisite block ────────────────────────────────────────────────────

    def _prerequisite_block(self, reminders: list[str]) -> str:
        lines = [
            "## Prerequisite reminder to surface",
            "Before diving into the bug, briefly acknowledge:",
        ]
        lines.extend(f"- {r}" for r in reminders)
        return "\n".join(lines)

    # ── Spaced-repetition nudge ───────────────────────────────────────────────

    def _review_nudge(self, concepts: list[str]) -> str:
        concept_list = ", ".join(concepts)
        return (
            "## Spaced repetition note\n"
            f"The student has the following concepts due for review today: {concept_list}. "
            "If any are relevant to the current question, weave in a brief revisit."
        )


prompt_transformer = PromptTransformer()
