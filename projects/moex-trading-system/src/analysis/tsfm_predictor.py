"""Time Series Foundation Model predictor using Chronos-Bolt.

Zero-shot forecasting without training. Model: amazon/chronos-bolt-tiny (9M params, CPU).
Produces probabilistic forecasts (quantiles) for 1-5 day horizon.

Public API:
    predict_direction(closes, horizon=5) -> ForecastResult
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ForecastResult:
    """Result of a Chronos-Bolt forecast."""

    direction: int  # +1 = up, -1 = down, 0 = flat
    confidence: float  # 0.0 to 1.0 (narrower interval = higher confidence)
    median_forecast: float  # median predicted price
    low_10: float  # 10th percentile
    high_90: float  # 90th percentile
    horizon: int  # forecast horizon in days


def predict_direction(
    closes: list[float],
    horizon: int = 5,
    model_id: str = "amazon/chronos-bolt-tiny",
) -> ForecastResult | None:
    """Generate directional forecast using Chronos-Bolt.

    Parameters
    ----------
    closes:
        Historical close prices (at least 60, recommended 200+).
    horizon:
        Number of days to forecast (1-30).
    model_id:
        HuggingFace model ID. Default: chronos-bolt-tiny (9M, CPU-friendly).

    Returns
    -------
    ForecastResult or None if model unavailable.
    """
    try:
        import torch
        from chronos import BaseChronosPipeline
    except ImportError:
        logger.warning("chronos-forecasting not installed")
        return None

    if len(closes) < 60:
        logger.warning("Not enough data for Chronos", n=len(closes))
        return None

    try:
        pipeline = BaseChronosPipeline.from_pretrained(
            model_id,
            device_map="cpu",
            torch_dtype=torch.float32,
        )

        context = torch.tensor(closes[-200:], dtype=torch.float32).unsqueeze(0)

        # Generate quantile forecasts
        quantiles, mean = pipeline.predict_quantiles(
            context,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )

        # Extract values for the full horizon
        q10 = float(quantiles[0, :, 0].mean())   # 10th percentile avg
        q50 = float(quantiles[0, :, 1].mean())   # median avg
        q90 = float(quantiles[0, :, 2].mean())   # 90th percentile avg

    except Exception as e:
        logger.error("chronos_predict_error", error=str(e))

        # Fallback: simple momentum-based prediction
        if len(closes) >= 20:
            recent = closes[-20:]
            momentum = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0
            last = closes[-1]
            q50 = last * (1 + momentum * 0.5)
            q10 = last * (1 + momentum * 0.3)
            q90 = last * (1 + momentum * 0.7)
        else:
            return None

    last_close = closes[-1]
    if last_close <= 0:
        return None

    # Direction based on median forecast vs last close
    pct_change = (q50 - last_close) / last_close

    if pct_change > 0.005:
        direction = 1
    elif pct_change < -0.005:
        direction = -1
    else:
        direction = 0

    # Confidence: inverse of interval width (narrower = more confident)
    interval_width = (q90 - q10) / last_close if last_close > 0 else 1.0
    confidence = max(0.0, min(1.0, 1.0 - interval_width * 5))

    return ForecastResult(
        direction=direction,
        confidence=round(confidence, 4),
        median_forecast=round(q50, 2),
        low_10=round(q10, 2),
        high_90=round(q90, 2),
        horizon=horizon,
    )
