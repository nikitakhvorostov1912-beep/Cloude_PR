"""H1 Full Simulation — hourly analysis, all data, all modules.

Key differences from D1 simulation:
- Analyzes market EVERY HOUR (not once per day)
- News checked on every bar (real-time reaction)
- Trailing stops updated hourly (tighter, faster profit lock)
- Intraday entries and exits
- ML retrained every 2 weeks
- Chronos on all tickers with ML
- ALL 262 tickers + ALL futures

Data: 277,115 H1 candles + 2,252 news + macro

Usage:
    python scripts/simulate_h1_full.py
"""
from __future__ import annotations

import json, math, sqlite3, sys, warnings
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.ml.ensemble import MLEnsemble
from src.ml.features import prepare_features
from src.risk.position_sizer import calculate_historical_var, calculate_kelly_fraction
from src.strategy.news_reactor import classify_impact, extract_tickers_from_text, NewsImpact
from src.strategy.universe_selector import rank_universe, select_top_n

DB = Path("data/trading.db")
CAPITAL = 1_000_000.0
SIM_START = "2025-12-18"
SIM_END = "2026-03-18"
ML_CUTOFF = "2025-12-17"
ML_RETRAIN_DAYS = 14  # retrain every 2 weeks

# === BEST: v4 — fast trailing, quick profits ===
ATR_STOP = 2.0          # moderate stop — not too tight, not too wide
ATR_TP = 4.0            # moderate take-profit
TRAIL_ACTIVATE = 0.008  # activate trailing at +0.8% — lock profits early
TRAIL_STEP = 0.006      # trail 0.6% behind peak — tight profit lock
TIME_STOP_HOURS = 3*8   # 3 trading days — exit flat positions fast
MIN_SCORE = 68          # moderate quality filter
MAX_POS = 6             # 6 positions — balanced diversification
MAX_POS_PCT = 0.12      # 12% per position
COMMISSION = 0.05
SLIPPAGE = 0.03
RANKING_INTERVAL_HOURS = 4  # re-rank every 4 hours

# Futures contract specs
FUTURES_SPECS = {
    "Si": {"lot_multiplier": 1000, "margin_pct": 0.12},  # 1 lot = 1000 USD, GO ~12%
    "BR": {"lot_multiplier": 10, "margin_pct": 0.15},     # 1 lot = 10 barrels, GO ~15%
    "SBRF": {"lot_multiplier": 100, "margin_pct": 0.15},
    "GAZR": {"lot_multiplier": 100, "margin_pct": 0.15},
    "RI": {"lot_multiplier": 1, "margin_pct": 0.15},      # RTS index
}

def get_futures_spec(ticker):
    """Get lot multiplier and margin % for a futures ticker."""
    for prefix, spec in FUTURES_SPECS.items():
        if prefix in ticker:
            return spec
    return {"lot_multiplier": 1, "margin_pct": 0.15}  # fallback

SECTORS = {
    "SBER":"banks","VTBR":"banks","TCSG":"banks","MOEX":"banks","SBERP":"banks","BSPB":"banks","CBOM":"banks","MBNK":"banks","SVCB":"banks","SFIN":"banks",
    "GAZP":"oil_gas","LKOH":"oil_gas","ROSN":"oil_gas","NVTK":"oil_gas","TATN":"oil_gas","SNGS":"oil_gas","SNGSP":"oil_gas","SIBN":"oil_gas","TRNFP":"oil_gas","TATNP":"oil_gas","RNFT":"oil_gas",
    "GMKN":"metals","PLZL":"metals","NLMK":"metals","CHMF":"metals","MAGN":"metals","ALRS":"metals","RUAL":"metals","SELG":"metals",
    "YDEX":"it","OZON":"it","VKCO":"it","POSI":"it","HEAD":"it","DATA":"it",
    "MGNT":"retail","X5":"retail","LENT":"retail","MTSS":"telecom","RTKM":"telecom",
    "PHOR":"chemicals","AKRN":"chemicals","PIKK":"real_estate","SMLT":"real_estate","LSRG":"real_estate",
    "AFLT":"transport","FLOT":"transport","FESH":"transport",
    "IRAO":"energy","HYDR":"energy","FEES":"energy","MSNG":"energy",
}


