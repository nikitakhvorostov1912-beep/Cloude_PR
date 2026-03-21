"""Strategy hyperparameter optimizer using Optuna with walk-forward validation.

Adapted from jesse-ai/jesse optimize_mode (MIT License) with:
- No Ray/Redis dependency — uses joblib for parallelism
- Pluggable backtest_fn callback instead of jesse internals
- 7 objective functions: sharpe, calmar, sortino, omega, serenity, smart_sharpe, smart_sortino
- Walk-forward rolling window support
- MOEX-specific defaults (252 trading days, CBR key rate)

Original: https://github.com/jesse-ai/jesse/blob/master/jesse/modes/optimize_mode/
License: MIT (c) 2020 Jesse.Trade
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Sequence

import numpy as np
import optuna

logger = logging.getLogger(__name__)

# Suppress Optuna's excessive logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ObjectiveFunction = Literal[
    "sharpe", "calmar", "sortino", "omega",
    "serenity", "smart_sharpe", "smart_sortino",
]

BacktestResult = dict[str, Any]
"""Dict returned by backtest_fn, must contain keys used by the chosen objective
(e.g. 'sharpe_ratio', 'total_trades', 'net_profit_pct', 'win_rate')."""

BacktestFn = Callable[[dict[str, Any]], BacktestResult]
"""Signature: backtest_fn(hyperparameters) -> metrics dict."""


# ---------------------------------------------------------------------------
# Hyperparameter spec
# ---------------------------------------------------------------------------

@dataclass
class HyperParam:
    """Single hyperparameter definition for optimization."""
    name: str
    type: Literal["int", "float", "categorical"] = "int"
    min: float | int = 0
    max: float | int = 100
    step: float | int | None = None
    options: list[Any] | None = None  # for categorical
    default: float | int | Any = None


# ---------------------------------------------------------------------------
# Fitness scoring (adapted from jesse fitness.py)
# ---------------------------------------------------------------------------

_OBJECTIVE_CONFIG: dict[str, tuple[str, float, float]] = {
    # objective_name: (metric_key, normalize_min, normalize_max)
    "sharpe":        ("sharpe_ratio",   -0.5, 5.0),
    "calmar":        ("calmar_ratio",   -0.5, 30.0),
    "sortino":       ("sortino_ratio",  -0.5, 15.0),
    "omega":         ("omega_ratio",    -0.5, 5.0),
    "serenity":      ("serenity_index", -0.5, 15.0),
    "smart_sharpe":  ("smart_sharpe",   -0.5, 5.0),
    "smart_sortino": ("smart_sortino",  -0.5, 15.0),
}


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to [0, 1] range, clipping at boundaries."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def calculate_fitness(
    metrics: BacktestResult,
    objective: ObjectiveFunction = "sharpe",
    optimal_total: int = 100,
    min_trades: int = 5,
) -> float:
    """Calculate fitness score from backtest metrics.

    Formula: score = total_effect_rate * ratio_normalized
    - total_effect_rate = min(log10(trades) / log10(optimal_total), 1)
    - ratio_normalized = normalize(metric_value, min, max)

    This rewards both sufficient number of trades AND good risk-adjusted returns.

    Args:
        metrics: Dict with keys like 'sharpe_ratio', 'total_trades', etc.
        objective: Which metric to optimize.
        optimal_total: Target trade count for full score.
        min_trades: Minimum trades required (below → score = 0).

    Returns:
        Fitness score in [0, 1]. Returns 0.0001 for invalid configs.
    """
    total_trades = metrics.get("total_trades", 0)
    if total_trades < min_trades:
        return 0.0001

    if objective not in _OBJECTIVE_CONFIG:
        raise ValueError(
            f"Unknown objective '{objective}'. "
            f"Choose from: {', '.join(_OBJECTIVE_CONFIG)}"
        )

    metric_key, norm_min, norm_max = _OBJECTIVE_CONFIG[objective]
    ratio = metrics.get(metric_key, 0.0)

    if ratio is None or (isinstance(ratio, float) and math.isnan(ratio)):
        return 0.0001

    if ratio < 0:
        return 0.0001

    total_effect = min(
        math.log10(max(total_trades, 1)) / math.log10(max(optimal_total, 2)),
        1.0,
    )
    ratio_norm = _normalize(ratio, norm_min, norm_max)
    score = total_effect * ratio_norm

    if math.isnan(score):
        return 0.0001

    return score


# ---------------------------------------------------------------------------
# Trial result
# ---------------------------------------------------------------------------

@dataclass
class TrialResult:
    """Result of a single optimization trial."""
    trial_number: int
    params: dict[str, Any]
    fitness: float
    training_metrics: BacktestResult
    testing_metrics: BacktestResult | None = None


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

@dataclass
class OptimizerConfig:
    """Configuration for strategy optimizer."""
    hyperparameters: list[HyperParam]
    objective: ObjectiveFunction = "sharpe"
    n_trials: int | None = None  # None → auto (200 * n_params)
    optimal_total: int = 100
    min_trades: int = 5
    n_jobs: int = 1  # parallel jobs (1 = sequential)
    study_name: str = "moex_optimizer"
    storage: str | None = None  # e.g. "sqlite:///optuna.db" for persistence


class StrategyOptimizer:
    """Optuna-based strategy hyperparameter optimizer.

    Usage:
        optimizer = StrategyOptimizer(
            config=OptimizerConfig(
                hyperparameters=[
                    HyperParam(name="rsi_period", type="int", min=5, max=50),
                    HyperParam(name="threshold", type="float", min=0.1, max=0.9, step=0.1),
                ],
                objective="sharpe",
                n_trials=200,
            ),
            train_backtest_fn=lambda hp: run_backtest(hp, train_data),
            test_backtest_fn=lambda hp: run_backtest(hp, test_data),
        )
        results = optimizer.run()
    """

    def __init__(
        self,
        config: OptimizerConfig,
        train_backtest_fn: BacktestFn,
        test_backtest_fn: BacktestFn | None = None,
    ) -> None:
        self.config = config
        self.train_backtest_fn = train_backtest_fn
        self.test_backtest_fn = test_backtest_fn

        n = config.n_trials or (200 * len(config.hyperparameters))
        self.n_trials = n

        self.study = optuna.create_study(
            direction="maximize",
            study_name=config.study_name,
            storage=config.storage,
            load_if_exists=True,
        )
        self.best_trials: list[TrialResult] = []

    def _suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:
        """Use Optuna's suggest API to sample hyperparameters."""
        params: dict[str, Any] = {}
        for hp in self.config.hyperparameters:
            if hp.type == "int":
                params[hp.name] = trial.suggest_int(
                    hp.name, int(hp.min), int(hp.max),
                    step=int(hp.step) if hp.step else 1,
                )
            elif hp.type == "float":
                if hp.step:
                    params[hp.name] = trial.suggest_float(
                        hp.name, float(hp.min), float(hp.max), step=float(hp.step),
                    )
                else:
                    params[hp.name] = trial.suggest_float(
                        hp.name, float(hp.min), float(hp.max),
                    )
            elif hp.type == "categorical":
                params[hp.name] = trial.suggest_categorical(
                    hp.name, hp.options or [],
                )
        return params

    def _objective(self, trial: optuna.Trial) -> float:
        """Optuna objective function — runs train backtest, scores fitness."""
        params = self._suggest_params(trial)

        try:
            train_metrics = self.train_backtest_fn(params)
        except Exception as e:
            logger.warning("Trial %d backtest failed: %s", trial.number, e)
            return 0.0001

        fitness = calculate_fitness(
            train_metrics,
            objective=self.config.objective,
            optimal_total=self.config.optimal_total,
            min_trades=self.config.min_trades,
        )

        # Run out-of-sample test if available and training passed
        test_metrics: BacktestResult | None = None
        if self.test_backtest_fn and fitness > 0.001:
            try:
                test_metrics = self.test_backtest_fn(params)
            except Exception as e:
                logger.warning("Trial %d test backtest failed: %s", trial.number, e)

        # Store metrics in trial user attrs for later retrieval
        trial.set_user_attr("training_metrics", train_metrics)
        if test_metrics:
            trial.set_user_attr("testing_metrics", test_metrics)
        trial.set_user_attr("params", params)

        # Track best trials
        result = TrialResult(
            trial_number=trial.number,
            params=params,
            fitness=round(fitness, 6),
            training_metrics=train_metrics,
            testing_metrics=test_metrics,
        )

        if fitness > 0.001:
            self.best_trials.append(result)
            self.best_trials.sort(key=lambda r: r.fitness, reverse=True)
            self.best_trials = self.best_trials[:20]

        metric_key = _OBJECTIVE_CONFIG[self.config.objective][0]
        ratio_val = train_metrics.get(metric_key, "N/A")
        total = train_metrics.get("total_trades", 0)
        logger.info(
            "Trial %d: fitness=%.4f, %s=%.3f, trades=%d",
            trial.number, fitness,
            self.config.objective, ratio_val if isinstance(ratio_val, (int, float)) else 0,
            total,
        )

        return fitness

    def run(self) -> list[TrialResult]:
        """Run the optimization and return best trials sorted by fitness.

        Returns:
            List of TrialResult sorted descending by fitness (top 20).
        """
        logger.info(
            "Starting optimization: %d trials, objective=%s, %d params",
            self.n_trials, self.config.objective,
            len(self.config.hyperparameters),
        )

        self.study.optimize(
            self._objective,
            n_trials=self.n_trials,
            n_jobs=self.config.n_jobs,
            show_progress_bar=True,
        )

        logger.info(
            "Optimization complete. Best fitness: %.4f",
            self.study.best_value if self.study.best_trial else 0,
        )

        return self.best_trials

    @property
    def best_params(self) -> dict[str, Any]:
        """Best hyperparameters found."""
        if self.best_trials:
            return self.best_trials[0].params
        try:
            return self.study.best_params
        except ValueError:
            return {}

    @property
    def best_fitness(self) -> float:
        """Best fitness score achieved."""
        if self.best_trials:
            return self.best_trials[0].fitness
        try:
            return self.study.best_value
        except ValueError:
            return 0.0


