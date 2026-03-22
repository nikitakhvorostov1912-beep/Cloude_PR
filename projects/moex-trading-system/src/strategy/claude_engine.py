"""Claude engine — main signal orchestrator for the live trading pipeline.

Called by main.py for each top candidate ticker.
Flow: market_context → multi_agent_analyze → TradingSignal

Note: Entry/macro filters are applied in main.py AFTER this function returns.
This function only handles LLM-based signal generation.
"""
from __future__ import annotations

import asyncio

import structlog

from src.core.llm_client import get_llm_client
from src.models.signal import Action, Direction, TradingSignal
from src.strategy.multi_agent import multi_agent_analyze

logger = structlog.get_logger(__name__)


def _arbiter_to_signal(ticker: str, arbiter: dict) -> TradingSignal | None:
    """Convert Arbiter JSON response → TradingSignal.

    Arbiter returns: {"action": "buy"/"hold"/"sell", "confidence": 0-100, ...}
    We convert to TradingSignal with confidence normalized to 0.0-1.0.
    """
    action_str = arbiter.get("action", "hold").lower()
    confidence_raw = arbiter.get("confidence", 0)

    # Normalize confidence: 0-100 → 0.0-1.0
    confidence = float(confidence_raw) / 100.0 if confidence_raw > 1 else float(confidence_raw)

    if action_str == "hold" or confidence < 0.40:
        logger.debug("arbiter_hold", ticker=ticker, action=action_str, confidence=confidence)
        return TradingSignal(
            ticker=ticker,
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=confidence,
            reasoning=arbiter.get("reasoning", "hold"),
        )

    try:
        action = Action(action_str)
    except ValueError:
        return TradingSignal(
            ticker=ticker,
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=0.0,
            reasoning=f"unknown action: {action_str}",
        )

    direction_str = arbiter.get("direction", "long").lower()
    direction = Direction.SHORT if direction_str == "short" else Direction.LONG

    return TradingSignal(
        ticker=ticker,
        action=action,
        direction=direction,
        confidence=confidence,
        entry_price=arbiter.get("entry_price"),
        stop_loss=arbiter.get("stop_loss"),
        take_profit=arbiter.get("take_profit"),
        reasoning=arbiter.get("reasoning", ""),
    )


async def get_trading_signal(
    ticker: str,
    market_context: str,
) -> TradingSignal:
    """Generate a trading signal for a ticker via 4-agent LLM pipeline.

    Called by main.py as:
        signal = await get_trading_signal(ticker=ticker, market_context=market_context)

    Flow:
      1. multi_agent_analyze → Bull/Bear/Risk/Arbiter via MiMo LLM
      2. _arbiter_to_signal  → convert to TradingSignal

    Entry/macro filters are applied by main.py after this returns.

    Args:
        ticker: MOEX ticker (e.g. "SBER").
        market_context: JSON string from build_market_context().

    Returns:
        TradingSignal (may be HOLD if LLM unavailable or arbiter says hold).
    """
    # Check LLM availability
    llm = get_llm_client()
    if not llm.is_available:
        logger.warning("llm_unavailable_returning_hold", ticker=ticker)
        return TradingSignal(
            ticker=ticker,
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=0.0,
            reasoning="LLM unavailable",
        )

    try:
        # Run 4-agent analysis
        agent_result = await multi_agent_analyze(
            ticker=ticker,
            market_context=market_context,
        )

        arbiter = agent_result.get("arbiter", {})
        if not arbiter or "error" in arbiter:
            logger.warning("arbiter_failed", ticker=ticker, result=arbiter)
            return TradingSignal(
                ticker=ticker,
                action=Action.HOLD,
                direction=Direction.LONG,
                confidence=0.0,
                reasoning=f"arbiter error: {arbiter.get('error', 'unknown')}",
            )

        # Convert to TradingSignal
        signal = _arbiter_to_signal(ticker, arbiter)
        if signal is None:
            return TradingSignal(
                ticker=ticker,
                action=Action.HOLD,
                direction=Direction.LONG,
                confidence=0.0,
                reasoning="arbiter returned None",
            )

        logger.info(
            "signal_generated",
            ticker=ticker,
            action=signal.action.value,
            confidence=round(signal.confidence, 3),
            entry=signal.entry_price,
            stop=signal.stop_loss,
        )
        return signal

    except Exception as e:
        logger.error("claude_engine_error", ticker=ticker, error=str(e))
        return TradingSignal(
            ticker=ticker,
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=0.0,
            reasoning=f"engine error: {e}",
        )


__all__ = ["get_trading_signal"]
