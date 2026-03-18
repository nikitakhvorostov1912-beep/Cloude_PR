"""V3.1 Neural Simulation — ALL modules + Chronos-Bolt + TSFRESH.

Everything from V3 PLUS:
- Chronos-Bolt (Transformer 9M): zero-shot price forecast, direction + confidence
- TSFRESH: 794 auto-features, filtered to top-50 significant
- Neural score integrated as 9th factor in ranking

Usage:
    python scripts/simulate_v3_neural.py
"""
from __future__ import annotations

import json, math, sqlite3, sys, warnings
from datetime import datetime
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

# Neural modules
CHRONOS_AVAILABLE = False
try:
    from src.analysis.tsfm_predictor import predict_direction, ForecastResult
    import torch
    CHRONOS_AVAILABLE = True
except ImportError:
    pass

TSFRESH_AVAILABLE = False
try:
    from src.analysis.tsfresh_features import extract_features as tsfresh_extract
    TSFRESH_AVAILABLE = True
except ImportError:
    pass

DB = Path("data/trading.db")
CAPITAL = 1_000_000.0
SIM_START, SIM_END = "2026-02-18", "2026-03-18"
ML_CUTOFF = "2026-02-17"

# Tuned parameters
ATR_STOP = 1.8
ATR_TP = 3.5
TRAIL_ACTIVATE = 0.015
TRAIL_STEP = 0.01
TIME_STOP = 7
MIN_SCORE = 62
MAX_POS = 7
MAX_POS_PCT = 0.10
COMMISSION = 0.05
SLIPPAGE = 0.03
FUTURES_ALLOC = 0.15  # 15% capital for futures hedge

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


def load_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    # Candles
    rows = conn.execute("SELECT * FROM candles ORDER BY date ASC").fetchall()
    by_t = {}
    for r in rows:
        t = r["ticker"]
        if t not in by_t: by_t[t] = []
        by_t[t].append(dict(r))
    # News
    news_rows = conn.execute("SELECT title, summary, source, published FROM news").fetchall()
    news_by_date = {}
    for r in news_rows:
        dt = str(r["published"])[:10]
        if dt not in news_by_date: news_by_date[dt] = []
        news_by_date[dt].append({"title": r["title"], "body": r["summary"] or "", "source": r["source"]})
    conn.close()
    return by_t, news_by_date


def calc_ta(candles):
    feats = []
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    vols = [float(c["volume"]) for c in candles]
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
            if al > 0: rsi = 100 - 100/(1+ag/al)
        adx = 25.0
        if i >= 14:
            pr = max(closes[i-14:i+1]) - min(closes[i-14:i+1])
            adx = (abs(closes[i]-closes[i-14])/pr*50) if pr > 0 else 20
        va = sum(vols[max(0,i-19):i+1])/min(20,i+1) if i > 0 else 1
        vr = vols[i]/va if va > 0 else 1
        atr = cl*0.02
        if i >= 1:
            trs = [max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1])) for j in range(max(1,i-13),i+1)]
            atr = sum(trs)/len(trs) if trs else cl*0.02
        mh = (sum(closes[i-11:i+1])/12 - sum(closes[i-25:i+1])/26) if i >= 26 else 0
        r1m = (closes[i]/closes[max(0,i-20)]-1) if i >= 20 else 0
        r3m = (closes[i]/closes[max(0,i-60)]-1) if i >= 60 else 0
        r20 = r1m
        feats.append({"close":cl,"ema_20":e20,"ema_50":e50,"ema_200":e200,"rsi_14":rsi,"adx":adx,
                       "di_plus":15,"di_minus":10,"volume_ratio_20":vr,"obv_trend":"up" if vr>1.1 else "flat",
                       "atr_14":atr,"macd_histogram":mh,"returns_1m":r1m,"returns_3m":r3m,"returns_20d":r20,
                       "date":candles[i]["date"]})
    return feats


class Pos:
    def __init__(s, tk, entry, shares, dt, sec, atr, is_futures=False):
        s.ticker, s.entry_price, s.shares, s.entry_date, s.sector = tk, entry, shares, dt, sec
        s.stop_loss = entry - atr * ATR_STOP
        s.take_profit = entry + atr * ATR_TP
        s.peak = entry
        s.trailing = False
        s.is_futures = is_futures


