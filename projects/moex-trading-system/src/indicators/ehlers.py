"""Ehlers DSP (Digital Signal Processing) indicators.

Three indicators by John F. Ehlers for cycle/momentum detection:
- Voss Filter: predictive bandpass filter
- BandPass Filter: cycle isolation with AGC normalization
- Reflex: zero-lag momentum oscillator

Adapted from jesse-ai/jesse indicators/ (MIT License).
Standalone NumPy implementation, no numba required.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Voss Filter
# ---------------------------------------------------------------------------

@dataclass
class VossResult:
    """Voss predictive filter output."""
    voss: np.ndarray  # predictive component
    filt: np.ndarray  # bandpass filtered component


def voss_filter(
    close: np.ndarray,
    period: int = 20,
    predict: int = 3,
    bandwidth: float = 0.25,
) -> VossResult:
    """Voss predictive filter — anticipates cycle turning points.

    Args:
        close: Close prices.
        period: Dominant cycle period (default 20).
        predict: Prediction bars (default 3).
        bandwidth: Filter bandwidth (default 0.25).

    Returns:
        VossResult with voss (predictive) and filt (bandpass) arrays.
    """
    n = len(close)
    filt = np.zeros(n)
    voss_arr = np.zeros(n)

    f1 = np.cos(2 * np.pi / period)
    g1 = np.cos(bandwidth * 2 * np.pi / period)
    s1 = 1.0 / g1 - np.sqrt(1.0 / (g1 * g1) - 1.0)
    order = 3 * predict

    # Bandpass filter
    for i in range(2, n):
        if i > period and i > order:
            filt[i] = (
                0.5 * (1 - s1) * (close[i] - close[i - 2])
                + f1 * (1 + s1) * filt[i - 1]
                - s1 * filt[i - 2]
            )

    # Predictive component
    for i in range(n):
        if i > period and i > order:
            sumc = sum(
                ((c + 1) / order) * voss_arr[i - (order - c)]
                for c in range(order)
            )
            voss_arr[i] = ((3 + order) / 2.0) * filt[i] - sumc

    return VossResult(voss=voss_arr, filt=filt)


# ---------------------------------------------------------------------------
# BandPass Filter
# ---------------------------------------------------------------------------

@dataclass
class BandPassResult:
    """BandPass filter output."""
    bp: np.ndarray             # raw bandpass
    bp_normalized: np.ndarray  # AGC-normalized bandpass [-1, +1]
    signal: np.ndarray         # +1/-1 signal (normalized vs trigger)
    trigger: np.ndarray        # high-pass filtered normalized


def _high_pass(source: np.ndarray, period: float) -> np.ndarray:
    """2-pole high-pass filter (Ehlers)."""
    n = len(source)
    hp = np.zeros(n)
    alpha1 = (np.cos(0.707 * 2 * np.pi / period) + np.sin(0.707 * 2 * np.pi / period) - 1) / np.cos(
        0.707 * 2 * np.pi / period
    )
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2) * (1 - alpha1 / 2) * (source[i] - 2 * source[i - 1] + source[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) * (1 - alpha1) * hp[i - 2]
        )
    return hp


def bandpass_filter(
    close: np.ndarray,
    period: int = 20,
    bandwidth: float = 0.3,
) -> BandPassResult:
    """BandPass filter — isolates dominant cycle from price data.

    Args:
        close: Close prices.
        period: Center period of the bandpass (default 20).
        bandwidth: Bandwidth as fraction of period (default 0.3).

    Returns:
        BandPassResult with bp, normalized, signal, and trigger.
    """
    n = len(close)
    hp = _high_pass(close, 4 * period / bandwidth)

    beta = np.cos(2 * np.pi / period)
    gamma = np.cos(2 * np.pi * bandwidth / period)
    alpha = 1.0 / gamma - np.sqrt(1.0 / (gamma ** 2) - 1.0)

    # Bandpass calculation
    bp = np.copy(hp)
    for i in range(2, n):
        bp[i] = (
            0.5 * (1 - alpha) * hp[i]
            - 0.5 * (1 - alpha) * hp[i - 2]
            + beta * (1 + alpha) * bp[i - 1]
            - alpha * bp[i - 2]
        )

    # AGC normalization
    K = 0.991
    peak = np.copy(np.abs(bp))
    for i in range(1, n):
        peak[i] = max(peak[i - 1] * K, abs(bp[i]))

    bp_norm = np.where(peak > 0, bp / peak, 0.0)

    trigger = _high_pass(bp_norm, period / bandwidth / 1.5)
    signal = np.where(bp_norm < trigger, 1, np.where(trigger < bp_norm, -1, 0)).astype(float)

    return BandPassResult(bp=bp, bp_normalized=bp_norm, signal=signal, trigger=trigger)


# ---------------------------------------------------------------------------
# Reflex indicator
# ---------------------------------------------------------------------------

def _supersmoother(source: np.ndarray, period: float) -> np.ndarray:
    """Ehlers SuperSmoother filter (2-pole)."""
    n = len(source)
    ssf = np.zeros(n)
    a = np.exp(-1.414 * np.pi / period)
    b = 2 * a * np.cos(1.414 * np.pi / period)
    c2 = b
    c3 = -a * a
    c1 = 1 - c2 - c3
    for i in range(2, n):
        ssf[i] = c1 * (source[i] + source[i - 1]) / 2 + c2 * ssf[i - 1] + c3 * ssf[i - 2]
    return ssf


def reflex(
    close: np.ndarray,
    period: int = 20,
) -> np.ndarray:
    """Reflex indicator — zero-lag momentum oscillator by Ehlers.

    Measures how much the smoothed price deviates from a linear extrapolation.
    Values > 0: bullish momentum, < 0: bearish momentum.

    Args:
        close: Close prices.
        period: Lookback period (default 20).

    Returns:
        NumPy array of reflex values.
    """
    n = len(close)
    ssf = _supersmoother(close, period / 2.0)
    rf = np.zeros(n)
    ms = np.zeros(n)

    for i in range(period, n):
        slope = (ssf[i - period] - ssf[i]) / period
        my_sum = sum((ssf[i] + t * slope) - ssf[i - t] for t in range(1, period + 1))
        my_sum /= period

        ms[i] = 0.04 * my_sum * my_sum + 0.96 * ms[i - 1]
        if ms[i] > 0:
            rf[i] = my_sum / np.sqrt(ms[i])

    return rf
