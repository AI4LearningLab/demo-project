"""app/api/routes/chat.py"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import ChatMessage, ChatResponse
from app.services.chat_service import chat_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    payload: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and receive a Socratic response from the LLM."""
    return await chat_service.handle_message(db, current_user.id, payload)


@router.post("/session/{session_id}/end")
async def end_session(
    session_id: str,
    resolved: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a session as ended.
    Generates summary embedding for future RAG retrieval.
    Triggers progress update.
    """
    await chat_service.end_session(db, session_id, resolved)
    return {"status": "ok", "session_id": session_id, "resolved": resolved}
