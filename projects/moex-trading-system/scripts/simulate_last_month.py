"""Simulate trading for the last month using full pipeline.

Loads real MOEX data, trains ML per ticker, runs daily:
  Universe ranking → Top-N selection → Signal generation → Risk check → Execute

Outputs: trade log, equity curve, PnL by ticker, QuantStats report.

Usage:
    python scripts/simulate_last_month.py
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import structlog

from src.analysis.scoring import SCORING_WEIGHTS, calculate_pre_score
from src.ml.ensemble import MLEnsemble
from src.ml.features import prepare_features
from src.risk.position_sizer import (
    calculate_historical_var,
    calculate_kelly_fraction,
)
from src.strategy.universe_selector import RankedTicker, rank_universe, select_top_n

logger = structlog.get_logger(__name__)

DB_PATH = Path("data/trading.db")

# Simulation parameters
INITIAL_CAPITAL = 1_000_000.0
COMMISSION_PCT = 0.05  # 0.05% per trade
SLIPPAGE_PCT = 0.02  # 0.02% slippage
MAX_POSITION_PCT = 0.12  # 12% per position
STOP_LOSS_PCT = 0.04  # 4% stop-loss
TAKE_PROFIT_PCT = 0.08  # 8% take-profit
MIN_SCORE_THRESHOLD = 55.0

# Sector map for scoring
SECTOR_MAP = {
    "SBER": "banks", "VTBR": "banks", "TCSG": "banks", "MOEX": "banks", "SBERP": "banks",
    "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", "NVTK": "oil_gas",
    "TATN": "oil_gas", "SNGS": "oil_gas", "SNGSP": "oil_gas", "SIBN": "oil_gas", "TRNFP": "oil_gas",
    "GMKN": "metals", "PLZL": "metals", "NLMK": "metals", "CHMF": "metals",
    "MAGN": "metals", "ALRS": "metals", "RUAL": "metals",
    "YDEX": "it", "OZON": "it", "VKCO": "it", "POSI": "it", "HEAD": "it",
    "MGNT": "retail", "MTSS": "telecom", "PHOR": "chemicals",
    "PIKK": "real_estate", "SMLT": "real_estate",
    "AFLT": "transport", "FLOT": "transport",
    "IRAO": "energy", "HYDR": "energy", "FEES": "energy",
}


def load_all_candles() -> dict[str, list[dict]]:
    """Load all candles from SQLite, grouped by ticker."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ticker, date, open, high, low, close, volume FROM candles ORDER BY date ASC"
    ).fetchall()
    conn.close()

    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        t = r["ticker"]
        if t not in by_ticker:
            by_ticker[t] = []
        by_ticker[t].append(dict(r))

    return by_ticker


