"""Prometheus metrics for MOEX Trading System.

Exposes key trading metrics via prometheus_client for Grafana dashboards.

Usage:
    from src.monitoring.metrics import METRICS, start_metrics_server

    # Update metrics during trading
    METRICS.equity.set(1_200_000)
    METRICS.drawdown.set(0.052)
    METRICS.daily_pnl.set(28_340)

    # Start HTTP server for Prometheus scraping
    start_metrics_server(port=8080)
"""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


class TradingMetrics:
    """Container for all Prometheus metrics."""

    def __init__(self) -> None:
        if not _HAS_PROMETHEUS:
            self._dummy = True
            return
        self._dummy = False

        # Portfolio
        self.equity = Gauge(
            "portfolio_equity_rub",
            "Total portfolio equity in roubles",
        )
        self.drawdown = Gauge(
            "portfolio_drawdown_pct",
            "Current portfolio drawdown as fraction (0.0 to 1.0)",
        )
        self.daily_pnl = Gauge(
            "portfolio_daily_pnl_rub",
            "Daily P&L in roubles",
        )
        self.exposure = Gauge(
            "portfolio_exposure_pct",
            "Portfolio exposure as fraction of equity",
        )

        # Risk
        self.circuit_breaker_state = Gauge(
            "risk_circuit_breaker_state",
            "Circuit breaker state (0=ON, 1=YELLOW, 2=RED)",
        )
        self.risk_checks_total = Counter(
            "risk_checks_total",
            "Total signals validated by Risk Gateway",
            ["decision"],  # approve, reject, reduce
        )
        self.var_95 = Gauge(
            "risk_var_95_pct",
            "Value at Risk (95%) as fraction",
        )

        # Trading
        self.signals_total = Counter(
            "trading_signals_total",
            "Total trading signals generated",
            ["action"],  # buy, sell, hold, reduce
        )
        self.trades_total = Counter(
            "trading_trades_total",
            "Total trades executed",
            ["direction"],  # long, short
        )
        self.order_latency = Histogram(
            "trading_order_latency_seconds",
            "Order submission to fill latency",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )
        self.slippage_bps = Histogram(
            "trading_slippage_bps",
            "Execution slippage in basis points",
            buckets=[1, 2, 5, 10, 20, 50],
        )

        # ML
        self.ml_score = Gauge(
            "ml_ensemble_score",
            "Latest ML ensemble prediction score (0-100)",
            ["ticker"],
        )
        self.pre_score = Gauge(
            "analysis_pre_score",
            "Latest pre-score (0-100)",
            ["ticker"],
        )

        # Macro
        self.key_rate = Gauge("macro_key_rate_pct", "CBR key rate percent")
        self.usd_rub = Gauge("macro_usd_rub", "USD/RUB exchange rate")
        self.brent = Gauge("macro_brent_usd", "Brent crude oil price USD")

    def record_signal(self, action: str) -> None:
        """Record a signal generation event."""
        if self._dummy:
            return
        self.signals_total.labels(action=action).inc()

    def record_risk_decision(self, decision: str) -> None:
        """Record a Risk Gateway decision."""
        if self._dummy:
            return
        self.risk_checks_total.labels(decision=decision).inc()

    def record_trade(self, direction: str) -> None:
        """Record a trade execution."""
        if self._dummy:
            return
        self.trades_total.labels(direction=direction).inc()

    def update_portfolio(
        self,
        equity: float,
        drawdown: float,
        daily_pnl: float,
        exposure: float,
    ) -> None:
        """Update portfolio metrics."""
        if self._dummy:
            return
        self.equity.set(equity)
        self.drawdown.set(drawdown)
        self.daily_pnl.set(daily_pnl)
        self.exposure.set(exposure)

    def update_macro(
        self,
        key_rate: float | None = None,
        usd_rub: float | None = None,
        brent: float | None = None,
    ) -> None:
        """Update macro indicator metrics."""
        if self._dummy:
            return
        if key_rate is not None:
            self.key_rate.set(key_rate)
        if usd_rub is not None:
            self.usd_rub.set(usd_rub)
        if brent is not None:
            self.brent.set(brent)


# Singleton instance
METRICS = TradingMetrics()


def start_metrics_server(port: int = 8080) -> None:
    """Start Prometheus HTTP metrics server.

    Call once at application startup. Prometheus scrapes /metrics endpoint.
    """
    if not _HAS_PROMETHEUS:
        logger.warning("prometheus_client not installed, metrics server disabled")
        return

    try:
        start_http_server(port)
        logger.info("prometheus_metrics_server_started", port=port)
    except OSError as e:
        logger.error("prometheus_server_error", port=port, error=str(e))
