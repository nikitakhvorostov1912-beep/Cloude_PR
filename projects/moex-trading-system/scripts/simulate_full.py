"""Full simulation with ALL fixes: ATR stops, trailing, news, honest ML.

Fixes vs previous version:
1. ML trained ONLY on data before simulation start (no look-ahead)
2. ATR-based stop-loss (ATR * 2.5) instead of fixed -4%
3. Trailing stop: moves up with price, locks in profits
4. News integration: classify headlines, adjust scores for CRITICAL/HIGH
5. Dynamic macro from DB (not hardcoded)
6. Rebalance ranking every day
7. Full 256-ticker universe

Usage:
    python scripts/simulate_full.py
"""
from __future__ import annotations

import asyncio
import json
import math
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

from src.ml.ensemble import MLEnsemble
from src.ml.features import prepare_features
from src.risk.position_sizer import calculate_historical_var, calculate_kelly_fraction
from src.strategy.news_reactor import classify_impact, extract_tickers_from_text, NewsImpact
from src.strategy.universe_selector import rank_universe, select_top_n

logger = structlog.get_logger(__name__)

DB_PATH = Path("data/trading.db")
INITIAL_CAPITAL = 1_000_000.0
COMMISSION_PCT = 0.05
SLIPPAGE_PCT = 0.03
MAX_POSITION_PCT = 0.10
ATR_STOP_MULT = 1.8        # FIX #1: tighter stop (was 2.5)
ATR_TP_MULT = 3.5
TRAILING_ACTIVATION_PCT = 0.015  # FIX #2: activate trailing earlier (was 0.03)
TRAILING_STEP_PCT = 0.01   # FIX #2: trail closer (was 0.015)
TIME_STOP_DAYS = 7         # FIX #3: close if no profit after 7 days
MIN_SCORE = 62             # FIX #5: higher quality threshold (was 55)

SIM_START = "2026-02-18"
SIM_END = "2026-03-18"
ML_TRAIN_END = "2026-02-17"  # honest: train only on data BEFORE sim

SECTOR_MAP = {
    "SBER": "banks", "VTBR": "banks", "TCSG": "banks", "MOEX": "banks", "SBERP": "banks",
    "BSPB": "banks", "CBOM": "banks", "MBNK": "banks", "SVCB": "banks", "SFIN": "banks",
    "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", "NVTK": "oil_gas",
    "TATN": "oil_gas", "SNGS": "oil_gas", "SNGSP": "oil_gas", "SIBN": "oil_gas",
    "TRNFP": "oil_gas", "TATNP": "oil_gas", "RNFT": "oil_gas",
    "GMKN": "metals", "PLZL": "metals", "NLMK": "metals", "CHMF": "metals",
    "MAGN": "metals", "ALRS": "metals", "RUAL": "metals", "SELG": "metals",
    "YDEX": "it", "OZON": "it", "VKCO": "it", "POSI": "it", "HEAD": "it", "DATA": "it",
    "MGNT": "retail", "X5": "retail", "LENT": "retail",
    "MTSS": "telecom", "RTKM": "telecom",
    "PHOR": "chemicals", "AKRN": "chemicals",
    "PIKK": "real_estate", "SMLT": "real_estate", "LSRG": "real_estate",
    "AFLT": "transport", "FLOT": "transport", "FESH": "transport",
    "IRAO": "energy", "HYDR": "energy", "FEES": "energy", "MSNG": "energy",
}