def calc_ta_features(candles: list[dict]) -> list[dict]:
    """Calculate basic TA features from candles."""
    features = []
    closes = [float(c["close"]) for c in candles]
    volumes = [float(c["volume"]) for c in candles]

    for i in range(len(candles)):
        close = closes[i]

        # EMAs
        ema20 = sum(closes[max(0, i - 19):i + 1]) / min(20, i + 1)
        ema50 = sum(closes[max(0, i - 49):i + 1]) / min(50, i + 1)
        ema200 = sum(closes[max(0, i - 199):i + 1]) / min(200, i + 1)

        # RSI (14)
        rsi = 50.0
        if i >= 14:
            gains, losses = [], []
            for j in range(i - 13, i + 1):
                delta = closes[j] - closes[j - 1]
                gains.append(max(0, delta))
                losses.append(max(0, -delta))
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

        # ADX approximation
        adx = 25.0
        if i >= 14:
            price_range = max(closes[i - 14:i + 1]) - min(closes[i - 14:i + 1])
            price_change = abs(closes[i] - closes[i - 14])
            adx = (price_change / price_range * 50) if price_range > 0 else 20

        # Volume ratio
        vol_avg = sum(volumes[max(0, i - 19):i + 1]) / min(20, i + 1) if i > 0 else 1
        vol_ratio = volumes[i] / vol_avg if vol_avg > 0 else 1.0

        # ATR
        atr = close * 0.02
        if i >= 1:
            tr_vals = []
            for j in range(max(1, i - 13), i + 1):
                h, l, pc = float(candles[j]["high"]), float(candles[j]["low"]), closes[j - 1]
                tr = max(h - l, abs(h - pc), abs(l - pc))
                tr_vals.append(tr)
            atr = sum(tr_vals) / len(tr_vals) if tr_vals else close * 0.02

        # MACD
        macd_hist = 0.0
        if i >= 26:
            ema12 = sum(closes[i - 11:i + 1]) / 12
            ema26 = sum(closes[i - 25:i + 1]) / 26
            macd_hist = ema12 - ema26

        # Returns
        ret_1m = (closes[i] / closes[max(0, i - 20)] - 1) if i >= 20 else 0
        ret_3m = (closes[i] / closes[max(0, i - 60)] - 1) if i >= 60 else 0
        ret_20d = (closes[i] / closes[max(0, i - 20)] - 1) if i >= 20 else 0

        features.append({
            "close": close,
            "ema_20": ema20,
            "ema_50": ema50,
            "ema_200": ema200,
            "rsi_14": rsi,
            "adx": adx,
            "di_plus": 15.0,
            "di_minus": 10.0,
            "volume_ratio_20": vol_ratio,
            "obv_trend": "up" if vol_ratio > 1.1 else ("down" if vol_ratio < 0.9 else "flat"),
            "atr_14": atr,
            "macd_histogram": macd_hist,
            "returns_1m": ret_1m,
            "returns_3m": ret_3m,
            "returns_20d": ret_20d,
            "date": candles[i]["date"],
        })

    return features


class Position:
    def __init__(self, ticker: str, entry_price: float, shares: int, entry_date: str, sector: str):
        self.ticker = ticker
        self.entry_price = entry_price
        self.shares = shares
        self.entry_date = entry_date
        self.sector = sector
        self.stop_loss = entry_price * (1 - STOP_LOSS_PCT)
        self.take_profit = entry_price * (1 + TAKE_PROFIT_PCT)


