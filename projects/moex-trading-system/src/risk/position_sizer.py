"""Position sizing calculations — Risk Gateway helper."""
from __future__ import annotations

import math
import random


SHORT_DISCOUNT = 0.6


def calculate_drawdown_multiplier(current_drawdown: float) -> float:
    """
    Returns position size multiplier based on current portfolio drawdown.

    < 10%  : 1.0 (normal trading)
    10-15% : 0.5 (yellow zone — half size)
    15-20% : 0.25 (orange zone — quarter size)
    >= 20% : 0.0 (red zone — no new positions)
    """
    if current_drawdown < 0.10:
        return 1.0
    if current_drawdown < 0.15:
        return 0.5
    if current_drawdown < 0.20:
        return 0.25
    return 0.0


def calculate_consecutive_multiplier(consecutive_losses: int) -> float:
    """
    Returns position size multiplier based on consecutive loss streak.

    < 3  : 1.0 (normal)
    3-4  : 0.5 (reduced)
    >= 5 : 0.0 (no new positions)
    """
    if consecutive_losses < 3:
        return 1.0
    if consecutive_losses < 5:
        return 0.5
    return 0.0


def calculate_position_size(
    equity: float,
    entry_price: float,
    stop_loss_price: float,
    lot_size: int,
    risk_per_trade: float = 0.015,
    max_position_pct: float = 0.15,
    max_adv_pct: float = 0.05,
    adv: float | None = None,
    direction: str = "long",
    drawdown_mult: float = 1.0,
    consecutive_mult: float = 1.0,
) -> tuple[int, float, float]:
    """
    Calculate position size using fixed-fractional risk method.

    Args:
        equity: Current portfolio equity.
        entry_price: Planned entry price.
        stop_loss_price: Stop-loss price.
        lot_size: Number of shares per lot (MOEX standard lot).
        risk_per_trade: Fraction of equity to risk per trade (default 1.5%).
        max_position_pct: Maximum position as fraction of equity (default 15%).
        max_adv_pct: Maximum fraction of average daily volume (default 5%).
        adv: Average daily volume in shares; None means no ADV constraint.
        direction: "long" or "short".
        drawdown_mult: Multiplier from calculate_drawdown_multiplier().
        consecutive_mult: Multiplier from calculate_consecutive_multiplier().

    Returns:
        (lots, position_value, actual_risk_pct)
    """
    stop_distance = abs(entry_price - stop_loss_price)
    if stop_distance <= 0:
        return 0, 0.0, 0.0
    if equity <= 0 or entry_price <= 0 or lot_size <= 0:
        return 0, 0.0, 0.0

    effective_risk = risk_per_trade * drawdown_mult * consecutive_mult
    if effective_risk <= 0:
        return 0, 0.0, 0.0

    risk_amount = equity * effective_risk
    shares_by_risk = risk_amount / stop_distance
    position_value = shares_by_risk * entry_price

    # Cap by maximum position percentage
    max_by_pct = equity * max_position_pct
    position_value = min(position_value, max_by_pct)

    # Cap by ADV constraint
    if adv is not None and adv > 0:
        max_by_adv = adv * max_adv_pct * entry_price
        position_value = min(position_value, max_by_adv)

    # Apply short discount — shorts require more margin, reduce size
    if direction == "short":
        position_value *= SHORT_DISCOUNT

    # Convert to whole lots
    value_per_lot = entry_price * lot_size
    if value_per_lot <= 0:
        return 0, 0.0, 0.0
    lots = math.floor(position_value / value_per_lot)
    if lots <= 0:
        return 0, 0.0, 0.0

    actual_position_value = lots * value_per_lot
    actual_risk_shares = lots * lot_size * stop_distance
    actual_risk_pct = actual_risk_shares / equity if equity > 0 else 0.0

    return lots, actual_position_value, actual_risk_pct


