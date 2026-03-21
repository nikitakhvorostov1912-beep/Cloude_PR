"""Tests for GARCH volatility forecasting and Limit Order Book."""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.limit_order_book import LimitOrderBook, BookSnapshot


# ===========================================================================
# GARCH — 7 tests (conditional on arch installed)
# ===========================================================================

try:
    import arch as _arch_lib  # noqa: F401
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

if HAS_ARCH:
    from src.indicators.garch_forecast import (
        forecast_volatility, compare_garch_models, VolForecast,
    )


@pytest.mark.skipif(not HAS_ARCH, reason="arch package not installed")
class TestGARCH:

    @pytest.fixture
    def returns(self):
        rng = np.random.default_rng(42)
        return rng.normal(0.0005, 0.02, 500)

    def test_garch_returns_forecast(self, returns):
        vf = forecast_volatility(returns, model="garch")
        assert isinstance(vf, VolForecast)
        assert vf.daily_vol > 0
        assert vf.annualized_vol > vf.daily_vol

    def test_ewma_returns_forecast(self, returns):
        vf = forecast_volatility(returns, model="ewma")
        assert vf.daily_vol > 0
        assert vf.model_name == "ewma"

    def test_egarch_returns_forecast(self, returns):
        vf = forecast_volatility(returns, model="egarch")
        assert vf.daily_vol > 0

    def test_gjr_returns_forecast(self, returns):
        vf = forecast_volatility(returns, model="gjr")
        assert vf.daily_vol > 0

    def test_short_returns(self):
        vf = forecast_volatility(np.array([0.01, -0.01]))
        assert vf.daily_vol == 0.0  # too short

    def test_horizon(self, returns):
        vf1 = forecast_volatility(returns, horizon=1)
        vf5 = forecast_volatility(returns, horizon=5)
        assert vf1.horizon == 1
        assert vf5.horizon == 5

    def test_compare_models(self, returns):
        results = compare_garch_models(returns)
        assert len(results) >= 2  # at least garch + ewma
        # Sorted by AIC
        for i in range(1, len(results)):
            assert results[i].aic >= results[i - 1].aic


# ===========================================================================
# Limit Order Book — 15 tests
# ===========================================================================


class TestLimitOrderBook:

    def test_empty_book(self):
        book = LimitOrderBook()
        assert book.best_bid == 0.0
        assert book.best_ask == 0.0
        assert book.mid_price == 0.0
        assert book.spread == 0.0

    def test_add_bid(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        assert book.best_bid == 300.0

    def test_add_ask(self):
        book = LimitOrderBook()
        book.update_level("ask", 301.0, 500)
        assert book.best_ask == 301.0

    def test_spread(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("ask", 300.5, 800)
        assert book.spread == 0.5
        assert abs(book.mid_price - 300.25) < 0.001

    def test_spread_pct(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("ask", 301.0, 800)
        assert abs(book.spread_pct - 1.0 / 300.5) < 0.0001

    def test_remove_level(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("bid", 300.0, 0)  # remove
        assert book.best_bid == 0.0

    def test_multiple_bid_levels(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("bid", 299.5, 500)
        book.update_level("bid", 299.0, 200)
        assert book.best_bid == 300.0
        levels = book.bid_levels(3)
        assert len(levels) == 3
        assert levels[0] == (300.0, 1000)
        assert levels[1] == (299.5, 500)

    def test_ask_levels_ascending(self):
        book = LimitOrderBook()
        book.update_level("ask", 301.0, 500)
        book.update_level("ask", 300.5, 800)
        book.update_level("ask", 302.0, 200)
        levels = book.ask_levels(3)
        assert levels[0] == (300.5, 800)  # lowest first
        assert levels[1] == (301.0, 500)

    def test_obi_equal(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("ask", 301.0, 1000)
        assert book.obi() == 0.0

    def test_obi_bid_heavy(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 2000)
        book.update_level("ask", 301.0, 500)
        assert book.obi() > 0

    def test_obi_ask_heavy(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 200)
        book.update_level("ask", 301.0, 1000)
        assert book.obi() < 0

    def test_microprice(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("ask", 301.0, 200)
        mp = book.microprice
        # bid_vol >> ask_vol → microprice closer to ask
        assert mp > 300.5

    def test_snapshot(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("ask", 301.0, 500)
        snap = book.snapshot()
        assert isinstance(snap, BookSnapshot)
        assert snap.best_bid == 300.0
        assert snap.best_ask == 301.0
        assert snap.n_bid_levels == 1
        assert snap.n_ask_levels == 1

    def test_apply_snapshot(self):
        book = LimitOrderBook()
        book.apply_snapshot(
            bids=[(300.0, 1000), (299.5, 500)],
            asks=[(301.0, 800), (301.5, 200)],
        )
        assert book.best_bid == 300.0
        assert book.best_ask == 301.0
        assert len(book.bid_levels()) == 2
        assert len(book.ask_levels()) == 2

    def test_clear(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.clear()
        assert book.best_bid == 0.0

    def test_volume_at_price(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1234)
        assert book.volume_at_price("bid", 300.0) == 1234
        assert book.volume_at_price("bid", 299.0) == 0.0

    def test_depth_up_to(self):
        book = LimitOrderBook()
        book.update_level("bid", 300.0, 1000)
        book.update_level("bid", 298.0, 500)   # 0.67% from best
        book.update_level("bid", 290.0, 200)   # 3.3% from best
        vol_1pct = book.depth_up_to("bid", 0.01)  # within 1%
        assert vol_1pct == 1500  # 300 + 298, not 290
