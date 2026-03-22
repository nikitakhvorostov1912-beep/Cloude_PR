"""Unified configuration loader for MOEX trading bot.

Loads settings from config/settings.yaml, validates via Pydantic,
and overlays environment variables from .env.
Singleton pattern — load once, use everywhere.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


# ── Sub-models ──────────────────────────────────────────────────────

class ProjectSettings(BaseModel):
    name: str = "moex-trading-bot"
    version: str = "0.2.0"


class MoexBoards(BaseModel):
    equities: str = "TQBR"
    futures: str = "RFUD"
    options: str = "ROPD"
    fx: str = "CETS"


class MoexSessions(BaseModel):
    main_start: str = "10:00"
    main_end: str = "18:40"
    evening_start: str = "19:05"
    evening_end: str = "23:50"
    clearing_1_start: str = "14:00"
    clearing_1_end: str = "14:05"
    clearing_2_start: str = "18:45"
    clearing_2_end: str = "19:00"
    auction_open_start: str = "09:50"
    auction_open_end: str = "10:00"
    auction_close_start: str = "18:40"
    auction_close_end: str = "18:50"


class MoexSettings(BaseModel):
    iss_url: str = "https://iss.moex.com/iss"
    max_requests_per_sec: int = Field(default=50, gt=0)
    boards: MoexBoards = Field(default_factory=MoexBoards)
    sessions: MoexSessions = Field(default_factory=MoexSessions)


class CostProfile(BaseModel):
    commission_pct: float = 0.0
    commission_rub: float = 0.0
    slippage_ticks: int = Field(default=1, ge=0)
    settlement: str = "T+1"


class CostsSettings(BaseModel):
    equity: CostProfile = Field(default_factory=CostProfile)
    futures: CostProfile = Field(default_factory=CostProfile)
    options: CostProfile = Field(default_factory=CostProfile)
    fx: CostProfile = Field(default_factory=CostProfile)


class RiskSettings(BaseModel):
    max_position_pct: float = Field(default=0.20, gt=0, lt=1)
    max_daily_drawdown_pct: float = Field(default=0.05, gt=0, lt=1)
    max_total_drawdown_pct: float = Field(default=0.15, gt=0, lt=1)
    max_correlated_exposure_pct: float = Field(default=0.40, gt=0, lt=1)
    circuit_breaker_daily_dd: float = Field(default=0.05, gt=0, lt=1)
    circuit_breaker_total_dd: float = Field(default=0.15, gt=0, lt=1)


class InstrumentInfo(BaseModel):
    lot: int = Field(default=1, ge=1)
    step: float = Field(default=0.01, gt=0)
    sector: str = ""
    go_pct: float = Field(default=0.0, ge=0)
    base: str = ""


class InstrumentsSettings(BaseModel):
    equities: dict[str, InstrumentInfo] = Field(default_factory=dict)
    futures: dict[str, InstrumentInfo] = Field(default_factory=dict)


class WalkForwardSettings(BaseModel):
    n_windows: int = Field(default=5, ge=1)
    train_ratio: float = Field(default=0.70, gt=0, lt=1)
    gap_bars: int = Field(default=1, ge=0)
    retrain_every_n_bars: int = Field(default=60, ge=1)


class BacktestSettings(BaseModel):
    default_capital: int = Field(default=1_000_000, gt=0)
    trading_days_per_year: int = Field(default=252, gt=0)
    benchmark: str = "IMOEX"
    min_sharpe_threshold: float = 1.0
    max_drawdown_threshold: float = Field(default=0.20, gt=0, le=1)
    min_trades_for_validity: int = Field(default=30, ge=1)
    walk_forward: WalkForwardSettings = Field(default_factory=WalkForwardSettings)


class FeatureSelectionSettings(BaseModel):
    method: str = "mutual_info"
    top_k: int = Field(default=50, ge=1)


class LabelSettings(BaseModel):
    method: str = "triple_barrier"
    take_profit_atr: float = Field(default=2.0, gt=0)
    stop_loss_atr: float = Field(default=1.5, gt=0)
    max_holding_bars: int = Field(default=20, ge=1)


class MLSettings(BaseModel):
    models: list[str] = Field(default_factory=lambda: ["catboost", "lightgbm", "xgboost"])
    ensemble_method: str = "stacking"
    feature_selection: FeatureSelectionSettings = Field(default_factory=FeatureSelectionSettings)
    label: LabelSettings = Field(default_factory=LabelSettings)


class LLMSettings(BaseModel):
    provider: str = "xiaomi"
    base_url: str = "https://api.xiaomimimo.com/v1"
    api_key_env: str = "XIAOMI_API_KEY"
    default_model: str = "MiMo-7B-RL"
    fallback_models: list[str] = Field(default_factory=lambda: ["MiMo-7B-RL"])
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=2000, gt=0)
    timeout: int = Field(default=30, gt=0)

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


class TelegramSettings(BaseModel):
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"
    alerts: list[str] = Field(default_factory=lambda: [
        "signal_generated", "order_filled", "stop_triggered",
        "circuit_breaker_activated", "daily_pnl_report",
    ])

    @property
    def bot_token(self) -> str | None:
        return os.environ.get(self.bot_token_env)

    @property
    def chat_id(self) -> str | None:
        return os.environ.get(self.chat_id_env)


class TinkoffSettings(BaseModel):
    token_env: str = "TINKOFF_TOKEN"
    sandbox: bool = True
    account_id_env: str = "TINKOFF_ACCOUNT_ID"

    @property
    def token(self) -> str | None:
        return os.environ.get(self.token_env)

    @property
    def account_id(self) -> str | None:
        return os.environ.get(self.account_id_env)


class BrokerSettings(BaseModel):
    default: str = "tinkoff"
    tinkoff: TinkoffSettings = Field(default_factory=TinkoffSettings)


# ── Root Settings ───────────────────────────────────────────────────

class Settings(BaseModel):
    """Root configuration model — single source of truth."""

    project: ProjectSettings = Field(default_factory=ProjectSettings)
    moex: MoexSettings = Field(default_factory=MoexSettings)
    costs: CostsSettings = Field(default_factory=CostsSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    instruments: InstrumentsSettings = Field(default_factory=InstrumentsSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    broker: BrokerSettings = Field(default_factory=BrokerSettings)

    # ── Convenience properties for main.py compatibility ──────────

    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO")

    @property
    def trading_mode(self) -> str:
        return os.environ.get("TRADING_MODE", "paper")

    @property
    def default_strategy(self) -> str:
        return os.environ.get("DEFAULT_STRATEGY", "conservative")

    @property
    def db_path(self) -> str:
        return os.environ.get("DB_PATH", "data/trading.db")

    @property
    def db_path_resolved(self) -> Path:
        return Path(self.db_path)

    @property
    def telegram_bot_token(self) -> str | None:
        return self.telegram.bot_token

    @property
    def telegram_chat_id(self) -> str | None:
        return self.telegram.chat_id

    @property
    def tinkoff_token(self) -> str | None:
        return self.broker.tinkoff.token

    @property
    def tinkoff_account_id(self) -> str | None:
        return self.broker.tinkoff.account_id

    # ── Lookup helpers ──────────────────────────────────────────

    def get_instrument_info(self, ticker: str) -> InstrumentInfo:
        """Get instrument info by ticker. Raises KeyError if not found."""
        if ticker in self.instruments.equities:
            return self.instruments.equities[ticker]
        if ticker in self.instruments.futures:
            return self.instruments.futures[ticker]
        raise KeyError(f"Unknown instrument: {ticker}")

    def get_cost_profile(self, instrument_type: str) -> CostProfile:
        """Get cost profile by instrument type."""
        profiles = {
            "equity": self.costs.equity,
            "futures": self.costs.futures,
            "options": self.costs.options,
            "fx": self.costs.fx,
        }
        if instrument_type not in profiles:
            raise KeyError(f"Unknown instrument type: {instrument_type}")
        return profiles[instrument_type]


# ── Loader ──────────────────────────────────────────────────────────

def _find_settings_yaml() -> Path:
    """Find settings.yaml relative to project root."""
    candidates = [
        Path("config/settings.yaml"),
        Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "config/settings.yaml not found. "
        f"Searched: {[str(c) for c in candidates]}"
    )


def load_settings(path: Path | str | None = None) -> Settings:
    """Load settings from YAML file and validate via Pydantic.

    Args:
        path: Explicit path to settings.yaml. Auto-discovered if None.

    Returns:
        Validated Settings instance.
    """
    if path is None:
        yaml_path = _find_settings_yaml()
    else:
        yaml_path = Path(path)

    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    # Overlay env vars for secrets
    _apply_env_overrides(raw)

    return Settings.model_validate(raw)


def _apply_env_overrides(raw: dict[str, Any]) -> None:
    """Apply environment variable overrides to raw config dict."""
    env_prefix = "MOEX_"
    for key, value in os.environ.items():
        if not key.startswith(env_prefix):
            continue
        parts = key[len(env_prefix):].lower().split("__")
        _set_nested(raw, parts, value)


def _set_nested(d: dict, keys: list[str], value: str) -> None:
    """Set a nested dict value from dot-separated keys."""
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    # Try numeric conversion
    try:
        d[keys[-1]] = int(value)
    except ValueError:
        try:
            d[keys[-1]] = float(value)
        except ValueError:
            d[keys[-1]] = value


@lru_cache(maxsize=1)
def get_config(path: str | None = None) -> Settings:
    """Get singleton config instance. Cached after first call."""
    return load_settings(path)


def reset_config() -> None:
    """Clear cached config (useful for testing)."""
    get_config.cache_clear()
