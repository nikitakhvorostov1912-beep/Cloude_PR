"""Backtest 4 strategij na realnyh dannyh MOEX.

Strategii:
  A) Trend Following (LONG)
  B) Mean Reversion LONG
  C) Mean Reversion SHORT
  D) Buy & Hold (benchmark)

Zapusk:
  ./venv/Scripts/python.exe -m scripts.strategy_audit_backtest
"""
from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands

import structlog

structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# -------------------------------------------------------------------------
# Konstanty
# -------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trading.db"
TICKERS = ["SBER", "GAZP", "LKOH", "NVTK", "ROSN", "GMKN", "VTBR", "MGNT", "MTSS"]
INITIAL_CAPITAL = 1_000_000.0
CAPITAL_PER_TICKER = INITIAL_CAPITAL / len(TICKERS)  # ~111 111
COMMISSION_PCT = 0.05 / 100  # 0.05% na storonu
SLIPPAGE_PCT = 0.02 / 100   # 0.02% na storonu
RISK_FREE_RATE = 0.19        # CB RF 19%
TRADING_DAYS_YEAR = 250


# -------------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------------

def load_candles(ticker: str) -> pd.DataFrame:
    """Zagruzka svechej iz SQLite v pandas DataFrame."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM candles "
        "WHERE ticker = ? AND date >= '2021-01-01' ORDER BY date",
        conn,
        params=(ticker,),
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


# -------------------------------------------------------------------------
# Indicators
# -------------------------------------------------------------------------

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Dobavit tehnicheskie indikatory dlja vseh strategij."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # EMA
    df["ema_50"] = EMAIndicator(close=close, window=50, fillna=False).ema_indicator()
    df["ema_200"] = EMAIndicator(close=close, window=200, fillna=False).ema_indicator()

    # RSI(14) i RSI(2)
    df["rsi_14"] = RSIIndicator(close=close, window=14, fillna=False).rsi()
    df["rsi_2"] = RSIIndicator(close=close, window=2, fillna=False).rsi()

    # ADX(14)
    adx_ind = ADXIndicator(high=high, low=low, close=close, window=14, fillna=False)
    df["adx"] = adx_ind.adx()

    # MACD histogram
    macd_ind = MACD(close=close, fillna=False)
    df["macd_hist"] = macd_ind.macd_diff()

    # Bollinger Bands (20, 2)
    bb = BollingerBands(close=close, window=20, window_dev=2.0, fillna=False)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    # ATR(14) dlja trailing stop
    df["atr_14"] = AverageTrueRange(
        high=high, low=low, close=close, window=14, fillna=False
    ).average_true_range()

    return df


# -------------------------------------------------------------------------
# Trade model
# -------------------------------------------------------------------------

@dataclass
class Trade:
    ticker: str
    direction: str  # "LONG" or "SHORT"
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    shares: int = 0


# -------------------------------------------------------------------------
# Strategy A: Trend Following (LONG only)
# -------------------------------------------------------------------------

def run_strategy_a(df: pd.DataFrame, ticker: str, capital: float) -> list[Trade]:
    """Trend Following LONG."""
    trades: list[Trade] = []
    in_position = False
    current_trade: Optional[Trade] = None
    trailing_stop = 0.0
    entry_bar_idx = 0

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if pd.isna(row["ema_200"]) or pd.isna(row["adx"]) or pd.isna(row["macd_hist"]):
            continue

        if not in_position:
            # Vhod: RSI(14) < 40 AND Close > EMA(200) AND ADX > 20 AND MACD hist > 0
            if (
                prev["rsi_14"] < 40
                and prev["close"] > prev["ema_200"]
                and prev["adx"] > 20
                and prev["macd_hist"] > 0
            ):
                entry_price = row["open"] * (1 + SLIPPAGE_PCT)
                shares = int(capital / entry_price)
                if shares <= 0:
                    continue
                cost = shares * entry_price * (1 + COMMISSION_PCT)
                if cost > capital:
                    shares = int(capital / (entry_price * (1 + COMMISSION_PCT)))
                if shares <= 0:
                    continue

                current_trade = Trade(
                    ticker=ticker,
                    direction="LONG",
                    entry_date=df.index[i],
                    entry_price=entry_price,
                    shares=shares,
                )
                in_position = True
                trailing_stop = entry_price - row["atr_14"] * 2.5 if not pd.isna(row["atr_14"]) else entry_price * 0.95
                entry_bar_idx = i

        else:
            assert current_trade is not None
            # Update trailing stop
            new_stop = row["close"] - row["atr_14"] * 2.5 if not pd.isna(row["atr_14"]) else trailing_stop
            if new_stop > trailing_stop:
                trailing_stop = new_stop

            days_held = (df.index[i] - current_trade.entry_date).days

            # Vyhod: RSI > 70 OR Close < EMA(50) OR trailing stop OR time stop 30 dnej
            exit_signal = False
            if prev["rsi_14"] > 70:
                exit_signal = True
            elif not pd.isna(prev["ema_50"]) and prev["close"] < prev["ema_50"]:
                exit_signal = True
            elif row["low"] <= trailing_stop:
                exit_signal = True
            elif days_held >= 30:
                exit_signal = True

            if exit_signal:
                exit_price = row["open"] * (1 - SLIPPAGE_PCT)
                # Esli trailing stop srabotal vnutri bara
                if row["low"] <= trailing_stop and trailing_stop < row["open"]:
                    exit_price = trailing_stop * (1 - SLIPPAGE_PCT)

                gross_pnl = (exit_price - current_trade.entry_price) * current_trade.shares
                commission = (
                    current_trade.entry_price * current_trade.shares * COMMISSION_PCT
                    + exit_price * current_trade.shares * COMMISSION_PCT
                )
                current_trade.exit_date = df.index[i]
                current_trade.exit_price = exit_price
                current_trade.pnl = gross_pnl - commission
                trades.append(current_trade)
                in_position = False
                current_trade = None

    # Zakryt otkrytuju poziciju v konce
    if in_position and current_trade is not None:
        exit_price = df.iloc[-1]["close"] * (1 - SLIPPAGE_PCT)
        gross_pnl = (exit_price - current_trade.entry_price) * current_trade.shares
        commission = (
            current_trade.entry_price * current_trade.shares * COMMISSION_PCT
            + exit_price * current_trade.shares * COMMISSION_PCT
        )
        current_trade.exit_date = df.index[-1]
        current_trade.exit_price = exit_price
        current_trade.pnl = gross_pnl - commission
        trades.append(current_trade)

    return trades


# -------------------------------------------------------------------------
# Strategy B: Mean Reversion LONG
# -------------------------------------------------------------------------

def run_strategy_b(df: pd.DataFrame, ticker: str, capital: float) -> list[Trade]:
    """Mean Reversion LONG: RSI(2)<10, Close>EMA(200), Close<BB_lower, ADX<25."""
    trades: list[Trade] = []
    in_position = False
    current_trade: Optional[Trade] = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if pd.isna(prev["ema_200"]) or pd.isna(prev["rsi_2"]) or pd.isna(prev["bb_lower"]) or pd.isna(prev["adx"]):
            continue

        if not in_position:
            if (
                prev["rsi_2"] < 10
                and prev["close"] > prev["ema_200"]
                and prev["close"] < prev["bb_lower"]
                and prev["adx"] < 25
            ):
                entry_price = row["open"] * (1 + SLIPPAGE_PCT)
                shares = int(capital / entry_price)
                if shares <= 0:
                    continue
                cost = shares * entry_price * (1 + COMMISSION_PCT)
                if cost > capital:
                    shares = int(capital / (entry_price * (1 + COMMISSION_PCT)))
                if shares <= 0:
                    continue

                current_trade = Trade(
                    ticker=ticker,
                    direction="LONG",
                    entry_date=df.index[i],
                    entry_price=entry_price,
                    shares=shares,
                )
                in_position = True
        else:
            assert current_trade is not None
            days_held = (df.index[i] - current_trade.entry_date).days

            exit_signal = False
            if prev["rsi_2"] > 70:
                exit_signal = True
            elif days_held >= 5:
                exit_signal = True

            if exit_signal:
                exit_price = row["open"] * (1 - SLIPPAGE_PCT)
                gross_pnl = (exit_price - current_trade.entry_price) * current_trade.shares
                commission = (
                    current_trade.entry_price * current_trade.shares * COMMISSION_PCT
                    + exit_price * current_trade.shares * COMMISSION_PCT
                )
                current_trade.exit_date = df.index[i]
                current_trade.exit_price = exit_price
                current_trade.pnl = gross_pnl - commission
                trades.append(current_trade)
                in_position = False
                current_trade = None

    if in_position and current_trade is not None:
        exit_price = df.iloc[-1]["close"] * (1 - SLIPPAGE_PCT)
        gross_pnl = (exit_price - current_trade.entry_price) * current_trade.shares
        commission = (
            current_trade.entry_price * current_trade.shares * COMMISSION_PCT
            + exit_price * current_trade.shares * COMMISSION_PCT
        )
        current_trade.exit_date = df.index[-1]
        current_trade.exit_price = exit_price
        current_trade.pnl = gross_pnl - commission
        trades.append(current_trade)

    return trades


# -------------------------------------------------------------------------
# Strategy C: Mean Reversion SHORT
# -------------------------------------------------------------------------

def run_strategy_c(df: pd.DataFrame, ticker: str, capital: float) -> list[Trade]:
    """Mean Reversion SHORT: RSI(2)>90, Close<EMA(200), Close>BB_upper, ADX<25."""
    trades: list[Trade] = []
    in_position = False
    current_trade: Optional[Trade] = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if pd.isna(prev["ema_200"]) or pd.isna(prev["rsi_2"]) or pd.isna(prev["bb_upper"]) or pd.isna(prev["adx"]):
            continue

        if not in_position:
            if (
                prev["rsi_2"] > 90
                and prev["close"] < prev["ema_200"]
                and prev["close"] > prev["bb_upper"]
                and prev["adx"] < 25
            ):
                entry_price = row["open"] * (1 - SLIPPAGE_PCT)  # short: prodaem
                shares = int(capital / entry_price)
                if shares <= 0:
                    continue
                cost = shares * entry_price * (1 + COMMISSION_PCT)
                if cost > capital:
                    shares = int(capital / (entry_price * (1 + COMMISSION_PCT)))
                if shares <= 0:
                    continue

                current_trade = Trade(
                    ticker=ticker,
                    direction="SHORT",
                    entry_date=df.index[i],
                    entry_price=entry_price,
                    shares=shares,
                )
                in_position = True
        else:
            assert current_trade is not None
            days_held = (df.index[i] - current_trade.entry_date).days

            exit_signal = False
            if prev["rsi_2"] < 30:
                exit_signal = True
            elif days_held >= 5:
                exit_signal = True

            if exit_signal:
                exit_price = row["open"] * (1 + SLIPPAGE_PCT)  # short: pokupaem
                gross_pnl = (current_trade.entry_price - exit_price) * current_trade.shares
                commission = (
                    current_trade.entry_price * current_trade.shares * COMMISSION_PCT
                    + exit_price * current_trade.shares * COMMISSION_PCT
                )
                current_trade.exit_date = df.index[i]
                current_trade.exit_price = exit_price
                current_trade.pnl = gross_pnl - commission
                trades.append(current_trade)
                in_position = False
                current_trade = None

    if in_position and current_trade is not None:
        exit_price = df.iloc[-1]["close"] * (1 + SLIPPAGE_PCT)
        gross_pnl = (current_trade.entry_price - exit_price) * current_trade.shares
        commission = (
            current_trade.entry_price * current_trade.shares * COMMISSION_PCT
            + exit_price * current_trade.shares * COMMISSION_PCT
        )
        current_trade.exit_date = df.index[-1]
        current_trade.exit_price = exit_price
        current_trade.pnl = gross_pnl - commission
        trades.append(current_trade)

    return trades


# -------------------------------------------------------------------------
# Strategy D: Buy & Hold
# -------------------------------------------------------------------------

def run_strategy_d(df: pd.DataFrame, ticker: str, capital: float) -> list[Trade]:
    """Buy & Hold: kupil v pervyj den, derzhi do konca."""
    entry_price = df.iloc[0]["open"] * (1 + SLIPPAGE_PCT)
    shares = int(capital / entry_price)
    if shares <= 0:
        return []
    exit_price = df.iloc[-1]["close"] * (1 - SLIPPAGE_PCT)
    gross_pnl = (exit_price - entry_price) * shares
    commission = (
        entry_price * shares * COMMISSION_PCT
        + exit_price * shares * COMMISSION_PCT
    )
    trade = Trade(
        ticker=ticker,
        direction="LONG",
        entry_date=df.index[0],
        entry_price=entry_price,
        exit_date=df.index[-1],
        exit_price=exit_price,
        pnl=gross_pnl - commission,
        shares=shares,
    )
    return [trade]


# -------------------------------------------------------------------------
# Metrics
# -------------------------------------------------------------------------

@dataclass
class Metrics:
    ticker: str
    strategy: str
    return_pct: float = 0.0
    sharpe: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0
    avg_pnl: float = 0.0
    avg_duration_days: float = 0.0
    total_pnl: float = 0.0


def _build_daily_equity(
    sorted_trades: list[Trade],
    capital: float,
    df: pd.DataFrame,
) -> pd.Series:
    """Postroit dnevnuju krivuju equity s uchetom otkrytyh pozicij."""
    dates = df.index
    equity = pd.Series(capital, index=dates, dtype=float)

    realized = 0.0
    for t in sorted_trades:
        # Na den vyhoda dobavlaem PnL
        if t.exit_date is not None and t.exit_date in equity.index:
            realized += t.pnl
            equity.loc[t.exit_date:] = capital + realized

    return equity


def compute_metrics(
    trades: list[Trade],
    ticker: str,
    strategy_name: str,
    capital: float,
    df: pd.DataFrame,
) -> Metrics:
    """Vychislit metriki dlja spiska sdelok."""
    m = Metrics(ticker=ticker, strategy=strategy_name)

    if not trades:
        return m

    m.num_trades = len(trades)
    total_pnl = sum(t.pnl for t in trades)
    m.total_pnl = total_pnl
    m.return_pct = (total_pnl / capital) * 100
    m.avg_pnl = total_pnl / len(trades)

    # Win rate
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    m.win_rate_pct = (len(wins) / len(trades)) * 100 if trades else 0

    # Profit factor
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    m.profit_factor = gross_profit / gross_loss if gross_loss > 0 else (99.99 if gross_profit > 0 else 0.0)

    # Avg duration
    durations = []
    for t in trades:
        if t.exit_date and t.entry_date:
            durations.append((t.exit_date - t.entry_date).days)
    m.avg_duration_days = np.mean(durations) if durations else 0

    # Sortiruju sdelki po entry_date
    sorted_trades = sorted(trades, key=lambda t: t.entry_date)

    # MaxDD cherez dnevnuju equity krivuju
    daily_eq = _build_daily_equity(sorted_trades, capital, df)
    eq_arr = daily_eq.values
    peak_arr = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - peak_arr) / np.where(peak_arr > 0, peak_arr, 1) * 100
    m.max_drawdown_pct = float(np.min(drawdowns))

    # Sharpe: annualizirovannyj cherez dnevnye equity returns
    if len(trades) >= 1 and len(trades) != 1:
        # Stroju dnevnuju krivuju equity
        daily_eq = _build_daily_equity(sorted_trades, capital, df)
        daily_ret = daily_eq.pct_change().dropna()
        if len(daily_ret) > 10 and daily_ret.std() > 1e-10:
            ann_ret = daily_ret.mean() * TRADING_DAYS_YEAR
            ann_std = daily_ret.std() * np.sqrt(TRADING_DAYS_YEAR)
            m.sharpe = (ann_ret - RISK_FREE_RATE) / ann_std
        else:
            m.sharpe = 0.0
    else:
        # 1 sdelka (Buy & Hold) -- ispolzuem dnevnye returny
        daily_prices = df["close"].values
        daily_returns = np.diff(daily_prices) / daily_prices[:-1]
        avg_daily = np.mean(daily_returns)
        std_daily = np.std(daily_returns, ddof=1)
        if std_daily > 0:
            ann_return = avg_daily * TRADING_DAYS_YEAR
            ann_std = std_daily * np.sqrt(TRADING_DAYS_YEAR)
            m.sharpe = (ann_return - RISK_FREE_RATE) / ann_std
        else:
            m.sharpe = 0.0

        # MaxDD dlja Buy & Hold -- po dnevnym cenam
        equity_bh = capital
        shares = trades[0].shares
        entry_p = trades[0].entry_price
        eq_arr = []
        for p in daily_prices:
            eq_arr.append(capital + (p - entry_p) * shares)
        eq_arr = np.array(eq_arr)
        peak_arr2 = np.maximum.accumulate(eq_arr)
        dd2 = (eq_arr - peak_arr2) / peak_arr2 * 100
        m.max_drawdown_pct = float(np.min(dd2))

    return m


# -------------------------------------------------------------------------
# Otchet
# -------------------------------------------------------------------------

def print_strategy_table(strategy_name: str, metrics_list: list[Metrics]) -> None:
    """Pechat tablicy po odnoj strategii."""
    print(f"\n{'=' * 80}")
    print(f"  {strategy_name}")
    print(f"{'=' * 80}")
    header = f"| {'Ticker':<6} | {'Return,%':>9} | {'Sharpe':>7} | {'MaxDD,%':>8} | {'Win,%':>6} | {'PF':>6} | {'Trades':>6} | {'Avg PnL':>10} | {'AvgDays':>7} |"
    separator = f"|{'-' * 8}|{'-' * 11}|{'-' * 9}|{'-' * 10}|{'-' * 8}|{'-' * 8}|{'-' * 8}|{'-' * 12}|{'-' * 9}|"
    print(header)
    print(separator)
    for m in metrics_list:
        sign = "+" if m.return_pct >= 0 else ""
        print(
            f"| {m.ticker:<6} | {sign}{m.return_pct:>7.1f}% | {m.sharpe:>7.2f} | {m.max_drawdown_pct:>7.1f}% | {m.win_rate_pct:>5.0f}% | {m.profit_factor:>6.2f} | {m.num_trades:>6} | {m.avg_pnl:>10.0f} | {m.avg_duration_days:>7.1f} |"
        )
    # Itog po portfolju
    total_pnl = sum(m.total_pnl for m in metrics_list)
    total_capital = CAPITAL_PER_TICKER * len(metrics_list)
    total_return = (total_pnl / total_capital) * 100
    total_trades = sum(m.num_trades for m in metrics_list)
    # Srednevzveshennyj Sharpe
    sharpes = [m.sharpe for m in metrics_list if m.num_trades > 0]
    avg_sharpe = np.mean(sharpes) if sharpes else 0.0
    # Worst MaxDD
    worst_dd = min(m.max_drawdown_pct for m in metrics_list) if metrics_list else 0.0
    print(separator)
    sign = "+" if total_return >= 0 else ""
    print(
        f"| {'TOTAL':<6} | {sign}{total_return:>7.1f}% | {avg_sharpe:>7.2f} | {worst_dd:>7.1f}% | {'':>5} | {'':>6} | {total_trades:>6} | {'':>10} | {'':>7} |"
    )


def print_summary_table(
    all_results: dict[str, list[Metrics]],
) -> None:
    """Itogovaja tablica sravnenija strategij."""
    print(f"\n{'=' * 80}")
    print("  ITOGO PO PORTFELJU")
    print(f"{'=' * 80}")
    header = f"| {'Strategy':<25} | {'Return,%':>9} | {'Sharpe':>7} | {'MaxDD,%':>8} | {'Trades':>6} |"
    separator = f"|{'-' * 27}|{'-' * 11}|{'-' * 9}|{'-' * 10}|{'-' * 8}|"
    print(header)
    print(separator)

    combo_pnl = 0.0
    combo_trades = 0
    combo_sharpes = []
    combo_dds = []

    for sname, mlist in all_results.items():
        total_pnl = sum(m.total_pnl for m in mlist)
        total_capital = CAPITAL_PER_TICKER * len(mlist)
        total_return = (total_pnl / total_capital) * 100
        total_trades = sum(m.num_trades for m in mlist)
        sharpes = [m.sharpe for m in mlist if m.num_trades > 0]
        avg_sharpe = np.mean(sharpes) if sharpes else 0.0
        worst_dd = min(m.max_drawdown_pct for m in mlist) if mlist else 0.0
        sign = "+" if total_return >= 0 else ""
        print(
            f"| {sname:<25} | {sign}{total_return:>7.1f}% | {avg_sharpe:>7.2f} | {worst_dd:>7.1f}% | {total_trades:>6} |"
        )
        if sname != "D: Buy & Hold":
            combo_pnl += total_pnl
            combo_trades += total_trades
            combo_sharpes.extend(sharpes)
            combo_dds.append(worst_dd)

    # Kombinacija A+B+C
    combo_capital = INITIAL_CAPITAL * 3
    combo_return = (combo_pnl / combo_capital) * 100 if combo_capital > 0 else 0
    combo_sharpe = np.mean(combo_sharpes) if combo_sharpes else 0
    combo_dd = min(combo_dds) if combo_dds else 0
    sign = "+" if combo_return >= 0 else ""
    print(separator)
    print(
        f"| {'A+B+C Combined':<25} | {sign}{combo_return:>7.1f}% | {combo_sharpe:>7.2f} | {combo_dd:>7.1f}% | {combo_trades:>6} |"
    )


def find_best_worst(all_results: dict[str, list[Metrics]]) -> None:
    """Luchshij i hudshij tikery/strategii."""
    print(f"\n{'=' * 80}")
    print("  LUCHSHIE I HUDSHIE")
    print(f"{'=' * 80}")

    # Luchshij/hudshij ticker (po A+B+C summa)
    ticker_pnl: dict[str, float] = {}
    for sname, mlist in all_results.items():
        if sname == "D: Buy & Hold":
            continue
        for m in mlist:
            ticker_pnl[m.ticker] = ticker_pnl.get(m.ticker, 0.0) + m.total_pnl

    if ticker_pnl:
        best_ticker = max(ticker_pnl, key=ticker_pnl.get)  # type: ignore
        worst_ticker = min(ticker_pnl, key=ticker_pnl.get)  # type: ignore
        print(f"  Luchshij ticker (A+B+C):  {best_ticker}  ({ticker_pnl[best_ticker]:+,.0f} rub)")
        print(f"  Hudshij ticker (A+B+C):   {worst_ticker}  ({ticker_pnl[worst_ticker]:+,.0f} rub)")

    # Luchshaja strategija (po return%)
    strat_returns = {}
    for sname, mlist in all_results.items():
        total_pnl = sum(m.total_pnl for m in mlist)
        total_capital = CAPITAL_PER_TICKER * len(mlist)
        strat_returns[sname] = (total_pnl / total_capital) * 100

    best_strat = max(strat_returns, key=strat_returns.get)  # type: ignore
    worst_strat = min(strat_returns, key=strat_returns.get)  # type: ignore
    print(f"  Luchshaja strategija:     {best_strat}  ({strat_returns[best_strat]:+.1f}%)")
    print(f"  Hudshaja strategija:      {worst_strat}  ({strat_returns[worst_strat]:+.1f}%)")

    # Luchshaja kombinacija ticker+strategija
    best_combo = None
    best_combo_ret = -999.0
    worst_combo = None
    worst_combo_ret = 999.0
    for sname, mlist in all_results.items():
        for m in mlist:
            if m.return_pct > best_combo_ret:
                best_combo_ret = m.return_pct
                best_combo = f"{m.ticker} / {sname}"
            if m.return_pct < worst_combo_ret:
                worst_combo_ret = m.return_pct
                worst_combo = f"{m.ticker} / {sname}"

    if best_combo:
        print(f"  Luchshaja kombinacija:    {best_combo}  ({best_combo_ret:+.1f}%)")
    if worst_combo:
        print(f"  Hudshaja kombinacija:     {worst_combo}  ({worst_combo_ret:+.1f}%)")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main() -> None:
    log.info("strategy_audit_backtest", db=str(DB_PATH), tickers=TICKERS)
    if not DB_PATH.exists():
        log.error("DB not found", path=str(DB_PATH))
        sys.exit(1)

    strategies = {
        "A: Trend Following LONG": run_strategy_a,
        "B: Mean Reversion LONG": run_strategy_b,
        "C: Mean Reversion SHORT": run_strategy_c,
        "D: Buy & Hold": run_strategy_d,
    }

    all_results: dict[str, list[Metrics]] = {}

    for sname, sfunc in strategies.items():
        log.info("running_strategy", strategy=sname)
        metrics_list: list[Metrics] = []

        for ticker in TICKERS:
            df = load_candles(ticker)
            if df.empty:
                log.warning("no_data", ticker=ticker)
                metrics_list.append(Metrics(ticker=ticker, strategy=sname))
                continue

            df = add_indicators(df)
            trades = sfunc(df, ticker, CAPITAL_PER_TICKER)
            m = compute_metrics(trades, ticker, sname, CAPITAL_PER_TICKER, df)
            metrics_list.append(m)
            log.info(
                "ticker_done",
                strategy=sname,
                ticker=ticker,
                trades=m.num_trades,
                return_pct=round(m.return_pct, 1),
            )

        all_results[sname] = metrics_list
        print_strategy_table(sname, metrics_list)

    print_summary_table(all_results)
    find_best_worst(all_results)
    print()


if __name__ == "__main__":
    main()
