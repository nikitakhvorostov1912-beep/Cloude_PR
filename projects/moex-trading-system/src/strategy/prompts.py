"""Claude prompts and context builders for the strategy layer."""
from __future__ import annotations

import json

from src.models.market import MarketRegime

SYSTEM_PROMPT = """Ты — систематический торговый аналитик для российского фондового рынка (MOEX).

## Метод анализа: Graph-of-Thought

Шаг 1 — МАКРО-КОНТЕКСТ:
  Оцени макро-среду: ставка ЦБ (направление), нефть Brent (тренд), USD/RUB (стресс?).
  Определи макро-режим: EASING / TIGHTENING / NEUTRAL / STRESS.
  Учти секторальную чувствительность этого тикера к макро-факторам.

Шаг 2 — ТЕХНИЧЕСКИЙ АНАЛИЗ:
  Тренд (ADX, DI+/DI-, EMA alignment).
  Моментум (RSI, MACD histogram, Stochastic).
  Волатильность (ATR, Bollinger %B).
  Объём (Volume Ratio, OBV trend).
  Определи точку входа и стоп-лосс на основе ATR.

Шаг 3 — СЕНТИМЕНТ И ФУНДАМЕНТАЛ:
  Оцени sentiment score. Совпадает ли с техникой?
  Расхождение техники и сентимента = снизить confidence на 15%.
  Проверь P/E vs сектор, дивидендную доходность.

Шаг 4 — ТРИ СЦЕНАРИЯ (обязательно):
  БЫЧИЙ: что должно произойти для роста? Вероятность X%.
  БАЗОВЫЙ: наиболее вероятный исход. Вероятность Y%.
  МЕДВЕЖИЙ: что пойдёт не так? Вероятность Z%.
  Проверь: X + Y + Z = 100%.

Шаг 5 — РЕШЕНИЕ:
  Сформируй сигнал с учётом ВСЕХ шагов.
  Confidence = (вероятность благоприятного сценария) × (согласованность факторов).
  При расхождении макро и техники → снизить confidence на 20%.
  При макро-режиме STRESS → только HOLD или SELL.
  При макро-режиме TIGHTENING → снизить confidence на 10%.

## Правила (неизменные):
1. НЕ исполняешь сделки — только формируешь сигнал
2. При неопределённости — HOLD
3. Стоп-лосс обязателен для BUY/SELL (рассчитай через ATR × 2.5)
4. Не выдумывай цены, которых нет в контексте
5. Торги MOEX: 10:00-18:50 МСК, T+1
6. Учитывай текущие позиции портфеля
7. При противоречивых индикаторах — уменьшить confidence

Ответь СТРОГО через tool_use submit_trading_signal."""

SECTOR_MAP: dict[str, str] = {
    "SBER": "banks", "VTBR": "banks", "TCSG": "banks",
    "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", "NVTK": "oil_gas",
    "GMKN": "metals",
    "MGNT": "retail",
    "YDEX": "it",
}

SECTOR_SENSITIVITY_DESC: dict[str, str] = {
    "oil_gas": "Сильно зависит от нефти Brent (+0.85) и USD/RUB (-0.68). Ставка ЦБ влияет умеренно (-0.45).",
    "banks": "Ключевая ставка ЦБ — главный фактор (-0.78). Нефть влияет слабо (+0.30).",
    "retail": "Зависит от ставки ЦБ (-0.60) и потребительского спроса. Нефть почти не влияет.",
    "metals": "Глобальный спрос и USD/RUB (-0.65). Нефть средне (+0.40).",
    "it": "Менее чувствителен к нефти (+0.10). Ставка ЦБ умеренно (-0.55).",
}