# ---------------------------------------------------------------------------
# Walk-forward optimizer
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardWindow:
    """A single train/test window for walk-forward analysis."""
    window_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    best_params: dict[str, Any] = field(default_factory=dict)
    train_fitness: float = 0.0
    train_metrics: BacktestResult = field(default_factory=dict)
    test_metrics: BacktestResult = field(default_factory=dict)


def walk_forward_optimize(
    hyperparameters: list[HyperParam],
    windows: list[tuple[str, str, str, str]],
    backtest_factory: Callable[[str, str, dict[str, Any]], BacktestResult],
    objective: ObjectiveFunction = "sharpe",
    n_trials_per_window: int = 100,
    optimal_total: int = 50,
    min_trades: int = 3,
) -> list[WalkForwardWindow]:
    """Run walk-forward optimization across multiple time windows.

    Args:
        hyperparameters: List of HyperParam definitions.
        windows: List of (train_start, train_end, test_start, test_end) date strings.
        backtest_factory: Callable(start, end, hyperparams) -> metrics dict.
        objective: Fitness objective function name.
        n_trials_per_window: Optuna trials per window.
        optimal_total: Target trade count for fitness scoring.
        min_trades: Minimum trades for valid trial.

    Returns:
        List of WalkForwardWindow with best params and metrics per window.
    """
    results: list[WalkForwardWindow] = []

    for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
        logger.info(
            "Walk-forward window %d/%d: train=%s..%s, test=%s..%s",
            i + 1, len(windows), train_start, train_end, test_start, test_end,
        )

        config = OptimizerConfig(
            hyperparameters=hyperparameters,
            objective=objective,
            n_trials=n_trials_per_window,
            optimal_total=optimal_total,
            min_trades=min_trades,
            study_name=f"wf_window_{i}",
        )

        optimizer = StrategyOptimizer(
            config=config,
            train_backtest_fn=lambda hp, s=train_start, e=train_end: backtest_factory(s, e, hp),
            test_backtest_fn=lambda hp, s=test_start, e=test_end: backtest_factory(s, e, hp),
        )

        trials = optimizer.run()

        window = WalkForwardWindow(
            window_index=i,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )

        if trials:
            best = trials[0]
            window.best_params = best.params
            window.train_fitness = best.fitness
            window.train_metrics = best.training_metrics
            window.test_metrics = best.testing_metrics or {}

        results.append(window)

    return results
