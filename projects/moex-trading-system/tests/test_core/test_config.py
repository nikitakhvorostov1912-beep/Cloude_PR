"""Tests for src/core/config.py — unified config loader."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.core.config import Settings, load_settings, get_config, reset_config

SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Reset singleton cache before each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def config() -> Settings:
    return load_settings(SETTINGS_PATH)


class TestLoadSettings:
    def test_load_settings(self, config: Settings):
        """settings.yaml loads without errors."""
        assert config is not None
        assert isinstance(config, Settings)

    def test_moex_section(self, config: Settings):
        """All MOEX fields present."""
        assert config.moex.iss_url == "https://iss.moex.com/iss"
        assert config.moex.max_requests_per_sec == 50
        assert config.moex.boards.equities == "TQBR"
        assert config.moex.boards.futures == "RFUD"
        assert config.moex.boards.options == "ROPD"
        assert config.moex.boards.fx == "CETS"
        assert config.moex.sessions.main_start == "10:00"
        assert config.moex.sessions.main_end == "18:40"
        assert config.moex.sessions.clearing_1_start == "14:00"

    def test_costs_section(self, config: Settings):
        """Commissions for all 4 instrument types."""
        assert config.costs.equity.commission_pct == 0.0001
        assert config.costs.equity.settlement == "T+1"
        assert config.costs.futures.commission_rub == 2.0
        assert config.costs.futures.settlement == "T+0"
        assert config.costs.options.commission_rub == 2.0
        assert config.costs.fx.commission_pct == 0.00003

    def test_instruments(self, config: Settings):
        """All 15 equities and 5 futures present."""
        assert len(config.instruments.equities) == 15
        assert len(config.instruments.futures) == 5
        assert "SBER" in config.instruments.equities
        assert "GAZP" in config.instruments.equities
        assert "Si" in config.instruments.futures
        assert "RTS" in config.instruments.futures

    def test_risk_limits(self, config: Settings):
        """All risk limits > 0 and < 1."""
        assert 0 < config.risk.max_position_pct < 1
        assert 0 < config.risk.max_daily_drawdown_pct < 1
        assert 0 < config.risk.max_total_drawdown_pct < 1
        assert 0 < config.risk.max_correlated_exposure_pct < 1
        assert 0 < config.risk.circuit_breaker_daily_dd < 1
        assert 0 < config.risk.circuit_breaker_total_dd < 1

    def test_get_instrument_info(self, config: Settings):
        """SBER returns correct lot and step."""
        info = config.get_instrument_info("SBER")
        assert info.lot == 10
        assert info.step == 0.01
        assert info.sector == "banks"

    def test_get_instrument_info_futures(self, config: Settings):
        """Si returns correct step and go_pct."""
        info = config.get_instrument_info("Si")
        assert info.step == 1.0
        assert info.go_pct == 0.15

    def test_unknown_instrument(self, config: Settings):
        """Unknown ticker raises KeyError."""
        with pytest.raises(KeyError, match="Unknown instrument"):
            config.get_instrument_info("NONEXISTENT")

    def test_env_override(self, config: Settings):
        """Environment variables override YAML values."""
        os.environ["MOEX_moex__max_requests_per_sec"] = "100"
        try:
            cfg = load_settings(SETTINGS_PATH)
            assert cfg.moex.max_requests_per_sec == 100
        finally:
            del os.environ["MOEX_moex__max_requests_per_sec"]

    def test_get_cost_profile(self, config: Settings):
        """Get cost profile by instrument type."""
        eq = config.get_cost_profile("equity")
        assert eq.commission_pct == 0.0001
        fut = config.get_cost_profile("futures")
        assert fut.commission_rub == 2.0
        with pytest.raises(KeyError):
            config.get_cost_profile("crypto")

    def test_backtest_settings(self, config: Settings):
        """Backtest settings loaded correctly."""
        assert config.backtest.default_capital == 1_000_000
        assert config.backtest.trading_days_per_year == 252
        assert config.backtest.benchmark == "IMOEX"
        assert config.backtest.walk_forward.n_windows == 5
        assert config.backtest.walk_forward.train_ratio == 0.70

    def test_ml_settings(self, config: Settings):
        """ML settings loaded correctly."""
        assert "catboost" in config.ml.models
        assert config.ml.ensemble_method == "stacking"
        assert config.ml.label.method == "triple_barrier"
        assert config.ml.feature_selection.top_k == 50

    def test_singleton_get_config(self):
        """get_config returns same instance on repeated calls."""
        c1 = get_config(str(SETTINGS_PATH))
        c2 = get_config(str(SETTINGS_PATH))
        assert c1 is c2

    def test_file_not_found(self):
        """Missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_settings("/nonexistent/path.yaml")
