# -*- coding: utf-8 -*-
"""Run ALL pipeline modes on ALL tickers, produce FULL_COMPARISON_REPORT.md."""
from __future__ import annotations

import math
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import requests
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.unified_pipeline import UnifiedPipeline, BacktestResult

TICKERS = ["SBER", "GAZP", "LKOH", "ROSN", "GMKN", "YNDX", "VTBR", "NVTK", "MGNT", "TATN"]
MODES = ["ema_only", "ema_scoring", "ema_regime", "full_ensemble", "buy_hold"]
START, END = "2022-01-01", "2025-12-31"
ISS = "https://iss.moex.com/iss"


def fetch(ticker, board="TQBR", engine="stock", market="shares"):
    rows, page = [], 0
    while True:
        url = f"{ISS}/engines/{engine}/markets/{market}/boards/{board}/securities/{ticker}/candles.json"
        params = {"from": START, "till": END, "interval": 24, "start": page, "iss.meta": "off", "iss.json": "extended"}
        try:
            r = requests.get(url, params=params, timeout=30)
            data = r.json()
        except Exception:
            break
        candles = []
        if isinstance(data, list):
            for b in data:
                if isinstance(b, dict) and "candles" in b:
                    candles = b["candles"]
                    break
        if not candles:
            break
        for c in candles:
            if isinstance(c, dict):
                rows.append({"timestamp": c.get("begin",""), "open": float(c.get("open",0)),
                    "high": float(c.get("high",0)), "low": float(c.get("low",0)),
                    "close": float(c.get("close",0)), "volume": int(c.get("volume",0))})
        if len(candles) < 500:
            break
        page += len(candles)
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows)
    df = df.with_columns(pl.col("timestamp").str.to_datetime("%Y-%m-%d %H:%M:%S"))
    return df.sort("timestamp").with_columns(pl.lit(ticker).alias("instrument"))


