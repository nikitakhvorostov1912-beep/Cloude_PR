"""Multi-agent Claude trading pipeline.

4 roles debate each ticker:
  1. Bull Analyst — argues FOR buying
  2. Bear Analyst — argues AGAINST
  3. Risk Manager — evaluates risk/reward
  4. Arbiter — makes final decision with confidence 0-100

Returns structured JSON signal that feeds into Risk Gateway.
"""
from __future__ import annotations

import asyncio
import json
import anthropic
import structlog

logger = structlog.get_logger(__name__)

BULL_PROMPT = """Ты — бычий аналитик MOEX. Твоя задача: найти ВСЕ аргументы ЗА покупку.
Анализируй: тренд EMA, RSI oversold, MACD разворот, объём, макро-поддержку, сектор.
Будь агрессивно оптимистичен, но обоснован. Не выдумывай данных.
Ответь JSON: {"score": 0-100, "arguments": ["arg1", "arg2", ...], "entry": цена, "target": цена}"""

BEAR_PROMPT = """Ты — медвежий аналитик MOEX. Твоя задача: найти ВСЕ аргументы ПРОТИВ покупки.
Анализируй: overbought RSI, слабый объём, макро-риски, секторальные проблемы, drawdown.
Будь агрессивно пессимистичен, но обоснован. Не выдумывай данных.
Ответь JSON: {"score": 0-100, "arguments": ["risk1", "risk2", ...], "stop_loss": цена}"""

RISK_PROMPT = """Ты — риск-менеджер MOEX. Оцени соотношение risk/reward.
Учти: ATR для стопа, текущий drawdown портфеля, концентрацию сектора, макро-режим.
Ответь JSON: {"risk_score": 0-100, "max_position_pct": 0-15, "stop_loss": цена, "verdict": "approve"/"reduce"/"reject", "reason": "..."}"""

ARBITER_PROMPT = """Ты — главный арбитр торговой системы MOEX. Перед тобой мнения трёх аналитиков.

## Правила арбитра:
1. Если Bull score > 70 И Bear score < 40 И Risk verdict = "approve" → BUY с высоким confidence
2. Если Bear score > 70 И Bull score < 40 → HOLD (не покупать)
3. Если Risk verdict = "reject" → HOLD независимо от аналитиков
4. При противоречиях — снизить confidence на 20%
5. Макро-режим STRESS → только HOLD

Ответь СТРОГО JSON:
{"action": "buy"/"hold"/"sell", "direction": "long"/"short", "confidence": 0-100,
 "entry_price": число, "stop_loss": число, "take_profit": число,
 "reasoning": "краткое обоснование", "key_factors": ["фактор1", ...]}"""


async def multi_agent_analyze(
    ticker: str,
    market_context: str,
    model: str = "claude-sonnet-4-20250514",
    api_key: str | None = None,
) -> dict:
    """Run 4-agent analysis pipeline on a single ticker.

    Uses Haiku for Bull/Bear/Risk (cheap, fast), Sonnet for Arbiter (quality).
    Total cost: ~$0.003 per ticker analysis.
    """
    kwargs = {"api_key": api_key} if api_key else {}
    client = anthropic.AsyncAnthropic(**kwargs)

    # Phase 1: Bull + Bear + Risk in parallel
    bull_result, bear_result, risk_result = await asyncio.gather(
        _call_agent(client, BULL_PROMPT, ticker, market_context, model),
        _call_agent(client, BEAR_PROMPT, ticker, market_context, model),
        _call_agent(client, RISK_PROMPT, ticker, market_context, model),
    )

    # Phase 2: Arbiter synthesizes (use smarter model)
    arbiter_context = (
        f"Тикер: {ticker}\n\n"
        f"Контекст рынка:\n{market_context}\n\n"
        f"БЫЧИЙ АНАЛИТИК:\n{json.dumps(bull_result, ensure_ascii=False)}\n\n"
        f"МЕДВЕЖИЙ АНАЛИТИК:\n{json.dumps(bear_result, ensure_ascii=False)}\n\n"
        f"РИСК-МЕНЕДЖЕР:\n{json.dumps(risk_result, ensure_ascii=False)}"
    )

    arbiter_result = await _call_agent(
        client, ARBITER_PROMPT, ticker, arbiter_context,
        model="claude-sonnet-4-20250514",
    )

    logger.info(
        "multi_agent_result",
        ticker=ticker,
        bull=bull_result.get("score", 0),
        bear=bear_result.get("score", 0),
        risk=risk_result.get("verdict", "?"),
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


async def _call_agent(
    client: anthropic.AsyncAnthropic,
    system_prompt: str,
    ticker: str,
    context: str,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Call a single agent, parse JSON response."""
    try:
        resp = await client.messages.create(
            model=model,
            max_tokens=512,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Тикер: {ticker}\n\n{context}"}],
        )
        text = resp.content[0].text if resp.content else "{}"
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"raw": text, "error": "no JSON found"}
    except Exception as e:
        logger.error("agent_error", ticker=ticker, error=str(e))
        return {"error": str(e)}
