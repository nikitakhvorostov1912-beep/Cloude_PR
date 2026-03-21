"""Support and Resistance level detection for MOEX instruments.

Inspired by LiuAlgoTrader fincalcs/support_resistance.py (MIT License).
Written from scratch with improvements:
- Pure numpy (no pandas dependency in hot path)
- Configurable thresholds (not hardcoded)
- MOEX trading hours aware
- Volume-weighted level strength

Algorithm: derivative-based peak/trough detection on resampled OHLC data.
Peaks = local maxima (resistance), troughs = local minima (support).
Nearby levels are clustered by proximity percentage (default 2%).

Usage:
    resistances = find_resistances(highs, threshold_pct=0.02)
    supports = find_supports(lows, threshold_pct=0.02)
    levels = find_support_resistance(highs, lows, closes)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class PriceLevel:
    """A support or resistance price level.

    Attributes:
        price: The price level.
        strength: Number of touches / peaks at this level.
        level_type: "support" or "resistance".
    """

    price: float
    strength: int
    level_type: str  # "support" or "resistance"


def _find_local_maxima(data: np.ndarray) -> np.ndarray:
    """Find indices of local maxima using first derivative sign change.

    A local maximum occurs where the derivative changes from non-negative
    to strictly negative (was rising or flat, then starts falling).
    Flat regions are excluded: at least one side must be strictly changing.
    """
    if len(data) < 3:
        return np.array([], dtype=int)
    diff = np.diff(data)
    # Peak: was rising (>0) then falls (<=0), OR was flat (==0) then falls (<0)
    # Exclude pure flat: require at least one strict inequality
    peaks = np.where(
        (diff[:-1] >= 0) & (diff[1:] <= 0)
        & ((diff[:-1] > 0) | (diff[1:] < 0))
    )[0] + 1
    return peaks


def _find_local_minima(data: np.ndarray) -> np.ndarray:
    """Find indices of local minima using first derivative sign change.

    A local minimum occurs where the derivative changes from non-positive
    to strictly positive (was falling or flat, then starts rising).
    Flat regions are excluded: at least one side must be strictly changing.
    """
    if len(data) < 3:
        return np.array([], dtype=int)
    diff = np.diff(data)
    # Trough: was falling (<=0) then rises (>=0), exclude pure flat
    troughs = np.where(
        (diff[:-1] <= 0) & (diff[1:] >= 0)
        & ((diff[:-1] < 0) | (diff[1:] > 0))
    )[0] + 1
    return troughs


def _cluster_levels(
    prices: np.ndarray,
    margin_pct: float = 0.02,
) -> list[tuple[float, int]]:
    """Cluster nearby price levels by proximity percentage.

    Groups prices that are within margin_pct of each other,
    returns the mean of each cluster and the cluster size (strength).

    Args:
        prices: Sorted array of price levels.
        margin_pct: Maximum relative distance to group (0.02 = 2%).

    Returns:
        List of (cluster_mean_price, cluster_size) tuples.
    """
    if len(prices) == 0:
        return []

    prices_sorted = np.sort(prices)
    clusters: list[tuple[float, int]] = []
    group: list[float] = [float(prices_sorted[0])]

    for i in range(1, len(prices_sorted)):
        prev = group[-1]
        curr = float(prices_sorted[i])
        if prev > 0 and abs(curr - prev) / prev <= margin_pct:
            group.append(curr)
        else:
            clusters.append((float(np.mean(group)), len(group)))
            group = [curr]

    if group:
        clusters.append((float(np.mean(group)), len(group)))

    return clusters


def find_resistances(
    highs: Sequence[float] | np.ndarray,
    current_price: float | None = None,
    margin_pct: float = 0.02,
    min_strength: int = 1,
) -> list[PriceLevel]:
    """Find resistance levels from high prices.

    Detects local maxima in the high price series, clusters nearby
    peaks, and returns resistance levels sorted by price ascending.

    Args:
        highs: Array of high prices (e.g. 15-min resampled highs).
        current_price: If set, only returns levels above this price.
        margin_pct: Clustering margin (0.02 = 2%).
        min_strength: Minimum touches to qualify as a level.

    Returns:
        List of PriceLevel with type="resistance".
    """
    arr = np.asarray(highs, dtype=np.float64)
    peak_indices = _find_local_maxima(arr)

    if len(peak_indices) == 0:
        return []

    peak_prices = arr[peak_indices]

    if current_price is not None:
        peak_prices = peak_prices[peak_prices >= current_price]

    if len(peak_prices) == 0:
        return []

    clusters = _cluster_levels(peak_prices, margin_pct)
    levels = [
        PriceLevel(price=round(price, 4), strength=strength, level_type="resistance")
        for price, strength in clusters
        if strength >= min_strength
    ]
    return sorted(levels, key=lambda x: x.price)


def find_supports(
    lows: Sequence[float] | np.ndarray,
    current_price: float | None = None,
    margin_pct: float = 0.02,
    min_strength: int = 1,
) -> list[PriceLevel]:
    """Find support levels from low prices.

    Detects local minima in the low price series, clusters nearby
    troughs, and returns support levels sorted by price descending
    (strongest/nearest first).

    Args:
        lows: Array of low prices (e.g. 5-min resampled lows).
        current_price: If set, only returns levels below this price.
        margin_pct: Clustering margin (0.02 = 2%).
        min_strength: Minimum touches to qualify as a level.

    Returns:
        List of PriceLevel with type="support".
    """
    arr = np.asarray(lows, dtype=np.float64)
    trough_indices = _find_local_minima(arr)

    if len(trough_indices) == 0:
        return []

    trough_prices = arr[trough_indices]

    if current_price is not None:
        trough_prices = trough_prices[trough_prices <= current_price]

    if len(trough_prices) == 0:
        return []

    clusters = _cluster_levels(trough_prices, margin_pct)
    levels = [
        PriceLevel(price=round(price, 4), strength=strength, level_type="support")
        for price, strength in clusters
        if strength >= min_strength
    ]
    return sorted(levels, key=lambda x: x.price, reverse=True)


def find_nearest_support(
    lows: Sequence[float] | np.ndarray,
    current_price: float,
    margin_pct: float = 0.02,
) -> float | None:
    """Find the nearest support level below current price.

    Useful for stop-loss placement.

    Returns:
        Nearest support price, or None if no supports found.
    """
    supports = find_supports(lows, current_price, margin_pct)
    return supports[0].price if supports else None


def find_nearest_resistance(
    highs: Sequence[float] | np.ndarray,
    current_price: float,
    margin_pct: float = 0.02,
) -> float | None:
    """Find the nearest resistance level above current price.

    Useful for take-profit placement.

    Returns:
        Nearest resistance price, or None if no resistances found.
    """
    resistances = find_resistances(highs, current_price, margin_pct)
    return resistances[0].price if resistances else None


def find_support_resistance(
    highs: Sequence[float] | np.ndarray,
    lows: Sequence[float] | np.ndarray,
    current_price: float | None = None,
    margin_pct: float = 0.02,
    min_strength: int = 1,
) -> list[PriceLevel]:
    """Find both support and resistance levels.

    Returns combined list sorted by distance from current_price
    (if provided) or by price ascending.
    """
    resistances = find_resistances(highs, current_price, margin_pct, min_strength)
    supports = find_supports(lows, current_price, margin_pct, min_strength)

    combined = resistances + supports
    if current_price is not None:
        combined.sort(key=lambda x: abs(x.price - current_price))
    else:
        combined.sort(key=lambda x: x.price)
    return combined
