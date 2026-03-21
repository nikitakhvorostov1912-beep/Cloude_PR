"""Tests for src/data/exchange_rates.py — FX rate cache (unit tests, no network)."""
from __future__ import annotations

import json
import sys
import os
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.exchange_rates import ExchangeRateCache, PAIR_MAP, INVERSE_MAP


# ---------------------------------------------------------------------------
# Unit tests (no network — test cache logic only)
# ---------------------------------------------------------------------------


class TestCacheBasics:
    def test_same_currency(self):
        cache = ExchangeRateCache()
        assert cache.get_rate("RUB", "RUB") == 1.0
        assert cache.get_rate("USD", "USD") == 1.0

    def test_manual_cache_and_retrieve(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-15", 89.25)
        rate = cache.get_rate("USD", "RUB", date(2024, 6, 15))
        assert rate == 89.25

    def test_inverse_rate(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-15", 89.25)
        rate = cache.get_rate("RUB", "USD", date(2024, 6, 15))
        assert rate is not None
        assert abs(rate - 1.0 / 89.25) < 1e-10

    def test_convert(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-15", 90.0)
        result = cache.convert(100, "USD", "RUB", date(2024, 6, 15))
        assert result == 9000.0

    def test_convert_inverse(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-15", 90.0)
        result = cache.convert(9000, "RUB", "USD", date(2024, 6, 15))
        assert result is not None
        assert abs(result - 100.0) < 0.01

    def test_unsupported_pair(self):
        cache = ExchangeRateCache()
        assert cache.get_rate("GBP", "RUB") is None

    def test_cache_size(self):
        cache = ExchangeRateCache()
        assert cache.cache_size == 0
        cache._cache_rate("USDRUB", "2024-06-15", 89.0)
        cache._cache_rate("USDRUB", "2024-06-16", 89.5)
        cache._cache_rate("EURRUB", "2024-06-15", 96.0)
        assert cache.cache_size == 3

    def test_clear(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-15", 89.0)
        cache.clear()
        assert cache.cache_size == 0

    def test_nearest_rate_from_cache(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-14", 89.0)  # Friday
        # Saturday/Sunday should find Friday's rate
        rate = cache._find_nearest_rate("USDRUB", date(2024, 6, 15), max_days=3)
        assert rate == 89.0


class TestFilePersistence:
    def test_save_and_load(self, tmp_path):
        cache_file = str(tmp_path / "fx_cache.json")

        # Save
        cache1 = ExchangeRateCache(cache_file=cache_file)
        cache1._cache_rate("USDRUB", "2024-06-15", 89.25)
        cache1._cache_rate("EURRUB", "2024-06-15", 96.50)
        cache1._save_to_file()

        # Load in new instance
        cache2 = ExchangeRateCache(cache_file=cache_file)
        assert cache2.cache_size == 2
        assert cache2.get_rate("USD", "RUB", date(2024, 6, 15)) == 89.25
        assert cache2.get_rate("EUR", "RUB", date(2024, 6, 15)) == 96.50


class TestPairMapping:
    def test_supported_pairs(self):
        assert "USDRUB" in PAIR_MAP
        assert "EURRUB" in PAIR_MAP
        assert "CNYRUB" in PAIR_MAP

    def test_inverse_mapping(self):
        assert "RUBUSD" in INVERSE_MAP
        assert INVERSE_MAP["RUBUSD"] == "USDRUB"

    def test_eur_rate(self):
        cache = ExchangeRateCache()
        cache._cache_rate("EURRUB", "2024-06-15", 96.50)
        assert cache.get_rate("EUR", "RUB", date(2024, 6, 15)) == 96.50

    def test_cny_rate(self):
        cache = ExchangeRateCache()
        cache._cache_rate("CNYRUB", "2024-06-15", 12.30)
        assert cache.get_rate("CNY", "RUB", date(2024, 6, 15)) == 12.30


class TestRatesRange:
    def test_cached_range(self):
        cache = ExchangeRateCache()
        cache._cache_rate("USDRUB", "2024-06-10", 88.0)
        cache._cache_rate("USDRUB", "2024-06-11", 88.5)
        cache._cache_rate("USDRUB", "2024-06-12", 89.0)
        # get_rates_range will attempt network call, but cached values should be there
        # For unit test, directly check cache
        assert "2024-06-10" in cache._cache.get("USDRUB", {})
        assert "2024-06-12" in cache._cache.get("USDRUB", {})
