"""Улучшенный бэктест: мультистратегия с Pre-Score, режимами рынка и шортами.

Стратегии по режиму рынка:
- UPTREND   (ADX>25 + Close>EMA200): Trend Following LONG (MACD + RSI pullback)
- DOWNTREND (ADX>25 + Close<EMA200): только закрытие позиций, новых лонгов нет
- RANGE     (ADX<20):  Mean Reversion LONG (RSI2<10) + SHORT (RSI2>90)
- CRISIS:   закрыть всё, нет новых позиций
- WEAK_TREND: облегчённый trend following

Exits:
- Trailing stop: ATR * 2.5 (подтягивается за ценой)
- 3-уровневый Take Profit: TP1(ATR*2, 30%), TP2(ATR*3.5, 30%), TP3(trailing, 40%)
- Time stop: 30 дней без +10%, 15 дней без +0%

Position Sizing: ATR-based volatility-adjusted 1% с drawdown multiplier
Sector limits: max 30% в одном секторе

Запуск: python -m scripts.run_enhanced_backtest
"""

from __future__ import annotations

import asyncio
import math
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
import structlog

from src.analysis.features import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger,
    calculate_ema,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
    calculate_volume_ratio,
)
from src.analysis.regime import detect_regime_from_index
from src.analysis.scoring import calculate_pre_score
from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.risk.position_sizer import (
    calculate_consecutive_multiplier,
    calculate_drawdown_multiplier,
    calculate_volatility_adjusted_size,
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=False),
    ],
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

DB_PATH = "data/trading.db"
TICKERS = ["SBER", "GAZP", "LKOH", "NVTK", "ROSN", "GMKN", "VTBR", "MGNT", "TCSG", "YDEX"]

TICKER_META: dict[str, dict] = {
    "SBER":  {"sector": "banks",   "lot_size": 1},
    "GAZP":  {"sector": "oil_gas", "lot_size": 10},
    "LKOH":  {"sector": "oil_gas", "lot_size": 1},
    "NVTK":  {"sector": "oil_gas", "lot_size": 1},
    "ROSN":  {"sector": "oil_gas", "lot_size": 1},
    "GMKN":  {"sector": "metals",  "lot_size": 1},
    "VTBR":  {"sector": "banks",   "lot_size": 10000},
    "MGNT":  {"sector": "retail",  "lot_size": 1},
    "TCSG":  {"sector": "banks",   "lot_size": 1},
    "YDEX":  {"sector": "it",      "lot_size": 1},
}

INITIAL_CAPITAL = 1_000_000.0
RISK_PER_TRADE = 0.01           # 1% на сделку
MAX_POSITION_PCT = 0.15         # 15% на тикер
MAX_SECTOR_PCT = 0.30           # 30% на сектор
MAX_SHORT_TOTAL_PCT = 0.15      # 15% суммарно в шортах
MAX_SHORT_ONE_PCT = 0.08        # 8% на один шорт

ATR_MULT_STOP = 2.5             # трейлинг стоп
ATR_MULT_TP1 = 2.0              # TP1
ATR_MULT_TP2 = 3.5              # TP2
TP1_FRAC = 0.30                 # доля позиции на TP1
TP2_FRAC = 0.30                 # доля позиции на TP2
TP3_FRAC = 0.40                 # остаток — трейлинг

COMMISSION_RT = 0.002           # 0.2% round-trip
PRE_SCORE_MIN_TREND = 55.0      # минимальный Pre-Score для trend входа
PRE_SCORE_MIN_MR = 40.0         # минимальный Pre-Score для mean reversion (мягче)

# Time stop параметры
TIME_STOP_NO_PROFIT_DAYS = 15   # 15 дней без прибыли — выход
TIME_STOP_NO_GROWTH_DAYS = 30   # 30 дней без +10% — выход
GROWTH_TARGET_PCT = 0.10        # целевой рост за 30 дней

# RSI(2) для Mean Reversion
MR_RSI2_BUY_THRESHOLD = 10.0
MR_RSI2_SELL_THRESHOLD = 90.0
MR_RSI2_EXIT_LONG = 70.0
MR_RSI2_EXIT_SHORT = 30.0
MR_HOLD_DAYS = 5               # максимум дней в MR позиции


# ---------------------------------------------------------------------------
# Структуры данных
# ---------------------------------------------------------------------------

@dataclass
class Position:
    ticker: str
    direction: str          # "long" | "short"
    strategy: str           # "trend" | "mean_reversion" | "mr_short"
    entry_price: float
    entry_date: date
    entry_idx: int
    lots: int
    lot_size: int
    stop_loss: float
    trail_stop: float       # подтягивается за ценой
    tp1_price: float
    tp2_price: float
    tp1_done: bool = False
    tp2_done: bool = False
    remaining_frac: float = 1.0  # оставшаяся доля позиции (после частичных TP)
    peak_price: float = 0.0      # максимум цены с момента входа (для trailing)