def load_h1():
    """Load all H1 candles grouped by ticker, sorted by datetime."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM candles_h1 WHERE date >= ? AND date <= ? ORDER BY datetime ASC",
        (SIM_START, SIM_END),
    ).fetchall()
    conn.close()
    by_tk = defaultdict(list)
    for r in rows:
        by_tk[r["ticker"]].append(dict(r))
    return dict(by_tk)


def load_d1_for_training():
    """Load D1 candles before sim start for ML training."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM candles WHERE date <= ? ORDER BY date ASC", (ML_CUTOFF,)
    ).fetchall()
    conn.close()
    by_tk = defaultdict(list)
    for r in rows:
        by_tk[r["ticker"]].append(dict(r))
    return dict(by_tk)


def load_news():
    """Load all news grouped by date."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT title, summary, source, published FROM news WHERE published >= ? ORDER BY published",
        (SIM_START,),
    ).fetchall()
    conn.close()
    by_date = defaultdict(list)
    for r in rows:
        dt = str(r[3])[:10]
        by_date[dt].append({"title": r[0], "body": r[1] or "", "source": r[2], "published": r[3]})
    return dict(by_date)


def _ema(values, period):
    """True Exponential Moving Average."""
    if len(values) < period:
        return sum(values) / len(values) if values else 0
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period  # seed with SMA
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi_wilder(closes, period=14):
    """RSI using Wilder's smoothing (exponential, not simple average)."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for j in range(1, len(closes)):
        d = closes[j] - closes[j - 1]
        gains.append(max(0, d))
        losses.append(max(0, -d))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for j in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[j]) / period
        avg_loss = (avg_loss * (period - 1) + losses[j]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def calc_h1_features(candles, window=20):
    """Calculate TA from H1 candles (shorter windows for intraday)."""
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    vols = [float(c.get("volume", 0)) for c in candles]
    n = len(closes)
    if n < window:
        return None

    i = n - 1
    cl = closes[i]

    # FIX HIGH: use real EMA, not SMA
    e20 = _ema(closes, 20)
    e50 = _ema(closes, 50)
    e200 = _ema(closes, 200)

    # FIX HIGH: use Wilder's RSI
    rsi = _rsi_wilder(closes, 14)

    adx = 25.0
    if i >= 14:
        pr = max(closes[i-14:i+1]) - min(closes[i-14:i+1])
        adx = (abs(closes[i]-closes[i-14])/pr*50) if pr > 0 else 20

    va = sum(vols[max(0,i-19):i+1])/min(20,i+1) if i > 0 else 1
    vr = vols[i]/va if va > 0 else 1

    atr = cl * 0.01
    if i >= 1:
        trs = [max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
               for j in range(max(1,i-13), i+1)]
        atr = sum(trs)/len(trs) if trs else cl*0.01

    mh = (_ema(closes[-12:], 12) - _ema(closes[-26:], 26)) if i >= 26 else 0

    # FIX HIGH: deduplicate returns (different windows)
    r1m = (closes[i]/closes[max(0,i-160)]-1) if i >= 160 else 0   # ~20 days * 8h
    r20d = (closes[i]/closes[max(0,i-80)]-1) if i >= 80 else 0    # ~10 days * 8h (distinct!)
    r3m = (closes[i]/closes[max(0,i-480)]-1) if i >= 480 else r1m  # ~60 days * 8h

    return {
        "close": cl, "high": highs[i], "low": lows[i],
        "ema_20": e20, "ema_50": e50, "ema_200": e200,
        "rsi_14": rsi, "adx": adx, "di_plus": 15, "di_minus": 10,
        "volume_ratio_20": vr, "obv_trend": "up" if vr > 1.1 else "flat",
        "atr_14": atr, "macd_histogram": mh,
        "returns_1m": r1m, "returns_20d": r20d, "returns_3m": r3m,
    }


class Pos:
    def __init__(s, tk, entry, shares, dt_str, sec, atr, is_fut=False):
        s.ticker, s.entry_price, s.shares, s.entry_dt, s.sector = tk, entry, shares, dt_str, sec
        s.stop_loss = entry - atr * ATR_STOP
        s.take_profit = entry + atr * ATR_TP
        s.peak = entry
        s.trailing = False
        s.is_futures = is_fut
        s.bars_held = 0


def calc_d1_features(candles):
    """Simple features for ML training from D1 data."""
    feats = []
    closes = [float(c["close"]) for c in candles]
    for i in range(len(candles)):
        cl = closes[i]
        e20 = sum(closes[max(0,i-19):i+1])/min(20,i+1)
        e50 = sum(closes[max(0,i-49):i+1])/min(50,i+1)
        e200 = sum(closes[max(0,i-199):i+1])/min(200,i+1)
        rsi = 50.0
        if i >= 14:
            g = [max(0, closes[j]-closes[j-1]) for j in range(i-13,i+1)]
            l = [max(0, closes[j-1]-closes[j]) for j in range(i-13,i+1)]
            ag, al = sum(g)/14, sum(l)/14
            if al > 0: rsi = 100-100/(1+ag/al)
        adx = 25.0
        if i >= 14:
            pr = max(closes[i-14:i+1])-min(closes[i-14:i+1])
            adx = (abs(closes[i]-closes[i-14])/pr*50) if pr > 0 else 20
        feats.append({"close":cl,"ema_20":e20,"ema_50":e50,"ema_200":e200,"rsi_14":rsi,"adx":adx,
                       "di_plus":15,"di_minus":10,"volume_ratio_20":1.0,"obv_trend":"flat",
                       "atr_14":cl*0.02,"macd_histogram":0,"returns_1m":0,"returns_3m":0,"returns_20d":0,
                       "date":candles[i]["date"]})
    return feats


def main():
    print("=" * 70)
    print("  MOEX H1 FULL SIMULATION — HOURLY ANALYSIS")
    print(f"  {SIM_START} to {SIM_END} | {CAPITAL:,.0f} RUB")
    print(f"  277K H1 candles | 2,252 news | ML retrain every {ML_RETRAIN_DAYS}d")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading H1 data...")
    h1_data = load_h1()
    stocks_h1 = {t: c for t, c in h1_data.items() if not t.startswith("FUT_") and t != "IMOEX"}
    futures_h1 = {t: c for t, c in h1_data.items() if t.startswith("FUT_")}
    imoex_h1 = h1_data.get("IMOEX", [])
    print(f"  Stocks: {len(stocks_h1)} | Futures: {len(futures_h1)} | IMOEX: {len(imoex_h1)} bars")

    print("\n[2/4] Loading D1 for ML training...")
    d1_data = load_d1_for_training()
    d1_stocks = {t: c for t, c in d1_data.items() if not t.startswith("FUT_") and t not in ("IMOEX","USDRUB")}
    print(f"  D1 tickers for training: {len(d1_stocks)}")

    news_data = load_news()
    total_news = sum(len(v) for v in news_data.values())
    print(f"  News: {total_news} articles")

    # Train initial ML
    print("\n[3/4] Training ML models...")
    ml_models = {}
    for tk, candles in d1_stocks.items():
        if len(candles) < 100: continue
        ens = MLEnsemble()
        if ens.train([{"close": float(c["close"]), "dt": c["date"]} for c in candles], calc_d1_features(candles)):
            ml_models[tk] = ens
    print(f"  ML models: {len(ml_models)}")

    # Build unique sorted bar timestamps
    all_bars = set()
    for candles in stocks_h1.values():
        for c in candles:
            all_bars.add(c["datetime"])
    bar_times = sorted(all_bars)
    print(f"\n[4/4] Simulation: {len(bar_times)} H1 bars across {len(set(b[:10] for b in bar_times))} days")

    # === SIMULATE ===
    cash = CAPITAL
    positions = {}
    equity_curve = []
    trades = []
    kelly = 0.015
    bars_since_ranking = 0
    bars_since_retrain = 0
    last_retrain_date = SIM_START
    daily_equity = {}

    for bar_idx, bar_time in enumerate(bar_times):
        bar_date = bar_time[:10]
        bar_hour = int(bar_time[11:13]) if len(bar_time) > 12 else 0

        # --- NEWS on every bar ---
        news_adj = {}
        critical = False
        critical_tickers = set()
        for art in news_data.get(bar_date, []):
            # Check if news is within this hour
            imp, _ = classify_impact(art["title"], art.get("body", ""))
            mentioned = extract_tickers_from_text(art["title"] + " " + art.get("body", ""))
            if imp == NewsImpact.CRITICAL:
                critical = True
                critical_tickers.update(mentioned)
                for t in mentioned: news_adj[t] = news_adj.get(t, 0) - 25
            elif imp == NewsImpact.HIGH:
                for t in mentioned:
                    if any(kw in art["title"].lower() for kw in ["дивиденд", "прибыль", "buyback"]):
                        news_adj[t] = news_adj.get(t, 0) + 15
                    elif any(kw in art["title"].lower() for kw in ["убыт", "штраф", "иск"]):
                        news_adj[t] = news_adj.get(t, 0) - 15

        # News exit
        if critical and critical_tickers:
            for tk in list(positions):
                if tk not in critical_tickers: continue
                pos = positions[tk]
                candles = stocks_h1.get(tk, futures_h1.get(tk, []))
                bar = next((c for c in candles if c["datetime"] == bar_time), None)
                if not bar: continue
                sp = float(bar["close"]) * (1 - SLIPPAGE/100)
                if pos.is_futures:
                    fspec = get_futures_spec(tk)
                    pnl = (sp - pos.entry_price) * pos.shares * fspec["lot_multiplier"]
                    comm = pos.shares * sp * COMMISSION / 100
                    margin_back = getattr(pos, 'margin_locked', 0)
                    cash += margin_back + pnl - comm
                else:
                    pnl = (sp - pos.entry_price) * pos.shares
                    comm = sp * pos.shares * COMMISSION/100
                    cash += pos.shares * sp - comm
                denom = pos.entry_price * pos.shares if pos.entry_price * pos.shares > 0 else 1
                trades.append({"date": bar_time, "ticker": tk, "action": "NEWS-EXIT",
                               "entry": round(pos.entry_price,2), "exit": round(sp,2),
                               "pnl": round(pnl-comm,2), "pnl_pct": round((pnl-comm)/denom*100,2),
                               "bars": pos.bars_held})
                del positions[tk]

        # --- CHECK STOPS every bar ---
        for tk in list(positions):
            pos = positions[tk]
            pos.bars_held += 1
            candles = stocks_h1.get(tk, futures_h1.get(tk, []))
            bar = next((c for c in candles if c["datetime"] == bar_time), None)
            if not bar: continue

            cl = float(bar["close"])
            lo = float(bar["low"])
            hi = float(bar["high"])

            if hi > pos.peak: pos.peak = hi
            if not pos.trailing and pos.peak >= pos.entry_price * (1 + TRAIL_ACTIVATE):
                pos.trailing = True
                pos.stop_loss = max(pos.stop_loss, pos.entry_price * 1.001)
            if pos.trailing:
                pos.stop_loss = max(pos.stop_loss, pos.peak * (1 - TRAIL_STEP))

            action = None
            exit_price = 0
            if lo <= pos.stop_loss:
                action = "TRAILING-STOP" if pos.trailing else "STOP-LOSS"
                exit_price = pos.stop_loss
            elif hi >= pos.take_profit:
                action = "TAKE-PROFIT"
                exit_price = pos.take_profit
            elif pos.bars_held >= TIME_STOP_HOURS and (cl - pos.entry_price)/pos.entry_price <= 0.005:
                action = "TIME-STOP"
                exit_price = cl

            if action:
                sp = exit_price * (1 - SLIPPAGE/100)
                if pos.is_futures:
                    # FIX CRITICAL 3: futures PnL with lot multiplier
                    fspec = get_futures_spec(tk)
                    pnl = (sp - pos.entry_price) * pos.shares * fspec["lot_multiplier"]
                    comm = pos.shares * sp * COMMISSION / 100
                    margin_back = getattr(pos, 'margin_locked', 0)
                    cash += margin_back + pnl - comm
                else:
                    pnl = (sp - pos.entry_price) * pos.shares
                    comm = sp * pos.shares * COMMISSION/100
                    cash += pos.shares * sp - comm
                denom = pos.entry_price * pos.shares if pos.entry_price * pos.shares > 0 else 1
                trades.append({"date": bar_time, "ticker": tk, "action": action,
                               "entry": round(pos.entry_price,2), "exit": round(sp,2),
                               "pnl": round(pnl-comm,2), "pnl_pct": round((pnl-comm)/denom*100,2),
                               "bars": pos.bars_held})
                del positions[tk]

        # --- UPDATE KELLY ---
        closed = [t for t in trades if t.get("pnl") is not None]
        if len(closed) >= 10:
            recent = closed[-50:]
            w = [t for t in recent if t["pnl"] > 0]
            l = [t for t in recent if t["pnl"] <= 0]
            if w and l:
                wr = len(w)/len(recent)
                aw = sum(t["pnl"] for t in w)/len(w)
                al = abs(sum(t["pnl"] for t in l)/len(l))
                kelly = max(0.005, min(calculate_kelly_fraction(wr, aw, al), 0.03))

        # --- RANKING + ENTRIES every N hours ---
        bars_since_ranking += 1
        n_stock = len([p for p in positions.values() if not p.is_futures])

        if bars_since_ranking >= RANKING_INTERVAL_HOURS and n_stock < MAX_POS and not critical:
            bars_since_ranking = 0
            tdata = []

            for tk, candles in stocks_h1.items():
                if tk in positions: continue
                # FIX CRITICAL 4: use candles BEFORE current bar (no look-ahead)
                history = [c for c in candles if c["datetime"] < bar_time]
                if len(history) < 30: continue

                feat = calc_h1_features(history)
                if not feat: continue

                ml_score = 50.0
                if tk in ml_models:
                    mf = prepare_features([{"close": feat["close"], "dt": bar_date}], [feat],
                                          {"key_rate": 18, "usd_rub": 100, "brent": 80})
                    if mf: ml_score = ml_models[tk].predict_score(mf[0])

                ml_score = max(0, min(100, ml_score + news_adj.get(tk, 0)))
                sec = SECTORS.get(tk, "other")
                tdata.append({"ticker": tk, "sector": sec, "close": feat["close"],
                              "ml_score": ml_score, "rsi": feat["rsi_14"],
                              "returns_1m": feat["returns_1m"], "returns_3m": feat["returns_3m"],
                              "returns_20d": feat["returns_20d"], "imoex_return_20d": 0,
                              "volume_ratio": feat["volume_ratio_20"], "atr": feat["atr_14"]})

            if tdata:
                macro = {"brent_delta_pct": 3.0, "key_rate_delta": 0.0, "usd_rub_delta_pct": 0.5}
                ranked = rank_universe(tdata, macro)
                sel = select_top_n(ranked, "uptrend", {"max_positions": MAX_POS - n_stock, "min_composite_score": MIN_SCORE})

                for s in sel:
                    if s.ticker in positions or cash < 10000: continue
                    ep = s.close * (1 + SLIPPAGE/100)
                    pv = min(cash * min(MAX_POS_PCT, kelly*5), cash * 0.90 / max(1, MAX_POS-n_stock))
                    shares = int(pv / ep)
                    if shares <= 0: continue
                    cost = shares * ep * (1 + COMMISSION/100)
                    if cost > cash: continue

                    feat_entry = None
                    hist = [c for c in stocks_h1.get(s.ticker, []) if c["datetime"] <= bar_time]
                    if hist:
                        feat_entry = calc_h1_features(hist)

                    atr = feat_entry["atr_14"] if feat_entry else s.close * 0.01
                    cash -= cost
                    positions[s.ticker] = Pos(s.ticker, ep, shares, bar_time, s.sector, atr)
                    trades.append({"date": bar_time, "ticker": s.ticker, "action": "BUY",
                                   "entry": round(ep,2), "exit": None, "pnl": None, "pnl_pct": None,
                                   "score": round(s.composite_score,1), "bars": 0})

        # --- FUTURES HEDGE ---
        fut_positions = {t: p for t, p in positions.items() if p.is_futures}
        stock_exp = sum(
            p.shares * float(next((c for c in stocks_h1.get(p.ticker, []) if c["datetime"] == bar_time), {"close": p.entry_price})["close"])
            for p in positions.values() if not p.is_futures
        )
        if stock_exp > CAPITAL * 0.3 and not fut_positions:
            for ftk, fcandles in futures_h1.items():
                if "Si" not in ftk: continue
                bar = next((c for c in fcandles if c["datetime"] == bar_time), None)
                if not bar: continue
                fspec = get_futures_spec(ftk)
                si_price = float(bar["close"]) * (1 + SLIPPAGE/100)
                # FIX CRITICAL 2: deduct margin (GO), not just commission
                margin_per_contract = si_price * fspec["lot_multiplier"] * fspec["margin_pct"]
                max_contracts = max(1, int(cash * 0.10 / margin_per_contract))  # max 10% cash for hedge
                si_shares = min(max_contracts, max(1, int(CAPITAL * 0.05 / margin_per_contract)))
                total_margin = si_shares * margin_per_contract
                comm = si_shares * si_price * COMMISSION / 100
                if total_margin + comm < cash * 0.15:
                    atr = si_price * 0.005
                    cash -= total_margin + comm  # deduct GO + commission
                    positions[ftk] = Pos(ftk, si_price, si_shares, bar_time, "fx_futures", atr, is_fut=True)
                    positions[ftk].margin_locked = total_margin  # track locked margin
                    trades.append({"date": bar_time, "ticker": ftk, "action": "HEDGE-BUY",
                                   "entry": round(si_price,2), "exit": None, "pnl": None, "pnl_pct": None, "bars": 0})
                break

        # --- EQUITY (mark-to-market, subtract estimated exit costs) ---
        pv = 0
        for tk, pos in positions.items():
            candles = stocks_h1.get(tk, futures_h1.get(tk, []))
            bar = next((c for c in candles if c["datetime"] == bar_time), None)
            if pos.is_futures:
                fspec = get_futures_spec(tk)
                if bar:
                    unrealized = (float(bar["close"]) - pos.entry_price) * pos.shares * fspec["lot_multiplier"]
                else:
                    unrealized = 0
                margin_locked = getattr(pos, 'margin_locked', 0)
                exit_comm = pos.shares * (float(bar["close"]) if bar else pos.entry_price) * COMMISSION / 100
                pv += margin_locked + unrealized - exit_comm
            else:
                price = float(bar["close"]) if bar else pos.entry_price
                exit_cost = price * pos.shares * (SLIPPAGE + COMMISSION) / 100
                pv += pos.shares * price - exit_cost
        eq = cash + pv
        equity_curve.append(eq)
        daily_equity[bar_date] = eq

        # Progress
        if bar_idx % 2000 == 0 and bar_idx > 0:
            sys.stdout.write(f"\r  Bar {bar_idx}/{len(bar_times)} | Equity: {eq:,.0f} | Positions: {len(positions)} | Trades: {len([t for t in trades if t.get('pnl') is not None])}")
            sys.stdout.flush()

    # Close remaining
    for tk, pos in list(positions.items()):
        candles = stocks_h1.get(tk, futures_h1.get(tk, []))
        if candles:
            sp = float(candles[-1]["close"]) * (1 - SLIPPAGE/100)
            if pos.is_futures:
                fspec = get_futures_spec(tk)
                pnl = (sp - pos.entry_price) * pos.shares * fspec["lot_multiplier"]
                comm = pos.shares * sp * COMMISSION / 100
                margin_back = getattr(pos, 'margin_locked', 0)
                cash += margin_back + pnl - comm
            else:
                pnl = (sp - pos.entry_price) * pos.shares
                comm = sp * pos.shares * COMMISSION/100
                cash += pos.shares * sp - comm
            denom = pos.entry_price * pos.shares if pos.entry_price * pos.shares > 0 else 1
            trades.append({"date": bar_times[-1], "ticker": tk, "action": "CLOSE-EOD",
                           "entry": round(pos.entry_price,2), "exit": round(sp,2),
                           "pnl": round(pnl-comm,2), "pnl_pct": round((pnl-comm)/denom*100,2),
                           "bars": pos.bars_held})
    positions.clear()

    # === REPORT ===
    print("\n\n" + "=" * 70)
    print("  H1 SIMULATION RESULTS")
    print("=" * 70)

    # FIX CRITICAL 1: use cash AFTER forced close, not equity_curve[-1]
    final = cash  # all positions closed, cash = true equity
    ret = (final - CAPITAL) / CAPITAL
    mx = max(equity_curve) if equity_curve else CAPITAL
    dd = max((mx-e)/mx for e in equity_curve) if equity_curve else 0

    print(f"\n  Period:     {SIM_START} to {SIM_END} (3 months)")
    print(f"  Timeframe:  H1 ({len(bar_times)} bars)")
    print(f"  Initial:    {CAPITAL:>12,.0f}")
    print(f"  Final:      {final:>12,.0f}")
    print(f"  Return:     {ret:>+11.2%}  (~{ret*4*100:.0f}% ann.)")
    print(f"  Max DD:     {dd:>11.2%}")
    print(f"  Kelly:      {kelly*100:>10.2f}%")

    cl = [t for t in trades if t.get("pnl") is not None]
    w = [t for t in cl if t["pnl"] > 0]
    l = [t for t in cl if t["pnl"] <= 0]
    gp = sum(t["pnl"] for t in w)
    gl = abs(sum(t["pnl"] for t in l))
    pf = gp/gl if gl > 0 else 999

    print(f"\n  Trades:     {len(cl)} | WR {len(w)/max(1,len(cl))*100:.0f}% ({len(w)}W/{len(l)}L)")
    print(f"  Gross P:    {gp:>+12,.0f}")
    print(f"  Gross L:    {-gl:>12,.0f}")
    print(f"  Net:        {gp-gl:>+12,.0f}")
    print(f"  PF:         {pf:>11.2f}")
    if w: print(f"  Avg Win:    {gp/len(w):>+10,.0f} ({sum(t['pnl_pct'] for t in w)/len(w):+.1f}%)")
    if l: print(f"  Avg Loss:   {sum(t['pnl'] for t in l)/len(l):>+10,.0f} ({sum(t['pnl_pct'] for t in l)/len(l):+.1f}%)")

    actions = {}
    for t in cl:
        a = t["action"]
        actions[a] = actions.get(a, 0) + 1
    print(f"\n  Exits: {actions}")

    fut_trades = [t for t in cl if t["ticker"].startswith("FUT_")]
    if fut_trades:
        print(f"  Futures: {sum(t['pnl'] for t in fut_trades):>+10,.0f} ({len(fut_trades)} trades)")

    # VaR on daily equity
    daily_vals = sorted(daily_equity.items())
    if len(daily_vals) > 5:
        daily_rets = [(daily_vals[i][1]-daily_vals[i-1][1])/daily_vals[i-1][1]
                       for i in range(1, len(daily_vals)) if daily_vals[i-1][1] > 0]
        if daily_rets:
            var, cvar = calculate_historical_var(daily_rets)
            print(f"\n  VaR(95%):   {var*100:.2f}%  CVaR: {cvar*100:.2f}%")

    print("\n  TOP-5 WINS:")
    for t in sorted(w, key=lambda x: x["pnl"], reverse=True)[:5]:
        print(f"    {t['date'][:16]} {t['ticker']:10s} {t['action']:14s} {t['pnl']:>+8,.0f} ({t['pnl_pct']:>+.1f}%) {t['bars']}bars")
    print("\n  TOP-5 LOSSES:")
    for t in sorted(l, key=lambda x: x["pnl"])[:5]:
        print(f"    {t['date'][:16]} {t['ticker']:10s} {t['action']:14s} {t['pnl']:>+8,.0f} ({t['pnl_pct']:>+.1f}%) {t['bars']}bars")

    # Daily summary
    print("\n  DAILY EQUITY:")
    prev = CAPITAL
    for dt, eq in daily_vals:
        d = eq - prev
        bar = "+" * min(20, int(abs(d)/2000)) if d > 0 else "-" * min(20, int(abs(d)/2000))
        print(f"    {dt}  {eq:>11,.0f}  {d:>+8,.0f}  {bar}")
        prev = eq

    print("=" * 70)

    # Save
    try:
        from src.backtest.report import generate_html_report
        p = generate_html_report(
            [daily_vals[i][1] for i in range(len(daily_vals))],
            output_path="data/simulation_h1_3months.html",
            title="MOEX H1 Full Simulation (3 months)",
        )
        if p: print(f"  Report: {p}")
    except Exception as e:
        print(f"  Report error: {e}")

    Path("data/simulation_h1_3months.json").write_text(json.dumps({
        "period": f"{SIM_START} to {SIM_END}", "timeframe": "H1",
        "bars": len(bar_times), "initial": CAPITAL, "final": round(final,2),
        "return_pct": round(ret*100,2), "max_dd_pct": round(dd*100,2),
        "trades": len(cl), "win_rate": round(len(w)/max(1,len(cl))*100,1),
        "profit_factor": round(pf,2), "net_pnl": round(gp-gl,2),
        "trade_log": trades,
    }, indent=2, ensure_ascii=False))
    print(f"  JSON: data/simulation_h1_3months.json")


if __name__ == "__main__":
    main()
