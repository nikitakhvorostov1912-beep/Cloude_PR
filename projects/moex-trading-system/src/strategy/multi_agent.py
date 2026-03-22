"""Multi-agent trading pipeline via Xiaomi MiMo LLM.

4 roles debate each ticker:
  1. Bull Analyst — argues FOR buying
  2. Bear Analyst — argues AGAINST
  3. Risk Manager — evaluates risk/reward
  4. Arbiter — makes final decision with confidence 0-100

Uses llm_client.py (OpenAI-compatible) instead of Anthropic SDK.
Total cost: ~$0.003 per ticker analysis via MiMo.
"""
from __future__ import annotations

import asyncio
import json

import structlog

from src.core.llm_client import get_llm_client

logger = structlog.get_logger(__name__)

BULL_PROMPT = """Ты — бычий аналитик MOEX. Твоя задача: найти ВСЕ аргументы ЗА покупку.
Анализируй: тренд EMA, RSI oversold, MACD разворот, объём, макро-поддержку, сектор.
Будь агрессивно оптимистичен, но обоснован. Не выдумывай данных.

Калибровка score:
- 80-100: сильный подтверждённый тренд (EMA20 > EMA50, ADX > 25, объём растёт)
- 60-79: умеренный сигнал (цена выше EMA50, RSI 40-60, нет красных флагов)
- 40-59: слабый/неопределённый
- 0-39: против покупки

Ответь JSON: {"score": 0-100, "arguments": ["arg1", "arg2"], "entry": цена, "target": цена}"""

BEAR_PROMPT = """Ты — медвежий аналитик MOEX. Твоя задача: найти ВСЕ аргументы ПРОТИВ покупки.
Анализируй: overbought RSI, слабый объём, макро-риски, секторальные проблемы, drawdown.
Будь агрессивно пессимистичен, но обоснован. Не выдумывай данных.

Калибровка score:
- 70-100: ТОЛЬКО при конкретных количественных рисках (RSI > 75, ATR spike > 2x, макро STRESS, пробой поддержки)
- 40-69: умеренные риски (неопределённость, боковик)
- 0-39: рисков мало, бычий рынок

НЕ завышай score из-за общей неопределённости. Неопределённость = 40-50, не 70.

Ответь JSON: {"score": 0-100, "arguments": ["risk1", "risk2"], "stop_loss": цена}"""

RISK_PROMPT = """Ты — риск-менеджер MOEX. Оцени соотношение risk/reward.
Учти: ATR для стопа, текущий drawdown, концентрацию сектора, макро-режим.

Правила verdict:
- "reject" ТОЛЬКО при: drawdown > 10% ИЛИ ATR spike > 3x среднего ИЛИ макро STRESS
- "reduce" при: повышенная волатильность, концентрация сектора > 40%, drawdown 5-10%
- "approve" во всех остальных случаях

Ответь JSON: {"risk_score": 0-100, "max_position_pct": 0-15, "stop_loss": цена,
"verdict": "approve"/"reduce"/"reject", "reason": "..."}"""

ARBITER_PROMPT = """Ты — главный арбитр торговой системы MOEX.

## Правила принятия решений:
1. Bull > 60 И Bear < 50 И Risk != "reject" → BUY, confidence = (bull - bear) * 0.7
2. Bull > 75 И Risk = "approve" → BUY высокий confidence (даже если Bear > 50)
3. Bear > 75 И Bull < 35 → SELL
4. Risk = "reject" → confidence -30 (НЕ автоматический HOLD — если Bull очень высокий, можно BUY с пониженным confidence)
5. При противоречиях (Bull и Bear оба > 55) → confidence -10
6. Макро STRESS → confidence -25 (НЕ автоматический HOLD)

## Калибровка confidence:
- 70-100: сильный сигнал, несколько подтверждений
- 50-69: умеренный сигнал, стоит торговать
- 35-49: слабый сигнал, малый размер позиции
- 0-34: нет сигнала → HOLD

Ответь СТРОГО JSON:
{"action": "buy"/"hold"/"sell", "direction": "long"/"short",
 "confidence": 0-100, "entry_price": число, "stop_loss": число,
 "take_profit": число, "reasoning": "краткое обоснование",
 "key_factors": ["фактор1"]}"""


def _call_agent_sync(system_prompt: str, ticker: str, context: str) -> dict:
    """Synchronous agent call via llm_client (MiMo)."""
    client = get_llm_client()
    if not client.is_available:
        logger.warning("llm_not_available_returning_neutral")
        return {"error": "llm_unavailable"}

    prompt = f"Тикер: {ticker}\n\n{context}"
    result = client.chat_json(prompt, system=system_prompt)
    return result if result else {"error": "empty_response"}


async def _call_agent(system_prompt: str, ticker: str, context: str) -> dict:
    """Async wrapper over synchronous llm_client."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _call_agent_sync, system_prompt, ticker, context,
    )


async def multi_agent_analyze(
    ticker: str,
    market_context: str,
    *,
    mtf_score: float = 0.0,
    regime: str = "",
    adx: float = 0.0,
    **kwargs,
) -> dict:
    """Run 4-agent analysis pipeline on a single ticker.

    Bull + Bear + Risk in parallel → Arbiter synthesizes.
    All via llm_client.py (Xiaomi MiMo), no Anthropic SDK.
    """
    # Early exit if LLM is not available — don't waste time on gather
    client = get_llm_client()
    if not client.is_available:
        logger.info("multi_agent_skip_llm_unavailable", ticker=ticker)
        return {
            "ticker": ticker,
            "bull": {"error": "llm_unavailable"},
            "bear": {"error": "llm_unavailable"},
            "risk": {"error": "llm_unavailable"},
            "arbiter": {"error": "llm_unavailable", "action": "hold", "confidence": 0},
        }

    # Phase 1: Bull + Bear + Risk in parallel
    bull_result, bear_result, risk_result = await asyncio.gather(
        _call_agent(BULL_PROMPT, ticker, market_context),
        _call_agent(BEAR_PROMPT, ticker, market_context),
        _call_agent(RISK_PROMPT, ticker, market_context),
    )

    # Phase 2: Arbiter synthesizes
    mtf_line = ""
    if mtf_score != 0.0 or regime or adx > 0:
        mtf_line = (
            f"\n\nДОП. КОНТЕКСТ: MTF score={mtf_score:+.2f}, "
            f"regime={regime or 'unknown'}, ADX={adx:.1f}"
        )

    arbiter_context = (
        f"Тикер: {ticker}\n\n"
        f"Контекст:\n{market_context}{mtf_line}\n\n"
        f"БЫЧИЙ: {json.dumps(bull_result, ensure_ascii=False)}\n\n"
        f"МЕДВЕЖИЙ: {json.dumps(bear_result, ensure_ascii=False)}\n\n"
        f"РИСК: {json.dumps(risk_result, ensure_ascii=False)}"
    )

    arbiter_result = await _call_agent(ARBITER_PROMPT, ticker, arbiter_context)

    logger.info(
        "multi_agent_result",
        ticker=ticker,
        bull=bull_result.get("score", 0),
        bear=bear_result.get("score", 0),
        risk_verdict=risk_result.get("verdict", "?"),
        action=arbiter_result.get("action", "hold"),
        confidence=arbiter_result.get("confidence", 0),
    )

    return {
        "ticker": ticker,
        "bull": bull_result,
        "bear": bear_result,
        "risk": risk_result,
        "arbiter": arbiter_result,
    }


__all__ = ["multi_agent_analyze"]