@dataclass
class TradeRecord:
    ticker: str
    direction: str
    strategy: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    lots: float             # может быть дробным после частичных TP
    pnl: float
    pnl_pct: float
    days_held: int
    exit_reason: str


@dataclass
class TickerState:
    """Состояние портфеля по одному тикеру."""
    ticker: str
    sector: str
    lot_size: int
    equity_allocated: float    # выделено капитала на тикер
    position: Optional[Position] = None
    trades: list[TradeRecord] = field(default_factory=list)
    consecutive_losses: int = 0
    equity_curve: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Построение DataFrame с индикаторами
# ---------------------------------------------------------------------------

def build_dataframe(candles: list[OHLCVBar]) -> pl.DataFrame:
    df = pl.DataFrame({
        "date":   [c.dt for c in candles],
        "open":   [c.open for c in candles],
        "high":   [c.high for c in candles],
        "low":    [c.low for c in candles],
        "close":  [c.close for c in candles],
        "volume": [c.volume for c in candles],
    }).sort("date")
    return df


def add_indicators(df: pl.DataFrame) -> pl.DataFrame:
    """Все нужные индикаторы за один проход."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # EMA
    ema20 = calculate_ema(close, 20)
    ema50 = calculate_ema(close, 50)
    ema200 = calculate_ema(close, 200)

    # RSI
    rsi14 = calculate_rsi(close, 14)
    rsi2 = calculate_rsi(close, 2)

    # MACD
    macd_d = calculate_macd(close)

    # ADX
    adx_d = calculate_adx(high, low, close, 14)

    # Bollinger
    bb_d = calculate_bollinger(close, 20, 2.0)

    # ATR
    atr14 = calculate_atr(high, low, close, 14)

    # OBV
    obv = calculate_obv(close, volume)

    # Volume ratio
    vol_ratio = calculate_volume_ratio(volume, 20)

    # Z-score цены (20-дневный)
    close_pd = close.to_pandas()
    z_mean = close_pd.rolling(20, min_periods=5).mean()
    z_std = close_pd.rolling(20, min_periods=5).std()
    z_score = (close_pd - z_mean) / z_std.replace(0, float("nan"))

    z_series = pl.Series(name="z_score", values=z_score.values)

    return df.with_columns([
        ema20.alias("ema_20"),
        ema50.alias("ema_50"),
        ema200.alias("ema_200"),
        rsi14.alias("rsi_14"),
        rsi2.alias("rsi_2"),
        macd_d["histogram"].alias("macd_hist"),
        macd_d["macd"].alias("macd"),
        macd_d["signal"].alias("macd_signal"),
        adx_d["adx"].alias("adx"),
        adx_d["di_plus"].alias("di_plus"),
        adx_d["di_minus"].alias("di_minus"),
        bb_d["bb_upper"].alias("bb_upper"),
        bb_d["bb_lower"].alias("bb_lower"),
        bb_d["bb_middle"].alias("bb_middle"),
        atr14.alias("atr"),
        obv.alias("obv"),
        vol_ratio.alias("vol_ratio"),
        z_series,
    ])


# ---------------------------------------------------------------------------
# Определение режима рынка
# ---------------------------------------------------------------------------

def get_regime(row: dict, imoex_regime: str | None = None) -> str:
    """Определить режим рынка.

    Если передан ``imoex_regime`` (режим, посчитанный по IMOEX), он
    используется как основной источник истины.  Это корректный подход:
    режим рынка отражает состояние всего рынка, а не отдельной акции.

    Fallback на расчёт по данным конкретной акции используется тогда,
    когда данные IMOEX недоступны (``imoex_regime is None``).
    """
    if imoex_regime is not None:
        return imoex_regime

    # --- Fallback: режим по данным конкретной акции ---
    adx = row.get("adx") or 0.0
    close = row.get("close") or 0.0
    ema200 = row.get("ema_200") or 0.0
    atr = row.get("atr") or 0.0

    atr_pct = atr / close if close > 0 else 0.0
    if atr_pct > 0.035:
        return "crisis"

    if adx > 25:
        if close > ema200:
            return "uptrend"
        return "downtrend"

    if adx < 20:
        return "range"

    return "weak_trend"


def build_imoex_regime_map(
    imoex_candles: list[OHLCVBar],
    drawdown: float = 0.0,
) -> dict[date, str]:
    """Построить словарь {дата: режим} по данным IMOEX.

    Проходит по всем барам IMOEX и для каждого момента времени
    определяет режим по накопленным к этой дате данным.
    Это позволяет использовать только исторически доступные данные.

    Parameters
    ----------
    imoex_candles:
        Отсортированный список баров IMOEX.
    drawdown:
        Текущая просадка (используется единая для всего периода).
        В production это должно пересчитываться динамически.

    Returns
    -------
    Словарь {date: режим_как_строка} для каждого бара.
    """
    from src.models.market import MarketRegime

    _regime_to_str = {
        MarketRegime.UPTREND: "uptrend",
        MarketRegime.DOWNTREND: "downtrend",
        MarketRegime.RANGE: "range",
        MarketRegime.CRISIS: "crisis",
        MarketRegime.WEAK_TREND: "weak_trend",
    }

    regime_map: dict[date, str] = {}
    # Нужен минимум 14 баров для ADX, 200 — для SMA200
    warmup = 14
    for i, bar in enumerate(imoex_candles):
        if i < warmup:
            regime_map[bar.dt] = "weak_trend"
        else:
            window_candles = imoex_candles[: i + 1]
            regime = detect_regime_from_index(window_candles, drawdown)
            regime_map[bar.dt] = _regime_to_str[regime]

    return regime_map


# ---------------------------------------------------------------------------
# OBV тренд
# ---------------------------------------------------------------------------

def obv_trend(obv_series: list[float], window: int = 5) -> str:
    """Определить тренд OBV по последним N значениям."""
    if len(obv_series) < window:
        return "flat"
    recent = obv_series[-window:]
    if recent[-1] > recent[0] * 1.01:
        return "up"
    if recent[-1] < recent[0] * 0.99:
        return "down"
    return "flat"


# ---------------------------------------------------------------------------
# Pre-Score для конкретного сигнала
# ---------------------------------------------------------------------------

def compute_pre_score(row: dict, direction: str, obv_tr: str) -> float:
    """Вычислить Pre-Score через scoring.py."""
    adx = row.get("adx") or 0.0
    di_plus = row.get("di_plus") or 0.0
    di_minus = row.get("di_minus") or 0.0
    rsi = row.get("rsi_14") or 50.0
    macd_hist = row.get("macd_hist") or 0.0
    close = row.get("close") or 1.0
    ema20 = row.get("ema_20") or close
    ema50 = row.get("ema_50") or close
    ema200 = row.get("ema_200") or close
    vol_ratio = row.get("vol_ratio") or 1.0

    score, _ = calculate_pre_score(
        adx=adx,
        di_plus=di_plus,
        di_minus=di_minus,
        rsi=rsi,
        macd_hist=macd_hist,
        close=close,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        volume_ratio=vol_ratio,
        obv_trend=obv_tr,
        sentiment_score=0.0,    # нет данных — нейтральный
        direction=direction,
    )
    return score


# ---------------------------------------------------------------------------
# Вычисление размера позиции
# ---------------------------------------------------------------------------

def calc_lot_size(
    equity: float,
    entry_price: float,
    atr: float,
    lot_size: int,
    direction: str,
    drawdown: float,
    consecutive_losses: int,
) -> tuple[int, float]:
    """Вычислить количество лотов и стоимость позиции (ATR-based sizing).

    Использует calculate_volatility_adjusted_size: волатильная бумага (большой ATR)
    получает меньший размер позиции, спокойная — больший. Каждая позиция несёт
    одинаковый риск в рублях.
    """
    dd_mult = calculate_drawdown_multiplier(drawdown)
    cons_mult = calculate_consecutive_multiplier(consecutive_losses)
    effective_drawdown_mult = dd_mult * cons_mult

    lots, pos_value, _ = calculate_volatility_adjusted_size(
        equity=equity,
        entry_price=entry_price,
        atr=atr,
        lot_size=lot_size,
        target_risk_pct=RISK_PER_TRADE,
        atr_multiplier=ATR_MULT_STOP,
        max_position_pct=MAX_POSITION_PCT,
        direction=direction,
        drawdown_mult=effective_drawdown_mult,
    )
    return lots, pos_value


# ---------------------------------------------------------------------------
# Проверка лимита сектора
# ---------------------------------------------------------------------------

def sector_exposure(
    ticker: str,
    states: dict[str, TickerState],
    total_equity: float,
) -> float:
    """Доля сектора от total_equity с учётом открытых позиций."""
    sector = TICKER_META.get(ticker, {}).get("sector", "unknown")
    exposure = 0.0
    for t, state in states.items():
        if TICKER_META.get(t, {}).get("sector") == sector and state.position is not None:
            pos = state.position
            exposure += pos.lots * pos.lot_size * pos.entry_price
    return exposure / total_equity if total_equity > 0 else 0.0


def short_exposure(states: dict[str, TickerState], total_equity: float) -> float:
    """Суммарная доля шортов от total_equity."""
    total_short = 0.0
    for state in states.values():
        if state.position and state.position.direction == "short":
            pos = state.position
            total_short += pos.lots * pos.lot_size * pos.entry_price
    return total_short / total_equity if total_equity > 0 else 0.0


# ---------------------------------------------------------------------------
# Основной бэктест одного тикера
# ---------------------------------------------------------------------------

def backtest_ticker(
    ticker: str,
    df: pl.DataFrame,
    initial_equity: float,
    lot_size: int,
    imoex_regime_map: dict[date, str] | None = None,
) -> dict:
    trades: list[TradeRecord] = []
    position: Optional[Position] = None
    equity = initial_equity
    peak_equity = equity
    obv_history: list[float] = []
    equity_curve: list[float] = [equity]
    consecutive_losses = 0

    rows = df.to_dicts()

    for i, row in enumerate(rows):
        close = row.get("close") or 0.0
        high = row.get("high") or close
        low = row.get("low") or close
        atr = row.get("atr") or 0.0
        rsi14 = row.get("rsi_14")
        rsi2 = row.get("rsi_2")
        ema200 = row.get("ema_200")
        ema50 = row.get("ema_50")
        macd_hist = row.get("macd_hist")
        adx = row.get("adx")
        bb_upper = row.get("bb_upper")
        bb_lower = row.get("bb_lower")
        z_score = row.get("z_score")
        vol_ratio = row.get("vol_ratio")
        obv_val = row.get("obv")

        dt = row["date"]

        # Обновить OBV историю
        if obv_val is not None:
            obv_history.append(obv_val)

        # Проверить наличие всех индикаторов (warmup период)
        required = [rsi14, rsi2, ema200, ema50, macd_hist, adx, atr, bb_upper, bb_lower]
        if any(v is None or (isinstance(v, float) and v != v) for v in required):
            equity_curve.append(equity)
            continue
        if atr <= 0 or close <= 0:
            equity_curve.append(equity)
            continue

        # Режим рынка: приоритет — IMOEX-карта, fallback — данные акции
        imoex_regime: str | None = (
            imoex_regime_map.get(dt) if imoex_regime_map is not None else None
        )
        regime = get_regime(row, imoex_regime)
        obv_tr = obv_trend(obv_history)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0

        # ---------------------------------------------------------------
        # EXIT логика
        # ---------------------------------------------------------------
        if position is not None:
            days_held = i - position.entry_idx
            pos = position
            exit_price: Optional[float] = None
            exit_reason: Optional[str] = None
            exit_lots_frac: float = 1.0  # доля выходящих лотов

            # CRISIS — закрыть всё
            if regime == "crisis":
                exit_price = close
                exit_reason = "crisis_close"

            # Шорт выходы
            elif pos.direction == "short":
                # Стоп-лосс шорта (цена выросла выше stop)
                if high >= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"
                # MR short exit: RSI2 < 30
                elif pos.strategy == "mr_short" and rsi2 < MR_RSI2_EXIT_SHORT:
                    exit_price = close
                    exit_reason = "mr_rsi2_exit"
                # Time stop MR
                elif pos.strategy == "mr_short" and days_held >= MR_HOLD_DAYS:
                    exit_price = close
                    exit_reason = "time_mr"
                # Трейлинг для шорта (обновляем минимум)
                elif pos.strategy != "mr_short":
                    if close < pos.peak_price:
                        pos.peak_price = close
                        pos.trail_stop = pos.peak_price + atr * ATR_MULT_STOP
                    if high >= pos.trail_stop:
                        exit_price = pos.trail_stop
                        exit_reason = "trailing_stop"

            # Лонг выходы
            else:
                # Трейлинг стоп — обновить если цена растёт
                if high > pos.peak_price:
                    pos.peak_price = high
                    new_trail = pos.peak_price - atr * ATR_MULT_STOP
                    pos.trail_stop = max(pos.trail_stop, new_trail)

                # TP1 (ATR * 2 от входа)
                if not pos.tp1_done and high >= pos.tp1_price:
                    # Закрыть 30% позиции
                    tp_lots = max(1, math.floor(pos.lots * TP1_FRAC))
                    pnl = (pos.tp1_price - pos.entry_price) * tp_lots * pos.lot_size
                    pnl -= pos.entry_price * tp_lots * pos.lot_size * COMMISSION_RT
                    equity += pnl
                    trades.append(TradeRecord(
                        ticker=ticker, direction="long", strategy=pos.strategy,
                        entry_date=pos.entry_date, exit_date=dt,
                        entry_price=pos.entry_price, exit_price=pos.tp1_price,
                        lots=tp_lots, pnl=round(pnl, 2),
                        pnl_pct=round((pos.tp1_price / pos.entry_price - 1) * 100, 2),
                        days_held=days_held, exit_reason="tp1",
                    ))
                    pos.lots -= tp_lots
                    pos.tp1_done = True
                    consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1

                # TP2 (ATR * 3.5 от входа)
                if pos.tp1_done and not pos.tp2_done and high >= pos.tp2_price:
                    tp_lots = max(1, math.floor(pos.lots * (TP2_FRAC / (TP1_FRAC + TP2_FRAC))))
                    pnl = (pos.tp2_price - pos.entry_price) * tp_lots * pos.lot_size
                    pnl -= pos.entry_price * tp_lots * pos.lot_size * COMMISSION_RT
                    equity += pnl
                    trades.append(TradeRecord(
                        ticker=ticker, direction="long", strategy=pos.strategy,
                        entry_date=pos.entry_date, exit_date=dt,
                        entry_price=pos.entry_price, exit_price=pos.tp2_price,
                        lots=tp_lots, pnl=round(pnl, 2),
                        pnl_pct=round((pos.tp2_price / pos.entry_price - 1) * 100, 2),
                        days_held=days_held, exit_reason="tp2",
                    ))
                    pos.lots -= tp_lots
                    pos.tp2_done = True

                # Основной стоп (trailing)
                if exit_price is None:
                    if low <= pos.trail_stop:
                        exit_price = pos.trail_stop
                        exit_reason = "trailing_stop"

                # Stop-loss начальный
                if exit_price is None and low <= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"

                # MR long exit: RSI2 > 70
                if exit_price is None and pos.strategy == "mean_reversion" and rsi2 > MR_RSI2_EXIT_LONG:
                    exit_price = close
                    exit_reason = "mr_rsi2_exit"

                # Time stop MR
                if exit_price is None and pos.strategy == "mean_reversion" and days_held >= MR_HOLD_DAYS:
                    exit_price = close
                    exit_reason = "time_mr"

                # Trend exit: пробой EMA50 при тренде
                if exit_price is None and pos.strategy == "trend" and close < ema50 and adx > 20:
                    exit_price = close
                    exit_reason = "ema50_break"

                # DOWNTREND — закрыть все лонги
                if exit_price is None and regime == "downtrend":
                    exit_price = close
                    exit_reason = "regime_downtrend"

                # Time stop — 30 дней без роста на 10%
                if exit_price is None and days_held >= TIME_STOP_NO_GROWTH_DAYS:
                    growth = (close - pos.entry_price) / pos.entry_price
                    if growth < GROWTH_TARGET_PCT:
                        exit_price = close
                        exit_reason = "time_30d"

                # Time stop — 15 дней без прибыли
                if exit_price is None and days_held >= TIME_STOP_NO_PROFIT_DAYS:
                    if close <= pos.entry_price:
                        exit_price = close
                        exit_reason = "time_15d"

            # Закрыть позицию если есть сигнал выхода
            if exit_price is not None and exit_reason is not None and pos.lots > 0:
                mult = -1 if pos.direction == "short" else 1
                pnl = mult * (exit_price - pos.entry_price) * pos.lots * pos.lot_size
                pnl -= pos.entry_price * pos.lots * pos.lot_size * COMMISSION_RT
                equity += pnl
                if pnl > 0:
                    consecutive_losses = 0
                else:
                    consecutive_losses += 1

                trades.append(TradeRecord(
                    ticker=ticker,
                    direction=pos.direction,
                    strategy=pos.strategy,
                    entry_date=pos.entry_date,
                    exit_date=dt,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    lots=pos.lots,
                    pnl=round(pnl, 2),
                    pnl_pct=round(mult * (exit_price / pos.entry_price - 1) * 100, 2),
                    days_held=days_held,
                    exit_reason=exit_reason,
                ))
                position = None

        # ---------------------------------------------------------------
        # ENTRY логика
        # ---------------------------------------------------------------
        if position is None and regime != "crisis" and regime != "downtrend":

            # --- TREND FOLLOWING (UPTREND / WEAK_TREND) ---
            if regime in ("uptrend", "weak_trend"):
                pre_score = compute_pre_score(row, "long", obv_tr)
                buy_signal = (
                    pre_score >= PRE_SCORE_MIN_TREND
                    and rsi14 < 48
                    and macd_hist > 0
                    and close > ema50
                    and (vol_ratio or 0.0) > 0.7
                )
                if buy_signal:
                    stop_dist = atr * ATR_MULT_STOP
                    lots, pos_val = calc_lot_size(
                        equity, close, atr, lot_size,
                        "long", drawdown, consecutive_losses
                    )
                    if lots > 0:
                        position = Position(
                            ticker=ticker,
                            direction="long",
                            strategy="trend",
                            entry_price=close,
                            entry_date=dt,
                            entry_idx=i,
                            lots=lots,
                            lot_size=lot_size,
                            stop_loss=close - stop_dist,
                            trail_stop=close - stop_dist,
                            tp1_price=close + atr * ATR_MULT_TP1,
                            tp2_price=close + atr * ATR_MULT_TP2,
                            peak_price=close,
                        )

            # --- MEAN REVERSION LONG (RANGE) ---
            elif regime == "range" and rsi2 is not None:
                mr_long_signal = (
                    rsi2 < MR_RSI2_BUY_THRESHOLD
                    and close > ema200
                    and close < (bb_lower or 0.0)
                )
                if mr_long_signal:
                    stop_dist = atr * ATR_MULT_STOP
                    lots, pos_val = calc_lot_size(
                        equity, close, atr, lot_size,
                        "long", drawdown, consecutive_losses
                    )
                    if lots > 0:
                        position = Position(
                            ticker=ticker,
                            direction="long",
                            strategy="mean_reversion",
                            entry_price=close,
                            entry_date=dt,
                            entry_idx=i,
                            lots=lots,
                            lot_size=lot_size,
                            stop_loss=close - stop_dist,
                            trail_stop=close - stop_dist,
                            tp1_price=close + atr * ATR_MULT_TP1,
                            tp2_price=close + atr * ATR_MULT_TP2,
                            peak_price=close,
                        )

                # --- MEAN REVERSION SHORT (RANGE) ---
                elif (
                    rsi2 > MR_RSI2_SELL_THRESHOLD
                    and close < ema200
                    and close > (bb_upper or float("inf"))
                    and (z_score or 0.0) > 2.0
                ):
                    stop_dist = atr * ATR_MULT_STOP
                    short_stop = close + stop_dist
                    lots, pos_val = calc_lot_size(
                        equity, close, atr, lot_size,
                        "short", drawdown, consecutive_losses
                    )
                    if lots > 0:
                        position = Position(
                            ticker=ticker,
                            direction="short",
                            strategy="mr_short",
                            entry_price=close,
                            entry_date=dt,
                            entry_idx=i,
                            lots=lots,
                            lot_size=lot_size,
                            stop_loss=short_stop,
                            trail_stop=short_stop,
                            tp1_price=close - atr * ATR_MULT_TP1,
                            tp2_price=close - atr * ATR_MULT_TP2,
                            peak_price=close,
                        )

        # Обновить пик капитала
        if equity > peak_equity:
            peak_equity = equity
        equity_curve.append(equity)

    # Закрыть открытую позицию по последней цене
    if position is not None and rows:
        last = rows[-1]
        last_close = last["close"]
        days_held = len(rows) - position.entry_idx
        mult = -1 if position.direction == "short" else 1
        pnl = mult * (last_close - position.entry_price) * position.lots * position.lot_size
        pnl -= position.entry_price * position.lots * position.lot_size * COMMISSION_RT
        equity += pnl
        trades.append(TradeRecord(
            ticker=ticker,
            direction=position.direction,
            strategy=position.strategy,
            entry_date=position.entry_date,
            exit_date=last["date"],
            entry_price=position.entry_price,
            exit_price=last_close,
            lots=position.lots,
            pnl=round(pnl, 2),
            pnl_pct=round(mult * (last_close / position.entry_price - 1) * 100, 2),
            days_held=days_held,
            exit_reason="end_of_data",
        ))

    # Метрики по тикеру
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_pnl = sum(t.pnl for t in trades)
    gross_win = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    return {
        "ticker": ticker,
        "trades": trades,
        "final_equity": round(equity, 2),
        "return_pct": round((equity / initial_equity - 1) * 100, 2),
        "num_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / max(len(trades), 1) * 100, 1),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(profit_factor, 2),
        "equity_curve": equity_curve,
    }


# ---------------------------------------------------------------------------
# Портфельные метрики
# ---------------------------------------------------------------------------

def calc_sharpe_from_trades(trades: list[TradeRecord], risk_free_annual: float = 0.10) -> float:
    """Annualised Sharpe ratio рассчитанный по трейдовым доходностям.

    Использует pnl_pct каждой сделки как return, нормирует к годовым.
    Более корректен при малом числе сделок (нет проблемы flat equity).
    """
    if len(trades) < 3:
        return 0.0
    rets = [t.pnl_pct / 100.0 for t in trades]
    import statistics
    mean_r = statistics.mean(rets)
    std_r = statistics.stdev(rets)
    if std_r == 0:
        return 0.0
    # Среднее число сделок в году: предположим ~10 на тикер
    avg_trades_per_year = len(trades) / 5.0  # 5 лет периода
    rf_per_trade = risk_free_annual / avg_trades_per_year if avg_trades_per_year > 0 else 0.0
    return round((mean_r - rf_per_trade) / std_r * math.sqrt(avg_trades_per_year), 3)


def calc_sharpe(equity_curve: list[float], risk_free_rate: float = 0.10) -> float:
    """Annualised Sharpe ratio по дневным изменениям equity.

    Примечание: при малом числе сделок и длинных flat-периодах
    может давать аномальные значения. Предпочтительно использовать
    calc_sharpe_from_trades() для более корректной оценки.
    """
    if len(equity_curve) < 10:
        return 0.0
    # Фильтруем нулевые изменения (flat периоды вне позиций)
    returns = []
    for j in range(1, len(equity_curve)):
        prev = equity_curve[j - 1]
        curr = equity_curve[j]
        if prev > 0 and curr != prev:  # только дни с реальными изменениями
            returns.append(curr / prev - 1)
    if len(returns) < 3:
        return 0.0
    import statistics
    mean_r = statistics.mean(returns)
    std_r = statistics.stdev(returns)
    if std_r == 0:
        return 0.0
    daily_rf = risk_free_rate / 252
    return round((mean_r - daily_rf) / std_r * math.sqrt(252), 3)


def calc_max_drawdown(equity_curve: list[float]) -> float:
    """Максимальная просадка в процентах."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return round(max_dd * 100, 2)


