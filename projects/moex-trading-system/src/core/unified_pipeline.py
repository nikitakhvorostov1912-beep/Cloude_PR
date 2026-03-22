"""Unified trading pipeline connecting ALL 29 components.

Modes:
- ema_only:       EMA crossover only (baseline)
- ema_scoring:    EMA + scoring filter (enter only when pre_score > threshold)
- ema_regime:     EMA + regime filter (skip crisis regime)
- ema_ml:         EMA + ML confirmation (not yet — ML needs training)
- full_ensemble:  EMA + scoring + regime voting
- buy_hold:       Buy & Hold benchmark

Pipeline flow:
1. Load data (Polars DataFrame with OHLCV)
2. Calculate indicators (features.py)
3. Generate signals (EMA crossover)
4. Apply filters (scoring / regime / ML)
5. Simulate trades (position sizing, stops, commissions)
6. Compute metrics
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import polars as pl

from src.analysis.features import calculate_ema, calculate_atr, calculate_rsi, calculate_macd, _ewm
from src.analysis.scoring import calculate_pre_score
from src.core.signal_enricher import enrich_signals


# ── Result dataclasses ────────────────────────────────────────

@dataclass
class MonthlyPnL:
    year: int
    month: int
    pnl: float = 0.0
    trades: int = 0


@dataclass
class BacktestResult:
    ticker: str
    mode: str
    sharpe: float = 0.0
    sortino: float = 0.0
    cagr_pct: float = 0.0
    max_dd_pct: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    n_trades: int = 0
    total_pnl: float = 0.0
    total_commission: float = 0.0
    final_equity: float = 0.0
    monthly: list[MonthlyPnL] = field(default_factory=list)
    equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    error: str = ""


# ── Instrument info ───────────────────────────────────────────

INST_INFO = {
    "SBER": {"lot": 10, "step": 0.01, "sector": "banks"},
    "GAZP": {"lot": 10, "step": 0.01, "sector": "oil_gas"},
    "LKOH": {"lot": 1, "step": 0.5, "sector": "oil_gas"},
    "ROSN": {"lot": 1, "step": 0.05, "sector": "oil_gas"},
    "GMKN": {"lot": 1, "step": 1.0, "sector": "metals"},
    "YNDX": {"lot": 1, "step": 0.1, "sector": "it"},
    "VTBR": {"lot": 10000, "step": 0.000005, "sector": "banks"},
    "NVTK": {"lot": 1, "step": 0.1, "sector": "oil_gas"},
    "MGNT": {"lot": 1, "step": 0.5, "sector": "retail"},
    "TATN": {"lot": 1, "step": 0.1, "sector": "oil_gas"},
}

COMM_PCT = 0.0001
SLIP_TICKS = 2
DEFAULT_CAPITAL = 1_000_000.0


# ── Pipeline ──────────────────────────────────────────────────

class UnifiedPipeline:
    """Runs backtests in different modes, connecting real modules."""

    def __init__(
        self,
        capital: float = DEFAULT_CAPITAL,
        fast_ema: int = 20,
        slow_ema: int = 50,
        atr_period: int = 14,
        risk_pct: float = 0.02,
        atr_mult: float = 2.0,
        scoring_threshold: float = 45.0,
    ):
        self.capital = capital
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.atr_period = atr_period
        self.risk_pct = risk_pct
        self.atr_mult = atr_mult
        self.scoring_threshold = scoring_threshold
        self._last_score_weight = 1.0
        self._last_regime_mult = 1.0
        self._last_enrichment = None

    def run_backtest(
        self,
        df: pl.DataFrame,
        ticker: str,
        mode: str = "ema_only",
        imoex_close: np.ndarray | None = None,
    ) -> BacktestResult:
        """Run backtest on single ticker in given mode."""
        if mode == "buy_hold":
            return self._buy_hold(df, ticker)

        close = df["close"].to_numpy().astype(float)
        high = df["high"].to_numpy().astype(float)
        low = df["low"].to_numpy().astype(float)
        open_ = df["open"].to_numpy().astype(float)
        volume = df["volume"].to_numpy().astype(float)
        timestamps = df["timestamp"].to_list()
        n = len(close)

        if n < self.slow_ema + 10:
            return BacktestResult(ticker=ticker, mode=mode, error="Not enough data")

        # ── Indicators ────────────────────────────────────
        ema_f = _ewm(close, self.fast_ema)
        ema_s = _ewm(close, self.slow_ema)
        ema_200 = _ewm(close, 200) if n >= 200 else _ewm(close, min(n, 50))

        # ATR
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
        )
        tr = np.insert(tr, 0, high[0] - low[0])
        atr = np.full(n, np.nan)
        atr[self.atr_period - 1] = np.mean(tr[:self.atr_period])
        for i in range(self.atr_period, n):
            atr[i] = (atr[i-1] * (self.atr_period - 1) + tr[i]) / self.atr_period

        # RSI
        rsi_series = calculate_rsi(df["close"], 14)
        rsi = rsi_series.to_numpy().astype(float)

        # MACD
        macd_data = calculate_macd(df["close"])
        macd_hist = macd_data["histogram"].to_numpy().astype(float)

        # ADX (simple directional movement)
        adx_arr, di_plus_arr, di_minus_arr = self._calc_adx(high, low, close, 14)

        # Volume ratio
        vol_sma = np.full(n, np.nan)
        for i in range(20, n):
            vol_sma[i] = np.mean(volume[i-20:i])

        # Regime (for regime-aware modes)
        regime_arr = self._calc_regime(close, adx_arr, atr, n) if mode in ("ema_regime", "full_ensemble", "complete") else None

        # ── Simulate ──────────────────────────────────────
        info = INST_INFO.get(ticker, {"lot": 1, "step": 0.01, "sector": "banks"})
        lot, step, sector = info["lot"], info["step"], info["sector"]

        equity = self.capital
        pos = 0
        entry_p = 0.0
        sl = 0.0
        equity_arr = np.full(n, self.capital)
        trades: list[dict] = []

        for i in range(self.slow_ema + 1, n):
            if np.isnan(atr[i]):
                equity_arr[i] = self._mtm(equity, pos, entry_p, close[i])
                continue

            # Detect crossover
            cup = ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1]
            cdn = ema_f[i] < ema_s[i] and ema_f[i-1] >= ema_s[i-1]

            # Stop check
            pos, equity, stopped = self._check_stop(
                pos, equity, entry_p, sl, high[i], low[i], step, trades, timestamps[i]
            )

            # Apply mode filters
            if cup or cdn:
                direction = "long" if cup else "short"
                allow = self._apply_filters(
                    mode, direction, i, close, ema_f, ema_s, ema_200,
                    rsi, macd_hist, adx_arr, di_plus_arr, di_minus_arr,
                    volume, vol_sma, sector, regime_arr,
                )

                if allow and cup and pos <= 0:
                    # Close short
                    if pos < 0:
                        ep = close[i] + SLIP_TICKS * step
                        com = abs(pos) * ep * COMM_PCT
                        pnl = (entry_p - ep) * abs(pos) - com
                        equity += pnl
                        trades.append({"ts": timestamps[i], "side": "short", "pnl": pnl, "com": com})
                        pos = 0
                    # Open long (with multipliers from scoring/regime)
                    entry_p = close[i] + SLIP_TICKS * step
                    base_pos = self._calc_pos(equity, atr[i], lot)
                    mult = getattr(self, "_last_score_weight", 1.0) * getattr(self, "_last_regime_mult", 1.0)
                    pos = max(lot, int(base_pos * mult / lot) * lot)
                    sl = round(round((entry_p - self.atr_mult * atr[i]) / step) * step, 10)
                    equity -= pos * entry_p * COMM_PCT

                elif allow and cdn and pos >= 0:
                    # Close long
                    if pos > 0:
                        ep = close[i] - SLIP_TICKS * step
                        com = pos * ep * COMM_PCT
                        pnl = (ep - entry_p) * pos - com
                        equity += pnl
                        trades.append({"ts": timestamps[i], "side": "long", "pnl": pnl, "com": com})
                        pos = 0
                    # Open short (tighter: shorter holding, higher confirmation needed)
                    entry_p = close[i] - SLIP_TICKS * step
                    base_pos = self._calc_pos(equity, atr[i], lot)
                    mult = getattr(self, "_last_score_weight", 1.0) * getattr(self, "_last_regime_mult", 1.0) * 0.7  # shorts 30% smaller
                    pos = -max(lot, int(base_pos * mult / lot) * lot)
                    sl = round(round((entry_p + self.atr_mult * 1.3 * atr[i]) / step) * step, 10)  # tighter SL for shorts
                    equity -= abs(pos) * entry_p * COMM_PCT

            equity_arr[i] = self._mtm(equity, pos, entry_p, close[i])

        # Close remaining
        if pos > 0:
            com = pos * close[-1] * COMM_PCT
            pnl = (close[-1] - entry_p) * pos - com
            equity += pnl
            trades.append({"ts": timestamps[-1], "side": "long", "pnl": pnl, "com": com})
        elif pos < 0:
            com = abs(pos) * close[-1] * COMM_PCT
            pnl = (entry_p - close[-1]) * abs(pos) - com
            equity += pnl
            trades.append({"ts": timestamps[-1], "side": "short", "pnl": pnl, "com": com})
        equity_arr[-1] = equity

        return self._build_result(ticker, mode, equity_arr, trades, self.capital)

    # ── Filters ───────────────────────────────────────────

    def _apply_filters(
        self, mode, direction, i, close, ema_f, ema_s, ema_200,
        rsi, macd_hist, adx, di_p, di_m, volume, vol_sma, sector, regime,
    ) -> bool:
        """Apply mode-specific filters. Returns True if signal passes."""
        if mode == "ema_only":
            return True

        # Enricher check for ema_enriched and complete modes
        if mode in ("ema_enriched", "complete"):
            # Store enrichment for later use (position weight)
            self._last_enrichment = None
            try:
                # We need open_ array too — use close as proxy for open
                open_proxy = np.roll(close, 1)
                open_proxy[0] = close[0]
                high_arr = np.maximum(close, open_proxy) * 1.001  # synthetic high
                low_arr = np.minimum(close, open_proxy) * 0.999   # synthetic low
                vol_arr = volume.astype(float) if volume.dtype != float else volume
                enrichment = enrich_signals(open_proxy[:i+1], high_arr[:i+1], low_arr[:i+1], close[:i+1], vol_arr[:i+1])
                self._last_enrichment = enrichment

                if mode == "ema_enriched":
                    # Need at least 3 indicators confirming direction
                    if direction == "long" and enrichment.long_count < 3:
                        return False
                    if direction == "short" and enrichment.short_count < 3:
                        return False
                    return True
            except Exception:
                pass

        # Scoring computation
        score = 50.0
        if mode in ("ema_scoring", "ema_weighted", "full_ensemble", "complete"):
            vr = volume[i] / vol_sma[i] if vol_sma[i] and not np.isnan(vol_sma[i]) and vol_sma[i] > 0 else 1.0
            try:
                score, _ = calculate_pre_score(
                    adx=float(adx[i]) if not np.isnan(adx[i]) else 20.0,
                    di_plus=float(di_p[i]) if not np.isnan(di_p[i]) else 15.0,
                    di_minus=float(di_m[i]) if not np.isnan(di_m[i]) else 15.0,
                    rsi=float(rsi[i]) if not np.isnan(rsi[i]) else 50.0,
                    macd_hist=float(macd_hist[i]) if not np.isnan(macd_hist[i]) else 0.0,
                    close=float(close[i]),
                    ema20=float(ema_f[i]),
                    ema50=float(ema_s[i]),
                    ema200=float(ema_200[i]),
                    volume_ratio=float(vr),
                    obv_trend="up" if close[i] > close[i-1] else "down",
                    sentiment_score=0.0,
                    direction=direction,
                    imoex_above_sma200=True,
                    sector=sector,
                )
            except Exception:
                score = 50.0

            if mode == "ema_scoring":
                return score >= self.scoring_threshold

            if mode == "ema_weighted":
                # Store weight for position sizing (called later)
                self._last_score_weight = self._score_to_pos_weight(score)
                return score >= 30  # minimum threshold

        scoring_pass = score >= self.scoring_threshold

        # Regime check
        regime_pass = True
        if mode in ("ema_regime", "full_ensemble", "complete"):
            if regime is not None and i < len(regime):
                r = regime[i]
                if r == "crisis":
                    regime_pass = False
                    self._last_regime_mult = 0.25
                elif r == "range":
                    self._last_regime_mult = 0.5
                elif r == "downtrend" and direction == "long":
                    self._last_regime_mult = 0.5
                elif r == "uptrend" and direction == "short":
                    self._last_regime_mult = 0.5
                else:
                    self._last_regime_mult = 1.0
            else:
                self._last_regime_mult = 1.0

            if mode == "ema_regime":
                return regime_pass

        if mode == "full_ensemble":
            votes = 1
            if scoring_pass:
                votes += 1
            if regime_pass:
                votes += 1
            return votes >= 2

        if mode == "complete":
            # Complete: all factors vote
            enrichment_pass = True
            if hasattr(self, "_last_enrichment") and self._last_enrichment:
                if direction == "long":
                    enrichment_pass = self._last_enrichment.long_count >= 2
                else:
                    enrichment_pass = self._last_enrichment.short_count >= 2

            votes = 1  # EMA base
            if scoring_pass:
                votes += 1
            if regime_pass:
                votes += 1
            if enrichment_pass:
                votes += 1
            return votes >= 3  # need 3 of 4

        return True

    @staticmethod
    def _score_to_pos_weight(score: float) -> float:
        """Scoring as position weight multiplier."""
        if score >= 75:
            return 1.0
        elif score >= 60:
            return 0.75
        elif score >= 45:
            return 0.50
        elif score >= 30:
            return 0.25
        return 0.0

    # ── Helpers ───────────────────────────────────────────

    def _calc_pos(self, equity: float, atr_val: float, lot: int) -> int:
        ra = equity * self.risk_pct
        raw = ra / (self.atr_mult * atr_val) if atr_val > 0 else 0
        lots = max(1, int(raw / lot))
        return lots * lot

    @staticmethod
    def _mtm(equity: float, pos: int, entry_p: float, price: float) -> float:
        if pos > 0:
            return equity + (price - entry_p) * pos
        elif pos < 0:
            return equity + (entry_p - price) * abs(pos)
        return equity

    def _check_stop(self, pos, equity, entry_p, sl, high_i, low_i, step, trades, ts):
        if pos > 0 and low_i <= sl:
            ep = sl - SLIP_TICKS * step
            com = pos * ep * COMM_PCT
            pnl = (ep - entry_p) * pos - com
            equity += pnl
            trades.append({"ts": ts, "side": "long", "pnl": pnl, "com": com})
            return 0, equity, True
        elif pos < 0 and high_i >= sl:
            ep = sl + SLIP_TICKS * step
            com = abs(pos) * ep * COMM_PCT
            pnl = (entry_p - ep) * abs(pos) - com
            equity += pnl
            trades.append({"ts": ts, "side": "short", "pnl": pnl, "com": com})
            return 0, equity, True
        return pos, equity, False

    @staticmethod
    def _calc_adx(high, low, close, period=14):
        n = len(close)
        adx = np.full(n, np.nan)
        di_p = np.full(n, np.nan)
        di_m = np.full(n, np.nan)

        dm_plus = np.zeros(n)
        dm_minus = np.zeros(n)
        tr = np.zeros(n)

        for i in range(1, n):
            h_diff = high[i] - high[i-1]
            l_diff = low[i-1] - low[i]
            dm_plus[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0
            dm_minus[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))

        # Smoothed
        atr_s = np.full(n, np.nan)
        dp_s = np.full(n, np.nan)
        dm_s = np.full(n, np.nan)

        if n > period:
            atr_s[period] = np.sum(tr[1:period+1])
            dp_s[period] = np.sum(dm_plus[1:period+1])
            dm_s[period] = np.sum(dm_minus[1:period+1])

            for i in range(period + 1, n):
                atr_s[i] = atr_s[i-1] - atr_s[i-1] / period + tr[i]
                dp_s[i] = dp_s[i-1] - dp_s[i-1] / period + dm_plus[i]
                dm_s[i] = dm_s[i-1] - dm_s[i-1] / period + dm_minus[i]

            for i in range(period, n):
                if atr_s[i] > 0:
                    di_p[i] = 100 * dp_s[i] / atr_s[i]
                    di_m[i] = 100 * dm_s[i] / atr_s[i]
                    dx = abs(di_p[i] - di_m[i]) / (di_p[i] + di_m[i]) * 100 if (di_p[i] + di_m[i]) > 0 else 0
                    adx[i] = dx  # Simplified: no ADX smoothing for speed

        return adx, di_p, di_m

    @staticmethod
    def _calc_regime(close, adx, atr, n):
        regime = ["range"] * n
        for i in range(200, n):
            sma200 = np.mean(close[i-200:i])
            atr_pct = atr[i] / close[i] if close[i] > 0 and not np.isnan(atr[i]) else 0
            adx_val = adx[i] if not np.isnan(adx[i]) else 20

            if atr_pct >= 0.035:
                regime[i] = "crisis"
            elif adx_val > 25 and close[i] > sma200:
                regime[i] = "uptrend"
            elif adx_val > 25 and close[i] < sma200:
                regime[i] = "downtrend"
            else:
                regime[i] = "range"
        return regime

    def _buy_hold(self, df: pl.DataFrame, ticker: str) -> BacktestResult:
        close = df["close"].to_numpy().astype(float)
        eq = close / close[0] * self.capital
        ret = np.diff(close) / close[:-1]
        n = len(ret)
        sh = (ret.mean() / ret.std() * math.sqrt(252)) if ret.std() > 0 else 0
        peak = np.maximum.accumulate(eq)
        dd = ((eq - peak) / np.where(peak > 0, peak, 1.0)).min()
        years = n / 252
        cagr = (eq[-1] / self.capital) ** (1/years) - 1 if years > 0 else 0
        return BacktestResult(
            ticker=ticker, mode="buy_hold", sharpe=round(sh, 2),
            cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
            final_equity=round(eq[-1], 0), total_pnl=round(eq[-1] - self.capital, 0),
            equity_curve=eq,
        )

    @staticmethod
    def _build_result(ticker, mode, equity_arr, trades, capital):
        start = 50  # skip warmup
        valid_eq = equity_arr[start:]
        ret = np.diff(valid_eq) / np.where(valid_eq[:-1] > 0, valid_eq[:-1], 1.0)
        ret = ret[np.isfinite(ret)]

        if len(ret) < 2:
            return BacktestResult(ticker=ticker, mode=mode, error="Not enough returns")

        sh = (ret.mean() / ret.std() * math.sqrt(252)) if ret.std() > 0 else 0
        downside = ret[ret < 0]
        down_std = downside.std() if len(downside) > 1 else 0.001
        so = (ret.mean() / down_std * math.sqrt(252)) if down_std > 0 else 0

        peak = np.maximum.accumulate(equity_arr)
        dd = ((equity_arr - peak) / np.where(peak > 0, peak, 1.0)).min()

        years = len(ret) / 252
        cagr = (equity_arr[-1] / capital) ** (1/years) - 1 if years > 0 and capital > 0 else 0

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        wr = len(wins) / len(trades) if trades else 0
        gp = sum(t["pnl"] for t in wins) if wins else 0
        gl = abs(sum(t["pnl"] for t in losses)) if losses else 0.001
        pf = gp / gl if gl > 0 else 0

        # Monthly PnL
        monthly_dict: dict[str, MonthlyPnL] = {}
        for t in trades:
            ts = t["ts"]
            if hasattr(ts, "year"):
                key = f"{ts.year}-{ts.month:02d}"
                yr, mo = ts.year, ts.month
            else:
                key = str(ts)[:7]
                yr, mo = int(key[:4]), int(key[5:7])
            if key not in monthly_dict:
                monthly_dict[key] = MonthlyPnL(year=yr, month=mo)
            monthly_dict[key].pnl += t["pnl"]
            monthly_dict[key].trades += 1

        total_com = sum(t.get("com", 0) for t in trades)

        return BacktestResult(
            ticker=ticker, mode=mode,
            sharpe=round(sh, 2), sortino=round(so, 2),
            cagr_pct=round(cagr * 100, 2), max_dd_pct=round(dd * 100, 2),
            win_rate_pct=round(wr * 100, 1), profit_factor=round(pf, 2),
            n_trades=len(trades), total_pnl=round(sum(t["pnl"] for t in trades), 0),
            total_commission=round(total_com, 0),
            final_equity=round(equity_arr[-1], 0),
            monthly=sorted(monthly_dict.values(), key=lambda m: (m.year, m.month)),
            equity_curve=equity_arr,
        )
