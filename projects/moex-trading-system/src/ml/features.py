"""Feature preparation for ML models.

Combines TA indicators, TSFRESH features, macro data, sentiment,
and calendar features into a single feature matrix for training/prediction.
"""
from __future__ import annotations

from datetime import date
from typing import Any


# Target thresholds for direction classification
DIRECTION_THRESHOLD = 0.005  # ±0.5% = flat


def prepare_features(
    candles: list[dict[str, Any]],
    ta_features: list[dict[str, Any]],
    macro: dict[str, float] | None = None,
    sentiment: float = 0.0,
    tsfresh_features: dict[str, list[float]] | None = None,
) -> list[dict[str, float]]:
    """Combine all feature sources into a flat feature dict per bar.

    Parameters
    ----------
    candles:
        OHLCV bars with ``close``, ``high``, ``low``, ``volume``, ``dt``.
    ta_features:
        Output of ``calculate_all_features()`` — one dict per bar.
    macro:
        Macro indicators: ``key_rate``, ``usd_rub``, ``brent``.
    sentiment:
        Daily sentiment score [-1, +1].
    tsfresh_features:
        Optional TSFRESH features (feature_name -> values).

    Returns
    -------
    list[dict[str, float]]
        One feature dict per bar (aligned with ta_features).
    """
    macro = macro or {}
    result: list[dict[str, float]] = []

    for i, ta in enumerate(ta_features):
        row: dict[str, float] = {}

        # TA indicators (15 core features)
        for key in (
            "rsi_14", "macd", "macd_signal", "macd_histogram",
            "adx", "di_plus", "di_minus",
            "ema_20", "ema_50", "ema_200",
            "bb_upper", "bb_lower", "bb_pct_b",
            "atr_14", "stoch_k", "stoch_d",
            "obv", "volume_ratio_20", "mfi",
        ):
            val = ta.get(key)
            if val is not None:
                row[f"ta_{key}"] = float(val)

        # Price-derived
        close = float(ta.get("close", 0))
        if close > 0:
            ema200 = float(ta.get("ema_200", close))
            row["price_vs_ema200"] = (close - ema200) / ema200 if ema200 > 0 else 0
            ema50 = float(ta.get("ema_50", close))
            row["price_vs_ema50"] = (close - ema50) / ema50 if ema50 > 0 else 0

        # Macro features
        row["macro_key_rate"] = float(macro.get("key_rate", 0))
        row["macro_usd_rub"] = float(macro.get("usd_rub", 0))
        row["macro_brent"] = float(macro.get("brent", 0))

        # Sentiment
        row["sentiment"] = sentiment

        # Calendar features
        dt = ta.get("dt") or (candles[i].get("dt") if i < len(candles) else None)
        if isinstance(dt, date):
            row["cal_month"] = float(dt.month)
            row["cal_dow"] = float(dt.weekday())
            row["cal_day"] = float(dt.day)
        elif isinstance(dt, str):
            try:
                d = date.fromisoformat(dt)
                row["cal_month"] = float(d.month)
                row["cal_dow"] = float(d.weekday())
                row["cal_day"] = float(d.day)
            except ValueError:
                pass

        result.append(row)

    # Merge TSFRESH features if available
    if tsfresh_features:
        offset = len(result) - len(next(iter(tsfresh_features.values()), []))
        for feat_name, values in tsfresh_features.items():
            safe_name = f"ts_{feat_name}"
            for j, val in enumerate(values):
                idx = offset + j
                if 0 <= idx < len(result):
                    result[idx][safe_name] = val

    return result


def compute_target(candles: list[dict[str, Any]], horizon: int = 1) -> list[int]:
    """Compute directional target: 1=up, 0=down, based on future returns.

    Parameters
    ----------
    candles:
        OHLCV bars with ``close``.
    horizon:
        Number of bars to look ahead.

    Returns
    -------
    list[int]
        Target values. Last ``horizon`` values are set to 0 (unknown future).
    """
    closes = [float(c.get("close", 0)) for c in candles]
    targets: list[int] = []

    for i in range(len(closes)):
        if i + horizon < len(closes) and closes[i] > 0:
            ret = (closes[i + horizon] - closes[i]) / closes[i]
            targets.append(1 if ret > DIRECTION_THRESHOLD else 0)
        else:
            targets.append(0)

    return targets
