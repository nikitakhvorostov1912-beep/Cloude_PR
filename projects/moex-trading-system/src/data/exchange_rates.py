"""Exchange rate cache for multi-currency P&L conversion via MOEX ISS API.

Inspired by Ghostfolio ExchangeRateDataService (AGPL — written from scratch).
Fetches historical and current FX rates from MOEX ISS (free, no API key needed).

Supported pairs: USD/RUB, EUR/RUB, CNY/RUB (MOEX official fixing).
Cache: in-memory dict with optional file persistence.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MOEX ISS endpoints
# ---------------------------------------------------------------------------

_ISS_BASE = "https://iss.moex.com/iss"
_FX_FIXING_URL = (
    _ISS_BASE + "/statistics/engines/currency/markets/fixing/securities/{pair}.json"
    "?iss.meta=off&iss.only=history&history.columns=TRADEDATE,RATE"
    "&from={from_date}&till={till_date}"
)
_FX_CURRENT_URL = (
    _ISS_BASE + "/statistics/engines/currency/markets/fixing.json"
    "?iss.meta=off&iss.only=securities&securities.columns=SECID,RATE"
)

# MOEX ISS FX pair names
PAIR_MAP: dict[str, str] = {
    "USDRUB": "USD/RUB",
    "EURRUB": "EUR/RUB",
    "CNYRUB": "CNY/RUB",
}

INVERSE_MAP: dict[str, str] = {
    "RUBUSD": "USDRUB",
    "RUBEUR": "EURRUB",
    "RUBCNY": "CNYRUB",
}


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

@dataclass
class ExchangeRateCache:
    """In-memory cache of FX rates with MOEX ISS fetching.

    Usage:
        cache = ExchangeRateCache()
        rate = cache.get_rate("USD", "RUB", date(2024, 6, 15))
        converted = cache.convert(1000, "USD", "RUB", date(2024, 6, 15))

    Rates are cached per (pair, date) and optionally persisted to JSON file.
    """

    # {pair: {date_str: rate}} e.g. {"USDRUB": {"2024-06-15": 89.25}}
    _cache: dict[str, dict[str, float]] = field(default_factory=dict)
    cache_file: str | None = None
    _loaded: bool = False

    def __post_init__(self):
        if self.cache_file and os.path.exists(self.cache_file):
            self._load_from_file()

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def get_rate(
        self,
        currency_from: str,
        currency_to: str,
        on_date: date | None = None,
    ) -> float | None:
        """Get exchange rate for a currency pair on a specific date.

        Args:
            currency_from: Source currency (e.g. "USD").
            currency_to: Target currency (e.g. "RUB").
            on_date: Date for historical rate (None = today).

        Returns:
            Exchange rate or None if not available.
        """
        if currency_from == currency_to:
            return 1.0

        pair = f"{currency_from}{currency_to}".upper()
        is_inverse = False

        # Check if we need the inverse pair
        if pair in INVERSE_MAP:
            pair = INVERSE_MAP[pair]
            is_inverse = True

        if pair not in PAIR_MAP:
            logger.warning("Unsupported FX pair: %s%s", currency_from, currency_to)
            return None

        date_str = (on_date or date.today()).isoformat()

        # Check cache first
        if pair in self._cache and date_str in self._cache[pair]:
            rate = self._cache[pair][date_str]
            return 1.0 / rate if is_inverse else rate

        # Fetch from MOEX ISS
        rate = self._fetch_rate(pair, on_date or date.today())
        if rate is not None:
            self._cache_rate(pair, date_str, rate)
            return 1.0 / rate if is_inverse else rate

        # Try nearest available date (weekends/holidays)
        rate = self._find_nearest_rate(pair, on_date or date.today())
        if rate is not None:
            return 1.0 / rate if is_inverse else rate

        return None

    def convert(
        self,
        amount: float,
        currency_from: str,
        currency_to: str,
        on_date: date | None = None,
    ) -> float | None:
        """Convert amount between currencies.

        Returns:
            Converted amount or None if rate unavailable.
        """
        rate = self.get_rate(currency_from, currency_to, on_date)
        if rate is None:
            return None
        return amount * rate

    def get_rates_range(
        self,
        currency_from: str,
        currency_to: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, float]:
        """Get exchange rates for a date range.

        Returns:
            Dict of {date_iso: rate} for all available dates in range.
        """
        pair = f"{currency_from}{currency_to}".upper()
        is_inverse = False
        if pair in INVERSE_MAP:
            pair = INVERSE_MAP[pair]
            is_inverse = True

        if pair not in PAIR_MAP:
            return {}

        rates = self._fetch_range(pair, start_date, end_date)

        if is_inverse:
            return {d: 1.0 / r for d, r in rates.items() if r != 0}
        return rates

    def preload(
        self,
        pairs: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """Preload rates into cache for given pairs and date range.

        Args:
            pairs: List of pairs like ["USDRUB", "EURRUB"]. None = all supported.
            start_date: Start of range (default: 1 year ago).
            end_date: End of range (default: today).

        Returns:
            Number of rates loaded.
        """
        pairs = pairs or list(PAIR_MAP.keys())
        start = start_date or (date.today() - timedelta(days=365))
        end = end_date or date.today()

        total = 0
        for pair in pairs:
            if pair not in PAIR_MAP:
                continue
            rates = self._fetch_range(pair, start, end)
            total += len(rates)

        if self.cache_file:
            self._save_to_file()

        logger.info("Preloaded %d FX rates for %s", total, pairs)
        return total

    # ---------------------------------------------------------------------------
    # MOEX ISS fetching
    # ---------------------------------------------------------------------------

    def _fetch_rate(self, pair: str, on_date: date) -> float | None:
        """Fetch a single rate from MOEX ISS."""
        try:
            import requests
        except ImportError:
            logger.error("requests library not installed")
            return None

        iss_pair = PAIR_MAP[pair]
        url = _FX_FIXING_URL.format(
            pair=iss_pair,
            from_date=on_date.isoformat(),
            till_date=on_date.isoformat(),
        )

        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("history", {}).get("data", [])
            if rows:
                return float(rows[0][1])
        except Exception as e:
            logger.debug("MOEX ISS fetch failed for %s on %s: %s", pair, on_date, e)

        return None

    def _fetch_range(self, pair: str, start_date: date, end_date: date) -> dict[str, float]:
        """Fetch rates for a date range from MOEX ISS."""
        try:
            import requests
        except ImportError:
            return {}

        iss_pair = PAIR_MAP[pair]
        url = _FX_FIXING_URL.format(
            pair=iss_pair,
            from_date=start_date.isoformat(),
            till_date=end_date.isoformat(),
        )

        rates: dict[str, float] = {}
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for row in data.get("history", {}).get("data", []):
                date_str = row[0]
                rate = float(row[1])
                rates[date_str] = rate
                self._cache_rate(pair, date_str, rate)
        except Exception as e:
            logger.warning("MOEX ISS range fetch failed for %s: %s", pair, e)

        return rates

    def _find_nearest_rate(self, pair: str, target_date: date, max_days: int = 7) -> float | None:
        """Find nearest available rate within max_days (for weekends/holidays)."""
        # Check cache first
        for offset in range(1, max_days + 1):
            for delta in (-offset, offset):
                check_date = target_date + timedelta(days=delta)
                date_str = check_date.isoformat()
                if pair in self._cache and date_str in self._cache[pair]:
                    return self._cache[pair][date_str]

        # Try fetching a range around the target date
        start = target_date - timedelta(days=max_days)
        rates = self._fetch_range(pair, start, target_date)
        if rates:
            # Return the most recent available rate
            sorted_dates = sorted(rates.keys(), reverse=True)
            return rates[sorted_dates[0]]

        return None

    # ---------------------------------------------------------------------------
    # Cache management
    # ---------------------------------------------------------------------------

    def _cache_rate(self, pair: str, date_str: str, rate: float) -> None:
        """Store rate in in-memory cache."""
        if pair not in self._cache:
            self._cache[pair] = {}
        self._cache[pair][date_str] = rate

    def _save_to_file(self) -> None:
        """Persist cache to JSON file."""
        if not self.cache_file:
            return
        try:
            Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save FX cache: %s", e)

    def _load_from_file(self) -> None:
        """Load cache from JSON file."""
        if not self.cache_file or not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file) as f:
                self._cache = json.load(f)
            self._loaded = True
            total = sum(len(v) for v in self._cache.values())
            logger.info("Loaded %d FX rates from cache file", total)
        except Exception as e:
            logger.warning("Failed to load FX cache: %s", e)

    @property
    def cache_size(self) -> int:
        """Total number of cached rates."""
        return sum(len(v) for v in self._cache.values())

    def clear(self) -> None:
        """Clear all cached rates."""
        self._cache.clear()
