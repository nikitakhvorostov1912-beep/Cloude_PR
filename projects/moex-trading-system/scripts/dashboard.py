"""Streamlit dashboard for monitoring live/paper trading.

Usage:
    streamlit run scripts/dashboard.py

Panels:
1. Portfolio overview — total value, cash, exposure
2. Open positions — table with P&L
3. Equity curve — daily chart
4. Drawdown chart — underwater plot
5. Today's trades — entry/exit/P&L
6. Strategy performance — Sharpe, DD, Win Rate per strategy
7. Risk status — circuit breaker, exposure limits
8. Last signals — recent signals with confidence
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st

from src.core.config import load_settings


def _generate_demo_data() -> dict:
    """Generate demo data for dashboard display."""
    np.random.seed(42)
    n_days = 252

    # Equity curve
    returns = np.random.normal(0.0005, 0.015, n_days)
    equity = 1_000_000 * np.cumprod(1 + returns)
    dates = pd.date_range(start="2024-01-01", periods=n_days, freq="B")

    # Drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak

    # Positions
    positions = pd.DataFrame({
        "Instrument": ["SBER", "GAZP", "LKOH"],
        "Side": ["LONG", "LONG", "SHORT"],
        "Qty": [100, 200, 50],
        "Entry": [250.50, 160.30, 6800.00],
        "Current": [265.10, 158.20, 6650.00],
        "P&L RUB": [1460.0, -420.0, 7500.0],
        "P&L %": [5.83, -1.31, 2.21],
    })

    # Today's trades
    trades = pd.DataFrame({
        "Time": ["10:15", "11:30", "14:45"],
        "Instrument": ["SBER", "GAZP", "LKOH"],
        "Side": ["BUY", "SELL", "BUY"],
        "Qty": [100, 50, 10],
        "Price": [250.50, 161.20, 6800.00],
        "P&L": ["+1,460", "-105", "0"],
    })

    # Signals
    signals = pd.DataFrame({
        "Time": ["09:55", "10:10", "11:25", "14:40"],
        "Instrument": ["SBER", "GAZP", "LKOH", "YNDX"],
        "Direction": ["LONG", "SHORT", "LONG", "LONG"],
        "Strength": [0.85, 0.62, 0.78, 0.55],
        "Confidence": [0.75, 0.60, 0.70, 0.50],
        "Strategy": ["ema_cross", "ema_cross", "ema_cross", "ml_ensemble"],
    })

    return {
        "equity": pd.Series(equity, index=dates),
        "drawdown": pd.Series(drawdown, index=dates),
        "positions": positions,
        "trades": trades,
        "signals": signals,
        "portfolio_value": equity[-1],
        "cash": 850_000,
        "daily_pnl": equity[-1] - equity[-2],
    }


def main() -> None:
    """Render the Streamlit dashboard."""
    st.set_page_config(
        page_title="MOEX Trading Bot",
        page_icon="\U0001F4C8",
        layout="wide",
    )

    st.title("\U0001F4C8 MOEX Trading Bot — Dashboard")

    try:
        cfg = load_settings()
        st.caption(f"v{cfg.project.version} | Benchmark: {cfg.backtest.benchmark}")
    except FileNotFoundError:
        st.caption("Config not found — using demo data")

    data = _generate_demo_data()

    # ── Row 1: KPI cards ────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Portfolio Value", f"{data['portfolio_value']:,.0f} RUB")
    with col2:
        st.metric("Cash", f"{data['cash']:,.0f} RUB")
    with col3:
        exposure = 1 - data["cash"] / data["portfolio_value"]
        st.metric("Exposure", f"{exposure * 100:.1f}%")
    with col4:
        st.metric("Daily P&L", f"{data['daily_pnl']:+,.0f} RUB")

    # ── Row 2: Charts ───────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Equity Curve")
        st.line_chart(data["equity"])

    with col_right:
        st.subheader("Drawdown")
        st.area_chart(data["drawdown"])

    # ── Row 3: Positions & Trades ───────────────────────────
    col_pos, col_trades = st.columns(2)

    with col_pos:
        st.subheader("Open Positions")
        st.dataframe(data["positions"], use_container_width=True, hide_index=True)

    with col_trades:
        st.subheader("Today's Trades")
        st.dataframe(data["trades"], use_container_width=True, hide_index=True)

    # ── Row 4: Signals & Risk ───────────────────────────────
    col_sig, col_risk = st.columns(2)

    with col_sig:
        st.subheader("Recent Signals")
        st.dataframe(data["signals"], use_container_width=True, hide_index=True)

    with col_risk:
        st.subheader("Risk Status")
        st.markdown("""
        | Metric | Value | Limit | Status |
        |--------|-------|-------|--------|
        | Daily DD | 1.2% | 5.0% | OK |
        | Total DD | 3.8% | 15.0% | OK |
        | Max Position | 18.5% | 20.0% | OK |
        | Corr Exposure | 25.0% | 40.0% | OK |
        | Circuit Breaker | — | 5.0% DD | INACTIVE |
        """)

    # ── Strategy Performance ────────────────────────────────
    st.subheader("Strategy Performance")
    perf = pd.DataFrame({
        "Strategy": ["ema_crossover", "ml_ensemble"],
        "Sharpe": [1.25, 0.85],
        "Max DD": ["12.5%", "15.2%"],
        "Win Rate": ["55%", "52%"],
        "Trades": [48, 32],
        "Avg P&L": ["+850 RUB", "+420 RUB"],
    })
    st.dataframe(perf, use_container_width=True, hide_index=True)

    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