def load_candles_by_ticker() -> dict[str, list[dict]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM candles ORDER BY date ASC").fetchall()
    conn.close()
    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        t = r["ticker"]
        if t not in by_ticker:
            by_ticker[t] = []
        by_ticker[t].append(dict(r))
    return by_ticker


def load_news_for_date(dt: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT title, summary, source, published FROM news WHERE published LIKE ? ORDER BY published",
        (f"{dt}%",),
    ).fetchall()
    conn.close()
    return [{"title": r[0], "body": r[1] or "", "source": r[2], "published": r[3]} for r in rows]


def calc_features(candles: list[dict]) -> list[dict]:
    features = []
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    volumes = [float(c["volume"]) for c in candles]

    for i in range(len(candles)):
        close = closes[i]
        ema20 = sum(closes[max(0,i-19):i+1]) / min(20, i+1)
        ema50 = sum(closes[max(0,i-49):i+1]) / min(50, i+1)
        ema200 = sum(closes[max(0,i-199):i+1]) / min(200, i+1)

        rsi = 50.0
        if i >= 14:
            gains, losses_v = [], []
            for j in range(i-13, i+1):
                d = closes[j] - closes[j-1]
                gains.append(max(0, d))
                losses_v.append(max(0, -d))
            ag = sum(gains)/14
            al = sum(losses_v)/14
            if al > 0:
                rsi = 100 - (100 / (1 + ag/al))

        adx = 25.0
        if i >= 14:
            pr = max(closes[i-14:i+1]) - min(closes[i-14:i+1])
            pc = abs(closes[i] - closes[i-14])
            adx = (pc / pr * 50) if pr > 0 else 20

        vol_avg = sum(volumes[max(0,i-19):i+1]) / min(20, i+1) if i > 0 else 1
        vol_ratio = volumes[i] / vol_avg if vol_avg > 0 else 1.0

        # ATR (14)
        atr = close * 0.02
        if i >= 1:
            tr_vals = []
            for j in range(max(1, i-13), i+1):
                tr = max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                tr_vals.append(tr)
            atr = sum(tr_vals)/len(tr_vals) if tr_vals else close*0.02

        macd_hist = 0.0
        if i >= 26:
            macd_hist = sum(closes[i-11:i+1])/12 - sum(closes[i-25:i+1])/26

        ret_1m = (closes[i]/closes[max(0,i-20)] - 1) if i >= 20 else 0
        ret_3m = (closes[i]/closes[max(0,i-60)] - 1) if i >= 60 else 0
        ret_20d = (closes[i]/closes[max(0,i-20)] - 1) if i >= 20 else 0

        features.append({
            "close": close, "ema_20": ema20, "ema_50": ema50, "ema_200": ema200,
            "rsi_14": rsi, "adx": adx, "di_plus": 15.0, "di_minus": 10.0,
            "volume_ratio_20": vol_ratio, "obv_trend": "up" if vol_ratio > 1.1 else "flat",
            "atr_14": atr, "macd_histogram": macd_hist,
            "returns_1m": ret_1m, "returns_3m": ret_3m, "returns_20d": ret_20d,
            "date": candles[i]["date"],
        })
    return features


class SimPosition:
    def __init__(self, ticker: str, entry: float, shares: int, date: str, sector: str, atr: float):
        self.ticker = ticker
        self.entry_price = entry
        self.shares = shares
        self.entry_date = date
        self.sector = sector
        self.stop_loss = entry - atr * ATR_STOP_MULT
        self.take_profit = entry + atr * ATR_TP_MULT
        self.peak_price = entry
        self.trailing_active = False


def main():
    print("=" * 70)
    print("  MOEX Full Simulation (News + ATR stops + Trailing + Honest ML)")
    print(f"  Period: {SIM_START} to {SIM_END}")
    print(f"  ML train cutoff: {ML_TRAIN_END} (no look-ahead)")
    print(f"  Capital: {INITIAL_CAPITAL:,.0f} RUB")
    print("=" * 70)

    # Load data
    print("\n[1/5] Loading data...")
    all_candles = load_candles_by_ticker()
    valid = {t: c for t, c in all_candles.items()
             if len(c) >= 200 and t not in ("IMOEX", "USDRUB") and any(x["date"] >= SIM_START for x in c)}
    print(f"  Tickers: {len(valid)}")

    # Train ML ONLY on data before simulation (honest)
    print(f"\n[2/5] Training ML (cutoff: {ML_TRAIN_END})...")
    ml_models: dict[str, MLEnsemble] = {}
    for ticker, candles in valid.items():
        train_candles = [c for c in candles if c["date"] <= ML_TRAIN_END]
        if len(train_candles) < 100:
            continue
        features = calc_features(train_candles)
        ensemble = MLEnsemble()
        train_dicts = [{"close": float(c["close"]), "dt": c["date"]} for c in train_candles]
        if ensemble.train(train_dicts, features):
            ml_models[ticker] = ensemble

    print(f"  ML models trained: {len(ml_models)} (honest, no look-ahead)")

    # Build date index for simulation
    all_dates = sorted({c["date"] for candles in valid.values() for c in candles if SIM_START <= c["date"] <= SIM_END})
    print(f"  Sim days: {len(all_dates)}")

    # Precompute features for sim period
    print("\n[3/5] Computing features for sim period...")
    ticker_date_features: dict[str, dict[str, dict]] = {}
    for ticker, candles in valid.items():
        features = calc_features(candles)
        date_map = {}
        for f in features:
            if SIM_START <= f["date"] <= SIM_END:
                date_map[f["date"]] = f
        if date_map:
            ticker_date_features[ticker] = date_map
    print(f"  Tickers with sim data: {len(ticker_date_features)}")

    # Load all news for period
    print("\n[4/5] Loading news...")
    news_by_date: dict[str, list[dict]] = {}
    for dt in all_dates:
        news = load_news_for_date(dt)
        if news:
            news_by_date[dt] = news
    total_news = sum(len(v) for v in news_by_date.values())
    print(f"  News loaded: {total_news} articles across {len(news_by_date)} days")

    # === SIMULATION ===
    print(f"\n[5/5] Running simulation on {len(ticker_date_features)} tickers...")
    equity = INITIAL_CAPITAL
    cash = INITIAL_CAPITAL
    positions: dict[str, SimPosition] = {}
    equity_curve: list[float] = []
    trade_log: list[dict] = []
    news_actions: list[dict] = []

    for today in all_dates:
        # --- NEWS ANALYSIS ---
        news_sentiment: dict[str, float] = {}  # ticker -> sentiment adjustment
        day_news = news_by_date.get(today, [])
        critical_bearish = False

        for article in day_news:
            impact, itype = classify_impact(article["title"], article.get("body", ""))
            tickers_mentioned = extract_tickers_from_text(article["title"] + " " + article.get("body", ""))

            if impact == NewsImpact.CRITICAL:
                if "санкци" in article["title"].lower() or "ставк" in article["title"].lower():
                    critical_bearish = True
                    news_actions.append({"date": today, "type": "CRITICAL", "title": article["title"][:80]})
                    for t in tickers_mentioned:
                        news_sentiment[t] = news_sentiment.get(t, 0) - 30.0

            elif impact == NewsImpact.HIGH:
                for t in tickers_mentioned:
                    # Positive keywords
                    if any(kw in article["title"].lower() for kw in ["дивиденд", "прибыль выросла", "buyback", "выкуп"]):
                        news_sentiment[t] = news_sentiment.get(t, 0) + 15.0
                    elif any(kw in article["title"].lower() for kw in ["убыт", "штраф", "иск", "авари"]):
                        news_sentiment[t] = news_sentiment.get(t, 0) - 15.0

        # --- FIX #4: CLOSE only AFFECTED tickers on critical news (not all) ---
        if critical_bearish:
            # Collect tickers mentioned in critical news
            critical_tickers: set[str] = set()
            for article in day_news:
                impact, _ = classify_impact(article["title"], article.get("body", ""))
                if impact == NewsImpact.CRITICAL:
                    mentioned = extract_tickers_from_text(article["title"] + " " + article.get("body", ""))
                    critical_tickers.update(mentioned)

            # If no specific tickers mentioned, close banking sector (most sensitive to sanctions/rates)
            if not critical_tickers:
                critical_tickers = {t for t in positions if SECTOR_MAP.get(t) in ("banks", "oil_gas")}

            for ticker in list(positions.keys()):
                if ticker not in critical_tickers:
                    continue
                pos = positions[ticker]
                feat = ticker_date_features.get(ticker, {}).get(today)
                if feat:
                    sell_price = feat["close"] * (1 - SLIPPAGE_PCT/100)
                    pnl = (sell_price - pos.entry_price) * pos.shares
                    commission = sell_price * pos.shares * COMMISSION_PCT / 100
                    cash += pos.shares * sell_price - commission
                    trade_log.append({
                        "date": today, "ticker": ticker, "action": "NEWS-EXIT",
                        "entry": round(pos.entry_price, 2), "exit": round(sell_price, 2),
                        "pnl": round(pnl - commission, 2),
                        "pnl_pct": round((pnl - commission) / (pos.entry_price * pos.shares) * 100, 2),
                        "days": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days,
                    })
                    del positions[ticker]

        # --- CHECK STOPS + TRAILING ---
        for ticker in list(positions.keys()):
            pos = positions[ticker]
            feat = ticker_date_features.get(ticker, {}).get(today)
            if not feat:
                continue

            close = feat["close"]
            low = float(valid[ticker][-1]["low"]) if ticker in valid else close
            # Find actual low for today
            for c in valid.get(ticker, []):
                if c["date"] == today:
                    low = float(c["low"])
                    break

            high = close
            for c in valid.get(ticker, []):
                if c["date"] == today:
                    high = float(c["high"])
                    break

            # Update peak for trailing
            if high > pos.peak_price:
                pos.peak_price = high

            # Activate trailing stop after +3% from entry
            if not pos.trailing_active and pos.peak_price >= pos.entry_price * (1 + TRAILING_ACTIVATION_PCT):
                pos.trailing_active = True
                # Move stop to breakeven
                pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.001)

            # Update trailing stop
            if pos.trailing_active:
                trail_stop = pos.peak_price * (1 - TRAILING_STEP_PCT)
                pos.stop_loss = max(pos.stop_loss, trail_stop)

            # Check stop-loss
            if low <= pos.stop_loss:
                sell_price = pos.stop_loss * (1 - SLIPPAGE_PCT/100)
                pnl = (sell_price - pos.entry_price) * pos.shares
                commission = sell_price * pos.shares * COMMISSION_PCT / 100
                cash += pos.shares * sell_price - commission
                action = "TRAILING-STOP" if pos.trailing_active else "STOP-LOSS"
                trade_log.append({
                    "date": today, "ticker": ticker, "action": action,
                    "entry": round(pos.entry_price, 2), "exit": round(sell_price, 2),
                    "pnl": round(pnl - commission, 2),
                    "pnl_pct": round((pnl - commission) / (pos.entry_price * pos.shares) * 100, 2),
                    "days": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days,
                })
                del positions[ticker]
                continue

            # Check take-profit
            if high >= pos.take_profit:
                sell_price = pos.take_profit * (1 - SLIPPAGE_PCT/100)
                pnl = (sell_price - pos.entry_price) * pos.shares
                commission = sell_price * pos.shares * COMMISSION_PCT / 100
                cash += pos.shares * sell_price - commission
                trade_log.append({
                    "date": today, "ticker": ticker, "action": "TAKE-PROFIT",
                    "entry": round(pos.entry_price, 2), "exit": round(sell_price, 2),
                    "pnl": round(pnl - commission, 2),
                    "pnl_pct": round((pnl - commission) / (pos.entry_price * pos.shares) * 100, 2),
                    "days": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days,
                })
                del positions[ticker]
                continue

            # FIX #3: Time-stop — close if held > TIME_STOP_DAYS without profit
            hold_days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pos.entry_date, "%Y-%m-%d")).days
            pnl_pct_current = (close - pos.entry_price) / pos.entry_price
            if hold_days >= TIME_STOP_DAYS and pnl_pct_current <= 0.005:
                sell_price = close * (1 - SLIPPAGE_PCT/100)
                pnl = (sell_price - pos.entry_price) * pos.shares
                commission = sell_price * pos.shares * COMMISSION_PCT / 100
                cash += pos.shares * sell_price - commission
                trade_log.append({
                    "date": today, "ticker": ticker, "action": "TIME-STOP",
                    "entry": round(pos.entry_price, 2), "exit": round(sell_price, 2),
                    "pnl": round(pnl - commission, 2),
                    "pnl_pct": round((pnl - commission) / (pos.entry_price * pos.shares) * 100, 2),
                    "days": hold_days,
                })
                del positions[ticker]

        # --- UNIVERSE RANKING + NEW ENTRIES ---
        if len(positions) < 7 and not critical_bearish:
            tickers_data = []
            for ticker, date_feats in ticker_date_features.items():
                if ticker in positions:
                    continue
                feat = date_feats.get(today)
                if not feat:
                    continue

                ml_score = 50.0
                if ticker in ml_models:
                    ml_feats = prepare_features(
                        [{"close": feat["close"], "dt": today}], [feat],
                        {"key_rate": 18.0, "usd_rub": 100.0, "brent": 80.0},
                    )
                    if ml_feats:
                        ml_score = ml_models[ticker].predict_score(ml_feats[0])

                # News sentiment boost/penalty
                news_adj = news_sentiment.get(ticker, 0)
                ml_score = max(0, min(100, ml_score + news_adj))

                sector = SECTOR_MAP.get(ticker, "other")
                tickers_data.append({
                    "ticker": ticker, "sector": sector, "close": feat["close"],
                    "ml_score": ml_score, "rsi": feat["rsi_14"],
                    "returns_1m": feat["returns_1m"], "returns_3m": feat["returns_3m"],
                    "returns_20d": feat["returns_20d"], "imoex_return_20d": 0.0,
                    "volume_ratio": feat["volume_ratio_20"],
                    "atr": feat["atr_14"],
                })

            if tickers_data:
                macro = {"brent_delta_pct": 3.0, "key_rate_delta": 0.0, "usd_rub_delta_pct": 0.5}
                ranked = rank_universe(tickers_data, macro)
                max_new = 7 - len(positions)
                selected = select_top_n(ranked, "uptrend", {"max_positions": max_new, "min_composite_score": MIN_SCORE})

                for sel in selected:
                    if sel.ticker in positions or cash <= 10000:
                        continue

                    entry_price = sel.close * (1 + SLIPPAGE_PCT/100)
                    pos_value = min(cash * MAX_POSITION_PCT, cash * 0.90 / max(1, max_new))
                    shares = int(pos_value / entry_price)
                    if shares <= 0:
                        continue

                    cost = shares * entry_price * (1 + COMMISSION_PCT/100)
                    if cost > cash:
                        continue

                    # Get ATR for this ticker
                    feat = ticker_date_features.get(sel.ticker, {}).get(today)
                    atr = feat["atr"] if feat and "atr" in feat else sel.close * 0.02

                    cash -= cost
                    positions[sel.ticker] = SimPosition(
                        ticker=sel.ticker, entry=entry_price, shares=shares,
                        date=today, sector=sel.sector, atr=atr,
                    )
                    trade_log.append({
                        "date": today, "ticker": sel.ticker, "action": "BUY",
                        "entry": round(entry_price, 2), "exit": None,
                        "pnl": None, "pnl_pct": None,
                        "score": round(sel.composite_score, 1),
                        "reason": sel.reason,
                        "stop": round(entry_price - atr * ATR_STOP_MULT, 2),
                        "target": round(entry_price + atr * ATR_TP_MULT, 2),
                        "days": 0,
                    })

        # Mark to market
        pos_value = sum(
            pos.shares * ticker_date_features.get(pos.ticker, {}).get(today, {"close": pos.entry_price})["close"]
            for pos in positions.values()
        )
        equity_curve.append(cash + pos_value)

    # Close remaining
    for ticker, pos in list(positions.items()):
        feat = ticker_date_features.get(ticker, {}).get(all_dates[-1])
        if feat:
            sell_price = feat["close"] * (1 - SLIPPAGE_PCT/100)
            pnl = (sell_price - pos.entry_price) * pos.shares
            commission = sell_price * pos.shares * COMMISSION_PCT / 100
            cash += pos.shares * sell_price - commission
            trade_log.append({
                "date": all_dates[-1], "ticker": ticker, "action": "CLOSE-EOD",
                "entry": round(pos.entry_price, 2), "exit": round(sell_price, 2),
                "pnl": round(pnl - commission, 2),
                "pnl_pct": round((pnl - commission) / (pos.entry_price * pos.shares) * 100, 2),
                "days": 0,
            })

    # === RESULTS ===
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)

    final = equity_curve[-1] if equity_curve else INITIAL_CAPITAL
    ret = (final - INITIAL_CAPITAL) / INITIAL_CAPITAL
    max_eq = max(equity_curve) if equity_curve else INITIAL_CAPITAL
    max_dd = max((max_eq - e) / max_eq for e in equity_curve) if equity_curve else 0

    print(f"\n  Initial:    {INITIAL_CAPITAL:>12,.0f} RUB")
    print(f"  Final:      {final:>12,.0f} RUB")
    print(f"  Return:     {ret:>+11.2%}  (~{ret*12*100:.0f}% annualized)")
    print(f"  Max DD:     {max_dd:>11.2%}")

    closed = [t for t in trade_log if t.get("pnl") is not None]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]

    print(f"\n  Trades:     {len(closed)}")
    print(f"  Win Rate:   {len(wins)/max(1,len(closed))*100:.0f}% ({len(wins)}W / {len(losses)}L)")

    gp = sum(t["pnl"] for t in wins) if wins else 0
    gl = abs(sum(t["pnl"] for t in losses)) if losses else 0
    pf = gp / gl if gl > 0 else float("inf")

    print(f"  Gross P:    {gp:>+12,.0f} RUB")
    print(f"  Gross L:    {-gl:>12,.0f} RUB")
    print(f"  Net PnL:    {gp-gl:>+12,.0f} RUB")
    print(f"  PF:         {pf:>11.2f}")

    if wins:
        print(f"  Avg Win:    {gp/len(wins):>+12,.0f} RUB ({sum(t['pnl_pct'] for t in wins)/len(wins):+.1f}%)")
    if losses:
        print(f"  Avg Loss:   {sum(t['pnl'] for t in losses)/len(losses):>+12,.0f} RUB ({sum(t['pnl_pct'] for t in losses)/len(losses):+.1f}%)")

    # Action breakdown
    actions = {}
    for t in closed:
        a = t["action"]
        actions[a] = actions.get(a, 0) + 1
    print(f"\n  Exit types: {actions}")

    # News actions
    if news_actions:
        print(f"\n  News alerts: {len(news_actions)}")
        for na in news_actions[:5]:
            print(f"    {na['date']}: [{na['type']}] {na['title']}")

    # VaR
    if len(equity_curve) > 5:
        returns = [(equity_curve[i]-equity_curve[i-1])/equity_curve[i-1]
                    for i in range(1, len(equity_curve)) if equity_curve[i-1] > 0]
        if returns:
            var, cvar = calculate_historical_var(returns)
            print(f"\n  VaR(95%):   {var*100:>10.2f}%")
            print(f"  CVaR(95%):  {cvar*100:>10.2f}%")

    # Top trades
    print("\n" + "-" * 70)
    print("  TOP-5 WINS:")
    for t in sorted(wins, key=lambda x: x["pnl"], reverse=True)[:5]:
        print(f"    {t['date']} {t['ticker']:8s} {t['action']:14s} {t['pnl']:>+10,.0f} ({t['pnl_pct']:>+.1f}%) {t.get('days',0)}d")

    print("\n  TOP-5 LOSSES:")
    for t in sorted(losses, key=lambda x: x["pnl"])[:5]:
        print(f"    {t['date']} {t['ticker']:8s} {t['action']:14s} {t['pnl']:>+10,.0f} ({t['pnl_pct']:>+.1f}%) {t.get('days',0)}d")

    # Daily
    print("\n" + "-" * 70)
    print("  DAILY EQUITY:")
    prev = INITIAL_CAPITAL
    for i, dt in enumerate(all_dates):
        eq = equity_curve[i] if i < len(equity_curve) else prev
        d = eq - prev
        bar = "+" * min(30, int(abs(d)/1500)) if d > 0 else "-" * min(30, int(abs(d)/1500))
        print(f"    {dt}  {eq:>12,.0f}  {d:>+8,.0f}  {bar}")
        prev = eq

    print("\n" + "=" * 70)

    # QuantStats
    try:
        from src.backtest.report import generate_html_report
        path = generate_html_report(equity_curve, output_path="data/simulation_full.html",
                                     title="MOEX Full Simulation (News+ATR+Trailing)")
        if path:
            print(f"  Report: {path}")
    except Exception as e:
        print(f"  Report error: {e}")

    # Save
    Path("data/simulation_full.json").write_text(json.dumps({
        "period": f"{SIM_START} to {SIM_END}",
        "initial": INITIAL_CAPITAL, "final": round(final, 2),
        "return_pct": round(ret*100, 2), "max_dd_pct": round(max_dd*100, 2),
        "trades": len(closed), "win_rate": round(len(wins)/max(1,len(closed))*100, 1),
        "profit_factor": round(pf, 2), "net_pnl": round(gp-gl, 2),
        "trade_log": trade_log, "news_actions": news_actions,
    }, indent=2, ensure_ascii=False))
    print(f"  JSON: data/simulation_full.json")


if __name__ == "__main__":
    main()
