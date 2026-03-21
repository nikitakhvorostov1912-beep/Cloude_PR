"""GARCH volatility forecasting for MOEX instruments.

Uses the `arch` library (pip install arch-model) — the gold standard
for conditional volatility modeling in Python (MIT, 1400+ stars).

Why GARCH over historical vol?
- Historical vol (std of returns) is BACKWARD-looking
- GARCH FORECASTS future vol based on recent shocks + persistence
- Critical for: options pricing, position sizing, regime detection

Supported models:
- GARCH(1,1): σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
- EGARCH: asymmetric — bad news increases vol more than good news
- EWMA (RiskMetrics): σ²_t = λ·σ²_{t-1} + (1-λ)·ε²_{t-1}
- GJR-GARCH: leverage effect (separate coeff for negative shocks)

Usage:
    from src.indicators.garch_forecast import forecast_volatility

    vol_forecast = forecast_volatility(returns, model="garch", horizon=5)
    print(f"5-day ahead vol: {vol_forecast.annualized_vol:.2%}")
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolForecast:
    """Volatility forecast result.

    Attributes:
        daily_variance: Forecasted daily variance (σ²).
        daily_vol: Forecasted daily volatility (σ).
        annualized_vol: Annualized volatility (σ * √252).
        horizon: Forecast horizon in days.
        model_name: Name of the GARCH variant used.
        aic: Akaike Information Criterion (lower = better fit).
        bic: Bayesian IC (penalizes complexity more than AIC).
        params: Fitted model parameters dict.
    """

    daily_variance: float
    daily_vol: float
    annualized_vol: float
    horizon: int
    model_name: str
    aic: float = 0.0
    bic: float = 0.0
    params: dict = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.params is None:
            object.__setattr__(self, "params", {})


def forecast_volatility(
    returns: np.ndarray | pd.Series,
    model: Literal["garch", "egarch", "ewma", "gjr"] = "garch",
    horizon: int = 1,
    p: int = 1,
    q: int = 1,
    dist: str = "normal",
    rescale: bool = True,
) -> VolForecast:
    """Forecast volatility using GARCH-family models.

    Args:
        returns: Daily log-returns or simple returns.
        model: Model type — "garch", "egarch", "ewma", "gjr".
        horizon: Days ahead to forecast (default 1).
        p: ARCH order (default 1).
        q: GARCH order (default 1).
        dist: Error distribution — "normal", "t", "skewt".
        rescale: Auto-rescale returns for numerical stability.

    Returns:
        VolForecast with daily and annualized volatility.

    Raises:
        ImportError: If `arch` package not installed.
    """
    try:
        from arch import arch_model
    except ImportError:
        raise ImportError(
            "arch package required: pip install arch-model"
        )

    arr = np.asarray(returns, dtype=np.float64) * 100 if rescale else np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]

    if len(arr) < 30:
        return VolForecast(0.0, 0.0, 0.0, horizon, model)

    # Build model
    if model == "ewma":
        am = arch_model(arr, mean="Zero", vol="EWMAVariance")
    elif model == "egarch":
        am = arch_model(arr, mean="Zero", vol="EGARCH", p=p, q=q, dist=dist)
    elif model == "gjr":
        am = arch_model(arr, mean="Zero", vol="GARCH", p=p, o=1, q=q, dist=dist)
    else:  # garch
        am = arch_model(arr, mean="Zero", vol="GARCH", p=p, q=q, dist=dist)

    # Fit
    res = am.fit(disp="off", show_warning=False)

    # Forecast
    fcast = res.forecast(horizon=horizon)
    daily_var = float(fcast.variance.iloc[-1].iloc[-1])

    # Undo rescale
    if rescale:
        daily_var /= 10000  # (100²)

    daily_vol = np.sqrt(max(daily_var, 0))
    ann_vol = daily_vol * np.sqrt(252)

    params_dict = dict(res.params)

    return VolForecast(
        daily_variance=daily_var,
        daily_vol=daily_vol,
        annualized_vol=ann_vol,
        horizon=horizon,
        model_name=model,
        aic=float(res.aic),
        bic=float(res.bic),
        params=params_dict,
    )


def compare_garch_models(
    returns: np.ndarray | pd.Series,
    horizon: int = 1,
) -> list[VolForecast]:
    """Compare all GARCH variants and return sorted by AIC.

    Fits GARCH, EGARCH, EWMA, GJR and ranks by information criterion.

    Args:
        returns: Daily returns.
        horizon: Forecast horizon.

    Returns:
        List of VolForecast sorted by AIC (best first).
    """
    results: list[VolForecast] = []
    for model in ("garch", "egarch", "ewma", "gjr"):
        try:
            vf = forecast_volatility(returns, model=model, horizon=horizon)
            results.append(vf)
        except Exception:
            continue
    results.sort(key=lambda x: x.aic)
    return results
