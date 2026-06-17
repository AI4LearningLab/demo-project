"""
app/services/llm/embedding_service.py
Embedding service — pgvector disabled until extension is installed.
find_similar_sessions returns empty list gracefully.
"""
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

PGVECTOR_ENABLED = False  # set to True after pgvector is installed


class EmbeddingService:
    def __init__(self) -> None:
        logger.info("embedding.loading_model", model=settings.embedding_model)
        self._model = SentenceTransformer(settings.embedding_model)

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    async def find_similar_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        query_text: str,
        top_k: int = 3,
        min_similarity: float = 0.6,
    ) -> list[dict]:
        """
        Returns similar past sessions.
        Currently disabled — returns empty list until pgvector is installed.
        """
        if not PGVECTOR_ENABLED:
            logger.debug("embedding.pgvector_disabled_skipping_search")
            return []

        # This code runs only when PGVECTOR_ENABLED = True
        from sqlalchemy import text
        vector = self.encode(query_text)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"

        sql = text("""
            SELECT id, summary, bug_type, sub_skill_tested, hints_given,
                   1 - (embedding <=> :vec ::vector) AS similarity
            FROM   debug_sessions
            WHERE  user_id = :uid
              AND  embedding IS NOT NULL
              AND  1 - (embedding <=> :vec ::vector) >= :min_sim
            ORDER  BY similarity DESC
            LIMIT  :top_k
        """)

        result = await db.execute(
            sql,
            {"vec": vector_str, "uid": user_id, "min_sim": min_similarity, "top_k": top_k},
        )
        return [dict(row._mapping) for row in result.fetchall()]


embedding_service = EmbeddingService()