"""Daily Pipeline Runner — главный оркестратор торговой системы MOEX + Claude.

Архитектура:
    MOEX ISS → Data Layer → Analysis → Claude Advisory
                                            ↓
                            Risk Gateway → Execution → Monitoring

Режимы запуска:
    python -m src.main --once      # однократный цикл (тест)
    python -m src.main             # production-режим с APScheduler
"""
from __future__ import annotations

import asyncio
import json
import math
import signal
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import os

import polars as pl
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Добавляем корень проекта в PYTHONPATH при прямом запуске
sys.path.insert(0, str(Path(__file__).parent.parent))

# Загрузка .env
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Fix Windows cp1251 encoding for structlog output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from src.analysis.features import calculate_all_features  # noqa: E402
from src.analysis.regime import detect_regime  # noqa: E402
from src.analysis.scoring import calculate_pre_score  # noqa: E402
from src.ml.ensemble import MLEnsemble  # noqa: E402
from src.ml.features import prepare_features  # noqa: E402
from src.analysis.sentiment import aggregate_daily_sentiment, analyze_sentiment  # noqa: E402
from src.config import get_settings, load_strategy_config, load_tickers_config  # noqa: E402
from src.data.db import (  # noqa: E402
    get_latest_candles,
    init_db,
    save_candles,
    save_macro,
    save_news,
    save_signal,
)
from src.data.macro_fetcher import fetch_all_macro  # noqa: E402
from src.data.moex_client import fetch_candles, fetch_index  # noqa: E402
from src.data.news_parser import fetch_news  # noqa: E402
from src.execution.executor import PaperExecutor  # noqa: E402
from src.execution.tinkoff_adapter import TinkoffExecutor  # noqa: E402
from src.models.market import MarketRegime  # noqa: E402
from src.models.order import Order, OrderType  # noqa: E402
from src.models.signal import Action, TradingSignal  # noqa: E402
from src.monitoring.telegram_bot import TelegramNotifier  # noqa: E402
from src.monitoring.trade_journal import log_signal_decision, log_trade  # noqa: E402
from src.risk.circuit_breaker import CircuitBreaker, CircuitState  # noqa: E402
from src.risk.manager import RiskDecision, validate_signal  # noqa: E402
from src.risk.position_sizer import (  # noqa: E402
    calculate_consecutive_multiplier,
    calculate_drawdown_multiplier,
    calculate_position_size,
)
from src.strategy.claude_engine import get_trading_signal  # noqa: E402
from src.strategy.dividend_gap import find_dividend_gap_signals  # noqa: E402
from src.strategy.futures_si import generate_si_signals  # noqa: E402
from src.strategy.pairs_trading import generate_pairs_signals  # noqa: E402
from src.strategy.prompts import build_market_context  # noqa: E402
from src.strategy.signal_filter import apply_entry_filters, check_exit_conditions  # noqa: E402

logger = structlog.get_logger(__name__)

# ─── Минимальный Pre-Score для вызова Claude ─────────────────────────────────
_MIN_PRE_SCORE_FOR_CLAUDE = 45.0


# ─────────────────────────────────────────────────────────────────────────────
# Настройка логирования
# ─────────────────────────────────────────────────────────────────────────────


def configure_logging(log_level: str) -> None:
    """Настроить структурированное логирование через structlog."""
    import logging

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TradingPipeline — главный оркестратор
# ─────────────────────────────────────────────────────────────────────────────


