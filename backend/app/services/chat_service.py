"""
app/services/chat_service.py

Orchestrates one full message cycle:
  1. Load / create session
  2. Build user context (RAG)
  3. Transform prompt
  4. Call LLM
  5. Parse response for signals
  6. Persist messages
  7. Return reply + metadata
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import DebugSession, SessionMessage
from app.services.context.context_builder import context_builder
from app.services.prompt.prompt_transformer import prompt_transformer
from app.services.llm.ollama_service import llm_service
from app.services.llm.embedding_service import embedding_service
from app.schemas.schemas import ChatMessage, ChatResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple keyword-based bug type detection
# Extend this dict as needed — or replace with a small LLM classifier later
BUG_TYPE_KEYWORDS: dict[str, list[str]] = {
    "null_pointer":   ["null", "none", "nullpointer", "nonetype", "nil"],
    "off_by_one":     ["index", "out of range", "off by one", "boundary", "fence"],
    "stack_overflow": ["recursion", "maximum recursion", "stackoverflow", "infinite loop"],
    "type_error":     ["typeerror", "cannot convert", "expected int", "expected str"],
    "scope_error":    ["undefined", "not defined", "out of scope", "nameerror"],
    "memory_leak":    ["memory", "leak", "heap", "garbage"],
}


def _detect_bug_type(text: str) -> str | None:
    lower = text.lower()
    for bug_type, keywords in BUG_TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return bug_type
    return None


class ChatService:

    async def handle_message(
        self,
        db: AsyncSession,
        user_id: str,
        message: ChatMessage,
    ) -> ChatResponse:
        # 1. Load or create session
        session = await self._get_or_create_session(db, user_id, message.session_id)

        # 2. Detect bug type from current message
        bug_type = _detect_bug_type(message.content)

        # 3. Build user context via RAG
        context = await context_builder.build(
            db, user_id, message.content, bug_type
        )

        # 4. Load conversation history for this session
        history = await self._load_history(db, session.id)

        # 5. Count hints given so far
        hint_level = session.hints_given if hasattr(session, "hints_given") else 0

        # 6. Transform prompt
        system_prompt = prompt_transformer.build(context, hint_level)

        # 7. Call LLM
        reply = await llm_service.chat(system_prompt, history + [
            {"role": "user", "content": message.content}
        ])

        # 8. Persist user message + assistant reply
        db.add(SessionMessage(session_id=session.id, role="user", content=message.content))
        db.add(SessionMessage(session_id=session.id, role="assistant", content=reply))

        # 9. Update session bug type if detected for first time
        if bug_type and not session.bug_type:
            session.bug_type = bug_type

        await db.flush()

        logger.info("chat.handled", session=session.id, bug_type=bug_type)

        return ChatResponse(
            session_id=session.id,
            reply=reply,
            reminders=context.prerequisite_reminders,
            hint_level=hint_level,
        )

    async def end_session(
        self,
        db: AsyncSession,
        session_id: str,
        resolved: bool,
    ) -> None:
        """
        Called when the student marks a session as done.
        Generates a summary embedding for future RAG retrieval.
        """
        result = await db.execute(
            select(DebugSession).where(DebugSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return

        # Build plain-text summary for embedding
        history = await self._load_history(db, session_id)
        summary = f"Bug: {session.bug_type or 'unknown'}. " + " ".join(
            m["content"][:100] for m in history[:4]  # first 4 turns
        )
        session.summary = summary[:500]
        session.resolved = resolved
        session.ended_at = datetime.utcnow()

        # Store embedding for future semantic search
        # session.embedding = embedding_service.encode(summary)
        await db.flush()

    # ── private ───────────────────────────────────────────────────────────────

    async def _get_or_create_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str | None,
    ) -> DebugSession:
        if session_id:
            result = await db.execute(
                select(DebugSession).where(DebugSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                return session

        # New session
        session = DebugSession(user_id=user_id)
        db.add(session)
        await db.flush()
        return session

    async def _load_history(
        self, db: AsyncSession, session_id: str
    ) -> list[dict]:
        result = await db.execute(
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.created_at.asc())
        )
        return [
            {"role": msg.role, "content": msg.content}
            for msg in result.scalars().all()
        ]


chat_service = ChatService()
