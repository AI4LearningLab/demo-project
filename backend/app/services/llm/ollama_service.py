"""
app/services/llm/ollama_service.py

LLM abstraction layer.
Everything talks to this service — never import langchain directly in routes.
Swap the underlying model by changing config only.
"""
from langchain_ollama import OllamaLLM
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.chat_models import ChatOllama
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMService:
    """
    Wraps Ollama chat completions.
    Keeps a single ChatOllama instance (thread-safe, reused across requests).
    """

    def __init__(self) -> None:
        self._model = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.4,   # low temp → more consistent Socratic responses
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],   # [{"role": "user"|"assistant", "content": "..."}]
    ) -> str:
        """
        Send a conversation to the LLM and return the assistant reply.

        Args:
            system_prompt: The fully-assembled transformed prompt (persona +
                           Socratic instructions + injected context).
            messages:      Conversation history in role/content dicts.

        Returns:
            Plain-text assistant reply.
        """
        lc_messages: list = [SystemMessage(content=system_prompt)]

        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))

        logger.debug("llm.chat", model=settings.ollama_model, turns=len(messages))

        response = await self._model.ainvoke(lc_messages)
        return response.content

    async def health_check(self) -> bool:
        """Ping Ollama — used in /health endpoint."""
        try:
            await self._model.ainvoke([HumanMessage(content="ping")])
            return True
        except Exception as exc:
            logger.warning("llm.health_check_failed", error=str(exc))
            return False


# Module-level singleton — imported by services that need LLM access
llm_service = LLMService()