def main() -> None:
    print("=" * 70)
    print("  MOEX Trading Simulation — Last Month")
    print("  Period: 2026-02-18 to 2026-03-18")
    print(f"  Capital: {INITIAL_CAPITAL:,.0f} RUB")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading data...")
    all_candles = load_all_candles()
    print(f"  Tickers with data: {len(all_candles)}")

    # Filter: need at least 200 bars for features
    valid_tickers = {t: c for t, c in all_candles.items() if len(c) >= 200 and t != "IMOEX" and t != "USDRUB"}
    print(f"  Tickers with 200+ bars: {len(valid_tickers)}")

    # Calculate features for all tickers
    print("\n[2/4] Calculating features + training ML...")
    ticker_features: dict[str, list[dict]] = {}
    ml_models: dict[str, MLEnsemble] = {}

    for ticker, candles in valid_tickers.items():
        features = calc_ta_features(candles)
        ticker_features[ticker] = features

        # Train ML on first 80% of data
        train_end = int(len(candles) * 0.8)
        ensemble = MLEnsemble()
        train_candles = [{"close": float(c["close"]), "dt": c["date"]} for c in candles[:train_end]]
        train_ta = features[:train_end]
        ok = ensemble.train(train_candles, train_ta)
        if ok:
            ml_models[ticker] = ensemble

    print(f"  ML models trained: {len(ml_models)}")

    # Simulation period
    sim_start = "2026-02-18"
    sim_end = "2026-03-18"

    # Find simulation date range
    all_dates: set[str] = set()
    for candles in valid_tickers.values():
        for c in candles:
            if sim_start <= c["date"] <= sim_end:
                all_dates.add(c["date"])
    sim_dates = sorted(all_dates)
    print(f"  Simulation days: {len(sim_dates)} ({sim_dates[0] if sim_dates else '?'} to {sim_dates[-1] if sim_dates else '?'})")

    # === SIMULATION ===
    print("\n[3/4] Running simulation...")
    equity = INITIAL_CAPITAL
    positions: dict[str, Position] = {}
    equity_curve: list[float] = []
    trade_log: list[dict] = []
    daily_pnl: list[dict] = []

    for day_idx, today in enumerate(sim_dates):
        day_equity_start = equity + sum(
            pos.shares * float(valid_tickers[pos.ticker][-1]["close"])
            for pos in positions.values()
            if pos.ticker in valid_tickers
        )

        # --- Check stops and take-profits ---
        closed_tickers = []
        for ticker, pos in list(positions.items()):
            candles = valid_tickers.get(ticker, [])
            today_candle = next((c for c in candles if c["date"] == today), None)
            if not today_candle:
                continue

            current_price = float(today_candle["close"])
            low_price = float(today_candle["low"])
            high_price = float(today_candle["high"])

            # Check stop-loss (use low)
            if low_price <= pos.stop_loss:
                sell_price = pos.stop_loss * (1 - SLIPPAGE_PCT / 100)
                pnl = (sell_price - pos.entry_price) * pos.shares
                commission = sell_price * pos.shares * COMMISSION_PCT / 100
                net_pnl = pnl - commission
                equity += pos.shares * sell_price - commission
                trade_log.append({
                    "date": today, "ticker": ticker, "action": "STOP-LOSS",
                    "entry": pos.entry_price, "exit": sell_price,
                    "pnl": round(net_pnl, 2), "pnl_pct": round(net_pnl / (pos.entry_price * pos.shares) * 100, 2),
                    "days": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days,
                })
                closed_tickers.append(ticker)
                continue

            # Check take-profit (use high)
            if high_price >= pos.take_profit:
                sell_price = pos.take_profit * (1 - SLIPPAGE_PCT / 100)
                pnl = (sell_price - pos.entry_price) * pos.shares
                commission = sell_price * pos.shares * COMMISSION_PCT / 100
                net_pnl = pnl - commission
                equity += pos.shares * sell_price - commission
                trade_log.append({
                    "date": today, "ticker": ticker, "action": "TAKE-PROFIT",
                    "entry": pos.entry_price, "exit": sell_price,
                    "pnl": round(net_pnl, 2), "pnl_pct": round(net_pnl / (pos.entry_price * pos.shares) * 100, 2),
                    "days": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days,
                })
                closed_tickers.append(ticker)
                continue

        for t in closed_tickers:
            del positions[t]

        # --- Universe ranking ---
        if len(positions) < 7:  # room for new positions
            tickers_data = []
            imoex_candles = all_candles.get("IMOEX", [])
            imoex_ret_20d = 0.0
            if len(imoex_candles) >= 20:
                imoex_today = next((c for c in imoex_candles if c["date"] == today), None)
                if imoex_today:
                    idx = imoex_candles.index(imoex_today)
                    if idx >= 20:
                        imoex_ret_20d = float(imoex_today["close"]) / float(imoex_candles[idx - 20]["close"]) - 1

            for ticker, features_list in ticker_features.items():
                if ticker in positions:
                    continue

                today_feat = next((f for f in features_list if f["date"] == today), None)
                if not today_feat:
                    continue

                # ML score
                ml_score = 50.0
                if ticker in ml_models:
                    ml_features = prepare_features(
                        [{"close": today_feat["close"], "dt": today}],
                        [today_feat],
                        {"key_rate": 18.0, "usd_rub": 100.0, "brent": 80.0},
                    )
                    if ml_features:
                        ml_score = ml_models[ticker].predict_score(ml_features[0])

                sector = SECTOR_MAP.get(ticker, "other")
                tickers_data.append({
                    "ticker": ticker,
                    "sector": sector,
                    "close": today_feat["close"],
                    "ml_score": ml_score,
                    "rsi": today_feat["rsi_14"],
                    "returns_1m": today_feat["returns_1m"],
                    "returns_3m": today_feat["returns_3m"],
                    "returns_20d": today_feat["returns_20d"],
                    "imoex_return_20d": imoex_ret_20d,
                    "volume_ratio": today_feat["volume_ratio_20"],
                })

            if tickers_data:
                macro = {"brent_delta_pct": 3.0, "key_rate_delta": 0.0, "usd_rub_delta_pct": 0.5}
                ranked = rank_universe(tickers_data, macro)
                selected = select_top_n(ranked, "uptrend", {"max_positions": 7 - len(positions), "min_composite_score": MIN_SCORE_THRESHOLD})

                for sel in selected:
                    if sel.ticker in positions:
                        continue
                    if equity <= 0:
                        break

                    pos_size = min(equity * MAX_POSITION_PCT, equity * 0.95 / max(1, 7 - len(positions)))
                    entry_price = sel.close * (1 + SLIPPAGE_PCT / 100)
                    shares = int(pos_size / entry_price)
                    if shares <= 0:
                        continue

                    cost = shares * entry_price * (1 + COMMISSION_PCT / 100)
                    if cost > equity:
                        continue

                    equity -= cost
                    positions[sel.ticker] = Position(
                        ticker=sel.ticker,
                        entry_price=entry_price,
                        shares=shares,
                        entry_date=today,
                        sector=sel.sector,
                    )
                    trade_log.append({
                        "date": today, "ticker": sel.ticker, "action": "BUY",
                        "entry": round(entry_price, 2), "exit": None,
                        "pnl": None, "pnl_pct": None,
                        "score": round(sel.composite_score, 1),
                        "reason": sel.reason,
                        "days": 0,
                    })

        # --- Mark to market ---
        positions_value = 0.0
        for ticker, pos in positions.items():
            candles = valid_tickers.get(ticker, [])
            today_candle = next((c for c in candles if c["date"] == today), None)
            if today_candle:
                positions_value += pos.shares * float(today_candle["close"])

        total_equity = equity + positions_value
        equity_curve.append(total_equity)

        day_pnl = total_equity - day_equity_start
        daily_pnl.append({"date": today, "equity": round(total_equity, 2), "pnl": round(day_pnl, 2), "positions": len(positions)})

    # --- Close remaining positions ---
    for ticker, pos in list(positions.items()):
        candles = valid_tickers.get(ticker, [])
        last_candle = next((c for c in reversed(candles) if c["date"] <= sim_end), None)
        if last_candle:
            sell_price = float(last_candle["close"]) * (1 - SLIPPAGE_PCT / 100)
            pnl = (sell_price - pos.entry_price) * pos.shares
            commission = sell_price * pos.shares * COMMISSION_PCT / 100
            net_pnl = pnl - commission
            equity += pos.shares * sell_price - commission
            trade_log.append({
                "date": sim_end, "ticker": ticker, "action": "CLOSE-EOD",
                "entry": pos.entry_price, "exit": round(sell_price, 2),
                "pnl": round(net_pnl, 2), "pnl_pct": round(net_pnl / (pos.entry_price * pos.shares) * 100, 2),
                "days": 0,
            })

    # === RESULTS ===
    print("\n[4/4] Results")
    print("=" * 70)

    final_equity = equity_curve[-1] if equity_curve else INITIAL_CAPITAL
    total_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL
    max_equity = max(equity_curve) if equity_curve else INITIAL_CAPITAL
    max_dd = max((max_equity - e) / max_equity for e in equity_curve) if equity_curve else 0

    print(f"\n  Initial Capital:  {INITIAL_CAPITAL:>12,.0f} RUB")
    print(f"  Final Equity:     {final_equity:>12,.0f} RUB")
    print(f"  Total Return:     {total_return:>+11.2%}")
    print(f"  Max Drawdown:     {max_dd:>11.2%}")

    # Trade stats
    closed_trades = [t for t in trade_log if t.get("pnl") is not None]
    wins = [t for t in closed_trades if t["pnl"] > 0]
    losses = [t for t in closed_trades if t["pnl"] <= 0]

    print(f"\n  Total Trades:     {len(closed_trades)}")
    print(f"  Winners:          {len(wins)} ({len(wins)/max(1,len(closed_trades))*100:.0f}%)")
    print(f"  Losers:           {len(losses)} ({len(losses)/max(1,len(closed_trades))*100:.0f}%)")

    total_profit = sum(t["pnl"] for t in wins) if wins else 0
    total_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

    print(f"  Gross Profit:     {total_profit:>+12,.0f} RUB")
    print(f"  Gross Loss:       {-total_loss:>12,.0f} RUB")
    print(f"  Net P&L:          {total_profit - total_loss:>+12,.0f} RUB")
    print(f"  Profit Factor:    {profit_factor:>11.2f}")

    if wins:
        avg_win = sum(t["pnl"] for t in wins) / len(wins)
        print(f"  Avg Win:          {avg_win:>+12,.0f} RUB")
    if losses:
        avg_loss = sum(t["pnl"] for t in losses) / len(losses)
        print(f"  Avg Loss:         {avg_loss:>+12,.0f} RUB")

    # VaR
    if len(equity_curve) > 5:
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                    for i in range(1, len(equity_curve)) if equity_curve[i-1] > 0]
        if returns:
            var, cvar = calculate_historical_var(returns)
            print(f"\n  VaR(95%, 1d):     {var*100:>10.2f}%")
            print(f"  CVaR(95%, 1d):    {cvar*100:>10.2f}%")

    # Top trades
    print("\n" + "-" * 70)
    print("  TOP-5 WINNERS:")
    for t in sorted(wins, key=lambda x: x["pnl"], reverse=True)[:5]:
        print(f"    {t['date']} {t['ticker']:6s} {t['action']:12s} PnL: {t['pnl']:>+10,.0f} ({t['pnl_pct']:>+.1f}%)")

    print("\n  TOP-5 LOSERS:")
    for t in sorted(losses, key=lambda x: x["pnl"])[:5]:
        print(f"    {t['date']} {t['ticker']:6s} {t['action']:12s} PnL: {t['pnl']:>+10,.0f} ({t['pnl_pct']:>+.1f}%)")

    # Daily PnL
    print("\n" + "-" * 70)
    print("  DAILY P&L:")
    for d in daily_pnl:
        bar = "+" * int(abs(d["pnl"]) / 2000) if d["pnl"] > 0 else "-" * int(abs(d["pnl"]) / 2000)
        print(f"    {d['date']}  equity={d['equity']:>12,.0f}  pnl={d['pnl']:>+10,.0f}  pos={d['positions']}  {bar}")

    print("\n" + "=" * 70)

    # QuantStats HTML
    try:
        from src.backtest.report import generate_html_report
        path = generate_html_report(equity_curve, output_path="data/simulation_last_month.html",
                                     title="MOEX Simulation Feb-Mar 2026")
        if path:
            print(f"  QuantStats report: {path}")
    except Exception as e:
        print(f"  QuantStats error: {e}")

    # Save results
    Path("data/simulation_results.json").write_text(json.dumps({
        "period": f"{sim_start} to {sim_end}",
        "initial_capital": INITIAL_CAPITAL,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_trades": len(closed_trades),
        "win_rate_pct": round(len(wins) / max(1, len(closed_trades)) * 100, 1),
        "profit_factor": round(profit_factor, 2),
        "trades": trade_log,
        "daily_pnl": daily_pnl,
    }, indent=2, ensure_ascii=False))
    print(f"  Results JSON: data/simulation_results.json")


if __name__ == "__main__":
    main()
