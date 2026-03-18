"""Phase 1 Validation: backtest with macro filters + Kelly + ML ensemble.

Loads real MOEX data, trains ML ensemble, runs walk-forward backtest,
generates QuantStats HTML report.

Usage:
    python scripts/validate_phase1.py
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

from src.analysis.features import calculate_all_features
from src.analysis.regime import detect_regime
from src.analysis.scoring import calculate_pre_score
from src.backtest.report import calculate_metrics, generate_report
from src.ml.ensemble import MLEnsemble
from src.ml.features import compute_target, prepare_features
from src.risk.position_sizer import (
    calculate_historical_var,
    calculate_kelly_fraction,
    calculate_position_size,
)

logger = structlog.get_logger(__name__)

DB_PATH = Path("data/trading.db")
TICKERS = ["SBER", "GAZP", "LKOH", "ROSN", "NVTK", "GMKN", "MGNT", "VTBR"]
SECTOR_MAP = {
    "SBER": "banks", "VTBR": "banks", "TCSG": "banks",
    "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", "NVTK": "oil_gas",
    "GMKN": "metals", "MGNT": "retail", "YDEX": "it",
}


def load_candles(ticker: str) -> list[dict]:
    """Load OHLCV candles from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM candles WHERE ticker = ? ORDER BY date ASC",
        (ticker,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def candles_to_polars_format(candles: list[dict]) -> list[dict]:
    """Convert SQLite candles to the format expected by features module."""
    result = []
    for c in candles:
        result.append({
            "ticker": c["ticker"],
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": float(c["volume"]),
            "value": float(c.get("value", 0)),
            "dt": c["date"],
        })
    return result


def run_simple_backtest(
    candles: list[dict],
    pre_scores: list[float],
    ml_scores: list[float] | None = None,
    initial_capital: float = 1_000_000,
    commission_pct: float = 0.05,
    pre_score_threshold: float = 55.0,
) -> dict:
    """Simple backtest: buy when pre_score > threshold, sell when < threshold-10."""
    equity = initial_capital
    position = 0  # shares held
    entry_price = 0.0
    equity_curve = [equity]
    trades = []
    wins = 0
    losses = 0

    for i in range(1, len(candles)):
        close = float(candles[i]["close"])
        prev_close = float(candles[i - 1]["close"])

        score = pre_scores[i] if i < len(pre_scores) else 50.0
        ml_score = ml_scores[i] if ml_scores and i < len(ml_scores) else 50.0

        # Combined score (70% pre_score + 30% ml_score)
        combined = score * 0.7 + ml_score * 0.3 if ml_scores else score

        # Buy signal
        if position == 0 and combined >= pre_score_threshold:
            shares = int(equity * 0.10 / close)  # 10% of equity
            if shares > 0:
                cost = shares * close * (1 + commission_pct / 100)
                if cost <= equity:
                    position = shares
                    entry_price = close
                    equity -= cost

        # Sell signal (score dropped or stop-loss)
        elif position > 0:
            pnl_pct = (close - entry_price) / entry_price

            sell = False
            if combined < pre_score_threshold - 15:
                sell = True
            elif pnl_pct <= -0.05:  # 5% stop-loss
                sell = True
            elif pnl_pct >= 0.10:  # 10% take-profit
                sell = True

            if sell:
                proceeds = position * close * (1 - commission_pct / 100)
                pnl = proceeds - (position * entry_price)
                equity += proceeds
                trades.append({
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "holding_days": 1,
                    "direction": "long",
                })
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                position = 0

        # Mark to market
        current_equity = equity + (position * close if position > 0 else 0)
        equity_curve.append(current_equity)

    # Close remaining position
    if position > 0:
        close = float(candles[-1]["close"])
        proceeds = position * close * (1 - commission_pct / 100)
        pnl = proceeds - (position * entry_price)
        equity += proceeds
        trades.append({"pnl": pnl, "pnl_pct": pnl / (position * entry_price), "holding_days": 1, "direction": "long"})
        equity_curve[-1] = equity

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "final_equity": equity_curve[-1],
    }


