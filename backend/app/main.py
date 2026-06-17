"""
app/main.py
FastAPI application factory.
Import order matters — logging must be configured before routes load.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api.routes import auth, chat, progress

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook."""
    logger.info("app.starting", env=settings.app_env, model=settings.ollama_model)
    yield
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Socratic Debug Tutor API",
        description="History-aware Socratic prompt wrapper for debugging skill development.",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(auth.router,     prefix="/api/v1")
    app.include_router(chat.router,     prefix="/api/v1")
    app.include_router(progress.router, prefix="/api/v1")

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        from app.services.llm.ollama_service import llm_service
        llm_ok = await llm_service.health_check()
        return {
            "status": "ok" if llm_ok else "degraded",
            "llm": "up" if llm_ok else "down",
            "model": settings.ollama_model,
        }

    return app


app = create_app()