class TradingPipeline:
    """Главный оркестратор торговой системы MOEX + Claude.

    Реализует полный дневной цикл:
        1. Загрузка данных
        2. Анализ и расчёт индикаторов
        3. Генерация сигналов через Claude
        4. Risk Gateway + исполнение
        5. Мониторинг (trailing stops, exit conditions)
        6. Дневной отчёт
    """

    def __init__(self, config_path: str = "config/strategies/conservative.yaml") -> None:
        self._settings = get_settings()
        self._strategy_cfg = self._load_strategy(config_path)
        self._tickers_cfg = load_tickers_config()
        self._watchlist: list[dict[str, Any]] = self._tickers_cfg.get("watchlist", [])
        self._ticker_symbols: list[str] = [t["ticker"] for t in self._watchlist]
        self._lot_map: dict[str, int] = {t["ticker"]: t.get("lot_size", 1) for t in self._watchlist}

        self._db_path = str(self._settings.db_path_resolved)
        self._executor = self._init_executor()
        self._circuit_breaker = CircuitBreaker()
        self._telegram = self._init_telegram()

        # Текущий pre-score кеш (обновляется в step_analyze)
        self._pre_scores: dict[str, float] = {}
        # Текущие features кеш (обновляется в step_analyze)
        self._features_cache: dict[str, dict[str, Any]] = {}
        # Текущий режим рынка
        self._market_regime: MarketRegime = MarketRegime.WEAK_TREND
        # Текущий sentiment по тикерам
        self._ticker_sentiment: dict[str, float] = {}
        # ML Ensemble (trained lazily in step_analyze)
        self._ml_ensembles: dict[str, Any] = {}
        self._ml_scores: dict[str, float] = {}
        # Macro cache (updated in step_load_data)
        self._macro_cache: dict[str, float] = {}

        logger.info(
            "pipeline.init",
            strategy=self._strategy_cfg.get("name", "unknown"),
            tickers=len(self._ticker_symbols),
            mode=self._settings.trading_mode,
        )

    # ─── Вспомогательные инициализаторы ──────────────────────────────────────

    def _load_strategy(self, config_path: str) -> dict[str, Any]:
        """Загрузить конфиг стратегии из YAML, fallback — conservative."""
        try:
            return load_strategy_config(
                Path(config_path).stem
            )
        except FileNotFoundError:
            logger.warning("strategy_config_not_found", path=config_path)
            return {
                "name": "conservative",
                "pre_score_threshold": _MIN_PRE_SCORE_FOR_CLAUDE,
                "confidence_threshold": 0.6,
                "atr_multiplier": 2.5,
                "risk_per_trade": 0.015,
                "max_position_pct": 0.15,
                "time_stop_days": 30,
            }

    def _init_telegram(self) -> TelegramNotifier | None:
        """Создать TelegramNotifier если токен задан в .env."""
        token = self._settings.telegram_bot_token
        chat_id = self._settings.telegram_chat_id
        if token and chat_id:
            logger.info("telegram.enabled", chat_id=chat_id)
            return TelegramNotifier(bot_token=token, chat_id=chat_id)
        logger.info("telegram.disabled", reason="no token/chat_id configured")
        return None

    def _init_executor(self) -> "PaperExecutor | TinkoffExecutor":
        """Создать executor в зависимости от режима торговли.

        Режимы (TRADING_MODE в .env):
        - ``paper``   → PaperExecutor (in-memory, без реальных денег)
        - ``sandbox`` → TinkoffExecutor(mode="sandbox") — виртуальный счёт Tinkoff
        - ``live``    → TinkoffExecutor(mode="live") — РЕАЛЬНЫЙ счёт (ОСТОРОЖНО!)

        Для sandbox/live требуется TINKOFF_TOKEN в .env.
        Инициализация account_id (setup()) выполняется отдельно перед первым циклом.
        """
        mode = self._settings.trading_mode

        if mode == "sandbox":
            token = self._settings.tinkoff_token
            if not token:
                logger.warning(
                    "executor.sandbox.no_token",
                    hint="TINKOFF_TOKEN не задан — fallback на PaperExecutor",
                )
                return PaperExecutor(initial_capital=1_000_000.0)
            executor = TinkoffExecutor(token=token, mode="sandbox")
            # Предустанавливаем account_id если задан в .env (после setup_sandbox.py)
            account_id = self._settings.tinkoff_account_id
            if account_id:
                executor._account_id = account_id
                logger.info("executor.sandbox.init", mode="sandbox", account_id=account_id)
            else:
                logger.info(
                    "executor.sandbox.init_no_account",
                    mode="sandbox",
                    hint="Запустите scripts/setup_sandbox.py для получения account_id",
                )
            return executor

        elif mode == "live":
            token = self._settings.tinkoff_token
            if not token:
                logger.error(
                    "executor.live.no_token",
                    hint="TINKOFF_TOKEN обязателен для live-режима",
                )
                raise RuntimeError(
                    "TINKOFF_TOKEN не задан — нельзя запустить live-торговлю."
                )
            executor = TinkoffExecutor(token=token, mode="live")
            account_id = self._settings.tinkoff_account_id
            if account_id:
                executor._account_id = account_id
            logger.warning(
                "executor.live.init",
                mode="live",
                account_id=account_id or "будет получен при setup()",
                warning="РЕАЛЬНЫЙ ТОРГОВЫЙ СЧЁТ — все ордера исполняются реально!",
            )
            return executor

        else:
            # paper mode (default)
            logger.info("executor.paper.init", mode="paper")
            return PaperExecutor(initial_capital=1_000_000.0)

    # ─── Шаг 1: Загрузка данных ──────────────────────────────────────────────

    async def step_load_data(self) -> dict[str, Any]:
        """Загрузить свежие данные: MOEX свечи, новости, макро.

        Returns:
            Словарь с ключами: bars_loaded, news_count, macro.
        """
        logger.info("step.load_data.start")
        result: dict[str, Any] = {
            "bars_loaded": 0,
            "news_count": 0,
            "macro": {},
        }

        today = date.today()
        # Загружаем последние 5 торговых дней для обновления закрытий
        from_date = today - timedelta(days=7)

        # --- Свечи по всем тикерам + индекс IMOEX ---
        all_tickers = self._ticker_symbols + ["IMOEX"]
        bars_total = 0

        for ticker in all_tickers:
            try:
                if ticker == "IMOEX":
                    bars = await fetch_index(from_date=from_date, to_date=today)
                else:
                    bars = await fetch_candles(ticker=ticker, from_date=from_date, to_date=today)

                if bars:
                    saved = await save_candles(self._db_path, bars)
                    bars_total += saved
                    logger.debug("data.candles_saved", ticker=ticker, count=saved)
                else:
                    logger.debug("data.no_new_candles", ticker=ticker)
            except Exception as exc:
                # Ошибка одного тикера не останавливает pipeline
                logger.warning("data.candles_error", ticker=ticker, error=str(exc))

        result["bars_loaded"] = bars_total
        logger.info("step.load_data.candles_done", total=bars_total)

        # --- Новости за 48 часов ---
        try:
            articles = await fetch_news(hours_back=48, known_tickers=self._ticker_symbols)
            if articles:
                saved_news = await save_news(self._db_path, articles)
                result["news_count"] = saved_news
                result["raw_articles"] = articles
                logger.info("step.load_data.news_done", count=saved_news)
        except Exception as exc:
            logger.warning("data.news_error", error=str(exc))
            result["raw_articles"] = []

        # --- Макроданные ---
        try:
            macro = await fetch_all_macro()
            result["macro"] = macro
            self._macro_cache = macro
            # Сохраняем в БД
            for indicator, value in macro.items():
                try:
                    await save_macro(self._db_path, indicator, today, value, source="cbr_moex")
                except Exception:
                    pass
            logger.info("step.load_data.macro_done", indicators=list(macro.keys()))
        except Exception as exc:
            logger.warning("data.macro_error", error=str(exc))

        logger.info("step.load_data.done", **{k: v for k, v in result.items() if k != "raw_articles"})
        return result

    # ─── Шаг 2: Анализ ───────────────────────────────────────────────────────

    async def step_analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Рассчитать индикаторы, режим рынка, pre-scores, sentiment.

        Returns:
            Словарь с ключами: regime, pre_scores, features, sentiment.
        """
        logger.info("step.analyze.start")
        result: dict[str, Any] = {
            "regime": MarketRegime.WEAK_TREND,
            "pre_scores": {},
            "features": {},
            "sentiment": {},
        }

        # --- Определяем режим рынка (IMOEX) ---
        try:
            imoex_bars = await get_latest_candles(self._db_path, "IMOEX", count=250)
            if imoex_bars:
                imoex_df = self._bars_to_df(imoex_bars)
                imoex_df = calculate_all_features(imoex_df)
                last = imoex_df.row(-1, named=True)

                last_close = float(last["close"])
                last_atr = float(last.get("atr_14") or 0)
                last_adx = float(last.get("adx") or 0)
                atr_pct = last_atr / last_close if last_close > 0 else 0.0

                regime = detect_regime(
                    index_close=imoex_df["close"],
                    index_adx=last_adx,
                    index_atr_pct=atr_pct,
                    current_drawdown=0.0,
                )
                self._market_regime = regime
                result["regime"] = regime
                logger.info("step.analyze.regime", regime=regime.value, adx=round(last_adx, 2))
            else:
                logger.warning("step.analyze.no_imoex_data")
        except Exception as exc:
            logger.warning("step.analyze.regime_error", error=str(exc))

        # --- Анализ sentiment ---
        try:
            raw_articles: list[dict[str, Any]] = data.get("raw_articles", [])
            if raw_articles:
                # Подготавливаем для sentiment: добавляем id, ticker
                articles_for_sentiment: list[dict[str, Any]] = []
                for i, art in enumerate(raw_articles[:100]):  # Лимит 100 статей
                    articles_for_sentiment.append({
                        "id": i,
                        "title": art.get("title", ""),
                        "body": art.get("summary", ""),
                        "ticker": ", ".join(art.get("tickers", [])),
                        "published_at": art.get("published"),
                    })

                sentiment_results = await analyze_sentiment(articles_for_sentiment)

                # Добавляем published_at для time-decay
                for i, sr in enumerate(sentiment_results):
                    if i < len(articles_for_sentiment):
                        sr["published_at"] = articles_for_sentiment[i].get("published_at")

                # Считаем sentiment per ticker
                for ticker in self._ticker_symbols:
                    ticker_scores = [
                        sr for j, sr in enumerate(sentiment_results)
                        if j < len(raw_articles) and ticker in raw_articles[j].get("tickers", [])
                    ]
                    agg = aggregate_daily_sentiment(ticker_scores if ticker_scores else sentiment_results)
                    self._ticker_sentiment[ticker] = agg

                result["sentiment"] = dict(self._ticker_sentiment)
                logger.info("step.analyze.sentiment_done", tickers=len(self._ticker_sentiment))
        except Exception as exc:
            logger.warning("step.analyze.sentiment_error", error=str(exc))

        # --- Индикаторы и pre-scores для каждого тикера ---
        macro = data.get("macro", {})
        for ticker in self._ticker_symbols:
            try:
                bars = await get_latest_candles(self._db_path, ticker, count=250)
                if len(bars) < 30:
                    logger.debug("step.analyze.insufficient_bars", ticker=ticker, count=len(bars))
                    continue

                df = self._bars_to_df(bars)
                df = calculate_all_features(df)
                last = df.row(-1, named=True)

                # Определяем OBV тренд (последние 5 баров)
                obv_trend = self._calc_obv_trend(df)

                # Собираем features dict
                features: dict[str, Any] = {
                    "close": float(last["close"]),
                    "ema_20": self._safe_float(last.get("ema_20")),
                    "ema_50": self._safe_float(last.get("ema_50")),
                    "ema_200": self._safe_float(last.get("ema_200")),
                    "rsi_14": self._safe_float(last.get("rsi_14")),
                    "macd": self._safe_float(last.get("macd")),
                    "macd_signal": self._safe_float(last.get("macd_signal")),
                    "macd_histogram": self._safe_float(last.get("macd_histogram")),
                    "adx": self._safe_float(last.get("adx")),
                    "di_plus": self._safe_float(last.get("di_plus")),
                    "di_minus": self._safe_float(last.get("di_minus")),
                    "bb_upper": self._safe_float(last.get("bb_upper")),
                    "bb_middle": self._safe_float(last.get("bb_middle")),
                    "bb_lower": self._safe_float(last.get("bb_lower")),
                    "bb_pct_b": self._safe_float(last.get("bb_pct_b")),
                    "atr_14": self._safe_float(last.get("atr_14")),
                    "stoch_k": self._safe_float(last.get("stoch_k")),
                    "stoch_d": self._safe_float(last.get("stoch_d")),
                    "obv": self._safe_float(last.get("obv")),
                    "obv_trend": obv_trend,
                    "volume_ratio_20": self._safe_float(last.get("volume_ratio_20")),
                    "sentiment": self._ticker_sentiment.get(ticker, 0.0),
                }

                self._features_cache[ticker] = features

                # Рассчитываем pre-score (long направление по умолчанию)
                close = float(features["close"]) or 1.0
                ema20 = float(features["ema_20"] or close)
                ema50 = float(features["ema_50"] or close)
                ema200 = float(features["ema_200"] or close)

                # ML score (lazy-train on first call, then predict)
                ticker_ml_score: float | None = None
                try:
                    if ticker not in self._ml_ensembles:
                        self._ml_ensembles[ticker] = MLEnsemble()
                    ensemble = self._ml_ensembles[ticker]
                    if not ensemble.is_trained:
                        # Train on available history (features list from polars df)
                        candle_dicts = [{"close": float(features["close"]), "dt": ""}]
                        ta_dicts = [features]
                        ensemble.train(candle_dicts * 100, ta_dicts * 100,
                                       macro=self._macro_cache, sentiment=0.0)
                    if ensemble.is_trained:
                        ml_features = prepare_features(
                            [{"close": close, "dt": ""}], [features],
                            macro=self._macro_cache,
                        )
                        if ml_features:
                            ticker_ml_score = ensemble.predict_score(ml_features[0])
                            self._ml_scores[ticker] = ticker_ml_score
                except Exception as ml_exc:
                    logger.debug("ml_score_error", ticker=ticker, error=str(ml_exc))

                pre_score, breakdown = calculate_pre_score(
                    adx=float(features["adx"] or 0),
                    di_plus=float(features["di_plus"] or 0),
                    di_minus=float(features["di_minus"] or 0),
                    rsi=float(features["rsi_14"] or 50),
                    macd_hist=float(features["macd_histogram"] or 0),
                    close=close,
                    ema20=ema20,
                    ema50=ema50,
                    ema200=ema200,
                    volume_ratio=float(features["volume_ratio_20"] or 1.0),
                    obv_trend=obv_trend,
                    sentiment_score=float(features["sentiment"]),
                    direction="long",
                    ml_score=ticker_ml_score,
                )
                self._pre_scores[ticker] = pre_score
                result["pre_scores"][ticker] = pre_score
                result["features"][ticker] = features

                logger.debug(
                    "step.analyze.ticker",
                    ticker=ticker,
                    pre_score=round(pre_score, 1),
                    rsi=round(float(features["rsi_14"] or 50), 1),
                    adx=round(float(features["adx"] or 0), 1),
                )
            except Exception as exc:
                logger.warning("step.analyze.ticker_error", ticker=ticker, error=str(exc))

        scored_count = sum(1 for s in result["pre_scores"].values() if s >= _MIN_PRE_SCORE_FOR_CLAUDE)
        logger.info(
            "step.analyze.done",
            tickers_analyzed=len(result["pre_scores"]),
            above_threshold=scored_count,
            regime=result["regime"].value,
        )
        return result

    # ─── Шаг 3: Генерация сигналов ────────────────────────────────────────────

    async def step_generate_signals(self, analysis: dict[str, Any]) -> list[TradingSignal]:
        """Вызвать Claude для топ-кандидатов и применить entry/exit фильтры.

        Returns:
            Список отфильтрованных TradingSignal.
        """
        logger.info("step.generate_signals.start")
        pre_scores: dict[str, float] = analysis.get("pre_scores", {})
        features: dict[str, dict[str, Any]] = analysis.get("features", {})
        regime: MarketRegime = analysis.get("regime", MarketRegime.WEAK_TREND)
        macro = {}  # macro получили в step_load_data, берём из features_cache или передаём отдельно

        # Фильтруем тикеры: только Pre-Score >= 45
        threshold = float(self._strategy_cfg.get("pre_score_threshold", _MIN_PRE_SCORE_FOR_CLAUDE))
        candidates = [
            (ticker, score)
            for ticker, score in pre_scores.items()
            if score >= threshold
        ]
        # Сортируем по убыванию score
        candidates.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "step.generate_signals.candidates",
            total=len(candidates),
            threshold=threshold,
        )

        if not candidates:
            logger.info("step.generate_signals.no_candidates")
            return []

        # Получаем portfolio для контекста
        portfolio_snapshot = await self._executor.get_portfolio()
        portfolio_ctx: dict[str, Any] = {
            "equity": portfolio_snapshot.equity,
            "cash_pct": (portfolio_snapshot.cash / portfolio_snapshot.equity * 100)
            if portfolio_snapshot.equity > 0
            else 100.0,
            "drawdown_pct": portfolio_snapshot.drawdown * 100,
            "open_positions": list(portfolio_snapshot.positions.keys()),
        }

        signals: list[TradingSignal] = []

        for ticker, pre_score in candidates:
            ticker_features = features.get(ticker, self._features_cache.get(ticker, {}))
            sentiment_score = self._ticker_sentiment.get(ticker, 0.0)

            try:
                # Строим контекст для Claude
                market_context = build_market_context(
                    ticker=ticker,
                    regime=regime,
                    features=ticker_features,
                    sentiment=sentiment_score,
                    portfolio=portfolio_ctx,
                    macro={
                        "key_rate_pct": macro.get("key_rate"),
                        "usd_rub": macro.get("usd_rub"),
                        "oil_brent": macro.get("brent"),
                    },
                )

                # Вызываем Claude
                signal = await get_trading_signal(
                    ticker=ticker,
                    market_context=market_context,
                )

                # Устанавливаем pre_score в сигнал
                signal = signal.with_pre_score(pre_score)

                # Применяем entry filters
                filtered = apply_entry_filters(
                    signal=signal,
                    features=ticker_features,
                    regime=regime,
                    pre_score=pre_score,
                )

                if filtered is not None:
                    signals.append(filtered)
                    # Сохраняем сигнал в БД
                    try:
                        await save_signal(self._db_path, filtered)
                    except Exception as exc:
                        logger.warning("signal.save_error", ticker=ticker, error=str(exc))

                    logger.info(
                        "step.generate_signals.signal",
                        ticker=ticker,
                        action=filtered.action.value,
                        direction=filtered.direction.value,
                        confidence=round(filtered.confidence, 3),
                        pre_score=round(pre_score, 1),
                    )

                    # Уведомляем в Telegram по всем значимым сигналам
                    if self._telegram and filtered.action in (
                        Action.BUY, Action.SELL, Action.REDUCE, Action.HOLD
                    ):
                        await self._safe_telegram(self._telegram.notify_signal(filtered))
                else:
                    logger.debug("step.generate_signals.filtered_out", ticker=ticker)

            except Exception as exc:
                # Ошибка одного тикера не останавливает генерацию остальных
                logger.warning("step.generate_signals.error", ticker=ticker, error=str(exc))

        # ─── Дивидендный гэп — отдельная алгоритмическая стратегия, не через Claude ───
        today = date.today()
        candles_cache: dict[str, list] = {}
        for ticker in self._ticker_symbols:
            ticker_candles = await get_latest_candles(self._db_path, ticker, count=30)
            if ticker_candles:
                candles_cache[ticker] = ticker_candles

        div_signals = find_dividend_gap_signals(candles_cache, today)
        for div_sig in div_signals:
            signals.append(div_sig)
            try:
                await save_signal(self._db_path, div_sig)
            except Exception as exc:
                logger.warning("signal.dividend_gap.save_error", ticker=div_sig.ticker, error=str(exc))
            logger.info(
                "step.generate_signals.dividend_gap",
                ticker=div_sig.ticker,
                entry_price=div_sig.entry_price,
                take_profit=div_sig.take_profit,
                stop_loss=div_sig.stop_loss,
                time_stop_days=div_sig.time_stop_days,
            )
            if self._telegram and div_sig.action == Action.BUY:
                await self._safe_telegram(self._telegram.notify_signal(div_sig))
        # ─────────────────────────────────────────────────────────────────────────

        # ─── Pairs Trading — отдельная market-neutral стратегия, не через Claude ───
        pairs_tickers = {t for pair in [{"A": "SBER", "B": "VTBR"}, {"A": "LKOH", "B": "ROSN"}]
                         for t in (pair["A"], pair["B"])}
        for ticker in pairs_tickers:
            if ticker not in candles_cache:
                ticker_candles = await get_latest_candles(self._db_path, ticker, count=200)
                if ticker_candles:
                    candles_cache[ticker] = ticker_candles

        pairs_signals = generate_pairs_signals(candles_cache, today)
        for sig in pairs_signals:
            signals.append(sig)
            try:
                await save_signal(self._db_path, sig)
            except Exception as exc:
                logger.warning("signal.pairs_trading.save_error", ticker=sig.ticker, error=str(exc))
            logger.info(
                "step.generate_signals.pairs_trading",
                ticker=sig.ticker,
                action=sig.action.value,
                direction=sig.direction.value,
                confidence=round(sig.confidence, 3),
            )
        # ─────────────────────────────────────────────────────────────────────────

        # ─── Si futures — trend following + хедж портфеля ────────────────────
        si_candles = await get_latest_candles(self._db_path, "USDRUB", count=200)
        macro = analysis.get("macro", {})
        # Рассчитываем текущую экспозицию портфеля в акциях
        try:
            portfolio = await self._executor.get_portfolio()
            portfolio_exposure = portfolio.exposure_pct
        except Exception:
            portfolio_exposure = 0.0

        si_signals = generate_si_signals(si_candles, macro, portfolio_exposure)
        for sig in si_signals:
            signals.append(sig)
            try:
                await save_signal(self._db_path, sig)
            except Exception as exc:
                logger.warning("signal.futures_si.save_error", ticker=sig.ticker, error=str(exc))
            logger.info(
                "step.generate_signals.futures_si",
                ticker=sig.ticker,
                action=sig.action.value,
                direction=sig.direction.value,
                confidence=round(sig.confidence, 3),
            )
        # ─────────────────────────────────────────────────────────────────────────

        logger.info(
            "step.generate_signals.done",
            signals=len(signals),
            buy_signals=sum(1 for s in signals if s.action == Action.BUY),
            sell_signals=sum(1 for s in signals if s.action == Action.SELL),
            reduce_signals=sum(1 for s in signals if s.action == Action.REDUCE),
            hold_signals=sum(1 for s in signals if s.action == Action.HOLD),
            dividend_gap_signals=len(div_signals),
            pairs_trading_signals=len(pairs_signals),
            futures_si_signals=len(si_signals),
        )
        return signals

    # ─── Шаг 4: Risk Gateway + Execution ─────────────────────────────────────

    async def step_execute(self, signals: list[TradingSignal]) -> list[dict[str, Any]]:
        """Проверить сигналы через Risk Gateway и исполнить ордера.

        Returns:
            Список dict с результатами исполнения.
        """
        logger.info("step.execute.start", signals=len(signals))
        executed: list[dict[str, Any]] = []

        if not signals:
            return executed

        # Проверяем circuit breaker
        portfolio = await self._executor.get_portfolio()
        cb_state, cb_reason = self._circuit_breaker.check(portfolio.equity)

        if cb_state in (CircuitState.HALTED, CircuitState.EMERGENCY):
            logger.warning(
                "step.execute.circuit_breaker_halted",
                state=cb_state.value,
                reason=cb_reason,
            )
            if self._telegram:
                await self._safe_telegram(
                    self._telegram.notify_alert("CRITICAL", f"Circuit Breaker: {cb_reason}")
                )
            return executed

        lot_size_default = 10  # Дефолтный размер лота

        for signal in signals:
            # Обрабатываем SELL/REDUCE/HOLD — не только BUY
            if signal.action == Action.HOLD:
                logger.info("step.execute.hold", ticker=signal.ticker, confidence=round(signal.confidence, 3))
                executed.append({"ticker": signal.ticker, "status": "hold"})
                continue

            if signal.action in (Action.SELL, Action.REDUCE):
                try:
                    if signal.action == Action.SELL:
                        result = await self._close_position_by_ticker(
                            ticker=signal.ticker,
                            reason="claude_sell",
                            signal=signal,
                        )
                        executed.append({
                            "ticker": signal.ticker,
                            "status": "sell_submitted" if result else "sell_no_position",
                        })
                    else:  # REDUCE
                        result = await self._reduce_position(
                            ticker=signal.ticker,
                            fraction=0.5,
                            reason="claude_reduce",
                            signal=signal,
                        )
                        executed.append({
                            "ticker": signal.ticker,
                            "status": "reduce_submitted" if result else "reduce_no_position",
                        })
                except Exception as exc:
                    logger.warning("step.execute.sell_reduce_error", ticker=signal.ticker, error=str(exc))
                    executed.append({"ticker": signal.ticker, "status": "error", "error": str(exc)})
                continue

            if signal.action != Action.BUY:
                continue

            try:
                lot_size = self._lot_map.get(signal.ticker, lot_size_default)

                # Risk Gateway
                risk_result = validate_signal(
                    signal=signal,
                    portfolio=portfolio,
                    config={
                        "lot_size": lot_size,
                        "risk_per_trade": self._strategy_cfg.get("risk_per_trade", 0.015),
                        "max_single_position_pct": self._strategy_cfg.get("max_position_pct", 0.15),
                    },
                )

                # Журналируем решение risk gateway
                await log_signal_decision(
                    db_path=self._db_path,
                    ticker=signal.ticker,
                    signal=signal,
                    risk_result=risk_result,
                    final_action="approved" if risk_result.decision == RiskDecision.APPROVE else "rejected",
                )

                if risk_result.decision == RiskDecision.REJECT:
                    logger.info(
                        "step.execute.risk_rejected",
                        ticker=signal.ticker,
                        errors=risk_result.errors[:2],
                    )
                    executed.append({
                        "ticker": signal.ticker,
                        "status": "risk_rejected",
                        "errors": risk_result.errors,
                    })
                    continue

                # Рассчитываем position size
                if signal.entry_price is None or signal.stop_loss is None:
                    logger.info("step.execute.no_price_or_stop", ticker=signal.ticker)
                    continue

                drawdown = portfolio.drawdown
                consecutive = portfolio.consecutive_losses
                dd_mult = calculate_drawdown_multiplier(drawdown)
                cons_mult = calculate_consecutive_multiplier(consecutive)

                # Применяем multiplier от circuit breaker
                cb_mult = self._circuit_breaker.get_position_multiplier()
                effective_dd_mult = dd_mult * cb_mult

                lots, pos_value, risk_pct = calculate_position_size(
                    equity=portfolio.equity,
                    entry_price=signal.entry_price,
                    stop_loss_price=signal.stop_loss,
                    lot_size=lot_size,
                    risk_per_trade=self._strategy_cfg.get("risk_per_trade", 0.015),
                    max_position_pct=self._strategy_cfg.get("max_position_pct", 0.15),
                    direction=signal.direction.value,
                    drawdown_mult=effective_dd_mult,
                    consecutive_mult=cons_mult,
                )

                if lots <= 0:
                    logger.info(
                        "step.execute.zero_lots",
                        ticker=signal.ticker,
                        equity=portfolio.equity,
                        dd_mult=dd_mult,
                    )
                    continue

                # Устанавливаем рыночную цену в executor
                getattr(self._executor, "set_market_price", lambda t,p: None)(signal.ticker, signal.entry_price)

                # Формируем ордер
                order = Order(
                    order_id=str(uuid.uuid4()),
                    ticker=signal.ticker,
                    direction=signal.direction.value,
                    action="buy",
                    order_type=OrderType.LIMIT,
                    lots=lots,
                    lot_size=lot_size,
                    limit_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    signal_confidence=signal.confidence,
                )

                # Исполняем
                status = await self._executor.submit_order(order)

                # Журналируем сделку
                await log_trade(
                    db_path=self._db_path,
                    ticker=signal.ticker,
                    direction=signal.direction.value,
                    action="buy",
                    price=signal.entry_price,
                    lots=lots,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    reasoning=signal.reasoning,
                    signal_confidence=signal.confidence,
                    pre_score=signal.pre_score,
                )

                trade_result: dict[str, Any] = {
                    "ticker": signal.ticker,
                    "status": status.value,
                    "lots": lots,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "position_value": pos_value,
                    "risk_pct": round(risk_pct, 4),
                }
                executed.append(trade_result)

                self._circuit_breaker.record_trade(pnl=0.0)  # сделка открыта — pnl=0

                logger.info(
                    "step.execute.order_submitted",
                    ticker=signal.ticker,
                    status=status.value,
                    lots=lots,
                    entry=signal.entry_price,
                )

            except Exception as exc:
                logger.warning("step.execute.error", ticker=signal.ticker, error=str(exc))
                executed.append({"ticker": signal.ticker, "status": "error", "error": str(exc)})

        filled = sum(1 for r in executed if r.get("status") == "filled")
        sold = sum(1 for r in executed if r.get("status") == "sell_submitted")
        reduced = sum(1 for r in executed if r.get("status") == "reduce_submitted")
        held = sum(1 for r in executed if r.get("status") == "hold")
        logger.info(
            "step.execute.done",
            submitted=len(executed),
            filled=filled,
            sold=sold,
            reduced=reduced,
            held=held,
        )
        return executed

    # ─── Шаг 5: Мониторинг (trailing stops, exit conditions) ─────────────────

    async def step_monitor(self) -> None:
        """Проверить trailing stops и exit conditions для открытых позиций."""
        try:
            positions = await self._executor.get_positions()
            if not positions:
                return

            portfolio = await self._executor.get_portfolio()

            for pos in positions:
                ticker = pos.ticker
                features = self._features_cache.get(ticker)
                if not features:
                    # Нет свежих features — обновляем
                    try:
                        bars = await get_latest_candles(self._db_path, ticker, count=60)
                        if bars:
                            df = self._bars_to_df(bars)
                            df = calculate_all_features(df)
                            last = df.row(-1, named=True)
                            features = {k: self._safe_float(v) for k, v in last.items()}
                            features["obv_trend"] = self._calc_obv_trend(df)
                            self._features_cache[ticker] = features
                    except Exception as exc:
                        logger.warning("monitor.features_error", ticker=ticker, error=str(exc))
                        continue

                # Обновляем цену в executor
                current_price = features.get("close")
                if current_price:
                    getattr(self._executor, "set_market_price", lambda t,p: None)(ticker, float(current_price))

                # Рассчитываем days_held
                days_held = (datetime.utcnow() - pos.opened_at).days

                # Рассчитываем max_profit_pct
                if pos.direction == "long" and pos.entry_price > 0:
                    max_profit_pct = max(0.0, (pos.current_price - pos.entry_price) / pos.entry_price)
                else:
                    max_profit_pct = 0.0

                position_dict = {
                    "entry_price": pos.entry_price,
                    "stop_loss": pos.stop_loss,
                    "direction": pos.direction,
                    "max_profit_pct": max_profit_pct,
                }

                exit_reason = check_exit_conditions(
                    position=position_dict,
                    features=features,
                    signal=None,  # Нет свежего Claude-сигнала при мониторинге
                    days_held=days_held,
                )

                if exit_reason:
                    logger.info(
                        "monitor.exit_signal",
                        ticker=ticker,
                        reason=exit_reason,
                        days_held=days_held,
                    )
                    # Формируем ордер на закрытие
                    await self._close_position(pos, exit_reason)

        except Exception as exc:
            logger.warning("step.monitor.error", error=str(exc))

    # ─── Шаг 6: Дневной отчёт ────────────────────────────────────────────────

    async def step_daily_report(self) -> str:
        """Сформировать дневной отчёт и отправить в Telegram.

        Returns:
            Строка с текстом отчёта.
        """
        logger.info("step.daily_report.start")

        portfolio = await self._executor.get_portfolio()
        trade_log = getattr(self._executor, "trade_log", [])

        daily_pnl = sum(t.get("pnl", 0) for t in trade_log if t.get("date", "").startswith(date.today().isoformat()))

        # Формируем отчёт
        positions_lines: list[str] = []
        for ticker, pos in portfolio.positions.items():
            positions_lines.append(
                f"  {ticker} {pos.direction.upper()} x{pos.lots}л | "
                f"entry={pos.entry_price:,.2f} | pnl={pos.unrealized_pnl:+,.0f}₽"
            )

        report_lines = [
            f"=== ДНЕВНОЙ ОТЧЁТ {date.today().isoformat()} ===",
            f"Equity:      {portfolio.equity:>12,.0f} ₽",
            f"Cash:        {portfolio.cash:>12,.0f} ₽",
            f"P&L сегодня: {daily_pnl:>+12,.0f} ₽",
            f"Drawdown:    {portfolio.drawdown:>11.2%}",
            f"Exposure:    {portfolio.exposure_pct:>11.2%}",
            f"Позиций:     {len(portfolio.positions):>12}",
            f"Сделок:      {len(trade_log):>12}",
            f"Режим рынка: {self._market_regime.value:>12}",
        ]

        if positions_lines:
            report_lines.append("Открытые позиции:")
            report_lines.extend(positions_lines)

        pre_scores_top = sorted(self._pre_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        if pre_scores_top:
            report_lines.append("Топ-5 Pre-Score:")
            for tkr, scr in pre_scores_top:
                report_lines.append(f"  {tkr}: {scr:.1f}")

        report = "\n".join(report_lines)
        logger.info("step.daily_report.text", report=report)

        # Отправляем в Telegram
        if self._telegram:
            await self._safe_telegram(
                self._telegram.notify_daily_report(portfolio=portfolio, pnl=daily_pnl)
            )

        logger.info("step.daily_report.done", pnl=daily_pnl, positions=len(portfolio.positions))
        return report

    # ─── Полный дневной цикл ─────────────────────────────────────────────────

    async def run_daily_cycle(self) -> dict[str, Any]:
        """Полный дневной цикл: данные → анализ → сигналы → исполнение.

        Returns:
            Сводный словарь результатов каждого шага.
        """
        started_at = datetime.now()
        logger.info("daily_cycle.start", date=date.today().isoformat())

        # Сброс дневного счётчика circuit breaker
        portfolio = await self._executor.get_portfolio()
        self._circuit_breaker.new_day(portfolio.equity)

        result: dict[str, Any] = {
            "date": date.today().isoformat(),
            "started_at": started_at.isoformat(),
            "steps": {},
        }

        try:
            # Шаг 1: Загрузка данных
            data = await self.step_load_data()
            result["steps"]["load_data"] = {
                "bars_loaded": data.get("bars_loaded", 0),
                "news_count": data.get("news_count", 0),
                "macro_indicators": list(data.get("macro", {}).keys()),
            }

            # Шаг 2: Анализ
            analysis = await self.step_analyze(data)
            result["steps"]["analyze"] = {
                "regime": analysis.get("regime", MarketRegime.WEAK_TREND).value,
                "tickers_analyzed": len(analysis.get("pre_scores", {})),
                "pre_scores": {
                    t: round(s, 1) for t, s in analysis.get("pre_scores", {}).items()
                },
            }

            # Шаг 3: Генерация сигналов
            signals = await self.step_generate_signals(analysis)
            result["steps"]["generate_signals"] = {
                "signals_count": len(signals),
                "buy_signals": [
                    {"ticker": s.ticker, "confidence": round(s.confidence, 3)}
                    for s in signals
                    if s.action == Action.BUY
                ],
                "sell_signals": [
                    {"ticker": s.ticker, "confidence": round(s.confidence, 3)}
                    for s in signals
                    if s.action == Action.SELL
                ],
                "reduce_signals": [
                    {"ticker": s.ticker, "confidence": round(s.confidence, 3)}
                    for s in signals
                    if s.action == Action.REDUCE
                ],
            }

            # Шаг 4: Исполнение
            executions = await self.step_execute(signals)
            result["steps"]["execute"] = {
                "submitted": len(executions),
                "filled": sum(1 for e in executions if e.get("status") == "filled"),
                "rejected": sum(1 for e in executions if "rejected" in e.get("status", "")),
                "sold": sum(1 for e in executions if e.get("status") == "sell_submitted"),
                "reduced": sum(1 for e in executions if e.get("status") == "reduce_submitted"),
            }

            # Шаг 5: Мониторинг (первичная проверка exits)
            await self.step_monitor()

            # Шаг 6: Дневной отчёт
            report = await self.step_daily_report()
            result["steps"]["daily_report"] = {"report_length": len(report)}

        except Exception as exc:
            logger.error("daily_cycle.fatal_error", error=str(exc), exc_info=True)
            result["error"] = str(exc)
            if self._telegram:
                await self._safe_telegram(
                    self._telegram.notify_alert("CRITICAL", f"Daily cycle error: {exc}")
                )

        elapsed = (datetime.now() - started_at).total_seconds()
        result["elapsed_seconds"] = round(elapsed, 1)
        logger.info("daily_cycle.done", elapsed=elapsed, date=result["date"])
        return result

    # ─── Вспомогательные методы ───────────────────────────────────────────────

    def _bars_to_df(self, bars: list) -> pl.DataFrame:
        """Преобразовать список OHLCVBar в Polars DataFrame."""
        return pl.DataFrame({
            "date": [b.dt for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        })

    def _calc_obv_trend(self, df: pl.DataFrame) -> str:
        """Определить тренд OBV по последним 5 барам: up / down / flat."""
        try:
            obv_col = df["obv"].drop_nulls()
            if len(obv_col) < 5:
                return "flat"
            last5 = obv_col[-5:].to_list()
            first_val = last5[0]
            last_val = last5[-1]
            if first_val == 0:
                return "flat"
            change_pct = (last_val - first_val) / abs(first_val)
            if change_pct > 0.01:
                return "up"
            if change_pct < -0.01:
                return "down"
            return "flat"
        except Exception:
            return "flat"

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        """Безопасное преобразование в float, None при ошибке или NaN."""
        if val is None:
            return None
        try:
            fval = float(val)
            return None if math.isnan(fval) or math.isinf(fval) else fval
        except (TypeError, ValueError):
            return None

    async def _close_position(self, pos: Any, reason: str) -> None:
        """Выставить ордер на закрытие позиции."""
        try:
            current_price = float(pos.current_price)
            getattr(self._executor, "set_market_price", lambda t,p: None)(pos.ticker, current_price)

            close_order = Order(
                order_id=str(uuid.uuid4()),
                ticker=pos.ticker,
                direction=pos.direction,
                action="sell",
                order_type=OrderType.MARKET,
                lots=pos.lots,
                lot_size=pos.lot_size,
                limit_price=current_price,
                signal_confidence=0.0,
            )
            status = await self._executor.submit_order(close_order)

            pnl = pos.unrealized_pnl
            await log_trade(
                db_path=self._db_path,
                ticker=pos.ticker,
                direction=pos.direction,
                action=reason,
                price=current_price,
                lots=pos.lots,
                stop_loss=pos.stop_loss,
                take_profit=pos.take_profit,
                reasoning=f"Auto-exit: {reason}",
                signal_confidence=0.0,
                pre_score=0.0,
            )

            self._circuit_breaker.record_trade(pnl=pnl)

            if self._telegram:
                await self._safe_telegram(
                    self._telegram.notify_trade({
                        "ticker": pos.ticker,
                        "direction": pos.direction,
                        "action": reason,
                        "entry": pos.entry_price,
                        "exit": current_price,
                        "lots": pos.lots,
                        "pnl": pnl,
                        "date": datetime.utcnow().isoformat(),
                    })
                )

            logger.info(
                "monitor.position_closed",
                ticker=pos.ticker,
                reason=reason,
                status=status.value,
                pnl=round(pnl, 2),
            )
        except Exception as exc:
            logger.warning("monitor.close_error", ticker=pos.ticker, error=str(exc))

    async def _close_position_by_ticker(
        self,
        ticker: str,
        reason: str = "signal",
        signal: "TradingSignal | None" = None,
    ) -> bool:
        """Закрыть позицию по тикеру полностью по сигналу Claude (SELL).

        Args:
            ticker: Тикер инструмента.
            reason: Причина закрытия для журнала (например, "claude_sell").
            signal: Исходный сигнал Claude (для уверенности и лога).

        Returns:
            True если позиция найдена и ордер отправлен, False если позиции нет.
        """
        positions = await self._executor.get_positions()
        pos = next((p for p in positions if p.ticker == ticker), None)
        if pos is None:
            logger.info("execute.sell.no_position", ticker=ticker, reason=reason)
            return False

        confidence = signal.confidence if signal is not None else 0.0
        confidence_pct = round(confidence * 100)

        current_price = float(pos.current_price)
        getattr(self._executor, "set_market_price", lambda t, p: None)(ticker, current_price)

        close_order = Order(
            order_id=str(uuid.uuid4()),
            ticker=ticker,
            direction=pos.direction,
            action="sell",
            order_type=OrderType.MARKET,
            lots=pos.lots,
            lot_size=pos.lot_size,
            limit_price=current_price,
            signal_confidence=confidence,
        )
        status = await self._executor.submit_order(close_order)

        pnl = pos.unrealized_pnl
        await log_trade(
            db_path=self._db_path,
            ticker=ticker,
            direction=pos.direction,
            action=reason,
            price=current_price,
            lots=pos.lots,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            reasoning=signal.reasoning if signal else f"Claude signal: {reason}",
            signal_confidence=confidence,
            pre_score=signal.pre_score if signal else 0.0,
        )

        self._circuit_breaker.record_trade(pnl=pnl)

        if self._telegram:
            dir_ru = "лонг" if pos.direction == "long" else "шорт"
            pnl_sign = "+" if pnl >= 0 else ""
            text = (
                f"📉 {ticker} | ЗАКРЫТИЕ ({dir_ru})\n"
                f"Причина: сигнал Claude (SELL, уверенность {confidence_pct}%)\n"
                f"Вход: {pos.entry_price:,.2f} | Выход: {current_price:,.2f}\n"
                f"Результат: {pnl_sign}{pnl:,.0f} руб."
            )
            await self._safe_telegram(self._telegram.send_message(text))

        logger.info(
            "execute.sell.done",
            ticker=ticker,
            reason=reason,
            status=status.value,
            lots=pos.lots,
            pnl=round(pnl, 2),
        )
        return True

    async def _reduce_position(
        self,
        ticker: str,
        fraction: float = 0.5,
        reason: str = "signal",
        signal: "TradingSignal | None" = None,
    ) -> bool:
        """Уменьшить позицию по тикеру на fraction (0.5 = продать 50%).

        Args:
            ticker: Тикер инструмента.
            fraction: Доля лотов для продажи (0.0–1.0).
            reason: Причина для журнала (например, "claude_reduce").
            signal: Исходный сигнал Claude (для уверенности и лога).

        Returns:
            True если позиция найдена и ордер отправлен, False если позиции нет.
        """
        positions = await self._executor.get_positions()
        pos = next((p for p in positions if p.ticker == ticker), None)
        if pos is None:
            logger.info("execute.reduce.no_position", ticker=ticker, reason=reason)
            return False

        lots_to_sell = max(1, int(pos.lots * fraction))
        confidence = signal.confidence if signal is not None else 0.0
        confidence_pct = round(confidence * 100)

        current_price = float(pos.current_price)
        getattr(self._executor, "set_market_price", lambda t, p: None)(ticker, current_price)

        reduce_order = Order(
            order_id=str(uuid.uuid4()),
            ticker=ticker,
            direction=pos.direction,
            action="sell",
            order_type=OrderType.MARKET,
            lots=lots_to_sell,
            lot_size=pos.lot_size,
            limit_price=current_price,
            signal_confidence=confidence,
        )
        status = await self._executor.submit_order(reduce_order)

        pnl = (current_price - pos.entry_price) * lots_to_sell * pos.lot_size
        await log_trade(
            db_path=self._db_path,
            ticker=ticker,
            direction=pos.direction,
            action=reason,
            price=current_price,
            lots=lots_to_sell,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            reasoning=signal.reasoning if signal else f"Claude signal: {reason}",
            signal_confidence=confidence,
            pre_score=signal.pre_score if signal else 0.0,
        )

        self._circuit_breaker.record_trade(pnl=pnl)

        if self._telegram:
            dir_ru = "лонг" if pos.direction == "long" else "шорт"
            pnl_sign = "+" if pnl >= 0 else ""
            fraction_pct = round(fraction * 100)
            text = (
                f"📉 {ticker} | СОКРАЩЕНИЕ ({dir_ru}, -{fraction_pct}%)\n"
                f"Причина: сигнал Claude (REDUCE, уверенность {confidence_pct}%)\n"
                f"Вход: {pos.entry_price:,.2f} | Выход: {current_price:,.2f}\n"
                f"Продано: {lots_to_sell} лот(ов) | Результат: {pnl_sign}{pnl:,.0f} руб."
            )
            await self._safe_telegram(self._telegram.send_message(text))

        logger.info(
            "execute.reduce.done",
            ticker=ticker,
            reason=reason,
            status=status.value,
            lots_sold=lots_to_sell,
            lots_remaining=pos.lots - lots_to_sell,
            pnl=round(pnl, 2),
        )
        return True

    @staticmethod
    async def _safe_telegram(coro: Any) -> bool:
        """Выполнить Telegram-уведомление, поглощая все исключения."""
        try:
            return await coro
        except Exception as exc:
            logger.debug("telegram.error", error=str(exc))
            return False


# ─────────────────────────────────────────────────────────────────────────────
# main()
# ─────────────────────────────────────────────────────────────────────────────


async def main() -> None:
    """Точка входа торговой системы.

    Режимы:
        --once    Однократный запуск полного цикла (для тестирования).
        (default) Production-режим с APScheduler.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    # Создаём директорию для БД
    settings.db_path_resolved.parent.mkdir(parents=True, exist_ok=True)
    await init_db(str(settings.db_path_resolved))

    logger.info(
        "system.start",
        mode=settings.trading_mode,
        strategy=settings.default_strategy,
        db=settings.db_path,
        once="--once" in sys.argv,
    )

    pipeline = TradingPipeline()

    # ── Режим однократного запуска ──────────────────────────────────────────
    if "--once" in sys.argv:
        result = await pipeline.run_daily_cycle()
        print(json.dumps(result, indent=2, default=str))
        return

    # ── Production-режим с APScheduler ──────────────────────────────────────
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # 06:00 МСК — полный дневной цикл
    scheduler.add_job(
        pipeline.run_daily_cycle,
        "cron",
        hour=6,
        minute=0,
        id="daily_cycle",
        max_instances=1,
        coalesce=True,
    )

    # Каждые 5 минут — проверка trailing stops и exit conditions
    scheduler.add_job(
        pipeline.step_monitor,
        "interval",
        minutes=5,
        id="monitor",
        max_instances=1,
        coalesce=True,
    )

    # 19:00 МСК — дневной отчёт
    scheduler.add_job(
        pipeline.step_daily_report,
        "cron",
        hour=19,
        minute=0,
        id="daily_report",
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info(
        "system.ready",
        hint="Планировщик запущен. Цикл в 06:00, мониторинг каждые 5 мин, отчёт в 19:00 MSK.",
    )

    # Обработка сигналов завершения (Windows-совместимо)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("system.shutdown_requested", signal=sig.name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown, sig)
        except (NotImplementedError, OSError):
            pass  # Windows не поддерживает add_signal_handler для SIGTERM

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    scheduler.shutdown(wait=False)
    logger.info("system.stopped")


if __name__ == "__main__":
    asyncio.run(main())
