"""Unified LLM client via Xiaomi MiMo API (OpenAI-compatible).

Uses OpenAI SDK with custom base_url (https://api.xiaomimimo.com/v1).
Supports model fallback, retry, structured JSON output, graceful degradation.

Usage:
    from src.core.llm_client import get_llm_client

    client = get_llm_client()
    if client.is_available:
        response = client.chat("Analyze: CBR raised rate to 21%")
        data = client.chat_json("Return JSON analysis", system="You are a MOEX analyst")
"""
from __future__ import annotations

import json
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LLMClient:
    """Xiaomi MiMo LLM client with fallback and graceful degradation."""

    def __init__(
        self,
        base_url: str = "https://api.xiaomimimo.com/v1",
        api_key: str = "",
        default_model: str = "mimo-v2-pro",
        fallback_models: list[str] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: int = 30,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = default_model
        self._fallback_models = fallback_models or []
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._client: Any = None

        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    timeout=self._timeout,
                )
                logger.info("LLM client initialized", provider="xiaomi", model=self._model)
            except ImportError:
                logger.warning("openai package not installed, LLM features disabled")
        else:
            logger.info("No API key provided, LLM features disabled")

    @property
    def is_available(self) -> bool:
        """True if client is configured and ready."""
        return self._client is not None and bool(self._api_key)

    def chat(self, prompt: str, system: str = "", model: str | None = None) -> str:
        """Send chat message, return response text.

        Tries default model, then fallbacks. Returns empty string on failure.
        """
        if not self.is_available:
            return ""

        models_to_try = [model or self._model] + self._fallback_models

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for m in models_to_try:
            try:
                response = self._client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )
                text = response.choices[0].message.content or ""
                tokens = response.usage.total_tokens if response.usage else 0
                logger.info("LLM response", model=m, tokens=tokens, length=len(text))
                return text
            except Exception as e:
                logger.warning("LLM call failed", model=m, error=str(e))
                continue

        logger.error("All LLM models failed")
        return ""

    def chat_json(self, prompt: str, system: str = "", model: str | None = None) -> dict:
        """Send chat expecting JSON response. Returns empty dict on failure."""
        json_instruction = "Respond ONLY with valid JSON. No markdown, no backticks, no preamble."
        full_system = f"{system}\n\n{json_instruction}" if system else json_instruction

        text = self.chat(prompt, system=full_system, model=model)
        if not text:
            return {}

        # Extract JSON from possible markdown wrapping
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM", response=cleaned[:200])
            return {}

    def analyze_news(self, headline: str, body: str = "") -> dict:
        """Analyze a news article for MOEX trading impact.

        Returns:
            {"sentiment": float, "affected_tickers": list, "confidence": float,
             "impact": str, "summary": str}
        """
        if not self.is_available:
            return {
                "sentiment": 0.0, "affected_tickers": [],
                "confidence": 0.0, "impact": "unknown",
                "summary": "LLM not available",
            }

        prompt = f"""Analyze this news for Russian stock market (MOEX) impact.

Headline: {headline}
{f'Body: {body[:500]}' if body else ''}

Return JSON:
{{
    "sentiment": <float -1.0 to +1.0, negative=bearish>,
    "affected_tickers": [<MOEX tickers like "SBER", "GAZP">],
    "confidence": <float 0.0 to 1.0>,
    "impact": <"critical"|"high"|"medium"|"low">,
    "summary": <one sentence analysis in Russian>
}}"""

        system = (
            "You are a senior Russian stock market analyst. "
            "You analyze news for MOEX trading impact. "
            "Tickers: SBER, GAZP, LKOH, ROSN, GMKN, YNDX, VTBR, NVTK, MGNT, TATN. "
            "Be precise and concise."
        )

        result = self.chat_json(prompt, system=system)
        # Validate and set defaults
        return {
            "sentiment": float(result.get("sentiment", 0.0)),
            "affected_tickers": list(result.get("affected_tickers", [])),
            "confidence": float(result.get("confidence", 0.0)),
            "impact": str(result.get("impact", "unknown")),
            "summary": str(result.get("summary", "")),
        }


# ── Singleton ──────────────────────────────────────────────────────

_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client. Configured from settings.yaml + .env."""
    global _instance
    if _instance is not None:
        return _instance

    try:
        from src.core.config import load_settings
        cfg = load_settings()
        api_key = os.environ.get(cfg.llm.api_key_env, "")
        _instance = LLMClient(
            base_url=cfg.llm.base_url,
            api_key=api_key,
            default_model=cfg.llm.default_model,
            fallback_models=cfg.llm.fallback_models,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            timeout=cfg.llm.timeout,
        )
    except Exception as e:
        logger.warning("Failed to load LLM config, using defaults", error=str(e))
        api_key = os.environ.get("XIAOMI_API_KEY", "")
        _instance = LLMClient(api_key=api_key)

    return _instance


def reset_llm_client() -> None:
    """Reset singleton (for testing)."""
    global _instance
    _instance = None