def main():
    print("Loading data from MOEX ISS...")
    data = {}
    for t in TICKERS:
        df = fetch(t)
        if df.height > 0:
            data[t] = df
            print(f"  {t}: {df.height} bars")

    df_imoex = fetch("IMOEX", "SNDX", "stock", "index")
    if df_imoex.height > 0:
        data["IMOEX"] = df_imoex
        print(f"  IMOEX: {df_imoex.height} bars")

    pipeline = UnifiedPipeline()
    results: dict[tuple[str, str], BacktestResult] = {}

    print("\nRunning backtests...")
    for mode in MODES:
        for ticker in TICKERS:
            if ticker not in data:
                continue
            r = pipeline.run_backtest(data[ticker], ticker, mode=mode)
            results[(mode, ticker)] = r
            if not r.error:
                print(f"  {mode:16s} {ticker:6s} Sharpe={r.sharpe:+.2f} DD={r.max_dd_pct:+.1f}% Trades={r.n_trades:3d} PnL={r.total_pnl:+,.0f}")

    # IMOEX benchmark
    if "IMOEX" in data:
        imoex_r = pipeline.run_backtest(data["IMOEX"], "IMOEX", mode="buy_hold")
        results[("buy_hold", "IMOEX")] = imoex_r
        print(f"  IMOEX B&H: Sharpe={imoex_r.sharpe:+.2f} DD={imoex_r.max_dd_pct:+.1f}%")

    # ── Generate report ───────────────────────────────────
    lines = []
    lines.append(f"# FULL COMPARISON REPORT")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Data: MOEX ISS, {START} -- {END}")
    lines.append(f"Capital: 1,000,000 RUB per ticker")
    lines.append("")

    # Table 1: Sharpe by mode x ticker
    lines.append("## Table 1: Sharpe Ratio by Mode x Ticker")
    lines.append("")
    header = "| Mode |" + "|".join(f" {t} " for t in TICKERS) + "| Avg |"
    lines.append(header)
    lines.append("|" + "---|" * (len(TICKERS) + 2))

    for mode in MODES:
        vals = []
        for t in TICKERS:
            r = results.get((mode, t))
            if r and not r.error:
                vals.append(r.sharpe)
            else:
                vals.append(float("nan"))
        avg = np.nanmean(vals) if vals else 0
        row = f"| {mode:16s} |"
        for v in vals:
            row += f" {v:+.2f} |" if not np.isnan(v) else " -- |"
        row += f" **{avg:+.2f}** |"
        lines.append(row)

    # IMOEX
    imoex_r = results.get(("buy_hold", "IMOEX"))
    if imoex_r:
        lines.append(f"\n**IMOEX B&H:** Sharpe={imoex_r.sharpe:+.2f}, Return={imoex_r.cagr_pct:+.1f}%, DD={imoex_r.max_dd_pct:+.1f}%")

    # Table 2: Full metrics for each mode (portfolio average)
    lines.append("\n## Table 2: Portfolio Average Metrics")
    lines.append("")
    lines.append("| Mode | Sharpe | Sortino | CAGR% | Max DD% | Win Rate% | PF | Trades | Total PnL |")
    lines.append("|------|--------|---------|-------|---------|-----------|-----|--------|-----------|")

    for mode in MODES:
        valid = [results[(mode, t)] for t in TICKERS if (mode, t) in results and not results[(mode, t)].error]
        if not valid:
            continue
        avg_sh = np.mean([r.sharpe for r in valid])
        avg_so = np.mean([r.sortino for r in valid])
        avg_cagr = np.mean([r.cagr_pct for r in valid])
        avg_dd = np.mean([r.max_dd_pct for r in valid])
        avg_wr = np.mean([r.win_rate_pct for r in valid])
        avg_pf = np.mean([r.profit_factor for r in valid])
        total_trades = sum(r.n_trades for r in valid)
        total_pnl = sum(r.total_pnl for r in valid)
        lines.append(
            f"| {mode:16s} | {avg_sh:+.2f} | {avg_so:+.2f} | {avg_cagr:+.1f} | {avg_dd:+.1f} "
            f"| {avg_wr:.1f} | {avg_pf:.2f} | {total_trades} | {total_pnl:+,.0f} |"
        )

    # Table 3: Component contribution
    lines.append("\n## Table 3: Component Contribution Analysis")
    lines.append("")
    lines.append("| Component Added | Avg Sharpe Before | Avg Sharpe After | Delta | Verdict |")
    lines.append("|-----------------|-------------------|------------------|-------|---------|")

    base_sharpes = [results[(m, t)].sharpe for m in ["ema_only"] for t in TICKERS if (m, t) in results and not results[(m, t)].error]
    base_avg = np.mean(base_sharpes) if base_sharpes else 0

    for mode, label in [("ema_scoring", "+ Scoring"), ("ema_regime", "+ Regime"), ("full_ensemble", "+ Full Ensemble")]:
        mode_sharpes = [results[(mode, t)].sharpe for t in TICKERS if (mode, t) in results and not results[(mode, t)].error]
        mode_avg = np.mean(mode_sharpes) if mode_sharpes else 0
        delta = mode_avg - base_avg
        verdict = "Useful" if delta > 0.02 else ("Neutral" if delta > -0.02 else "Harmful")
        lines.append(f"| {label:16s} | {base_avg:+.2f} | {mode_avg:+.2f} | {delta:+.3f} | {verdict} |")

    # Table 4: Monthly returns for best mode
    lines.append("\n## Table 4: Monthly Returns - Best Strategy")
    lines.append("")

    # Find best mode
    mode_avgs = {}
    for mode in ["ema_only", "ema_scoring", "ema_regime", "full_ensemble"]:
        vals = [results[(mode, t)].sharpe for t in TICKERS if (mode, t) in results and not results[(mode, t)].error]
        mode_avgs[mode] = np.mean(vals) if vals else 0
    best_mode = max(mode_avgs, key=mode_avgs.get)
    lines.append(f"Best mode: **{best_mode}** (avg Sharpe = {mode_avgs[best_mode]:+.2f})")
    lines.append("")

    for ticker in TICKERS:
        r = results.get((best_mode, ticker))
        if not r or r.error or not r.monthly:
            continue

        lines.append(f"\n### {ticker}")
        lines.append("| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |")
        lines.append("|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|")

        for year in [2022, 2023, 2024, 2025]:
            row = [str(year)]
            yr_total = 0
            for month in range(1, 13):
                mp = next((m for m in r.monthly if m.year == year and m.month == month), None)
                val = mp.pnl if mp else 0
                yr_total += val
                row.append(f"{val/1000:+.0f}" if val != 0 else "0")
            row.append(f"{yr_total/1000:+.0f}")
            lines.append(f"| {' | '.join(row)} |")

    # Table 5: Per-ticker comparison (best mode vs B&H)
    lines.append("\n## Table 5: Best Strategy vs Buy & Hold")
    lines.append("")
    lines.append(f"| Ticker | {best_mode} Sharpe | {best_mode} CAGR% | {best_mode} DD% | B&H CAGR% | B&H DD% | Delta |")
    lines.append("|--------|" + "---|" * 6)

    for t in TICKERS:
        strat = results.get((best_mode, t))
        bh = results.get(("buy_hold", t))
        if not strat or strat.error or not bh:
            continue
        delta = strat.cagr_pct - bh.cagr_pct
        lines.append(
            f"| {t} | {strat.sharpe:+.2f} | {strat.cagr_pct:+.1f} | {strat.max_dd_pct:+.1f} "
            f"| {bh.cagr_pct:+.1f} | {bh.max_dd_pct:+.1f} | {delta:+.1f}% |"
        )

    # Save
    report_path = Path(__file__).resolve().parent.parent / "FULL_COMPARISON_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved: {report_path}")
    print(f"Lines: {len(lines)}")

    # Save equity CSV
    best_ticker_result = max(
        [results[(best_mode, t)] for t in TICKERS if (best_mode, t) in results and not results[(best_mode, t)].error],
        key=lambda r: r.sharpe,
    )
    csv_path = Path(__file__).resolve().parent.parent / "system_equity.csv"
    eq = best_ticker_result.equity_curve
    ts_list = data[best_ticker_result.ticker]["timestamp"].to_list()
    csv_rows = ["date,equity"]
    for i in range(min(len(ts_list), len(eq))):
        csv_rows.append(f"{str(ts_list[i])[:10]},{eq[i]:.2f}")
    csv_path.write_text("\n".join(csv_rows), encoding="utf-8")
    print(f"Equity CSV: {csv_path} ({best_ticker_result.ticker})")


if __name__ == "__main__":
    main()
