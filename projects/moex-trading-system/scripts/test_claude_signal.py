"""Одиночный интеграционный тест — вызов Claude API для получения торгового сигнала по SBER.

Запуск:
    cd C:\\CLOUDE_PR\\projects\\moex-trading-system
    venv\\Scripts\\python.exe scripts/test_claude_signal.py
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Добавляем корень проекта в sys.path, чтобы работали импорты src.*
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Проверяем наличие .env, при отсутствии — создаём заготовку
# ---------------------------------------------------------------------------

ENV_PATH = PROJECT_ROOT / ".env"
if not ENV_PATH.exists():
    ENV_PATH.write_text(
        "# Заполни реальными значениями и перезапусти скрипт\n"
        "ANTHROPIC_API_KEY=sk-ant-ВАШ_КЛЮЧ_ЗДЕСЬ\n"
        "DB_PATH=data/trading.db\n"
        "TRADING_MODE=paper\n",
        encoding="utf-8",
    )
    print(
        f"[!] .env не найден. Создан шаблон: {ENV_PATH}\n"
        "    Укажи ANTHROPIC_API_KEY и перезапусти скрипт."
    )
    sys.exit(1)

# Загружаем .env вручную (без Pydantic Settings — чтобы не требовать все поля)
for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, val = line.partition("=")
        k, v = key.strip(), val.strip()
        if v and (k not in os.environ or not os.environ[k]):
            os.environ[k] = v

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith("sk-ant-ВАШ"):
    print(
        "[!] ANTHROPIC_API_KEY не заполнен.\n"
        f"    Открой {ENV_PATH} и укажи реальный ключ."
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Импорты проекта (после добавления PROJECT_ROOT в sys.path)
# ---------------------------------------------------------------------------

import polars as pl  # noqa: E402

from src.analysis.features import calculate_all_features  # noqa: E402
from src.analysis.regime import detect_regime  # noqa: E402
from src.analysis.scoring import SCORING_WEIGHTS, calculate_pre_score  # noqa: E402
from src.models.market import MarketRegime  # noqa: E402
from src.models.portfolio import Portfolio  # noqa: E402
from src.models.signal import Direction  # noqa: E402
from src.risk.manager import validate_signal  # noqa: E402
from src.risk.position_sizer import (  # noqa: E402
    calculate_consecutive_multiplier,
    calculate_drawdown_multiplier,
    calculate_position_size,
)
from src.strategy.claude_engine import get_trading_signal  # noqa: E402
from src.strategy.prompts import build_market_context  # noqa: E402

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

TICKER = "SBER"
LOT_SIZE = 10
EQUITY = 100_000.0
DB_PATH = PROJECT_ROOT / os.environ.get("DB_PATH", "data/trading.db")


# ---------------------------------------------------------------------------
# Загрузка данных из SQLite
# ---------------------------------------------------------------------------


def load_candles(ticker: str, limit: int = 200) -> pl.DataFrame:
    """Загрузить последние `limit` свечей из trading.db."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            """
            SELECT date, open, high, low, close, volume, COALESCE(value, 0.0) AS value
            FROM candles
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker, limit),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise RuntimeError(f"Нет данных для {ticker} в {DB_PATH}")

    # Данные пришли в обратном порядке (DESC) — разворачиваем
    rows = list(reversed(rows))

    return pl.DataFrame(
        {
            "date": [r[0] for r in rows],
            "open": [float(r[1]) for r in rows],
            "high": [float(r[2]) for r in rows],
            "low": [float(r[3]) for r in rows],
            "close": [float(r[4]) for r in rows],
            "volume": [int(r[5]) for r in rows],
            "value": [float(r[6]) for r in rows],
        }
    )


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _safe_float(val: float | None, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and val != val):  # NaN guard
        return default
    return float(val)


def _get_last(series: pl.Series, default: float = 0.0) -> float:
    """Получить последнее не-null значение из серии."""
    clean = series.drop_nulls()
    if len(clean) == 0:
        return default
    val = clean[-1]
    if val is None or (isinstance(val, float) and val != val):
        return default
    return float(val)


def _detect_obv_trend(obv: pl.Series, window: int = 10) -> str:
    """Определить направление OBV по последним `window` барам."""
    clean = obv.drop_nulls()
    if len(clean) < window:
        return "unknown"
    recent = clean[-window:].to_list()
    slope = recent[-1] - recent[0]
    if slope > 0:
        return "up"
    if slope < 0:
        return "down"
    return "flat"


def _score_label(score: float) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------