def build_market_context(
    ticker: str,
    regime: MarketRegime,
    features: dict,
    sentiment: float,
    portfolio: dict,
    macro: dict,
    fundamentals: dict | None = None,
    news: list[dict] | None = None,
) -> str:
    """Build a structured JSON context string for Claude (~2000 tokens).

    Parameters
    ----------
    ticker:
        Target security ticker (e.g. "SBER").
    regime:
        Current market regime detected from IMOEX.
    features:
        Dict of latest indicator values for the ticker
        (keys: ema_20, ema_50, ema_200, rsi_14, macd, macd_signal,
         macd_histogram, adx, di_plus, di_minus, bb_upper, bb_lower,
         bb_pct_b, atr_14, stoch_k, stoch_d, obv, volume_ratio_20,
         close, etc.).
    sentiment:
        Aggregated daily sentiment score [-1.0, +1.0].
    portfolio:
        Current portfolio state: positions, cash, equity, drawdown.
    macro:
        Macro indicators: key_rate, usd_rub, oil_brent, etc.
    fundamentals:
        Optional fundamental data: pe_ratio, sector_pe, div_yield, etc.

    Returns
    -------
    str
        JSON-formatted context string, ≤ ~2000 tokens.
    """
    close = features.get("close", 0)
    regime_str = regime.value if hasattr(regime, "value") else str(regime)
    context: dict = {
        "ticker": ticker,
        "market_regime": regime_str,
        "price": {
            "close": close,
            "ema_20": features.get("ema_20"),
            "ema_50": features.get("ema_50"),
            "ema_200": features.get("ema_200"),
        },
        "trend": {
            "adx": features.get("adx"),
            "di_plus": features.get("di_plus"),
            "di_minus": features.get("di_minus"),
        },
        "momentum": {
            "rsi_14": features.get("rsi_14"),
            "macd": features.get("macd"),
            "macd_signal": features.get("macd_signal"),
            "macd_histogram": features.get("macd_histogram"),
            "stoch_k": features.get("stoch_k"),
            "stoch_d": features.get("stoch_d"),
        },
        "volatility": {
            "atr_14": features.get("atr_14"),
            "bb_upper": features.get("bb_upper"),
            "bb_lower": features.get("bb_lower"),
            "bb_pct_b": features.get("bb_pct_b"),
        },
        "volume": {
            "volume_ratio_20": features.get("volume_ratio_20"),
            "obv_trend": features.get("obv_trend", "unknown"),
        },
        "sentiment": {
            "score": round(sentiment, 4),
            "interpretation": (
                "bullish" if sentiment > 0.2
                else "bearish" if sentiment < -0.2
                else "neutral"
            ),
        },
        "portfolio": {
            "cash_pct": portfolio.get("cash_pct"),
            "equity": portfolio.get("equity"),
            "drawdown_pct": portfolio.get("drawdown_pct"),
            "open_positions": portfolio.get("open_positions", []),
        },
        "macro": {
            "key_rate_pct": macro.get("key_rate_pct"),
            "usd_rub": macro.get("usd_rub"),
            "oil_brent": macro.get("oil_brent"),
        },
    }

    # Macro regime determination
    key_rate = macro.get("key_rate_pct", 0)
    macro_regime = "NEUTRAL"
    if key_rate and key_rate > 15:
        macro_regime = "TIGHTENING"
    elif key_rate and key_rate < 8:
        macro_regime = "EASING"

    usd_rub = macro.get("usd_rub")
    if usd_rub and usd_rub > 110:
        macro_regime = "STRESS"

    context["macro"]["regime"] = macro_regime

    # Sector sensitivity
    sector = SECTOR_MAP.get(ticker, "banks")
    context["sector_sensitivity"] = SECTOR_SENSITIVITY_DESC.get(sector, "")

    if fundamentals:
        context["fundamentals"] = {
            "pe_ratio": fundamentals.get("pe_ratio"),
            "sector_pe": fundamentals.get("sector_pe"),
            "div_yield_pct": fundamentals.get("div_yield"),
            "roe_pct": fundamentals.get("roe"),
        }

    # Recent news for this ticker
    if news:
        context["recent_news"] = [
            {
                "title": n.get("title", "")[:100],
                "sentiment": round(n.get("sentiment", 0.0), 2),
                "impact": n.get("impact", "low"),
                "direction": n.get("direction", "neutral"),
            }
            for n in news[:3]
        ]
        n_bull = sum(1 for n in news if n.get("direction") == "bullish")
        n_bear = sum(1 for n in news if n.get("direction") == "bearish")
        context["news_summary"] = f"{len(news)} новостей: {n_bull} bullish, {n_bear} bearish"

    return json.dumps(context, ensure_ascii=False, indent=None)
