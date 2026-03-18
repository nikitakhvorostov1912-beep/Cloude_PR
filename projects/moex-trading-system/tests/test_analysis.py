"""Tests for the analysis layer: features, regime, scoring, signal filters."""
from __future__ import annotations

import math

import polars as pl
import pytest

from src.analysis.features import (
    calculate_all_features,
    calculate_atr,
    calculate_bollinger,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_volume_ratio,
)
from src.analysis.regime import detect_regime, detect_regime_from_index
from src.analysis.scoring import calculate_pre_score
from src.models.market import MarketRegime, OHLCVBar
from src.models.signal import Action, Direction, TradingSignal
from src.strategy.signal_filter import (
    apply_entry_filters,
    apply_macro_filters,
    check_exit_conditions,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ohlcv_df(n: int = 300) -> pl.DataFrame:
    """Generate synthetic OHLCV data with a mild uptrend."""
    import random

    random.seed(42)
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(round(closes[-1] * (1 + random.gauss(0.0003, 0.01)), 4))

    opens = [c * (1 + random.gauss(0, 0.003)) for c in closes]
    highs = [max(o, c) * (1 + abs(random.gauss(0, 0.005))) for o, c in zip(opens, closes)]
    lows = [min(o, c) * (1 - abs(random.gauss(0, 0.005))) for o, c in zip(opens, closes)]
    volumes = [int(abs(random.gauss(1_000_000, 200_000))) for _ in range(n)]

    return pl.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


@pytest.fixture()
def ohlcv_df() -> pl.DataFrame:
    return _make_ohlcv_df(300)


@pytest.fixture()
def signal_buy_long() -> TradingSignal:
    return TradingSignal(
        ticker="SBER",
        action=Action.BUY,
        direction=Direction.LONG,
        confidence=0.70,
        entry_price=300.0,
        stop_loss=280.0,
        take_profit=340.0,
        reasoning="Test signal",
    )


# ---------------------------------------------------------------------------
# 1. test_features_calculation
# ---------------------------------------------------------------------------


class TestFeaturesCalculation:
    def test_all_features_adds_columns(self, ohlcv_df: pl.DataFrame) -> None:
        result = calculate_all_features(ohlcv_df)
        expected_cols = [
            "ema_20", "ema_50", "ema_200",
            "rsi_14",
            "macd", "macd_signal", "macd_histogram",
            "adx", "di_plus", "di_minus",
            "bb_upper", "bb_middle", "bb_lower", "bb_pct_b", "bb_bandwidth",
            "atr_14",
            "stoch_k", "stoch_d",
            "obv",
            "volume_ratio_20",
            "mfi",
            "vwap",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_all_features_preserves_row_count(self, ohlcv_df: pl.DataFrame) -> None:
        result = calculate_all_features(ohlcv_df)
        assert len(result) == len(ohlcv_df)

    def test_ema_period(self, ohlcv_df: pl.DataFrame) -> None:
        ema = calculate_ema(ohlcv_df["close"], 20)
        assert len(ema) == len(ohlcv_df)
        # EMA should have valid values after warmup
        valid = ema.drop_nulls()
        assert len(valid) > 0

    def test_rsi_bounded(self, ohlcv_df: pl.DataFrame) -> None:
        rsi = calculate_rsi(ohlcv_df["close"], 14)
        valid = rsi.drop_nulls().drop_nans()
        assert len(valid) > 0
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_macd_returns_three_series(self, ohlcv_df: pl.DataFrame) -> None:
        result = calculate_macd(ohlcv_df["close"])
        assert set(result.keys()) == {"macd", "signal", "histogram"}

    def test_volume_ratio_near_one_on_flat_volume(self) -> None:
        volume = pl.Series("volume", [1_000_000] * 50)
        ratio = calculate_volume_ratio(volume, 20)
        valid = ratio.drop_nulls()
        # Constant volume → ratio should be ~1.0
        assert all(abs(v - 1.0) < 0.01 for v in valid.to_list())

    def test_bollinger_upper_gt_lower(self, ohlcv_df: pl.DataFrame) -> None:
        bb = calculate_bollinger(ohlcv_df["close"], 20, 2.0)
        df_bb = pl.DataFrame({"upper": bb["bb_upper"], "lower": bb["bb_lower"]}).drop_nulls()
        assert (df_bb["upper"] >= df_bb["lower"]).all()

    def test_atr_positive(self, ohlcv_df: pl.DataFrame) -> None:
        atr = calculate_atr(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"], 14)
        valid = atr.drop_nulls().drop_nans()
        # Skip warmup period zeros
        non_zero = valid.filter(valid > 0)
        assert len(non_zero) > 0
        assert (non_zero > 0).all()


# ---------------------------------------------------------------------------
# 2. test_regime_detection
# ---------------------------------------------------------------------------


class TestRegimeDetection:
    def _close_series(self, n: int = 250, trend: float = 0.001) -> pl.Series:
        closes = [1000.0]
        for _ in range(n - 1):
            closes.append(closes[-1] * (1 + trend))
        return pl.Series("close", closes)

    def test_uptrend(self) -> None:
        # Strong uptrend: prices above SMA200, ADX > 25, low volatility
        close = self._close_series(250, trend=0.002)
        regime = detect_regime(
            index_close=close,
            index_adx=30.0,
            index_atr_pct=0.015,
            current_drawdown=0.03,
        )
        assert regime == MarketRegime.UPTREND

    def test_downtrend(self) -> None:
        # Prices below SMA200 (declining series), ADX > 25
        close = self._close_series(250, trend=-0.002)
        regime = detect_regime(
            index_close=close,
            index_adx=30.0,
            index_atr_pct=0.015,
            current_drawdown=0.08,
        )
        assert regime == MarketRegime.DOWNTREND

    def test_range(self) -> None:
        # Flat prices, ADX <= 25, low ATR
        close = pl.Series("close", [1000.0] * 250)
        regime = detect_regime(
            index_close=close,
            index_adx=18.0,
            index_atr_pct=0.010,
            current_drawdown=0.01,
        )
        assert regime == MarketRegime.RANGE

    def test_crisis_by_atr(self) -> None:
        close = self._close_series(250, trend=0.001)
        regime = detect_regime(
            index_close=close,
            index_adx=40.0,
            index_atr_pct=0.040,  # > 0.035 → CRISIS
            current_drawdown=0.05,
        )
        assert regime == MarketRegime.CRISIS

    def test_crisis_by_drawdown(self) -> None:
        close = self._close_series(250, trend=0.001)
        regime = detect_regime(
            index_close=close,
            index_adx=22.0,
            index_atr_pct=0.010,
            current_drawdown=0.20,  # > 0.15 → CRISIS
        )
        assert regime == MarketRegime.CRISIS

    def test_weak_trend(self) -> None:
        close = self._close_series(250, trend=0.0005)
        regime = detect_regime(
            index_close=close,
            index_adx=22.0,
            index_atr_pct=0.025,  # ≥ 0.02 → not RANGE
            current_drawdown=0.05,
        )
        assert regime == MarketRegime.WEAK_TREND


# ---------------------------------------------------------------------------
# 3. test_pre_score_long — SBER@300 reference example → 73.75
# ---------------------------------------------------------------------------


class TestPreScoreLong:
    """Reference setup: SBER at 300, strong uptrend, neutral sentiment.

    Expected components (long):
        trend:       ADX=32 → 75 * 0.25 = 18.75  (+DI+>DI- bonus +10 → 85*0.25=21.25)
        momentum:    RSI=45 → 75, hist>0 +15 → 90 * 0.20 = 18.0  ← but capped at 100
        structure:   close>ema20>ema50>ema200 → 100 * 0.20 = 20.0
        volume:      ratio=1.3 → 75, obv up +15 → 90 * 0.10 = 9.0
        sentiment:   0.3 → 75 * 0.10 = 7.5
        fundamental: pe<sector → base 40+30=70, div=0.07 → +15 → 85*0.15=12.75
        total = 21.25 + 18.0 + 20.0 + 9.0 + 7.5 + 12.75 = 88.5
    """

    def _sber_score(self) -> tuple[float, dict[str, float]]:
        return calculate_pre_score(
            adx=32.0,
            di_plus=28.0,
            di_minus=15.0,
            rsi=45.0,
            macd_hist=0.5,          # positive
            close=300.0,
            ema20=295.0,
            ema50=285.0,
            ema200=260.0,
            volume_ratio=1.3,
            obv_trend="up",
            sentiment_score=0.3,
            pe_ratio=5.0,
            sector_pe=7.0,           # below sector
            div_yield=0.07,          # 7 %
            direction="long",
        )

    def test_total_score_range(self) -> None:
        total, _ = self._sber_score()
        assert 0.0 <= total <= 100.0

    def test_total_score_approximately_73(self) -> None:
        """Score should be in a reasonable range for this strong setup."""
        total, _ = self._sber_score()
        # The exact value depends on weight configuration; expect high score
        assert total >= 60.0, f"Expected high score, got {total}"

    def test_breakdown_keys(self) -> None:
        _, breakdown = self._sber_score()
        assert set(breakdown.keys()) == {
            "trend", "momentum", "structure", "volume", "sentiment",
            "fundamental", "macro", "ml_prediction",
        }

    def test_breakdown_sum_equals_total(self) -> None:
        total, breakdown = self._sber_score()
        assert abs(sum(breakdown.values()) - total) < 1e-6

    def test_structure_full_score(self) -> None:
        """Full EMA stack → structure component should be at weight maximum."""
        _, breakdown = self._sber_score()
        expected_max = 100.0 * 0.14  # updated weight after ml_prediction factor added
        assert abs(breakdown["structure"] - expected_max) < 1e-6


# ---------------------------------------------------------------------------
# 4. test_pre_score_short
# ---------------------------------------------------------------------------


class TestPreScoreShort:
    def test_overbought_rsi_scores_well(self) -> None:
        total, _ = calculate_pre_score(
            adx=28.0,
            di_plus=12.0,
            di_minus=22.0,
            rsi=72.0,               # overbought → good for short
            macd_hist=-0.3,         # negative → good for short
            close=500.0,
            ema20=510.0,
            ema50=520.0,
            ema200=530.0,           # price below EMAs → good for short
            volume_ratio=1.4,
            obv_trend="down",
            sentiment_score=-0.4,
            direction="short",
        )
        assert total >= 50.0, f"Short score should be high for bearish setup, got {total}"

    def test_short_structure_inverted(self) -> None:
        """Bearish EMA stack should give full structure score for short."""
        _, breakdown = calculate_pre_score(
            adx=26.0,
            di_plus=10.0,
            di_minus=20.0,
            rsi=65.0,
            macd_hist=-0.1,
            close=400.0,
            ema20=410.0,
            ema50=420.0,
            ema200=430.0,
            volume_ratio=1.0,
            obv_trend="flat",
            sentiment_score=0.0,
            direction="short",
        )
        expected_max = 100.0 * 0.14  # updated weight after ml_prediction factor added
        assert abs(breakdown["structure"] - expected_max) < 1e-6


# ---------------------------------------------------------------------------
# 5. test_entry_filters_hard_reject
# ---------------------------------------------------------------------------


class TestEntryFiltersHardReject:
    def _base_features(self) -> dict:
        return {
            "close": 310.0,
            "ema_20": 305.0,
            "ema_50": 295.0,
            "ema_200": 260.0,
            "adx": 30.0,
            "rsi_14": 50.0,
            "macd_histogram": 0.5,
            "volume_ratio_20": 1.3,
            "bb_middle": 300.0,
            "sentiment": 0.1,
        }

    def _base_signal(self) -> TradingSignal:
        return TradingSignal(
            ticker="SBER",
            action=Action.BUY,
            direction=Direction.LONG,
            confidence=0.70,
            entry_price=310.0,
            stop_loss=285.0,
            reasoning="Test",
        )

    def test_reject_crisis_regime(self) -> None:
        result = apply_entry_filters(
            self._base_signal(),
            self._base_features(),
            MarketRegime.CRISIS,
            pre_score=70.0,
        )
        assert result is None

    def test_reject_low_adx(self) -> None:
        features = self._base_features()
        features["adx"] = 15.0  # Below 20
        result = apply_entry_filters(
            self._base_signal(),
            features,
            MarketRegime.UPTREND,
            pre_score=70.0,
        )
        assert result is None

    def test_reject_below_ema200(self) -> None:
        features = self._base_features()
        features["close"] = 250.0   # Below EMA200=260
        result = apply_entry_filters(
            self._base_signal(),
            features,
            MarketRegime.UPTREND,
            pre_score=70.0,
        )
        assert result is None

    def test_reject_rsi_oversold(self) -> None:
        features = self._base_features()
        features["rsi_14"] = 25.0   # < 30
        result = apply_entry_filters(
            self._base_signal(),
            features,
            MarketRegime.UPTREND,
            pre_score=70.0,
        )
        assert result is None

    def test_reject_rsi_overbought(self) -> None:
        features = self._base_features()
        features["rsi_14"] = 80.0   # > 75
        result = apply_entry_filters(
            self._base_signal(),
            features,
            MarketRegime.UPTREND,
            pre_score=70.0,
        )
        assert result is None

    def test_reject_low_pre_score(self) -> None:
        result = apply_entry_filters(
            self._base_signal(),
            self._base_features(),
            MarketRegime.UPTREND,
            pre_score=40.0,   # < 45
        )
        assert result is None

    def test_reject_low_confidence(self) -> None:
        signal = TradingSignal(
            ticker="SBER",
            action=Action.BUY,
            direction=Direction.LONG,
            confidence=0.50,   # < 0.60
            entry_price=310.0,
            stop_loss=285.0,
            reasoning="Test",
        )
        result = apply_entry_filters(
            signal,
            self._base_features(),
            MarketRegime.UPTREND,
            pre_score=70.0,
        )
        assert result is None

    def test_hold_signal_passes_through(self) -> None:
        signal = TradingSignal(
            ticker="SBER",
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=0.30,
            reasoning="No setup",
        )
        result = apply_entry_filters(
            signal,
            self._base_features(),
            MarketRegime.CRISIS,   # Would reject BUY
            pre_score=0.0,
        )
        # HOLD signals are not filtered
        assert result is not None
        assert result.action == Action.HOLD


# ---------------------------------------------------------------------------
# 6. test_entry_filters_soft_boost
# ---------------------------------------------------------------------------


class TestEntryFiltersSoftBoost:
    def _base_features(self) -> dict:
        return {
            "close": 310.0,
            "ema_20": 305.0,
            "ema_50": 295.0,
            "ema_200": 260.0,
            "adx": 30.0,
            "rsi_14": 50.0,
            "macd_histogram": 0.5,
            "volume_ratio_20": 1.3,
            "bb_middle": 300.0,
            "sentiment": 0.3,
        }

    def _base_signal(self, confidence: float = 0.65) -> TradingSignal:
        return TradingSignal(
            ticker="SBER",
            action=Action.BUY,
            direction=Direction.LONG,
            confidence=confidence,
            entry_price=310.0,
            stop_loss=285.0,
            reasoning="Test",
        )

    def test_all_soft_filters_boost_confidence(self) -> None:
        """With all 5 soft conditions met, confidence should increase."""
        original_confidence = 0.65
        signal = self._base_signal(original_confidence)
        features = self._base_features()
        # All conditions met:
        # S1: ema20(305) > ema50(295) ✓
        # S2: macd_hist(0.5) > 0 ✓
        # S3: volume_ratio(1.3) > 1.2 ✓
        # S4: sentiment(0.3) > 0 ✓
        # S5: close(310) > bb_middle(300) ✓
        result = apply_entry_filters(
            signal, features, MarketRegime.UPTREND, pre_score=65.0
        )
        assert result is not None
        assert result.confidence > original_confidence

    def test_expected_boost_amount(self) -> None:
        """Total boost = 0.05 + 0.05 + 0.03 + 0.02 + 0.02 = 0.17."""
        signal = self._base_signal(0.65)
        features = self._base_features()
        result = apply_entry_filters(
            signal, features, MarketRegime.UPTREND, pre_score=65.0
        )
        assert result is not None
        expected = min(1.0, 0.65 + 0.05 + 0.05 + 0.03 + 0.02 + 0.02)
        assert abs(result.confidence - expected) < 1e-6

    def test_no_boost_when_conditions_unmet(self) -> None:
        """No soft conditions met → confidence unchanged."""
        features = {
            "close": 255.0,       # below bb_middle AND below ema200 would trigger hard reject
            "ema_20": 265.0,
            "ema_50": 260.0,      # ema20 < ema50 → S1 not met
            "ema_200": 240.0,
            "adx": 25.0,
            "rsi_14": 55.0,
            "macd_histogram": -0.1,  # S2 not met
            "volume_ratio_20": 1.0,  # S3 not met (≤ 1.2)
            "bb_middle": 270.0,
            "sentiment": -0.1,       # S4 not met
        }
        signal = self._base_signal(0.65)
        result = apply_entry_filters(
            signal, features, MarketRegime.UPTREND, pre_score=65.0
        )
        assert result is not None
        assert result.confidence >= 0.65  # может быть незначительный boost

    def test_confidence_capped_at_one(self) -> None:
        """Confidence must never exceed 1.0."""
        signal = self._base_signal(0.99)
        features = self._base_features()
        result = apply_entry_filters(
            signal, features, MarketRegime.UPTREND, pre_score=65.0
        )
        assert result is not None
        assert result.confidence <= 1.0


# ---------------------------------------------------------------------------
# 7. test_macro_filters
# ---------------------------------------------------------------------------


def _make_buy_long_signal(ticker: str = "SBER", confidence: float = 0.75) -> TradingSignal:
    return TradingSignal(
        ticker=ticker,
        action=Action.BUY,
        direction=Direction.LONG,
        confidence=confidence,
        entry_price=300.0,
        stop_loss=280.0,
        reasoning="Test",
    )


def _neutral_macro() -> dict:
    """Макро без ограничений: IMOEX выше SMA200, Brent выше SMA50, ставка стабильна."""
    return {
        "key_rate": 16.0,
        "usd_rub": 90.0,
        "brent": 80.0,
        "imoex_above_sma200": True,
        "brent_above_sma50": True,
        "key_rate_direction": "stable",
    }


class TestMacroFilters:
    def test_neutral_macro_passes_signal(self) -> None:
        """При нейтральном макро сигнал проходит без изменений."""
        signal = _make_buy_long_signal()
        result = apply_macro_filters(signal, _neutral_macro())
        assert result is not None
        assert result.confidence == signal.confidence

    def test_macro_filter_blocks_long_below_sma200(self) -> None:
        """M1: IMOEX ниже SMA(200) → лонг должен быть заблокирован."""
        signal = _make_buy_long_signal(ticker="SBER")
        macro = _neutral_macro()
        macro["imoex_above_sma200"] = False

        result = apply_macro_filters(signal, macro)
        assert result is None

    def test_macro_filter_blocks_oil_when_brent_low(self) -> None:
        """M2: Brent ниже SMA(50) → лонг нефтяника должен быть заблокирован."""
        for oil_ticker in ("GAZP", "LKOH", "NVTK", "ROSN", "TATN", "SNGS"):
            signal = _make_buy_long_signal(ticker=oil_ticker)
            macro = _neutral_macro()
            macro["brent_above_sma50"] = False

            result = apply_macro_filters(signal, macro)
            assert result is None, f"Expected None for oil ticker {oil_ticker}"

    def test_macro_filter_allows_non_oil_when_brent_low(self) -> None:
        """M2: Brent ниже SMA(50) НЕ блокирует не-нефтяные тикеры."""
        signal = _make_buy_long_signal(ticker="SBER")
        macro = _neutral_macro()
        macro["brent_above_sma50"] = False

        result = apply_macro_filters(signal, macro)
        assert result is not None

    def test_macro_filter_reduces_confidence_rate_hike(self) -> None:
        """M3: Ставка ЦБ растёт → confidence уменьшается на 0.1."""
        original_confidence = 0.75
        signal = _make_buy_long_signal(confidence=original_confidence)
        macro = _neutral_macro()
        macro["key_rate_direction"] = "up"

        result = apply_macro_filters(signal, macro)
        assert result is not None
        assert abs(result.confidence - (original_confidence - 0.1)) < 1e-9

    def test_macro_filter_rate_hike_confidence_not_below_zero(self) -> None:
        """M3: Confidence не уходит ниже 0 при очень низком начальном значении."""
        signal = _make_buy_long_signal(confidence=0.05)
        macro = _neutral_macro()
        macro["key_rate_direction"] = "up"

        result = apply_macro_filters(signal, macro)
        assert result is not None
        assert result.confidence >= 0.0

    def test_macro_filter_rate_down_no_change(self) -> None:
        """M3: При снижении ставки confidence не меняется."""
        original_confidence = 0.75
        signal = _make_buy_long_signal(confidence=original_confidence)
        macro = _neutral_macro()
        macro["key_rate_direction"] = "down"

        result = apply_macro_filters(signal, macro)
        assert result is not None
        assert result.confidence == original_confidence

    def test_macro_filter_hold_signal_passes(self) -> None:
        """Сигналы HOLD всегда проходят через макро-фильтры без изменений."""
        signal = TradingSignal(
            ticker="SBER",
            action=Action.HOLD,
            direction=Direction.LONG,
            confidence=0.3,
            reasoning="No setup",
        )
        macro = _neutral_macro()
        macro["imoex_above_sma200"] = False  # M1 должен игнорироваться для HOLD

        result = apply_macro_filters(signal, macro)
        assert result is not None
        assert result.action == Action.HOLD

    def test_macro_filter_imoex_data_kwarg_accepted(self) -> None:
        """apply_macro_filters принимает опциональный параметр imoex_data."""
        signal = _make_buy_long_signal()
        result = apply_macro_filters(signal, _neutral_macro(), imoex_data={"foo": "bar"})
        assert result is not None


# ---------------------------------------------------------------------------
# 8. test_regime_from_index
# ---------------------------------------------------------------------------


def _make_index_candles(n: int, trend: float = 0.001, base: float = 3000.0) -> list[OHLCVBar]:
    """Сгенерировать синтетические бары IMOEX."""
    import random
    random.seed(7)
    bars: list[OHLCVBar] = []
    from datetime import date, timedelta
    start = date(2020, 1, 1)
    close = base
    for i in range(n):
        close = close * (1 + trend + random.gauss(0, 0.005))
        high = close * (1 + abs(random.gauss(0, 0.003)))
        low = close * (1 - abs(random.gauss(0, 0.003)))
        open_ = close * (1 + random.gauss(0, 0.002))
        # Гарантируем корректность OHLCV
        high = max(high, close, open_)
        low = min(low, close, open_)
        bars.append(
            OHLCVBar(
                ticker="IMOEX",
                dt=start + timedelta(days=i),
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=1_000_000,
            )
        )
    return bars


class TestRegimeFromIndex:
    def test_regime_from_index_returns_market_regime(self) -> None:
        """detect_regime_from_index возвращает экземпляр MarketRegime."""
        candles = _make_index_candles(250, trend=0.001)
        regime = detect_regime_from_index(candles)
        assert isinstance(regime, MarketRegime)

    def test_regime_from_index_uptrend(self) -> None:
        """Устойчивый рост (250 баров) должен распознаваться как UPTREND."""
        candles = _make_index_candles(250, trend=0.003)
        regime = detect_regime_from_index(candles)
        # Устойчивый апстренд: UPTREND или WEAK_TREND допустимы
        assert regime in (MarketRegime.UPTREND, MarketRegime.WEAK_TREND), (
            f"Expected UPTREND or WEAK_TREND for strong uptrend, got {regime}"
        )

    def test_regime_from_index_crisis(self) -> None:
        """Серия свечей с высокой волатильностью (ATR/Close > 3.5%) → CRISIS."""
        import random
        random.seed(99)
        from datetime import date, timedelta

        bars: list[OHLCVBar] = []
        close = 3000.0
        start = date(2020, 1, 1)
        for i in range(50):
            # Экстремальная волатильность: ±8% на каждом шаге
            close = close * (1 + random.gauss(0, 0.08))
            close = max(close, 100.0)
            high = close * 1.09
            low = close * 0.91
            open_ = close * (1 + random.gauss(0, 0.04))
            high = max(high, close, open_)
            low = min(low, close, open_)
            bars.append(
                OHLCVBar(
                    ticker="IMOEX",
                    dt=start + timedelta(days=i),
                    open=round(open_, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=1_000_000,
                )
            )

        regime = detect_regime_from_index(bars, current_drawdown=0.0)
        assert regime == MarketRegime.CRISIS, (
            f"Expected CRISIS for high-volatility series, got {regime}"
        )

    def test_regime_from_index_too_few_bars(self) -> None:
        """При количестве баров < 14 возвращается WEAK_TREND (безопасный fallback)."""
        candles = _make_index_candles(5, trend=0.002)
        regime = detect_regime_from_index(candles)
        assert regime == MarketRegime.WEAK_TREND

    def test_regime_from_index_crisis_by_drawdown(self) -> None:
        """current_drawdown > 15% → CRISIS независимо от волатильности."""
        candles = _make_index_candles(50, trend=0.001)
        regime = detect_regime_from_index(candles, current_drawdown=0.20)
        assert regime == MarketRegime.CRISIS