def calculate_volatility_adjusted_size(
    equity: float,
    entry_price: float,
    atr: float,
    lot_size: int,
    target_risk_pct: float = 0.01,
    atr_multiplier: float = 2.5,
    max_position_pct: float = 0.15,
    direction: str = "long",
    drawdown_mult: float = 1.0,
) -> tuple[int, float, float]:
    """
    ATR-based position sizing.

    Вместо фиксированного % от цены, размер позиции основан на волатильности:
    - Волатильная бумага (большой ATR) → маленькая позиция
    - Спокойная бумага (малый ATR) → большая позиция
    - Каждая позиция несёт ОДИНАКОВЫЙ риск в рублях

    Формула:
    risk_amount = equity * target_risk_pct * drawdown_mult
    stop_distance = atr * atr_multiplier
    shares = risk_amount / stop_distance
    lots = floor(shares / lot_size)

    Для short: shares *= 0.6 (SHORT_DISCOUNT)

    Args:
        equity: Текущий капитал портфеля.
        entry_price: Планируемая цена входа.
        atr: Average True Range (14-дневный или другой период).
        lot_size: Количество акций в одном лоте (стандарт MOEX).
        target_risk_pct: Доля капитала под риском на сделку (по умолчанию 1%).
        atr_multiplier: Множитель ATR для расчёта стоп-дистанции (по умолчанию 2.5).
        max_position_pct: Максимальная доля капитала в одной позиции (по умолчанию 15%).
        direction: "long" или "short".
        drawdown_mult: Множитель из calculate_drawdown_multiplier().

    Returns:
        (lots, position_value_rub, actual_risk_pct)
    """
    if atr <= 0 or entry_price <= 0 or equity <= 0 or lot_size <= 0:
        return 0, 0.0, 0.0

    effective_risk = target_risk_pct * drawdown_mult
    if effective_risk <= 0:
        return 0, 0.0, 0.0

    risk_amount = equity * effective_risk
    stop_distance = atr * atr_multiplier
    shares = risk_amount / stop_distance

    # Применить SHORT_DISCOUNT для шортов
    if direction == "short":
        shares *= SHORT_DISCOUNT

    position_value = shares * entry_price

    # Ограничить долей капитала
    max_by_pct = equity * max_position_pct
    position_value = min(position_value, max_by_pct)

    # Перевести в целые лоты
    value_per_lot = entry_price * lot_size
    if value_per_lot <= 0:
        return 0, 0.0, 0.0

    lots = math.floor(position_value / value_per_lot)
    if lots <= 0:
        return 0, 0.0, 0.0

    actual_position_value = lots * value_per_lot
    actual_risk_rub = lots * lot_size * stop_distance
    actual_risk_pct = actual_risk_rub / equity if equity > 0 else 0.0

    return lots, actual_position_value, actual_risk_pct


def calculate_kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.5,
) -> float:
    """Calculate fractional Kelly Criterion for position sizing.

    Kelly formula: f* = p - q/b
    where p = win_rate, q = 1-p, b = avg_win/avg_loss (win/loss ratio)

    Uses fractional Kelly (default 0.5 = Half Kelly) to reduce volatility.
    Industry standard: Half Kelly or Quarter Kelly.

    Parameters
    ----------
    win_rate: Fraction of winning trades (0.0 to 1.0)
    avg_win: Average profit of winning trades (positive)
    avg_loss: Average loss of losing trades (positive, absolute value)
    fraction: Kelly fraction (0.5 = Half Kelly, 0.25 = Quarter Kelly)

    Returns
    -------
    float: Optimal fraction of equity to risk (0.0 to max 0.05)
    """
    if win_rate <= 0 or win_rate >= 1 or avg_win <= 0 or avg_loss <= 0:
        return 0.0

    b = avg_win / avg_loss  # win/loss ratio
    q = 1.0 - win_rate

    kelly = win_rate - q / b

    if kelly <= 0:
        return 0.0

    # Apply fraction and cap at 5% max
    return min(kelly * fraction, 0.05)


def calculate_historical_var(
    returns: list[float],
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate Historical VaR and CVaR (Expected Shortfall).

    VaR: maximum expected loss at given confidence level.
    CVaR: average loss beyond VaR (tail risk measure).

    Parameters
    ----------
    returns: List of daily returns (e.g. [-0.02, 0.01, -0.005, ...])
    confidence: Confidence level (0.95 = 95%)

    Returns
    -------
    tuple[float, float]: (var, cvar) as positive numbers representing loss
    """
    if len(returns) < 10:
        return 0.0, 0.0

    sorted_returns = sorted(returns)
    cutoff_index = int(len(sorted_returns) * (1 - confidence))
    cutoff_index = max(cutoff_index, 1)

    var = abs(sorted_returns[cutoff_index])

    # CVaR = average of returns below VaR
    tail = sorted_returns[:cutoff_index]
    cvar = abs(sum(tail) / len(tail)) if tail else var

    return var, cvar


def calculate_monte_carlo_var(
    returns: list[float],
    confidence: float = 0.95,
    simulations: int = 10000,
    horizon_days: int = 1,
) -> tuple[float, float]:
    """Monte Carlo VaR simulation.

    Generates random portfolio paths assuming normal distribution
    of returns, then calculates VaR/CVaR from simulated outcomes.

    Parameters
    ----------
    returns: Historical daily returns
    confidence: Confidence level
    simulations: Number of Monte Carlo simulations
    horizon_days: Risk horizon in days

    Returns
    -------
    tuple[float, float]: (var, cvar)
    """
    if len(returns) < 20:
        return 0.0, 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_return = math.sqrt(variance)

    # Simulate paths
    simulated_returns = []
    for _ in range(simulations):
        cumulative = 0.0
        for _ in range(horizon_days):
            daily = random.gauss(mean_return, std_return)
            cumulative += daily
        simulated_returns.append(cumulative)

    simulated_returns.sort()
    cutoff_index = max(int(simulations * (1 - confidence)), 1)

    var = abs(simulated_returns[cutoff_index])
    tail = simulated_returns[:cutoff_index]
    cvar = abs(sum(tail) / len(tail)) if tail else var

    return var, cvar
