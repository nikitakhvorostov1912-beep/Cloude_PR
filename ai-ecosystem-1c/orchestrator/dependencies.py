"""FastAPI dependency injection — service factories."""

from __future__ import annotations

from typing import Any, Optional

from orchestrator.config import get_settings

# Singletons initialized at app startup (set in main.py lifespan)
_call_handler: Any = None
_session_store: Any = None
_voice_agent: Any = None
_routing_engine: Any = None
_llm_client: Any = None


def set_services(
    *,
    call_handler: Any,
    session_store: Any,
    voice_agent: Any = None,
    routing_engine: Any = None,
    llm_client: Any = None,
) -> None:
    """Called from lifespan to register singletons."""
    global _call_handler, _session_store, _voice_agent, _routing_engine, _llm_client
    _call_handler = call_handler
    _session_store = session_store
    _voice_agent = voice_agent
    _routing_engine = routing_engine
    _llm_client = llm_client


def get_call_handler() -> Any:
    return _call_handler


def get_session_store() -> Any:
    return _session_store


def get_voice_agent() -> Any:
    return _voice_agent


def get_routing_engine() -> Any:
    return _routing_engine


def get_llm_client() -> Any:
    return _llm_client