def calc_benchmark_return(equity_curve_benchmark: list[float]) -> float:
    """Buy & Hold return."""
    if len(equity_curve_benchmark) < 2:
        return 0.0
    return round((equity_curve_benchmark[-1] / equity_curve_benchmark[0] - 1) * 100, 2)


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("enhanced_backtest_start", tickers=len(TICKERS), capital=INITIAL_CAPITAL)

    from_date = date(2021, 1, 1)
    to_date = date(2026, 3, 18)
    capital_per_ticker = INITIAL_CAPITAL / len(TICKERS)

    all_trades: list[TradeRecord] = []
    all_results: list[dict] = []
    total_equity = 0.0
    portfolio_equity_curve: list[float] = []

    # ---------------------------------------------------------------------------
    # Загрузить данные IMOEX и построить карту режимов рынка
    # ---------------------------------------------------------------------------
    imoex_regime_map: dict[date, str] | None = None
    try:
        imoex_candles = await get_candles(DB_PATH, "IMOEX", from_date, to_date)
        if len(imoex_candles) >= 14:
            log.info("imoex_data_loaded", bars=len(imoex_candles))
            imoex_regime_map = build_imoex_regime_map(imoex_candles)
            log.info("imoex_regime_map_built", dates=len(imoex_regime_map))
        else:
            log.warning(
                "imoex_data_insufficient",
                bars=len(imoex_candles),
                fallback="per_ticker_regime",
            )
    except Exception as exc:
        log.warning("imoex_data_unavailable", error=str(exc), fallback="per_ticker_regime")

    # Загружаем данные и запускаем бэктест по каждому тикеру
    for ticker in TICKERS:
        meta = TICKER_META.get(ticker, {"sector": "unknown", "lot_size": 1})
        lot_size = meta["lot_size"]

        candles = await get_candles(DB_PATH, ticker, from_date, to_date)
        if len(candles) < 220:
            log.warning("insufficient_data", ticker=ticker, bars=len(candles))
            total_equity += capital_per_ticker
            continue

        df = build_dataframe(candles)
        df = add_indicators(df)

        result = backtest_ticker(ticker, df, capital_per_ticker, lot_size, imoex_regime_map)
        all_results.append(result)
        all_trades.extend(result["trades"])
        total_equity += result["final_equity"]

        # Агрегировать equity curve портфеля (сумма по тикерам)
        if not portfolio_equity_curve:
            portfolio_equity_curve = list(result["equity_curve"])
        else:
            n = min(len(portfolio_equity_curve), len(result["equity_curve"]))
            portfolio_equity_curve = [
                portfolio_equity_curve[j] + result["equity_curve"][j]
                for j in range(n)
            ]

        log.info(
            "ticker_done",
            ticker=ticker,
            sector=meta["sector"],
            trades=result["num_trades"],
            win_rate=f"{result['win_rate']:.0f}%",
            ret=f"{result['return_pct']:+.1f}%",
            equity=f"{result['final_equity']:,.0f}",
        )

    # ---------------------------------------------------------------------------
    # Портфельная статистика
    # ---------------------------------------------------------------------------
    total_return = (total_equity / INITIAL_CAPITAL - 1) * 100
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t.pnl > 0)
    total_pnl = sum(t.pnl for t in all_trades)
    gross_win = sum(t.pnl for t in all_trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in all_trades if t.pnl <= 0))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    sharpe = calc_sharpe_from_trades(all_trades)
    max_dd = calc_max_drawdown(portfolio_equity_curve)

    # ---------------------------------------------------------------------------
    # Breakdown по стратегиям
    # ---------------------------------------------------------------------------
    breakdown: dict[str, dict] = {
        "trend": {"trades": 0, "pnl": 0.0, "wins": 0},
        "mean_reversion": {"trades": 0, "pnl": 0.0, "wins": 0},
        "mr_short": {"trades": 0, "pnl": 0.0, "wins": 0},
    }
    for t in all_trades:
        strat = t.strategy if t.strategy in breakdown else "trend"
        bd = breakdown.setdefault(strat, {"trades": 0, "pnl": 0.0, "wins": 0})
        bd["trades"] += 1
        bd["pnl"] += t.pnl
        if t.pnl > 0:
            bd["wins"] += 1

    # ---------------------------------------------------------------------------
    # Вывод результатов
    # ---------------------------------------------------------------------------
    separator = "=" * 60

    log.info(separator)
    log.info("ENHANCED BACKTEST RESULTS")
    log.info(separator)
    log.info("portfolio_summary",
             strategy="MultiStrategy (Trend+MR+Short)",
             period=f"{from_date} to {to_date}",
             initial_capital=f"{INITIAL_CAPITAL:,.0f}",
             final_equity=f"{total_equity:,.0f}",
             total_return=f"{total_return:+.2f}%",
             sharpe=f"{sharpe:.3f}",
             max_drawdown=f"{max_dd:.2f}%",
             total_trades=total_trades,
             win_rate=f"{total_wins}/{total_trades} ({total_wins / max(total_trades, 1) * 100:.0f}%)",
             profit_factor=f"{profit_factor:.2f}")

    # Бенчмарк (Buy & Hold SBER как прокси — первый тикер с данными)
    bh_results = [r for r in all_results if r["ticker"] == "SBER"]
    if bh_results and bh_results[0]["equity_curve"]:
        bh_curve = bh_results[0]["equity_curve"]
        bh_return = calc_benchmark_return(bh_curve)
        log.info("benchmark_comparison",
                 strategy_return=f"{total_return:+.2f}%",
                 sber_buy_hold=f"{bh_return:+.2f}%",
                 alpha=f"{total_return - bh_return:+.2f}%")

    # Breakdown по стратегиям
    log.info(separator)
    log.info("STRATEGY BREAKDOWN")
    for strat, bd in breakdown.items():
        if bd["trades"] > 0:
            wr = bd["wins"] / bd["trades"] * 100
            log.info(
                f"  {strat}",
                trades=bd["trades"],
                pnl=f"{bd['pnl']:+,.0f}",
                win_rate=f"{wr:.0f}%",
            )

    # Per-ticker summary
    log.info(separator)
    log.info("PER-TICKER RESULTS")
    for r in sorted(all_results, key=lambda x: x["return_pct"], reverse=True):
        log.info(
            f"  {r['ticker']}",
            trades=r["num_trades"],
            wins=f"{r['wins']}/{r['num_trades']}",
            win_rate=f"{r['win_rate']:.0f}%",
            ret=f"{r['return_pct']:+.1f}%",
            pf=f"{r['profit_factor']:.2f}",
        )

    # Топ-5 лучших сделок
    sorted_trades = sorted(all_trades, key=lambda t: t.pnl, reverse=True)
    log.info(separator)
    log.info("TOP 5 BEST TRADES")
    for t in sorted_trades[:5]:
        log.info(
            f"  {t.ticker} [{t.strategy}] {t.entry_date} to {t.exit_date}"
            f" PnL={t.pnl:+,.0f} ({t.pnl_pct:+.1f}%) [{t.exit_reason}]"
        )

    # Топ-5 худших сделок
    log.info("TOP 5 WORST TRADES")
    for t in sorted_trades[-5:]:
        log.info(
            f"  {t.ticker} [{t.strategy}] {t.entry_date} to {t.exit_date}"
            f" PnL={t.pnl:+,.0f} ({t.pnl_pct:+.1f}%) [{t.exit_reason}]"
        )

    # Equity curve (первые/последние значения + длина)
    log.info(separator)
    log.info("EQUITY CURVE SAMPLE",
             length=len(portfolio_equity_curve),
             start=f"{portfolio_equity_curve[0]:,.0f}" if portfolio_equity_curve else "N/A",
             end=f"{portfolio_equity_curve[-1]:,.0f}" if portfolio_equity_curve else "N/A",
             mid=f"{portfolio_equity_curve[len(portfolio_equity_curve)//2]:,.0f}"
                  if len(portfolio_equity_curve) > 2 else "N/A")

    # Сравнение с базовым бэктестом
    log.info(separator)
    log.info("VS BASELINE COMPARISON",
             baseline_return="-0.4%",
             enhanced_return=f"{total_return:+.2f}%",
             improvement=f"{total_return - (-0.4):+.2f}pp")


# ---------------------------------------------------------------------------
# Точка входа — с исправлением импорта z_score
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
