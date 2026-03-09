"""FastAPI application factory with lifespan and middleware."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agents.classifier.agent import ClassifierAgent
from agents.voice_agent.agent import VoiceAgent
from database.connection import close_db, init_db
from orchestrator.api import calls, health, webhooks
from orchestrator.config import get_settings
from orchestrator.core.call_handler import CallHandler
from orchestrator.core.call_session import CallSessionStore
from orchestrator.core.deduplication import DeduplicationService
from orchestrator.core.routing_engine import RoutingEngine
from orchestrator.dependencies import set_services
from services.llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and teardown services."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting AI Ecosystem 1C — env=%s", settings.env)

    # Database
    await init_db()

    # Redis (optional — None in dev mode uses in-memory fallback)
    redis = None
    if not settings.is_dev:
        try:
            import redis.asyncio as aioredis

            redis = aioredis.from_url(settings.redis.url)
            await redis.ping()
            logger.info("Redis connected: %s", settings.redis.url)
        except Exception:
            logger.warning("Redis not available, using in-memory fallback")
            redis = None

    # Services
    llm = ClaudeClient(settings.ai)

    session_store = CallSessionStore(redis, ttl_seconds=settings.redis.call_session_ttl)
    dedup = DeduplicationService(redis, window_minutes=settings.deduplication_window_minutes)

    classifier = ClassifierAgent(llm)
    voice_agent = VoiceAgent(llm, max_questions=settings.ai.max_questions)

    routing = RoutingEngine(
        classifier,
        escalation_threshold=settings.escalation_confidence_threshold,
        low_confidence_threshold=settings.low_confidence_flag_threshold,
    )

    call_handler = CallHandler(
        session_store=session_store,
        dedup=dedup,
        routing=routing,
    )

    # Register singletons for DI
    set_services(
        call_handler=call_handler,
        session_store=session_store,
        voice_agent=voice_agent,
        routing_engine=routing,
        llm_client=llm,
    )

    logger.info("All services initialized")
    yield

    # Shutdown
    await llm.close()
    await close_db()
    if redis is not None:
        await redis.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI Ecosystem 1C",
        description="AI-панель суфлёра для техподдержки франчайзи 1С",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router)
    app.include_router(webhooks.router)
    app.include_router(calls.router)

    return app


app = create_app()
