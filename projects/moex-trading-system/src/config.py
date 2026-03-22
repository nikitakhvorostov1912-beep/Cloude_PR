"""Compatibility shim — re-exports from src.core.config.

main.py imports from src.config; actual implementation lives in src.core.config.
"""
from src.core.config import (
    get_config as get_settings,
    load_settings,
    Settings,
    RiskSettings,
    LLMSettings,
    BrokerSettings,
)


def load_strategy_config(name: str = "conservative") -> dict:
    """Load strategy config from config/strategies/<name>.yaml.

    Falls back to sensible defaults if file not found.
    """
    from pathlib import Path
    import yaml

    candidates = [
        Path(f"config/strategies/{name}.yaml"),
        Path(__file__).resolve().parent.parent / "config" / "strategies" / f"{name}.yaml",
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    return {
        "name": name,
        "pre_score_threshold": 45.0,
        "confidence_threshold": 0.45,
        "atr_multiplier": 2.5,
        "risk_per_trade": 0.015,
        "max_position_pct": 0.15,
        "time_stop_days": 30,
    }


def load_tickers_config() -> dict:
    """Load tickers config from config/tickers.yaml.

    Falls back to sensible defaults if file not found.
    """
    from pathlib import Path
    import yaml

    candidates = [
        Path("config/tickers.yaml"),
        Path(__file__).resolve().parent.parent / "config" / "tickers.yaml",
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    return {"watchlist": []}


__all__ = [
    "get_settings",
    "load_settings",
    "load_strategy_config",
    "load_tickers_config",
    "Settings",
    "RiskSettings",
    "LLMSettings",
    "BrokerSettings",
]
