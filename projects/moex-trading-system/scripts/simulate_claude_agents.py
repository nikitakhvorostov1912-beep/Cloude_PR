"""Claude Multi-Agent Live Simulation.

Runs real Claude API calls on last week of MOEX data.
4 agents (Bull/Bear/Risk/Arbiter) analyze top tickers.
Shows what Claude would have traded and the PnL.

Cost estimate: ~15 tickers × 4 agents × 5 days = 300 API calls ≈ $1-2

Usage:
    python scripts/simulate_claude_agents.py
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env for ANTHROPIC_API_KEY
import os
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from src.strategy.multi_agent import multi_agent_analyze

DB = Path("data/trading.db")
CAPITAL = 1_000_000.0
COMMISSION = 0.05  # %
SLIPPAGE = 0.03    # %
MAX_POS = 5
MAX_POS_PCT = 0.12

# Top liquid tickers to analyze
TOP_TICKERS = [
    "SBER", "GAZP", "LKOH", "YDEX", "GMKN",
    "ROSN", "NVTK", "VTBR", "TCSG", "MGNT",
    "PLZL", "NLMK", "CHMF", "OZON", "POSI",
]

SECTORS = {
    "SBER": "banks", "VTBR": "banks", "TCSG": "banks",
    "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", "NVTK": "oil_gas",
    "GMKN": "metals", "PLZL": "metals", "NLMK": "metals", "CHMF": "metals",
    "MGNT": "retail", "YDEX": "it", "OZON": "it", "POSI": "it",
}


def load_daily_candles(start_date: str, end_date: str) -> dict:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM candles WHERE date >= ? AND date <= ? ORDER BY date ASC",
        (start_date, end_date),
    ).fetchall()
    conn.close()
    by_tk = defaultdict(list)
    for r in rows:
        by_tk[r["ticker"]].append(dict(r))
    return dict(by_tk)


def load_news(start_date: str) -> dict:
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT title, summary, source, published FROM news WHERE published >= ? ORDER BY published",
        (start_date,),
    ).fetchall()
    conn.close()
    by_date = defaultdict(list)
    for r in rows:
        dt = str(r[3])[:10]
        by_date[dt].append({"title": r[0], "body": r[1] or "", "source": r[2]})
    return dict(by_date)


def calc_features(candles: list[dict]) -> dict | None:
    if len(candles) < 20:
        return None
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    vols = [float(c.get("volume", 0)) for c in candles]
    n = len(closes)
    i = n - 1
    cl = closes[i]

    # EMA
    def ema(values, period):
        if len(values) < period:
            return sum(values) / len(values)
        k = 2.0 / (period + 1)
        e = sum(values[:period]) / period
        for v in values[period:]:
            e = v * k + e * (1 - k)
        return e

    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200) if n >= 200 else ema(closes, n)

    # RSI Wilder
    rsi = 50.0
    if n > 14:
        gains, losses = [], []
        for j in range(1, n):
            d = closes[j] - closes[j-1]
            gains.append(max(0, d))
            losses.append(max(0, -d))
        ag = sum(gains[:14]) / 14
        al = sum(losses[:14]) / 14
        for j in range(14, len(gains)):
            ag = (ag * 13 + gains[j]) / 14
            al = (al * 13 + losses[j]) / 14
        rsi = 100 - 100 / (1 + ag / al) if al > 0 else 100

    # ATR
    trs = []
    for j in range(max(1, n-14), n):
        trs.append(max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1])))
    atr = sum(trs) / len(trs) if trs else cl * 0.02

    # ADX proxy
    adx = 25.0
    if n > 14:
        pr = max(closes[-14:]) - min(closes[-14:])
        adx = abs(closes[-1] - closes[-14]) / pr * 50 if pr > 0 else 20

    # Volume ratio
    va = sum(vols[-20:]) / min(20, n)
    vr = vols[-1] / va if va > 0 else 1

    # MACD
    macd_h = ema(closes[-12:], 12) - ema(closes[-26:], 26) if n >= 26 else 0

    # Returns
    r1m = closes[-1] / closes[-20] - 1 if n >= 20 else 0
    r3m = closes[-1] / closes[-60] - 1 if n >= 60 else r1m

    return {
        "close": cl, "high": highs[-1], "low": lows[-1],
        "ema_20": round(e20, 2), "ema_50": round(e50, 2), "ema_200": round(e200, 2),
        "rsi_14": round(rsi, 1), "adx": round(adx, 1),
        "di_plus": 15, "di_minus": 10,
        "atr_14": round(atr, 2), "macd_histogram": round(macd_h, 4),
        "volume_ratio_20": round(vr, 2),
        "obv_trend": "up" if vr > 1.2 else ("down" if vr < 0.8 else "flat"),
        "returns_1m": round(r1m, 4), "returns_3m": round(r3m, 4),
    }


def build_context(ticker: str, feat: dict, news: list, macro: dict) -> str:
    """Build market context for Claude agents."""
    sector = SECTORS.get(ticker, "other")
    news_text = "\n".join(f"- {n['title']}" for n in news[:5]) if news else "Нет новостей"

    ctx = {
        "ticker": ticker,
        "sector": sector,
        "price": {"close": feat["close"], "ema_20": feat["ema_20"],
                  "ema_50": feat["ema_50"], "ema_200": feat["ema_200"]},
        "momentum": {"rsi_14": feat["rsi_14"], "macd_histogram": feat["macd_histogram"]},
        "trend": {"adx": feat["adx"]},
        "volatility": {"atr_14": feat["atr_14"]},
        "volume": {"volume_ratio_20": feat["volume_ratio_20"], "obv_trend": feat["obv_trend"]},
        "returns": {"1m": feat["returns_1m"], "3m": feat["returns_3m"]},
        "macro": macro,
        "recent_news": news_text,
    }
    return json.dumps(ctx, ensure_ascii=False)


async def run_simulation():
    print("=" * 70)
    print("  CLAUDE MULTI-AGENT SIMULATION")
    print("  4 agents: Bull / Bear / Risk / Arbiter")
    print("  Real API calls, real decisions")
    print("=" * 70)

    # Load 3 months for features, simulate last 5 trading days
    end_date = "2026-03-18"
    start_date = "2025-12-01"  # enough history for features
    sim_start = "2026-03-10"   # last week

    print(f"\n  Simulation: {sim_start} to {end_date}")
    print(f"  Tickers: {len(TOP_TICKERS)}")
    print(f"  Capital: {CAPITAL:,.0f} RUB")

    d1 = load_daily_candles(start_date, end_date)
    news = load_news(sim_start)
    macro = {"key_rate_pct": 21.0, "usd_rub": 84.5, "oil_brent": 71.0,
             "macro_regime": "TIGHTENING"}

    # Get unique trading days in sim period
    all_dates = set()
    for tk_candles in d1.values():
        for c in tk_candles:
            if c["date"] >= sim_start:
                all_dates.add(c["date"])
    sim_days = sorted(all_dates)
    print(f"  Trading days: {len(sim_days)}")

    # Simulate
    cash = CAPITAL
    positions = {}
    trades = []
    daily_log = []
    api_calls = 0

    for day_idx, day in enumerate(sim_days):
        print(f"\n{'='*60}")
        print(f"  DAY {day_idx+1}: {day}")
        print(f"{'='*60}")

        day_news = news.get(day, [])
        if day_news:
            print(f"  News: {len(day_news)} articles")
            for n in day_news[:3]:
                print(f"    - {n['title'][:80]}")

        # Check existing positions — close if stop hit
        for tk in list(positions):
            pos = positions[tk]
            candles = d1.get(tk, [])
            today = next((c for c in candles if c["date"] == day), None)
            if not today:
                continue
            cl = float(today["close"])
            lo = float(today["low"])

            # Stop loss check
            if lo <= pos["stop_loss"]:
                sp = pos["stop_loss"] * (1 - SLIPPAGE/100)
                pnl = (sp - pos["entry"]) * pos["shares"]
                comm = sp * pos["shares"] * COMMISSION / 100
                cash += pos["shares"] * sp - comm
                trades.append({"date": day, "ticker": tk, "action": "STOP-LOSS",
                               "entry": pos["entry"], "exit": round(sp, 2),
                               "pnl": round(pnl - comm, 2)})
                print(f"  EXIT {tk}: STOP-LOSS @ {sp:.2f} | PnL {pnl-comm:+,.0f}")
                del positions[tk]
            # Trailing
            elif cl > pos.get("peak", pos["entry"]):
                pos["peak"] = cl
                new_sl = cl * (1 - 0.02)  # 2% trail
                if new_sl > pos["stop_loss"]:
                    pos["stop_loss"] = new_sl

        # Analyze tickers with Claude
        signals = []
        n_pos = len(positions)

        if n_pos < MAX_POS:
            candidates = [t for t in TOP_TICKERS if t not in positions]
            print(f"\n  Analyzing {len(candidates)} candidates with Claude agents...")

            for tk in candidates:
                candles = [c for c in d1.get(tk, []) if c["date"] < day]
                feat = calc_features(candles)
                if not feat:
                    continue

                print(f"\n  --- {tk} @ {feat['close']:.2f} ---")
                t0 = time.time()

                try:
                    result = await multi_agent_analyze(
                        tk, build_context(tk, feat, day_news, macro),
                        api_key=os.environ.get("ANTHROPIC_API_KEY"),
                    )
                    api_calls += 4  # 3 agents + 1 arbiter
                except Exception as e:
                    print(f"    ERROR: {e}")
                    continue

                elapsed = time.time() - t0

                bull = result.get("bull", {})
                bear = result.get("bear", {})
                risk = result.get("risk", {})
                arb = result.get("arbiter", {})

                print(f"    Bull:  {bull.get('score', '?')}/100 | {', '.join(bull.get('arguments', [])[:2])}")
                print(f"    Bear:  {bear.get('score', '?')}/100 | {', '.join(bear.get('arguments', [])[:2])}")
                print(f"    Risk:  {risk.get('verdict', '?')} | max pos {risk.get('max_position_pct', '?')}%")
                print(f"    >>> ARBITER: {arb.get('action', 'hold').upper()} confidence={arb.get('confidence', 0)} ({elapsed:.1f}s)")

                if arb.get("reasoning"):
                    print(f"    Reasoning: {arb['reasoning'][:120]}")

                action = arb.get("action", "hold")
                confidence = arb.get("confidence", 0)
                if isinstance(confidence, str):
                    confidence = int(confidence) if confidence.isdigit() else 0

                if action == "buy" and confidence >= 60:
                    signals.append({
                        "ticker": tk, "confidence": confidence,
                        "entry": arb.get("entry_price", feat["close"]),
                        "stop_loss": arb.get("stop_loss", feat["close"] * 0.97),
                        "take_profit": arb.get("take_profit", feat["close"] * 1.05),
                        "reasoning": arb.get("reasoning", ""),
                    })

        # Execute top signals
        signals.sort(key=lambda s: s["confidence"], reverse=True)
        for sig in signals[:MAX_POS - n_pos]:
            tk = sig["ticker"]
            ep = sig["entry"] * (1 + SLIPPAGE/100)
            pv = min(cash * MAX_POS_PCT, cash * 0.90 / max(1, MAX_POS - len(positions)))
            shares = int(pv / ep)
            if shares <= 0 or shares * ep > cash:
                continue

            cost = shares * ep * (1 + COMMISSION/100)
            cash -= cost
            sl = sig["stop_loss"]
            if sl >= ep:
                sl = ep * 0.97  # safety

            positions[tk] = {
                "entry": round(ep, 2), "shares": shares, "stop_loss": round(sl, 2),
                "take_profit": sig.get("take_profit", ep * 1.05),
                "date": day, "peak": ep,
                "confidence": sig["confidence"],
                "reasoning": sig["reasoning"],
            }
            trades.append({"date": day, "ticker": tk, "action": "BUY",
                           "entry": round(ep, 2), "exit": None, "pnl": None,
                           "confidence": sig["confidence"]})
            print(f"\n  >>> OPEN {tk}: {shares} shares @ {ep:.2f} | SL={sl:.2f} | conf={sig['confidence']}")

        # Daily equity
        pv = 0
        for tk, pos in positions.items():
            today = next((c for c in d1.get(tk, []) if c["date"] == day), None)
            price = float(today["close"]) if today else pos["entry"]
            pv += pos["shares"] * price
        eq = cash + pv
        daily_log.append({"date": day, "equity": round(eq, 2), "positions": len(positions), "cash": round(cash, 2)})
        print(f"\n  EOD: Equity {eq:,.0f} | Cash {cash:,.0f} | Positions {len(positions)}")

    # Force close remaining
    print(f"\n{'='*60}")
    print("  CLOSING ALL POSITIONS")
    print(f"{'='*60}")
    for tk, pos in list(positions.items()):
        candles = d1.get(tk, [])
        if candles:
            sp = float(candles[-1]["close"]) * (1 - SLIPPAGE/100)
            pnl = (sp - pos["entry"]) * pos["shares"]
            comm = sp * pos["shares"] * COMMISSION / 100
            cash += pos["shares"] * sp - comm
            trades.append({"date": sim_days[-1], "ticker": tk, "action": "CLOSE-EOD",
                           "entry": pos["entry"], "exit": round(sp, 2),
                           "pnl": round(pnl - comm, 2)})
            print(f"  CLOSE {tk}: {pnl-comm:+,.0f} (entry {pos['entry']} → exit {sp:.2f})")
    positions.clear()

    # Results
    final = cash
    ret = (final - CAPITAL) / CAPITAL

    print(f"\n{'='*70}")
    print(f"  CLAUDE MULTI-AGENT RESULTS")
    print(f"{'='*70}")
    print(f"  Period:      {sim_start} to {end_date}")
    print(f"  Initial:     {CAPITAL:>12,.0f}")
    print(f"  Final:       {final:>12,.0f}")
    print(f"  Return:      {ret:>+11.2%}")
    print(f"  API calls:   {api_calls}")

    closed = [t for t in trades if t.get("pnl") is not None]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    gp = sum(t["pnl"] for t in wins)
    gl = abs(sum(t["pnl"] for t in losses))

    print(f"\n  Trades:      {len(closed)} | WR {len(wins)/max(1,len(closed))*100:.0f}%")
    print(f"  Gross P:     {gp:>+12,.0f}")
    print(f"  Gross L:     {-gl:>12,.0f}")
    print(f"  Net:         {gp-gl:>+12,.0f}")
    print(f"  PF:          {gp/gl:.2f}" if gl > 0 else "  PF:          inf")

    print(f"\n  TRADE LOG:")
    for t in trades:
        pnl_str = f"{t['pnl']:>+8,.0f}" if t.get("pnl") is not None else "    OPEN"
        conf_str = f" conf={t.get('confidence','')}" if t.get("confidence") else ""
        print(f"    {t['date']}  {t['ticker']:6s}  {t['action']:12s}  {pnl_str}{conf_str}")

    print(f"\n  DAILY EQUITY:")
    for d in daily_log:
        chg = d["equity"] - (daily_log[daily_log.index(d)-1]["equity"] if daily_log.index(d) > 0 else CAPITAL)
        print(f"    {d['date']}  {d['equity']:>11,.0f}  {chg:>+8,.0f}  pos={d['positions']}")

    # Save
    Path("data/claude_agents_simulation.json").write_text(json.dumps({
        "period": f"{sim_start} to {end_date}",
        "initial": CAPITAL, "final": round(final, 2),
        "return_pct": round(ret * 100, 2),
        "api_calls": api_calls,
        "trades": trades,
        "daily": daily_log,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Saved: data/claude_agents_simulation.json")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simulation())