async def main() -> None:
    today = date.today().isoformat()

    # ------------------------------------------------------------------
    # 1. Загрузка свечей
    # ------------------------------------------------------------------
    print(f"\nЗагрузка последних 200 свечей {TICKER} из {DB_PATH}...")
    df = load_candles(TICKER, limit=200)
    last_bar = df.row(-1, named=True)
    close_price = float(last_bar["close"])
    bar_date = last_bar["date"]

    # ------------------------------------------------------------------
    # 2. Технические индикаторы
    # ------------------------------------------------------------------
    df_feat = calculate_all_features(df)

    rsi = _get_last(df_feat["rsi_14"])
    macd_val = _get_last(df_feat["macd"])
    macd_signal = _get_last(df_feat["macd_signal"])
    macd_hist = _get_last(df_feat["macd_histogram"])
    adx = _get_last(df_feat["adx"])
    di_plus = _get_last(df_feat["di_plus"])
    di_minus = _get_last(df_feat["di_minus"])
    ema20 = _get_last(df_feat["ema_20"])
    ema50 = _get_last(df_feat["ema_50"])
    ema200 = _get_last(df_feat["ema_200"])
    atr = _get_last(df_feat["atr_14"])
    bb_upper = _get_last(df_feat["bb_upper"])
    bb_lower = _get_last(df_feat["bb_lower"])
    bb_pct_b = _get_last(df_feat["bb_pct_b"])
    stoch_k = _get_last(df_feat["stoch_k"])
    stoch_d = _get_last(df_feat["stoch_d"])
    volume_ratio = _get_last(df_feat["volume_ratio_20"], default=1.0)
    obv_trend = _detect_obv_trend(df_feat["obv"])

    # ------------------------------------------------------------------
    # 3. Режим рынка
    # ------------------------------------------------------------------
    atr_pct = atr / close_price if close_price > 0 else 0.0
    regime: MarketRegime = detect_regime(
        index_close=df_feat["close"],
        index_adx=adx,
        index_atr_pct=atr_pct,
        current_drawdown=0.0,
    )

    # ------------------------------------------------------------------
    # 4. Pre-Score
    # ------------------------------------------------------------------
    # Для SBER используем типовые фундаментальные данные
    pe_ratio = 4.8
    sector_pe = 6.5
    div_yield = 0.12  # ~12% дивидендная доходность SBER

    pre_score, breakdown = calculate_pre_score(
        adx=adx,
        di_plus=di_plus,
        di_minus=di_minus,
        rsi=rsi,
        macd_hist=macd_hist,
        close=close_price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        volume_ratio=volume_ratio,
        obv_trend=obv_trend,
        sentiment_score=0.15,  # нейтрально-позитивный сентимент
        pe_ratio=pe_ratio,
        sector_pe=sector_pe,
        div_yield=div_yield,
        direction="long",
    )

    # ------------------------------------------------------------------
    # 5. Формирование контекста и вызов Claude
    # ------------------------------------------------------------------
    features_dict = {
        "close": close_price,
        "ema_20": ema20,
        "ema_50": ema50,
        "ema_200": ema200,
        "rsi_14": round(rsi, 2),
        "macd": round(macd_val, 4),
        "macd_signal": round(macd_signal, 4),
        "macd_histogram": round(macd_hist, 4),
        "adx": round(adx, 2),
        "di_plus": round(di_plus, 2),
        "di_minus": round(di_minus, 2),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "bb_pct_b": round(bb_pct_b, 4),
        "atr_14": round(atr, 2),
        "stoch_k": round(stoch_k, 2),
        "stoch_d": round(stoch_d, 2),
        "volume_ratio_20": round(volume_ratio, 4),
        "obv_trend": obv_trend,
    }

    portfolio_dict = {
        "cash_pct": 100.0,
        "equity": EQUITY,
        "drawdown_pct": 0.0,
        "open_positions": [],
    }

    macro_dict = {
        "key_rate_pct": 21.0,   # ЦБ РФ ключевая ставка
        "usd_rub": 85.5,
        "oil_brent": 72.0,
    }

    fundamentals_dict = {
        "pe_ratio": pe_ratio,
        "sector_pe": sector_pe,
        "div_yield": div_yield,
        "roe": 0.24,
    }

    market_context = build_market_context(
        ticker=TICKER,
        regime=regime,
        features=features_dict,
        sentiment=0.15,
        portfolio=portfolio_dict,
        macro=macro_dict,
        fundamentals=fundamentals_dict,
    )

    print(f"Вызов Claude API (claude-sonnet-4-20250514)...")
    signal = await get_trading_signal(
        ticker=TICKER,
        market_context=market_context,
    )
    signal = signal.with_pre_score(pre_score)

    # ------------------------------------------------------------------
    # 6. Risk Gateway
    # ------------------------------------------------------------------
    portfolio = Portfolio(
        cash=EQUITY,
        peak_equity=EQUITY,
        daily_start_equity=EQUITY,
        positions={},
        consecutive_losses=0,
        trades_today=0,
    )

    risk_result = validate_signal(signal=signal, portfolio=portfolio)

    # ------------------------------------------------------------------
    # 7. Position Sizing
    # ------------------------------------------------------------------
    lots = 0
    pos_value = 0.0
    risk_pct = 0.0

    if signal.entry_price and signal.stop_loss:
        dd_mult = calculate_drawdown_multiplier(portfolio.drawdown)
        cons_mult = calculate_consecutive_multiplier(portfolio.consecutive_losses)
        lots, pos_value, risk_pct = calculate_position_size(
            equity=EQUITY,
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss,
            lot_size=LOT_SIZE,
            risk_per_trade=0.015,
            max_position_pct=0.15,
            direction=signal.direction.value,
            drawdown_mult=dd_mult,
            consecutive_mult=cons_mult,
        )

    # ------------------------------------------------------------------
    # 8. Вывод результата
    # ------------------------------------------------------------------
    print()
    print("=" * 50)
    print("=== Claude Trading Signal Test ===")
    print("=" * 50)
    print(f"Ticker: {TICKER}")
    print(f"Date:   {bar_date}")
    print(f"Price:  {close_price:.2f}")

    print()
    print("--- Technical Indicators ---")
    print(f"RSI(14):          {rsi:.1f}")
    print(f"MACD Histogram:   {macd_hist:.4f}")
    print(f"MACD:             {macd_val:.4f}")
    print(f"MACD Signal:      {macd_signal:.4f}")
    print(f"ADX(14):          {adx:.1f}")
    print(f"DI+:              {di_plus:.1f}  |  DI-: {di_minus:.1f}")
    print(f"EMA20/50/200:     {ema20:.0f} / {ema50:.0f} / {ema200:.0f}")
    print(f"ATR(14):          {atr:.2f}")
    print(f"Bollinger %B:     {bb_pct_b:.3f}  (Upper: {bb_upper:.2f} / Lower: {bb_lower:.2f})")
    print(f"Stoch K/D:        {stoch_k:.1f} / {stoch_d:.1f}")
    print(f"Volume Ratio:     {volume_ratio:.2f}x  |  OBV Trend: {obv_trend}")

    print()
    print("--- Market Regime ---")
    print(f"Regime: {regime.value.upper()}")

    print()
    print("--- Pre-Score ---")
    print(f"Total: {pre_score:.2f} ({_score_label(pre_score)})")
    weights = SCORING_WEIGHTS
    max_scores = {f: weights[f] * 100 for f in weights}
    for factor, weighted in breakdown.items():
        print(f"  {factor.capitalize():12s}: {weighted:.2f}/{max_scores[factor]:.2f}")

    print()
    print("--- Claude Signal ---")
    print(f"Action:     {signal.action.value.upper()}")
    print(f"Direction:  {signal.direction.value.upper()}")
    print(f"Confidence: {signal.confidence:.2f}")
    if signal.entry_price:
        print(f"Entry:      {signal.entry_price:.2f}")
    if signal.stop_loss:
        print(f"Stop-Loss:  {signal.stop_loss:.2f}")
    if signal.take_profit:
        print(f"Take-Profit:{signal.take_profit:.2f}")
    print(f"Strategy:   {signal.strategy}")
    print(f"Time Stop:  {signal.time_stop_days} дней")
    if signal.key_factors:
        print("Key factors:")
        for kf in signal.key_factors:
            print(f"  + {kf}")
    if signal.risk_factors:
        print("Risk factors:")
        for rf in signal.risk_factors:
            print(f"  - {rf}")
    print(f"Reasoning:  {signal.reasoning}")

    print()
    print("--- Risk Gateway ---")
    print(f"Decision: {risk_result.decision.value.upper()}")
    print(f"Checks: {risk_result.checks_passed}/{risk_result.checks_total} passed")
    if risk_result.errors:
        print("Errors:")
        for e in risk_result.errors:
            print(f"  [ERR] {e}")
    if risk_result.warnings:
        print("Warnings:")
        for w in risk_result.warnings:
            print(f"  [WRN] {w}")
    else:
        print("Warnings: []")

    print()
    print("--- Position Sizing ---")
    if lots > 0:
        pos_pct = pos_value / EQUITY * 100
        risk_rub = EQUITY * risk_pct
        print(f"Lots:   {lots}")
        print(f"Value:  {pos_value:,.0f} ({pos_pct:.1f}% of {EQUITY:,.0f})")
        print(f"Risk:   {risk_rub:,.0f} ({risk_pct:.2%})")
    else:
        reason = "нет стоп-лосса или точки входа" if not (signal.entry_price and signal.stop_loss) else "расчёт дал 0 лотов"
        print(f"Позиция не рассчитана: {reason}")

    print()
    print("=" * 50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
