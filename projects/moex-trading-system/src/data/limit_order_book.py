"""Lightweight Limit Order Book for MOEX market data.

Inspired by PyLimitBook (danielktaylor, unlicensed) architecture.
Written from scratch using sortedcontainers (no bintrees dependency).

Maintains a sorted order book with O(log N) insert/remove/update.
Provides best bid/ask, spread, OBI, microprice, depth snapshots.

For MOEX: feed L2 data from ASTS Gateway or MOEX ISS WebSocket.

Usage:
    book = LimitOrderBook()
    book.update_level("bid", 300.0, 1000)
    book.update_level("bid", 299.5, 500)
    book.update_level("ask", 300.5, 800)

    print(book.best_bid)      # 300.0
    print(book.spread)        # 0.5
    print(book.obi(5))        # order book imbalance at 5 levels
    print(book.microprice)    # volume-weighted fair price
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sortedcontainers import SortedDict


@dataclass(frozen=True)
class BookSnapshot:
    """Order book snapshot at a point in time.

    Attributes:
        best_bid: Highest bid price.
        best_ask: Lowest ask price.
        mid_price: (bid + ask) / 2.
        spread: ask - bid.
        spread_pct: spread / mid.
        bid_depth: Total bid volume across all levels.
        ask_depth: Total ask volume across all levels.
        obi: Order Book Imbalance at all levels.
        microprice: Volume-weighted fair price.
        n_bid_levels: Number of bid price levels.
        n_ask_levels: Number of ask price levels.
    """

    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_pct: float
    bid_depth: float
    ask_depth: float
    obi: float
    microprice: float
    n_bid_levels: int
    n_ask_levels: int


class LimitOrderBook:
    """In-memory limit order book with sorted price levels.

    Bids stored in descending order (highest first).
    Asks stored in ascending order (lowest first).
    Uses SortedDict for O(log N) operations.

    Args:
        tick_size: Minimum price increment (e.g. 0.01 for SBER).
    """

    def __init__(self, tick_size: float = 0.01) -> None:
        # Bids: negate keys for descending order in SortedDict
        self._bids: SortedDict = SortedDict()  # key = -price → volume
        self._asks: SortedDict = SortedDict()  # key = price → volume
        self._tick_size = tick_size

    # --- Updates ---

    def update_level(
        self,
        side: Literal["bid", "ask"],
        price: float,
        volume: float,
    ) -> None:
        """Insert or update a price level. Volume=0 removes the level."""
        if side == "bid":
            key = -price
            if volume <= 0:
                self._bids.pop(key, None)
            else:
                self._bids[key] = volume
        else:
            key = price
            if volume <= 0:
                self._asks.pop(key, None)
            else:
                self._asks[key] = volume

    def clear(self) -> None:
        """Clear entire book (e.g. on reconnect)."""
        self._bids.clear()
        self._asks.clear()

    def apply_snapshot(
        self,
        bids: list[tuple[float, float]],
        asks: list[tuple[float, float]],
    ) -> None:
        """Replace entire book from snapshot.

        Args:
            bids: List of (price, volume) tuples.
            asks: List of (price, volume) tuples.
        """
        self._bids.clear()
        self._asks.clear()
        for price, vol in bids:
            if vol > 0:
                self._bids[-price] = vol
        for price, vol in asks:
            if vol > 0:
                self._asks[price] = vol

    # --- Queries ---

    @property
    def best_bid(self) -> float:
        """Highest bid price (0 if empty)."""
        if not self._bids:
            return 0.0
        return -self._bids.keys()[0]

    @property
    def best_ask(self) -> float:
        """Lowest ask price (0 if empty)."""
        if not self._asks:
            return 0.0
        return self._asks.keys()[0]

    @property
    def mid_price(self) -> float:
        bb, ba = self.best_bid, self.best_ask
        if bb <= 0 or ba <= 0:
            return 0.0
        return (bb + ba) / 2

    @property
    def spread(self) -> float:
        bb, ba = self.best_bid, self.best_ask
        if bb <= 0 or ba <= 0:
            return 0.0
        return ba - bb

    @property
    def spread_pct(self) -> float:
        mid = self.mid_price
        if mid <= 0:
            return 0.0
        return self.spread / mid

    @property
    def microprice(self) -> float:
        """Volume-weighted fair price from best bid/ask."""
        bb, ba = self.best_bid, self.best_ask
        if bb <= 0 or ba <= 0:
            return self.mid_price
        bv = self._bids.values()[0] if self._bids else 0
        av = self._asks.values()[0] if self._asks else 0
        total = bv + av
        if total <= 0:
            return self.mid_price
        return (bb * av + ba * bv) / total

    def bid_levels(self, n: int | None = None) -> list[tuple[float, float]]:
        """Top N bid levels as (price, volume), descending by price."""
        items = list(self._bids.items())[:n]
        return [(-k, v) for k, v in items]

    def ask_levels(self, n: int | None = None) -> list[tuple[float, float]]:
        """Top N ask levels as (price, volume), ascending by price."""
        return list(self._asks.items())[:n]

    def obi(self, n_levels: int = 5) -> float:
        """Order Book Imbalance at N levels depth."""
        bid_vol = sum(v for _, v in self.bid_levels(n_levels))
        ask_vol = sum(v for _, v in self.ask_levels(n_levels))
        total = bid_vol + ask_vol
        if total <= 0:
            return 0.0
        return (bid_vol - ask_vol) / total

    @property
    def total_bid_volume(self) -> float:
        return sum(self._bids.values())

    @property
    def total_ask_volume(self) -> float:
        return sum(self._asks.values())

    def snapshot(self) -> BookSnapshot:
        """Full snapshot of current book state."""
        bb = self.best_bid
        ba = self.best_ask
        mid = (bb + ba) / 2 if bb > 0 and ba > 0 else 0.0
        spr = ba - bb if bb > 0 and ba > 0 else 0.0
        spr_pct = spr / mid if mid > 0 else 0.0
        bid_d = self.total_bid_volume
        ask_d = self.total_ask_volume

        return BookSnapshot(
            best_bid=bb, best_ask=ba,
            mid_price=mid, spread=spr, spread_pct=spr_pct,
            bid_depth=bid_d, ask_depth=ask_d,
            obi=self.obi(), microprice=self.microprice,
            n_bid_levels=len(self._bids),
            n_ask_levels=len(self._asks),
        )

    def volume_at_price(
        self, side: Literal["bid", "ask"], price: float,
    ) -> float:
        """Volume at specific price level."""
        if side == "bid":
            return self._bids.get(-price, 0.0)
        return self._asks.get(price, 0.0)

    def depth_up_to(
        self, side: Literal["bid", "ask"], depth_pct: float = 0.01,
    ) -> float:
        """Cumulative volume within depth_pct of best price."""
        if side == "bid":
            best = self.best_bid
            if best <= 0:
                return 0.0
            threshold = best * (1 - depth_pct)
            return sum(
                v for k, v in self._bids.items() if -k >= threshold
            )
        else:
            best = self.best_ask
            if best <= 0:
                return 0.0
            threshold = best * (1 + depth_pct)
            return sum(
                v for k, v in self._asks.items() if k <= threshold
            )
