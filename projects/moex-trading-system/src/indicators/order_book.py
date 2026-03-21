"""Order Book indicators for MOEX instruments.

Inspired by hummingbot OBI calculation (Apache 2.0), written from scratch.

Order Book Imbalance (OBI) is a short-term directional signal:
- OBI > 0: more buying pressure → price likely to rise
- OBI < 0: more selling pressure → price likely to fall

Usage:
    obi = order_book_imbalance(bid_volumes, ask_volumes)
    microprice = compute_microprice(best_bid, best_ask, bid_vol, ask_vol)
"""
from __future__ import annotations

import numpy as np


def order_book_imbalance(
    bid_volumes: np.ndarray | list[float],
    ask_volumes: np.ndarray | list[float],
    n_levels: int | None = None,
) -> float:
    """Order Book Imbalance — directional signal from volume asymmetry.

    Formula: OBI = (sum(bid_vol[:n]) - sum(ask_vol[:n])) /
                   (sum(bid_vol[:n]) + sum(ask_vol[:n]))

    Range: [-1, +1]. Positive = buying pressure.

    Args:
        bid_volumes: Volumes at each bid level (best first).
        ask_volumes: Volumes at each ask level (best first).
        n_levels: Number of levels to use (None = all).

    Returns:
        OBI value in [-1, 1].
    """
    bids = np.asarray(bid_volumes, dtype=np.float64)
    asks = np.asarray(ask_volumes, dtype=np.float64)

    if n_levels is not None:
        bids = bids[:n_levels]
        asks = asks[:n_levels]

    bid_sum = bids.sum()
    ask_sum = asks.sum()
    total = bid_sum + ask_sum

    if total <= 0:
        return 0.0
    return float((bid_sum - ask_sum) / total)


def obi_ema(
    bid_volumes_series: list[list[float]],
    ask_volumes_series: list[list[float]],
    n_levels: int = 5,
    ema_period: int = 10,
) -> np.ndarray:
    """Smoothed OBI time series using EMA.

    Reduces noise from individual snapshots by smoothing.

    Args:
        bid_volumes_series: List of bid volume snapshots over time.
        ask_volumes_series: List of ask volume snapshots over time.
        n_levels: Levels per snapshot.
        ema_period: EMA smoothing period.

    Returns:
        Array of smoothed OBI values.
    """
    n = len(bid_volumes_series)
    raw = np.array([
        order_book_imbalance(b, a, n_levels)
        for b, a in zip(bid_volumes_series, ask_volumes_series)
    ])

    if n == 0:
        return np.array([])

    alpha = 2.0 / (ema_period + 1)
    result = np.empty(n)
    result[0] = raw[0]
    for i in range(1, n):
        result[i] = alpha * raw[i] + (1 - alpha) * result[i - 1]
    return result


def compute_microprice(
    best_bid: float,
    best_ask: float,
    bid_volume: float,
    ask_volume: float,
) -> float:
    """Microprice — volume-weighted fair price estimator.

    Better than mid-price when order book is asymmetric.

    Formula: microprice = (bid * ask_vol + ask * bid_vol) /
                          (bid_vol + ask_vol)

    When bid_vol >> ask_vol → microprice closer to ask (buying pressure).

    Args:
        best_bid, best_ask: Top-of-book prices.
        bid_volume, ask_volume: Volumes at best bid/ask.

    Returns:
        Estimated fair price.
    """
    total = bid_volume + ask_volume
    if total <= 0:
        return (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0.0
    return (best_bid * ask_volume + best_ask * bid_volume) / total


def book_pressure_ratio(
    bid_volumes: np.ndarray | list[float],
    ask_volumes: np.ndarray | list[float],
    depth: int = 5,
) -> float:
    """Cumulative volume ratio at N depth levels.

    Values > 1: bid-heavy (bullish). Values < 1: ask-heavy (bearish).

    Args:
        bid_volumes: Bid volumes (best first).
        ask_volumes: Ask volumes (best first).
        depth: Number of levels.

    Returns:
        bid_cumul / ask_cumul ratio.
    """
    bids = np.asarray(bid_volumes, dtype=np.float64)[:depth]
    asks = np.asarray(ask_volumes, dtype=np.float64)[:depth]
    ask_sum = asks.sum()
    if ask_sum <= 0:
        return float("inf") if bids.sum() > 0 else 1.0
    return float(bids.sum() / ask_sum)
