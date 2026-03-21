"""Avellaneda-Stoikov market making model for MOEX.

Inspired by hummingbot avellaneda_market_making (Apache 2.0).
Formulas from Avellaneda & Stoikov (2008) "High-frequency trading
in a limit order book".

The model computes:
1. Reservation price: mid-price adjusted for inventory risk
2. Optimal spread: minimizes inventory risk + maximizes fill rate

Key insight: the more inventory you hold, the more aggressively
you should quote on that side to offload risk.

Usage:
    model = AvellanedaStoikov(
        gamma=0.5, sigma=0.02, kappa=1.5,
        session_duration_seconds=31800,  # MOEX 10:00-18:50
    )
    bid, ask = model.compute_quotes(
        mid_price=300.0,
        inventory=100,  # long 100 shares
        time_remaining=15000,  # 4.2 hours left
    )
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteResult:
    """Market making quote output.

    Attributes:
        bid_price: Recommended bid quote.
        ask_price: Recommended ask quote.
        reservation_price: Inventory-adjusted fair price.
        optimal_spread: Total bid-ask spread.
        inventory_skew: How much reservation deviates from mid.
    """

    bid_price: float
    ask_price: float
    reservation_price: float
    optimal_spread: float
    inventory_skew: float


class AvellanedaStoikov:
    """Avellaneda-Stoikov optimal market making model.

    Core formulas:
        reservation_price = mid - q * gamma * sigma^2 * (T - t)
        optimal_spread = gamma * sigma^2 * (T-t) + (2/gamma) * ln(1 + gamma/kappa)

    Where:
        q     = signed inventory (positive = long, negative = short)
        gamma = risk aversion parameter (higher = more conservative)
        sigma = volatility (daily or per-period)
        kappa = order fill rate parameter (higher = more fills expected)
        T-t   = time remaining until session end

    The model naturally:
    - Widens spread in high volatility
    - Narrows spread near session close (T-t → 0)
    - Shifts quotes against inventory to offload risk

    Args:
        gamma: Risk aversion (0.1 = aggressive, 2.0 = conservative).
        sigma: Volatility estimate (annualized or per-bar).
        kappa: Market order arrival rate (1.0-5.0 typical).
        session_duration_seconds: Total session length.
        min_spread_pct: Minimum spread floor as fraction of price.
        max_spread_pct: Maximum spread cap as fraction of price.
        inventory_target: Target inventory (0 = market-neutral).
        max_inventory: Hard inventory limit (absolute value).
    """

    def __init__(
        self,
        gamma: float = 0.5,
        sigma: float = 0.02,
        kappa: float = 1.5,
        session_duration_seconds: float = 31800.0,
        min_spread_pct: float = 0.001,
        max_spread_pct: float = 0.05,
        inventory_target: float = 0.0,
        max_inventory: float = float("inf"),
    ) -> None:
        self._gamma = gamma
        self._sigma = sigma
        self._kappa = kappa
        self._session_duration = session_duration_seconds
        self._min_spread_pct = min_spread_pct
        self._max_spread_pct = max_spread_pct
        self._inventory_target = inventory_target
        self._max_inventory = max_inventory

    def compute_quotes(
        self,
        mid_price: float,
        inventory: float = 0.0,
        time_remaining: float | None = None,
        sigma_override: float | None = None,
    ) -> QuoteResult:
        """Compute optimal bid and ask quotes.

        Args:
            mid_price: Current mid-market price.
            inventory: Signed inventory (+ long, - short).
            time_remaining: Seconds until session end. None = full session.
            sigma_override: Override volatility for this tick.

        Returns:
            QuoteResult with bid, ask, reservation price, spread.
        """
        if mid_price <= 0:
            return QuoteResult(0.0, 0.0, 0.0, 0.0, 0.0)

        sigma = sigma_override if sigma_override is not None else self._sigma
        t_remaining = time_remaining if time_remaining is not None else self._session_duration

        # Normalize time to [0, 1] fraction of session
        t_frac = max(t_remaining / self._session_duration, 1e-6)

        # Effective inventory (deviation from target)
        q = inventory - self._inventory_target

        # 1. Reservation price: adjusted for inventory risk
        #    r = mid - q * gamma * sigma^2 * (T - t)
        inventory_skew = q * self._gamma * sigma ** 2 * t_frac
        reservation_price = mid_price - inventory_skew

        # 2. Optimal spread
        #    spread = gamma * sigma^2 * (T-t) + (2/gamma) * ln(1 + gamma/kappa)
        gamma_term = self._gamma * sigma ** 2 * t_frac
        if self._gamma > 0 and self._kappa > 0:
            kappa_term = (2.0 / self._gamma) * math.log(1 + self._gamma / self._kappa)
        else:
            kappa_term = 0.0
        optimal_spread = gamma_term + kappa_term

        # Clamp spread to min/max
        min_spread = mid_price * self._min_spread_pct
        max_spread = mid_price * self._max_spread_pct
        optimal_spread = max(min_spread, min(optimal_spread, max_spread))

        # 3. Bid and ask
        bid_price = reservation_price - optimal_spread / 2
        ask_price = reservation_price + optimal_spread / 2

        # Inventory limit: if at max, don't quote the aggravating side
        if abs(inventory) >= self._max_inventory:
            if inventory > 0:
                bid_price = 0.0  # don't buy more
            else:
                ask_price = 0.0  # don't sell more

        return QuoteResult(
            bid_price=round(bid_price, 6),
            ask_price=round(ask_price, 6),
            reservation_price=round(reservation_price, 6),
            optimal_spread=round(optimal_spread, 6),
            inventory_skew=round(inventory_skew, 6),
        )

    def update_sigma(self, new_sigma: float) -> None:
        """Update volatility estimate (e.g. from RogersSatchell)."""
        self._sigma = new_sigma