def main():
    print("=" * 70)
    print("  MOEX V3 SIMULATION — ALL MODULES")
    print(f"  {SIM_START} to {SIM_END} | {CAPITAL:,.0f} RUB")
    print("=" * 70)

    all_candles, news_by_date = load_db()

    # Separate stocks vs futures vs index
    stocks = {t: c for t, c in all_candles.items() if len(c) >= 200 and not t.startswith("FUT_") and t not in ("IMOEX","USDRUB")}
    futures = {t: c for t, c in all_candles.items() if t.startswith("FUT_") and len(c) >= 30}
    imoex = all_candles.get("IMOEX", [])
    usdrub = all_candles.get("USDRUB", [])

    print(f"  Stocks: {len(stocks)} | Futures: {len(futures)} | IMOEX: {len(imoex)} bars | USDRUB: {len(usdrub)} bars")
    print(f"  News: {sum(len(v) for v in news_by_date.values())} articles")

    # Real macro series
    imoex_by_date = {c["date"]: float(c["close"]) for c in imoex}
    usdrub_by_date = {c["date"]: float(c["close"]) for c in usdrub}
    # Brent from futures
    brent_dates = {}
    for t, candles in futures.items():
        if "BR" in t:
            for c in candles:
                brent_dates[c["date"]] = float(c["close"])

    # Train ML
    print("\nTraining ML (honest)...")
    ml_models = {}
    for tk, candles in stocks.items():
        train = [c for c in candles if c["date"] <= ML_CUTOFF]
        if len(train) < 100: continue
        ens = MLEnsemble()
        if ens.train([{"close": float(c["close"]), "dt": c["date"]} for c in train], calc_ta(train)):
            ml_models[tk] = ens
    print(f"  ML models: {len(ml_models)}")

    # === CHRONOS-BOLT: precompute forecasts for top tickers ===
    chronos_forecasts: dict[str, dict[str, ForecastResult]] = {}  # ticker -> {date -> ForecastResult}
    if CHRONOS_AVAILABLE:
        print("\nComputing Chronos-Bolt forecasts (Transformer 9M)...")
        # Only for tickers with ML models (most liquid)
        chronos_count = 0
        pipeline = None
        try:
            from chronos import BaseChronosPipeline
            pipeline = BaseChronosPipeline.from_pretrained(
                "amazon/chronos-bolt-tiny", device_map="cpu", torch_dtype=torch.float32)
        except Exception as e:
            print(f"  Chronos init error: {e}")

        if pipeline:
            top_tickers = sorted(ml_models.keys(), key=lambda t: len(stocks.get(t, [])), reverse=True)[:50]
            for tk in top_tickers:
                candles = stocks.get(tk, [])
                train = [c for c in candles if c["date"] <= ML_CUTOFF]
                if len(train) < 60:
                    continue
                closes_train = [float(c["close"]) for c in train]

                # For each sim date, predict using data up to that date
                tk_forecasts = {}
                all_closes = [float(c["close"]) for c in candles]
                date_to_idx = {c["date"]: i for i, c in enumerate(candles)}

                for dt in sorted({c["date"] for c in candles if SIM_START <= c["date"] <= SIM_END}):
                    idx = date_to_idx.get(dt)
                    if idx is None or idx < 60:
                        continue
                    history = all_closes[:idx]  # only data before this date
                    try:
                        context = torch.tensor(history[-200:], dtype=torch.float32).unsqueeze(0)
                        quantiles, _ = pipeline.predict_quantiles(
                            context, prediction_length=5, quantile_levels=[0.1, 0.5, 0.9])
                        q10 = float(quantiles[0, :, 0].mean())
                        q50 = float(quantiles[0, :, 1].mean())
                        q90 = float(quantiles[0, :, 2].mean())
                        last = history[-1]
                        pct = (q50 - last) / last if last > 0 else 0
                        direction = 1 if pct > 0.005 else (-1 if pct < -0.005 else 0)
                        width = (q90 - q10) / last if last > 0 else 1
                        conf = max(0.0, min(1.0, 1.0 - width * 5))
                        tk_forecasts[dt] = ForecastResult(
                            direction=direction, confidence=round(conf, 4),
                            median_forecast=round(q50, 2), low_10=round(q10, 2),
                            high_90=round(q90, 2), horizon=5)
                    except Exception:
                        pass

                if tk_forecasts:
                    chronos_forecasts[tk] = tk_forecasts
                    chronos_count += 1

            print(f"  Chronos forecasts: {chronos_count} tickers, {sum(len(v) for v in chronos_forecasts.values())} predictions")
    else:
        print("\n  Chronos-Bolt: not available (install torch + chronos-forecasting)")

    # === TSFRESH: precompute features for top tickers ===
    tsfresh_features: dict[str, dict[str, dict]] = {}  # ticker -> {date -> {feature: value}}
    if TSFRESH_AVAILABLE:
        print("\nComputing TSFRESH features (794 extractors)...")
        tsfresh_count = 0
        top_tickers = sorted(ml_models.keys(), key=lambda t: len(stocks.get(t, [])), reverse=True)[:30]
        for tk in top_tickers:
            candles = stocks.get(tk, [])
            train = [c for c in candles if c["date"] <= ML_CUTOFF]
            if len(train) < 100:
                continue
            # Extract features on training data
            candle_dicts = [{"close": float(c["close"]), "volume": float(c["volume"]), "dt": c["date"]} for c in train]
            try:
                features = tsfresh_extract(candle_dicts, window=60, column="close")
                if features:
                    # Map last features to sim dates (simplified: use last window's features)
                    n_rows = len(next(iter(features.values())))
                    if n_rows > 0:
                        last_feats = {k: v[-1] for k, v in features.items() if v}
                        # Use same features for all sim dates (they won't change much day-to-day)
                        tk_tsf = {}
                        for c in candles:
                            if SIM_START <= c["date"] <= SIM_END:
                                tk_tsf[c["date"]] = last_feats
                        if tk_tsf:
                            tsfresh_features[tk] = tk_tsf
                            tsfresh_count += 1
            except Exception as e:
                pass  # TSFRESH can be noisy

        print(f"  TSFRESH features: {tsfresh_count} tickers, {len(next(iter(next(iter(tsfresh_features.values())).values()), {})) if tsfresh_features else 0} features each")
    else:
        print("\n  TSFRESH: not available (install tsfresh)")

    # Features
    tk_feats = {}
    for tk, candles in stocks.items():
        feats = calc_ta(candles)
        dm = {f["date"]: f for f in feats if SIM_START <= f["date"] <= SIM_END}
        if dm: tk_feats[tk] = dm

    # Futures features
    fut_feats = {}
    for tk, candles in futures.items():
        feats = calc_ta(candles)
        dm = {f["date"]: f for f in feats if SIM_START <= f["date"] <= SIM_END}
        if dm: fut_feats[tk] = dm

    sim_dates = sorted({c["date"] for cs in stocks.values() for c in cs if SIM_START <= c["date"] <= SIM_END})
    print(f"  Sim dates: {len(sim_dates)}")

    # === SIMULATE ===
    cash = CAPITAL
    positions = {}
    equity_curve = []
    trades = []
    kelly_fraction = 0.015  # start with 1.5%, update after trades

    for today in sim_dates:
        # --- REAL MACRO ---
        imoex_today = imoex_by_date.get(today, 0)
        imoex_20d_ago = 0
        for d in sim_dates:
            if d < today:
                past = imoex_by_date.get(d, 0)
                if past > 0: imoex_20d_ago = past
        imoex_sma200 = sum(imoex_by_date.get(d, 0) for d in sorted(imoex_by_date) if d <= today)
        imoex_sma200_count = sum(1 for d in imoex_by_date if d <= today)
        imoex_sma200 = imoex_sma200 / max(1, imoex_sma200_count)
        imoex_above_sma = imoex_today > imoex_sma200 if imoex_today > 0 else True

        usd_today = usdrub_by_date.get(today, 0)
        usd_prev = 0
        for d in sorted(usdrub_by_date):
            if d < today and usdrub_by_date[d] > 0: usd_prev = usdrub_by_date[d]
        usd_delta_pct = ((usd_today - usd_prev) / usd_prev * 100) if usd_prev > 0 and usd_today > 0 else 0

        brent_today = brent_dates.get(today, 0)
        brent_30d = [brent_dates.get(d, 0) for d in sorted(brent_dates) if d <= today and brent_dates.get(d, 0) > 0]
        brent_delta = 0
        if len(brent_30d) >= 20 and brent_30d[-1] > 0:
            brent_delta = (brent_30d[-1] - brent_30d[-20]) / brent_30d[-20] * 100

        imoex_ret_20d = (imoex_today / imoex_20d_ago - 1) if imoex_20d_ago > 0 and imoex_today > 0 else 0
        real_macro = {"key_rate_delta": 0.0, "brent_delta_pct": brent_delta, "usd_rub_delta_pct": usd_delta_pct}

        # --- NEWS ---
        news_adj = {}
        critical = False
        critical_tickers = set()
        for art in news_by_date.get(today, []):
            imp, _ = classify_impact(art["title"], art.get("body", ""))
            mentioned = extract_tickers_from_text(art["title"] + " " + art.get("body", ""))
            if imp == NewsImpact.CRITICAL:
                critical = True
                critical_tickers.update(mentioned)
                for t in mentioned: news_adj[t] = news_adj.get(t, 0) - 25
            elif imp == NewsImpact.HIGH:
                for t in mentioned:
                    if any(kw in art["title"].lower() for kw in ["дивиденд", "прибыль", "buyback", "выкуп"]):
                        news_adj[t] = news_adj.get(t, 0) + 15
                    elif any(kw in art["title"].lower() for kw in ["убыт", "штраф", "иск"]):
                        news_adj[t] = news_adj.get(t, 0) - 15

        # News exit (only affected tickers)
        if critical and critical_tickers:
            for tk in list(positions):
                if tk not in critical_tickers: continue
                pos = positions[tk]
                feat = tk_feats.get(tk, {}).get(today) or fut_feats.get(tk, {}).get(today)
                if not feat: continue
                sp = feat["close"] * (1 - SLIPPAGE/100)
                pnl = (sp - pos.entry_price) * pos.shares
                comm = sp * pos.shares * COMMISSION / 100
                cash += pos.shares * sp - comm
                trades.append({"date": today, "ticker": tk, "action": "NEWS-EXIT",
                               "entry": pos.entry_price, "exit": round(sp, 2), "pnl": round(pnl-comm, 2),
                               "pnl_pct": round((pnl-comm)/(pos.entry_price*pos.shares)*100, 2),
                               "days": (datetime.strptime(today,"%Y-%m-%d")-datetime.strptime(pos.entry_date,"%Y-%m-%d")).days})
                del positions[tk]

        # --- STOPS + TRAILING + TIME-STOP ---
        for tk in list(positions):
            pos = positions[tk]
            feat = tk_feats.get(tk, {}).get(today) or fut_feats.get(tk, {}).get(today)
            if not feat: continue
            cl, lo, hi = feat["close"], feat["close"]*0.98, feat["close"]*1.02
            # Try real high/low
            for cs in (stocks.get(tk, []) + futures.get(tk, [])):
                if cs.get("date") == today:
                    lo, hi = float(cs["low"]), float(cs["high"])
                    break

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
            else:
                hold = (datetime.strptime(today,"%Y-%m-%d") - datetime.strptime(pos.entry_date,"%Y-%m-%d")).days
                if hold >= TIME_STOP and (cl - pos.entry_price) / pos.entry_price <= 0.005:
                    action = "TIME-STOP"
                    exit_price = cl

            if action:
                sp = exit_price * (1 - SLIPPAGE/100)
                pnl = (sp - pos.entry_price) * pos.shares
                comm = sp * pos.shares * COMMISSION / 100
                cash += pos.shares * sp - comm
                days = (datetime.strptime(today,"%Y-%m-%d") - datetime.strptime(pos.entry_date,"%Y-%m-%d")).days
                trades.append({"date": today, "ticker": tk, "action": action,
                               "entry": round(pos.entry_price,2), "exit": round(sp,2),
                               "pnl": round(pnl-comm,2), "pnl_pct": round((pnl-comm)/(pos.entry_price*pos.shares)*100,2),
                               "days": days})
                del positions[tk]

        # --- UPDATE KELLY from recent trades ---
        closed = [t for t in trades if t.get("pnl") is not None]
        if len(closed) >= 10:
            wins = [t for t in closed[-30:] if t["pnl"] > 0]
            losses_t = [t for t in closed[-30:] if t["pnl"] <= 0]
            if wins and losses_t:
                wr = len(wins) / len(closed[-30:])
                aw = sum(t["pnl"] for t in wins) / len(wins)
                al = abs(sum(t["pnl"] for t in losses_t) / len(losses_t))
                kelly_fraction = calculate_kelly_fraction(wr, aw, al)
                kelly_fraction = max(0.005, min(kelly_fraction, 0.03))

        # --- FUTURES HEDGE ---
        # If portfolio is long-biased and USDRUB rising → buy Si (USD hedge)
        stock_positions = {tk: p for tk, p in positions.items() if not p.is_futures}
        fut_positions = {tk: p for tk, p in positions.items() if p.is_futures}
        stock_exposure = sum(p.shares * tk_feats.get(p.ticker, {}).get(today, {"close": p.entry_price})["close"]
                            for p in stock_positions.values())

        if stock_exposure > CAPITAL * 0.3 and not fut_positions and usd_delta_pct > 1:
            # Hedge with Si futures
            si_feat = None
            si_ticker = None
            for ftk in ["FUT_SiH6", "FUT_SiM6"]:
                f = fut_feats.get(ftk, {}).get(today)
                if f:
                    si_feat = f
                    si_ticker = ftk
                    break
            if si_feat and si_ticker:
                hedge_capital = CAPITAL * FUTURES_ALLOC * 0.12  # 12% margin
                si_price = si_feat["close"] * (1 + SLIPPAGE/100)
                si_shares = max(1, int(hedge_capital / si_price))
                cost = si_shares * si_price * COMMISSION / 100
                if cost < cash * 0.05:  # only margin cost
                    cash -= cost
                    atr = si_feat["atr_14"]
                    positions[si_ticker] = Pos(si_ticker, si_price, si_shares, today, "fx_futures", atr, is_futures=True)
                    trades.append({"date": today, "ticker": si_ticker, "action": "HEDGE-BUY",
                                   "entry": round(si_price, 2), "exit": None, "pnl": None, "pnl_pct": None, "days": 0})

        # --- STOCK ENTRIES ---
        n_stock = len(stock_positions)
        if n_stock < MAX_POS and not critical:
            tdata = []
            for tk, dfeats in tk_feats.items():
                if tk in positions: continue
                feat = dfeats.get(today)
                if not feat: continue
                ml = 50.0
                if tk in ml_models:
                    mf = prepare_features([{"close": feat["close"], "dt": today}], [feat],
                                          {"key_rate": 18, "usd_rub": usd_today or 100, "brent": brent_today or 80})
                    if mf: ml = ml_models[tk].predict_score(mf[0])

                # Chronos-Bolt neural boost: +15 if bullish forecast, -10 if bearish
                chronos_boost = 0
                cf = chronos_forecasts.get(tk, {}).get(today)
                if cf:
                    if cf.direction == 1 and cf.confidence > 0.3:
                        chronos_boost = 15 * cf.confidence  # up to +15
                    elif cf.direction == -1 and cf.confidence > 0.3:
                        chronos_boost = -10 * cf.confidence  # up to -10

                # TSFRESH feature boost: use as additional confidence signal
                tsfresh_boost = 0
                tsf = tsfresh_features.get(tk, {}).get(today)
                if tsf:
                    # Count positive momentum features
                    positive_features = sum(1 for v in tsf.values() if isinstance(v, (int, float)) and v > 0)
                    total_features = len(tsf) or 1
                    ratio = positive_features / total_features
                    tsfresh_boost = (ratio - 0.5) * 20  # -10 to +10

                ml = max(0, min(100, ml + news_adj.get(tk, 0) + chronos_boost + tsfresh_boost))
                sec = SECTORS.get(tk, "other")
                tdata.append({"ticker": tk, "sector": sec, "close": feat["close"], "ml_score": ml,
                              "rsi": feat["rsi_14"], "returns_1m": feat["returns_1m"], "returns_3m": feat["returns_3m"],
                              "returns_20d": feat["returns_20d"], "imoex_return_20d": imoex_ret_20d,
                              "volume_ratio": feat["volume_ratio_20"], "atr": feat["atr_14"]})

            if tdata:
                ranked = rank_universe(tdata, real_macro)
                sel = select_top_n(ranked, "uptrend" if imoex_above_sma else "range",
                                   {"max_positions": MAX_POS - n_stock, "min_composite_score": MIN_SCORE})
                for s in sel:
                    if s.ticker in positions or cash < 10000: continue
                    ep = s.close * (1 + SLIPPAGE/100)
                    pv = min(cash * min(MAX_POS_PCT, kelly_fraction * 5), cash * 0.90 / max(1, MAX_POS - n_stock))
                    shares = int(pv / ep)
                    if shares <= 0: continue
                    cost = shares * ep * (1 + COMMISSION/100)
                    if cost > cash: continue
                    feat = tk_feats[s.ticker][today]
                    cash -= cost
                    positions[s.ticker] = Pos(s.ticker, ep, shares, today, s.sector, feat["atr_14"])
                    trades.append({"date": today, "ticker": s.ticker, "action": "BUY",
                                   "entry": round(ep, 2), "exit": None, "pnl": None, "pnl_pct": None,
                                   "score": round(s.composite_score, 1), "days": 0})

        # Equity
        pv = sum(p.shares * (tk_feats.get(p.ticker, {}).get(today, fut_feats.get(p.ticker, {}).get(today, {"close": p.entry_price})))["close"]
                 for p in positions.values())
        equity_curve.append(cash + pv)

    # Close remaining
    for tk, pos in list(positions.items()):
        feat = tk_feats.get(tk, {}).get(sim_dates[-1]) or fut_feats.get(tk, {}).get(sim_dates[-1])
        if feat:
            sp = feat["close"] * (1 - SLIPPAGE/100)
            pnl = (sp - pos.entry_price) * pos.shares
            comm = sp * pos.shares * COMMISSION / 100
            cash += pos.shares * sp - comm
            trades.append({"date": sim_dates[-1], "ticker": tk, "action": "CLOSE-EOD",
                           "entry": round(pos.entry_price,2), "exit": round(sp,2),
                           "pnl": round(pnl-comm,2), "pnl_pct": round((pnl-comm)/(pos.entry_price*pos.shares)*100,2), "days": 0})

    # === REPORT ===
    print("\n" + "=" * 70)
    final = equity_curve[-1] if equity_curve else CAPITAL
    ret = (final - CAPITAL) / CAPITAL
    mx = max(equity_curve) if equity_curve else CAPITAL
    dd = max((mx - e) / mx for e in equity_curve) if equity_curve else 0

    print(f"  Initial:    {CAPITAL:>12,.0f}")
    print(f"  Final:      {final:>12,.0f}")
    print(f"  Return:     {ret:>+11.2%}  (~{ret*12*100:.0f}% ann.)")
    print(f"  Chronos:    {'ON (' + str(len(chronos_forecasts)) + ' tickers)' if chronos_forecasts else 'OFF'}")
    print(f"  TSFRESH:    {'ON (' + str(len(tsfresh_features)) + ' tickers)' if tsfresh_features else 'OFF'}")
    print(f"  Max DD:     {dd:>11.2%}")
    print(f"  Kelly:      {kelly_fraction*100:>10.2f}%")

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

    # Futures trades
    fut_trades = [t for t in cl if t["ticker"].startswith("FUT_")]
    if fut_trades:
        fp = sum(t["pnl"] for t in fut_trades)
        print(f"  Futures PnL: {fp:>+10,.0f} ({len(fut_trades)} trades)")

    if len(equity_curve) > 5:
        rets = [(equity_curve[i]-equity_curve[i-1])/equity_curve[i-1] for i in range(1, len(equity_curve)) if equity_curve[i-1] > 0]
        if rets:
            v, cv = calculate_historical_var(rets)
            print(f"\n  VaR(95%):   {v*100:.2f}%  CVaR: {cv*100:.2f}%")

    print("\n  TOP-5 WINS:")
    for t in sorted(w, key=lambda x: x["pnl"], reverse=True)[:5]:
        print(f"    {t['date']} {t['ticker']:10s} {t['action']:14s} {t['pnl']:>+8,.0f} ({t['pnl_pct']:>+.1f}%) {t['days']}d")
    print("\n  TOP-5 LOSSES:")
    for t in sorted(l, key=lambda x: x["pnl"])[:5]:
        print(f"    {t['date']} {t['ticker']:10s} {t['action']:14s} {t['pnl']:>+8,.0f} ({t['pnl_pct']:>+.1f}%) {t['days']}d")

    print("\n  DAILY:")
    prev = CAPITAL
    for i, dt in enumerate(sim_dates):
        eq = equity_curve[i] if i < len(equity_curve) else prev
        d = eq - prev
        bar = "+" * min(20, int(abs(d)/2000)) if d > 0 else "-" * min(20, int(abs(d)/2000))
        print(f"    {dt}  {eq:>11,.0f}  {d:>+8,.0f}  {bar}")
        prev = eq

    print("=" * 70)
    try:
        from src.backtest.report import generate_html_report
        p = generate_html_report(equity_curve, output_path="data/simulation_v3_neural.html", title="MOEX V3.1 Neural (Chronos + TSFRESH)")
        if p: print(f"  Report: {p}")
    except Exception as e: print(f"  Report error: {e}")
    Path("data/simulation_v3_neural.json").write_text(json.dumps({"return": round(ret*100,2), "trades": len(cl), "pf": round(pf,2), "trade_log": trades}, indent=2, ensure_ascii=False))
    print(f"  JSON: data/simulation_v3_neural.json")


if __name__ == "__main__":
    main()
