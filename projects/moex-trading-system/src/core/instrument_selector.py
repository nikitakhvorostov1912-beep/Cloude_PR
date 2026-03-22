"""Intelligent instrument selection — ranks ALL instruments by composite score.

Combines 6 factors to select TOP-N for long and TOP-M for short.
Applies sector correlation filter to avoid concentration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
import structlog

from src.analysis.features import calculate_ema, calculate_atr, calculate_rsi, calculate_macd, _ewm
from src.analysis.scoring import calculate_pre_score
from src.core.signal_enricher import enrich_signals
from src.data.market_scanner import SECTOR_MAP

logger = structlog.get_logger(__name__)


@dataclass
class SelectionEntry:
    """One instrument's selection data."""
    ticker: str
    sector: str
    composite_score: float = 50.0
    technical_score: float = 50.0
    scoring_score: float = 50.0
    ml_score: float = 50.0
    news_score: float = 50.0
    liquidity_score: float = 50.0
    momentum_score: float = 50.0
    direction: str = "neutral"  # long/short/neutral
    position_weight: float = 0.0  # 0-1
    reason: str = ""


@dataclass
class SelectionResult:
    """Output of instrument selector."""
    longs: list[SelectionEntry] = field(default_factory=list)
    shorts: list[SelectionEntry] = field(default_factory=list)
    skipped: list[SelectionEntry] = field(default_factory=list)
    all_ranked: list[SelectionEntry] = field(default_factory=list)


# Default weights
DEFAULT_WEIGHTS = {
    "technical": 0.25,
    "scoring": 0.20,
    "ml_prediction": 0.25,
    "news_sentiment": 0.15,
    "liquidity": 0.10,
    "momentum_rank": 0.05,
}