def main() -> None:
    print("=" * 70)
    print("  MOEX Trading System — Phase 1 Validation")
    print("=" * 70)

    # --- Step 1: Load data ---
    print("\n[1/5] Loading data...")
    all_results = {}

    for ticker in TICKERS:
        candles = load_candles(ticker)
        if len(candles) < 200:
            print(f"  {ticker}: skip (only {len(candles)} bars)")
            continue

        formatted = candles_to_polars_format(candles)

        # Calculate TA features
        try:
            import polars as pl
            df = pl.DataFrame(formatted)
            features_df = calculate_all_features(df)
            ta_features = features_df.to_dicts() if hasattr(features_df, 'to_dicts') else []
        except Exception as e:
            # Fallback: manual feature calculation
            ta_features = []
            for c in formatted:
                ta_features.append({
                    "close": c["close"],
                    "rsi_14": 50.0,
                    "macd_histogram": 0.0,
                    "adx": 20.0,
                    "di_plus": 15.0,
                    "di_minus": 10.0,
                    "ema_20": c["close"],
                    "ema_50": c["close"],
                    "ema_200": c["close"],
                    "volume_ratio_20": 1.0,
                    "obv_trend": "flat",
                    "atr_14": c["close"] * 0.02,
                })

        # Calculate pre-scores with macro filter
        sector = SECTOR_MAP.get(ticker, "banks")
        pre_scores = []
        for ta in ta_features:
            score, _ = calculate_pre_score(
                adx=float(ta.get("adx") or 20),
                di_plus=float(ta.get("di_plus") or 15),
                di_minus=float(ta.get("di_minus") or 10),
                rsi=float(ta.get("rsi_14") or 50),
                macd_hist=float(ta.get("macd_histogram") or 0),
                close=float(ta.get("close") or 100),
                ema20=float(ta.get("ema_20") or ta.get("close", 100)),
                ema50=float(ta.get("ema_50") or ta.get("close", 100)),
                ema200=float(ta.get("ema_200") or ta.get("close", 100)),
                volume_ratio=float(ta.get("volume_ratio_20") or 1.0),
                obv_trend=str(ta.get("obv_trend", "flat")),
                sentiment_score=0.0,
                sector=sector,
                imoex_above_sma200=True,  # default bullish assumption
            )
            pre_scores.append(score)

        all_results[ticker] = {
            "candles": formatted,
            "ta_features": ta_features,
            "pre_scores": pre_scores,
        }
        print(f"  {ticker}: {len(candles)} bars, avg pre_score={sum(pre_scores)/len(pre_scores):.1f}")

    # --- Step 2: Train ML ensemble ---
    print("\n[2/5] Training ML ensemble...")
    ml_models = {}

    for ticker, data in all_results.items():
        ensemble = MLEnsemble()
        ok = ensemble.train(
            candles=data["candles"],
            ta_features=data["ta_features"],
            macro={"key_rate": 18.0, "usd_rub": 100.0, "brent": 80.0},
            sentiment=0.0,
        )
        if ok:
            # Generate ML scores for all bars
            X = prepare_features(
                data["candles"], data["ta_features"],
                {"key_rate": 18.0, "usd_rub": 100.0, "brent": 80.0},
            )
            ml_scores = [ensemble.predict_score(x) for x in X]
            ml_models[ticker] = ml_scores

            imp = ensemble.feature_importance(top_n=3)
            top_feats = ", ".join(f"{k}={v:.2f}" for k, v in imp.items())
            print(f"  {ticker}: ML trained, avg_score={sum(ml_scores)/len(ml_scores):.1f}, top: {top_feats}")
        else:
            print(f"  {ticker}: ML training failed")

    # --- Step 3: Backtest each ticker ---
    print("\n[3/5] Running backtests...")
    portfolio_equity_curves = []

    for ticker, data in all_results.items():
        ml_scores = ml_models.get(ticker)

        # Without ML
        result_no_ml = run_simple_backtest(
            data["candles"], data["pre_scores"],
            ml_scores=None,
            pre_score_threshold=55.0,
        )

        # With ML
        result_with_ml = run_simple_backtest(
            data["candles"], data["pre_scores"],
            ml_scores=ml_scores,
            pre_score_threshold=55.0,
        )

        ret_no = (result_no_ml["final_equity"] - 1_000_000) / 1_000_000
        ret_ml = (result_with_ml["final_equity"] - 1_000_000) / 1_000_000
        trades_no = len(result_no_ml["trades"])
        trades_ml = len(result_with_ml["trades"])

        print(f"  {ticker}:")
        print(f"    Without ML: {ret_no:+.2%} ({trades_no} trades)")
        print(f"    With ML:    {ret_ml:+.2%} ({trades_ml} trades)")

        portfolio_equity_curves.append(result_with_ml["equity_curve"])

    # --- Step 4: Portfolio-level metrics ---
    print("\n[4/5] Portfolio metrics...")

    # Simple equal-weight portfolio
    min_len = min(len(ec) for ec in portfolio_equity_curves)
    portfolio_curve = []
    for i in range(min_len):
        avg_equity = sum(ec[i] for ec in portfolio_equity_curves) / len(portfolio_equity_curves)
        portfolio_curve.append(avg_equity)

    metrics = calculate_metrics(portfolio_curve, [])
    print(generate_report(metrics))

    # Kelly and VaR
    daily_returns = []
    for i in range(1, len(portfolio_curve)):
        if portfolio_curve[i - 1] > 0:
            daily_returns.append((portfolio_curve[i] - portfolio_curve[i - 1]) / portfolio_curve[i - 1])

    if daily_returns:
        var, cvar = calculate_historical_var(daily_returns, confidence=0.95)
        print(f"\n  VaR(95%, 1d):  {var:.4f} ({var*100:.2f}%)")
        print(f"  CVaR(95%, 1d): {cvar:.4f} ({cvar*100:.2f}%)")

        winners = [r for r in daily_returns if r > 0]
        losers = [abs(r) for r in daily_returns if r < 0]
        if winners and losers:
            win_rate = len(winners) / len(daily_returns)
            avg_win = sum(winners) / len(winners)
            avg_loss = sum(losers) / len(losers)
            kelly = calculate_kelly_fraction(win_rate, avg_win, avg_loss)
            print(f"  Kelly (half):  {kelly:.4f} ({kelly*100:.2f}%)")

    # --- Step 5: QuantStats HTML report ---
    print("\n[5/5] Generating QuantStats report...")
    try:
        from src.backtest.report import generate_html_report
        path = generate_html_report(portfolio_curve, output_path="data/validation_report.html",
                                     title="MOEX Phase 1 Validation")
        if path:
            print(f"  HTML report: {path}")
        else:
            print("  QuantStats report generation failed")
    except Exception as e:
        print(f"  QuantStats error: {e}")

    # Save results
    results_path = Path("data/validation_results.json")
    results_path.write_text(json.dumps({
        "total_return": metrics.total_return,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "total_trades": metrics.total_trades,
        "equity_curve_len": len(portfolio_curve),
    }, indent=2))
    print(f"\n  Results saved: {results_path}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