class InstrumentSelector:
    """Selects best instruments for long and short from universe."""

    def __init__(
        self,
        max_long: int = 10,
        max_short: int = 5,
        max_sector_pct: float = 0.30,
        max_correlation: float = 0.70,
        long_threshold: float = 60.0,
        short_threshold: float = 40.0,
        weights: dict[str, float] | None = None,
    ):
        self.max_long = max_long
        self.max_short = max_short
        self.max_sector_pct = max_sector_pct
        self.max_correlation = max_correlation
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.weights = weights or DEFAULT_WEIGHTS

    def select(
        self,
        data: dict[str, pl.DataFrame],
        news_scores: dict[str, float] | None = None,
        ml_scores: dict[str, float] | None = None,
    ) -> SelectionResult:
        """Rank all instruments and select best for trading.

        Args:
            data: ticker -> DataFrame with OHLCV
            news_scores: ticker -> sentiment (-1 to +1), from MiMo
            ml_scores: ticker -> prediction (0 to 1), from ML ensemble
        """
        news = news_scores or {}
        ml = ml_scores or {}
        entries: list[SelectionEntry] = []

        for ticker, df in data.items():
            if ticker == "IMOEX" or df.height < 60:
                continue

            try:
                entry = self._score_instrument(ticker, df, news.get(ticker, 0.0), ml.get(ticker, 0.5))
                entries.append(entry)
            except Exception as e:
                logger.debug("scoring_failed", ticker=ticker, error=str(e))

        # Rank by composite score
        entries.sort(key=lambda e: e.composite_score, reverse=True)

        # Select longs (high score) and shorts (low score)
        longs = []
        shorts = []
        skipped = []

        sector_count_long: dict[str, int] = {}
        sector_count_short: dict[str, int] = {}

        for entry in entries:
            if entry.composite_score >= self.long_threshold and len(longs) < self.max_long:
                # Check sector limit
                sc = sector_count_long.get(entry.sector, 0)
                max_per_sector = max(1, int(self.max_long * self.max_sector_pct))
                if sc >= max_per_sector:
                    entry.reason = f"sector_limit ({entry.sector}={sc})"
                    skipped.append(entry)
                    continue
                entry.direction = "long"
                entry.position_weight = self._score_to_weight(entry.composite_score, "long")
                longs.append(entry)
                sector_count_long[entry.sector] = sc + 1

        # Shorts from bottom
        for entry in reversed(entries):
            if entry.composite_score <= self.short_threshold and len(shorts) < self.max_short:
                sc = sector_count_short.get(entry.sector, 0)
                max_per_sector = max(1, int(self.max_short * self.max_sector_pct))
                if sc >= max_per_sector:
                    entry.reason = f"sector_limit ({entry.sector}={sc})"
                    skipped.append(entry)
                    continue
                entry.direction = "short"
                entry.position_weight = self._score_to_weight(entry.composite_score, "short")
                shorts.append(entry)
                sector_count_short[entry.sector] = sc + 1

        return SelectionResult(
            longs=longs, shorts=shorts, skipped=skipped, all_ranked=entries,
        )

    def _score_instrument(
        self, ticker: str, df: pl.DataFrame,
        news_sentiment: float, ml_prediction: float,
    ) -> SelectionEntry:
        """Compute composite score for one instrument."""
        close = df["close"].to_numpy().astype(float)
        high = df["high"].to_numpy().astype(float)
        low = df["low"].to_numpy().astype(float)
        open_ = df["open"].to_numpy().astype(float)
        volume = df["volume"].to_numpy().astype(float)
        sector = SECTOR_MAP.get(ticker, "other")

        # 1. Technical score from enricher (0-100)
        enrichment = enrich_signals(open_, high, low, close, volume)
        technical = enrichment.confirmation_score * 100  # 0-100

        # 2. Scoring score
        try:
            ema20 = _ewm(close, 20)
            ema50 = _ewm(close, 50)
            ema200 = _ewm(close, min(200, len(close) - 1))
            rsi_arr = calculate_rsi(df["close"], 14).to_numpy()
            macd_data = calculate_macd(df["close"])
            macd_hist = macd_data["histogram"].to_numpy()

            # Simple ADX approximation
            adx_val = 25.0  # default
            di_p, di_m = 15.0, 15.0

            vol_avg = np.mean(volume[-20:]) if len(volume) >= 20 else 1.0
            vr = volume[-1] / vol_avg if vol_avg > 0 else 1.0

            score_val, _ = calculate_pre_score(
                adx=adx_val, di_plus=di_p, di_minus=di_m,
                rsi=float(rsi_arr[-1]), macd_hist=float(macd_hist[-1]),
                close=float(close[-1]), ema20=float(ema20[-1]),
                ema50=float(ema50[-1]), ema200=float(ema200[-1]),
                volume_ratio=float(vr), obv_trend="up" if close[-1] > close[-2] else "down",
                sentiment_score=news_sentiment,
                direction="long",
                imoex_above_sma200=True,
                sector=sector,
            )
            scoring = float(score_val)
        except Exception:
            scoring = 50.0

        # 3. ML score (0-100)
        ml_100 = ml_prediction * 100

        # 4. News score (0-100, mapped from -1..+1)
        news_100 = (news_sentiment + 1) * 50  # -1->0, 0->50, +1->100

        # 5. Liquidity score
        avg_vol = np.mean(volume[-20:]) * close[-1] if len(volume) >= 20 else 0
        if avg_vol > 1e9:
            liquidity = 100
        elif avg_vol > 100e6:
            liquidity = 75
        elif avg_vol > 10e6:
            liquidity = 50
        else:
            liquidity = 25

        # 6. Momentum rank (relative return last 20 days)
        if len(close) >= 20:
            ret_20d = (close[-1] / close[-20] - 1) * 100
            momentum = max(0, min(100, 50 + ret_20d * 5))  # scale to 0-100
        else:
            momentum = 50

        # Composite
        w = self.weights
        composite = (
            technical * w.get("technical", 0.25)
            + scoring * w.get("scoring", 0.20)
            + ml_100 * w.get("ml_prediction", 0.25)
            + news_100 * w.get("news_sentiment", 0.15)
            + liquidity * w.get("liquidity", 0.10)
            + momentum * w.get("momentum_rank", 0.05)
        )

        return SelectionEntry(
            ticker=ticker, sector=sector,
            composite_score=round(composite, 1),
            technical_score=round(technical, 1),
            scoring_score=round(scoring, 1),
            ml_score=round(ml_100, 1),
            news_score=round(news_100, 1),
            liquidity_score=round(liquidity, 1),
            momentum_score=round(momentum, 1),
        )

    @staticmethod
    def _score_to_weight(score: float, direction: str) -> float:
        """Convert composite score to position weight (0-1)."""
        if direction == "long":
            if score >= 75:
                return 1.0
            elif score >= 65:
                return 0.75
            elif score >= 55:
                return 0.5
            elif score >= 45:
                return 0.25
            return 0.0
        else:  # short
            if score <= 20:
                return 1.0
            elif score <= 30:
                return 0.75
            elif score <= 35:
                return 0.5
            elif score <= 40:
                return 0.25
            return 0.0
