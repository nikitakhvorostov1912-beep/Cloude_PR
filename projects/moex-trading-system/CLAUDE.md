# CLAUDE.md — MOEX Trading Bot: Фаза реализации

## Контекст

Проект уже содержит 58 модулей и 599 тестов. Всё скомпилировано из 12 репозиториев.
Код работает, тесты зелёные. Но есть критические пробелы которые не дают перейти к live.

**Что уже есть (НЕ ТРОГАЙ без необходимости):**
- `src/indicators/` — 11 файлов (Ehlers, Damiani, SuperTrend, GARCH, squeeze, S/R, candle patterns...)
- `src/backtest/metrics.py` — Sharpe, Sortino, Calmar, Omega, Serenity, CVaR, PSR, SQN, Kelly, Alpha/Beta
- `src/backtest/monte_carlo.py` — trade shuffling, candle noise, block bootstrap
- `src/backtest/optimizer.py` — Optuna + fitness functions
- `src/backtest/commissions.py` — MOEX commission rules engine
- `src/execution/` — TWAP, DCA, Grid, Triple Barrier, Quoting (Avellaneda-Stoikov)
- `src/risk/` — PortfolioCircuitBreaker, ProtectiveController, PositionSizer, PositionTracker, Rules
- `src/ml/` — ensemble, UMP filter, processors, label generators, trainer, predictor
- `src/analysis/` — features, regime detection, scoring, TSFRESH
- `src/data/` — exchange_rates, LOB, universe_loader
- `src/models/` — market.py, signal.py
- `src/strategy/` — multi_agent, news_reactor, signal_synthesis, signal_filter, universe_selector
- `tests/` — 20 тест-файлов, 599 passed, 7 skipped (GARCH)

**Что ОТСУТСТВУЕТ (твоя задача):**
1. BaseStrategy ABC — единый интерфейс для всех стратегий
2. Pydantic-модели — Bar, Order, Position, Portfolio (полные, с валидацией)
3. MOEX ISS коннектор — загрузка свечей, инструментов, стакана
4. E2E тесты — полный pipeline от данных до метрик
5. Walk-forward оркестратор — train/predict/shift для ML
6. Недостающие зависимости — arch, sortedcontainers в requirements.txt
7. Paper trading — Tinkoff/Alor API + Telegram алерты
8. Конфигурация settings.yaml — единая точка правды

---

## Режим работы

Ты работаешь ПОСЛЕДОВАТЕЛЬНО по фазам 1 → 2 → 3 → 4.
Внутри каждой фазы — по задачам в указанном порядке.
Каждая задача = код + тесты + проверка + коммит.

**ПРАВИЛА:**
- НЕ ЛОМАЙ существующие 599 тестов. После КАЖДОГО коммита: `pytest tests/ -v --tb=short` = 0 failures
- НЕ ПЕРЕПИСЫВАЙ существующие модули без явной необходимости
- Новый код ИМПОРТИРУЕТ существующие модули, а не дублирует их
- Каждая зависимость: `pip install X --break-system-packages && python -c "import X; print('OK')"`
- Каждый новый файл: минимум 7 тестов (не заглушки, с assert)
- ЗАПРЕЩЕНО: `pass`, `TODO`, `# потом`, `NotImplementedError` в финальном коде
- После каждой задачи пиши чеклист ✅/❌ — не коммить с ❌

---

# ═══════════════════════════════════════════
# ФАЗА 1: ФУНДАМЕНТ (закрыть архитектурный долг)
# ═══════════════════════════════════════════

## Задача 1.0: Зависимости

```bash
# Недостающие зависимости (7 тестов skipped из-за этого)
pip install arch --break-system-packages && python -c "from arch import arch_model; print('arch OK')"
pip install sortedcontainers --break-system-packages && python -c "from sortedcontainers import SortedList; print('sortedcontainers OK')"

# Для фаз 2-4 (установи СЕЙЧАС, не потом)
pip install tinkoff-investments --break-system-packages && python -c "from tinkoff.invest import Client; print('tinkoff OK')"
pip install python-telegram-bot --break-system-packages && python -c "import telegram; print('telegram OK')"
pip install aiomoex --break-system-packages && python -c "import aiomoex; print('aiomoex OK')"
pip install vectorbt --break-system-packages && python -c "import vectorbt; print('vectorbt OK')" || echo "vectorbt optional"
pip install streamlit --break-system-packages && python -c "import streamlit; print('streamlit OK')" || echo "streamlit optional"
```

Обнови `requirements.txt` — добавь ВСЕ новые пакеты с версиями.

**Проверка:** Перезапусти ВСЕ тесты — GARCH тесты теперь должны проходить (не skip):
```bash
pytest tests/ -v --tb=short 2>&1 | grep -E "passed|failed|skipped"
# Цель: 606 passed, 0 skipped (или ≤ 2 skipped по другим причинам)
```

**Коммит:** `fix: add missing dependencies (arch, sortedcontainers, tinkoff, telegram)`

---

## Задача 1.1: Единый конфиг — `config/settings.yaml`

Создай ЕСЛИ НЕТ, или ДОПОЛНИ существующий. Это единая точка правды для всего проекта.

```yaml
project:
  name: "moex-trading-bot"
  version: "0.2.0"

moex:
  iss_url: "https://iss.moex.com/iss"
  max_requests_per_sec: 50
  boards:
    equities: "TQBR"
    futures: "RFUD"
    options: "ROPD"
    fx: "CETS"
  sessions:
    main_start: "10:00"
    main_end: "18:40"
    evening_start: "19:05"
    evening_end: "23:50"
    clearing_1_start: "14:00"
    clearing_1_end: "14:05"
    clearing_2_start: "18:45"
    clearing_2_end: "19:00"
    auction_open_start: "09:50"
    auction_open_end: "10:00"
    auction_close_start: "18:40"
    auction_close_end: "18:50"

costs:
  equity:
    commission_pct: 0.0001
    slippage_ticks: 2
    settlement: "T+1"
  futures:
    commission_rub: 2.0
    slippage_ticks: 1
    settlement: "T+0"
  options:
    commission_rub: 2.0
    slippage_ticks: 3
    settlement: "T+0"
  fx:
    commission_pct: 0.00003
    slippage_ticks: 1
    settlement: "T+1"

risk:
  max_position_pct: 0.20
  max_daily_drawdown_pct: 0.05
  max_total_drawdown_pct: 0.15
  max_correlated_exposure_pct: 0.40
  circuit_breaker_daily_dd: 0.05
  circuit_breaker_total_dd: 0.15

instruments:
  equities:
    SBER: {lot: 10, step: 0.01, sector: "banks"}
    GAZP: {lot: 10, step: 0.01, sector: "oil_gas"}
    LKOH: {lot: 1, step: 0.5, sector: "oil_gas"}
    VTBR: {lot: 10000, step: 0.000005, sector: "banks"}
    GMKN: {lot: 1, step: 1.0, sector: "metals"}
    ROSN: {lot: 1, step: 0.05, sector: "oil_gas"}
    YNDX: {lot: 1, step: 0.1, sector: "tech"}
    MGNT: {lot: 1, step: 0.5, sector: "retail"}
    NVTK: {lot: 1, step: 0.1, sector: "oil_gas"}
    PLZL: {lot: 1, step: 1.0, sector: "metals"}
    MOEX: {lot: 10, step: 0.01, sector: "finance"}
    TCSG: {lot: 1, step: 0.2, sector: "banks"}
    ALRS: {lot: 10, step: 0.01, sector: "metals"}
    SNGS: {lot: 100, step: 0.005, sector: "oil_gas"}
    TATN: {lot: 1, step: 0.1, sector: "oil_gas"}
  futures:
    Si: {step: 1.0, go_pct: 0.15, base: "USD/RUB"}
    RTS: {step: 10.0, go_pct: 0.20, base: "RTS Index"}
    BR: {step: 0.01, go_pct: 0.15, base: "Brent"}
    GOLD: {step: 0.1, go_pct: 0.15, base: "Gold"}
    NG: {step: 0.001, go_pct: 0.15, base: "Natural Gas"}

backtest:
  default_capital: 1_000_000
  trading_days_per_year: 252
  benchmark: "IMOEX"
  min_sharpe_threshold: 1.0
  max_drawdown_threshold: 0.20
  min_trades_for_validity: 30
  walk_forward:
    n_windows: 5
    train_ratio: 0.70
    gap_bars: 1
    retrain_every_n_bars: 60

ml:
  models: ["catboost", "lightgbm", "xgboost"]
  ensemble_method: "stacking"
  feature_selection:
    method: "mutual_info"
    top_k: 50
  label:
    method: "triple_barrier"
    take_profit_atr: 2.0
    stop_loss_atr: 1.5
    max_holding_bars: 20

telegram:
  # Заполнить через .env
  bot_token_env: "TELEGRAM_BOT_TOKEN"
  chat_id_env: "TELEGRAM_CHAT_ID"
  alerts:
    - signal_generated
    - order_filled
    - stop_triggered
    - circuit_breaker_activated
    - daily_pnl_report

broker:
  default: "tinkoff"
  tinkoff:
    token_env: "TINKOFF_TOKEN"
    sandbox: true
    account_id_env: "TINKOFF_ACCOUNT_ID"
```

Напиши `src/core/config.py` — загрузчик конфига:

```python
# Должен:
# 1. Загружать config/settings.yaml
# 2. Валидировать через Pydantic Settings
# 3. Overlay .env переменные
# 4. Быть singleton (один раз загрузил — везде используешь)
# 5. Давать доступ: config.moex.iss_url, config.costs.equity.commission_pct и т.д.
```

**Тесты:** `tests/test_core/test_config.py`
```
[ ] test_load_settings — файл загружается без ошибок
[ ] test_moex_section — все поля MOEX присутствуют
[ ] test_costs_section — комиссии для 4 типов инструментов
[ ] test_instruments — все 15 акций и 5 фьючерсов
[ ] test_risk_limits — все лимиты > 0 и < 1
[ ] test_get_instrument_info — SBER → {lot: 10, step: 0.01}
[ ] test_unknown_instrument — KeyError или None
[ ] test_env_override — переменные окружения перезаписывают YAML
```

```bash
pytest tests/test_core/test_config.py -v  # 0 failures
pytest tests/ -v --tb=short  # ВСЕ тесты проходят
```

**Коммит:** `feat(core): add unified settings.yaml + Pydantic config loader`

---

## Задача 1.2: Pydantic-модели — `src/core/models.py`

> Существующий `src/models/market.py` и `src/models/signal.py` НЕ УДАЛЯЙ.
> Новые модели в `src/core/models.py`. Потом можно рефакторить импорты.

```python
"""Core domain models for the MOEX trading bot.

All models use Pydantic v2 for validation, serialization, and type safety.
These are the canonical data structures passed between all modules.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
# ...

class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class InstrumentType(str, Enum):
    EQUITY = "equity"
    FUTURES = "futures"
    OPTIONS = "options"
    FX = "fx"

class Bar(BaseModel):
    """Single OHLCV bar."""
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    instrument: str
    timeframe: str = "1d"  # "1m", "5m", "15m", "1h", "1d"

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v, info):
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v

class Signal(BaseModel):
    """Trading signal from a strategy."""
    instrument: str
    side: Side
    strength: float = Field(ge=-1.0, le=1.0)
    strategy_name: str
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    metadata: dict = Field(default_factory=dict)

class Order(BaseModel):
    """Order to be executed."""
    instrument: str
    side: Side
    quantity: float = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    strategy_name: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    fill_price: float | None = None
    fill_timestamp: datetime | None = None
    commission: float = 0.0

class Position(BaseModel):
    """Open position."""
    instrument: str
    side: Side
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    stop_loss: float | None = None
    take_profit: float | None = None
    entry_timestamp: datetime = Field(default_factory=datetime.now)
    strategy_name: str = ""
    instrument_type: InstrumentType = InstrumentType.EQUITY
    lot_size: int = 1
    price_step: float = 0.01

    @property
    def unrealized_pnl(self) -> float:
        diff = self.current_price - self.entry_price
        if self.side == Side.SHORT:
            diff = -diff
        return diff * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        return self.unrealized_pnl / (self.entry_price * self.quantity) if self.entry_price > 0 else 0.0

class Portfolio(BaseModel):
    """Portfolio state snapshot."""
    positions: list[Position] = Field(default_factory=list)
    cash: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def total_value(self) -> float:
        positions_value = sum(p.current_price * p.quantity for p in self.positions)
        return self.cash + positions_value

    @property
    def exposure(self) -> float:
        return sum(p.current_price * p.quantity for p in self.positions) / self.total_value if self.total_value > 0 else 0.0

class TradeResult(BaseModel):
    """Completed trade for backtest reporting."""
    instrument: str
    side: Side
    entry_price: float
    exit_price: float
    quantity: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    strategy_name: str = ""
    commission: float = 0.0
    slippage: float = 0.0

    @property
    def gross_pnl(self) -> float:
        diff = self.exit_price - self.entry_price
        if self.side == Side.SHORT:
            diff = -diff
        return diff * self.quantity

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.commission - self.slippage

    @property
    def duration(self) -> float:
        return (self.exit_timestamp - self.entry_timestamp).total_seconds()

    @property
    def return_pct(self) -> float:
        return self.net_pnl / (self.entry_price * self.quantity) if self.entry_price > 0 else 0.0
```

**Тесты:** `tests/test_core/test_models.py` — минимум 15 тестов:
```
[ ] test_bar_creation — валидные данные
[ ] test_bar_high_gte_low — high < low → ValidationError
[ ] test_bar_negative_price — open < 0 → ValidationError
[ ] test_signal_strength_range — strength > 1 → ValidationError
[ ] test_signal_creation — все поля
[ ] test_order_default_status — pending
[ ] test_order_serialization — .model_dump() / .model_validate()
[ ] test_position_unrealized_pnl_long — buy 100, price up → positive
[ ] test_position_unrealized_pnl_short — sell 100, price down → positive
[ ] test_position_pnl_pct — процент корректный
[ ] test_portfolio_total_value — cash + positions
[ ] test_portfolio_exposure — 0 при пустом, >0 при позициях
[ ] test_trade_result_gross_pnl — long win
[ ] test_trade_result_net_pnl — gross - commission - slippage
[ ] test_trade_result_duration — seconds between entry/exit
[ ] test_trade_result_return_pct — корректный %
[ ] test_enums — Side.LONG, OrderType.MARKET и т.д.
```

```bash
pytest tests/test_core/test_models.py -v  # 0 failures
pytest tests/ -v --tb=short  # ВСЕ тесты
```

**Коммит:** `feat(core): add canonical Pydantic models (Bar, Signal, Order, Position, Portfolio, TradeResult)`

---

## Задача 1.3: BaseStrategy ABC — `src/core/base_strategy.py`

```python
"""Abstract base class for all trading strategies.

Every strategy in src/strategies/ MUST inherit from this class.
This ensures uniform interface for backtesting, optimization, and live trading.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import polars as pl
from src.core.models import Signal, Side

class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, name: str, timeframe: str = "1d", instruments: list[str] | None = None):
        self.name = name
        self.timeframe = timeframe
        self.instruments = instruments or []
        self._params: dict[str, Any] = {}

    @abstractmethod
    def generate_signals(self, data: pl.DataFrame) -> list[Signal]:
        """Generate trading signals from market data.

        Args:
            data: DataFrame with columns: timestamp, open, high, low, close, volume.
                  May contain additional indicator columns.

        Returns:
            List of Signal objects. Empty list = no signal.
        """
        ...

    @abstractmethod
    def calculate_position_size(
        self, signal: Signal, portfolio_value: float, atr: float
    ) -> float:
        """Calculate position size in units (shares/contracts).

        Args:
            signal: The signal to size.
            portfolio_value: Current portfolio value in RUB.
            atr: Current ATR for the instrument.

        Returns:
            Number of units to trade. Must respect lot size.
        """
        ...

    @abstractmethod
    def get_stop_loss(self, entry_price: float, side: Side, atr: float) -> float:
        """Calculate stop-loss price.

        Args:
            entry_price: Entry price.
            side: LONG or SHORT.
            atr: Current ATR.

        Returns:
            Stop-loss price. For LONG: below entry. For SHORT: above entry.
        """
        ...

    def get_take_profit(self, entry_price: float, side: Side, atr: float) -> float | None:
        """Calculate take-profit price. Optional."""
        return None

    def on_bar(self, bar: dict) -> list[Signal]:
        """Process a single bar in real-time mode. Override for live trading."""
        return []

    def get_params(self) -> dict[str, Any]:
        """Return current strategy parameters for optimization."""
        return self._params.copy()

    def set_params(self, params: dict[str, Any]) -> None:
        """Set strategy parameters (used by optimizer)."""
        self._params.update(params)

    def warm_up_period(self) -> int:
        """Number of bars needed before strategy can generate signals."""
        return 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tf='{self.timeframe}')"
```

Дополнительно напиши `src/core/strategy_registry.py`:

```python
"""Registry for strategy discovery and instantiation."""
# Должен:
# 1. Автоматически находить все наследники BaseStrategy
# 2. Регистрировать по имени
# 3. Создавать экземпляры с параметрами из config
# 4. Перечислять доступные стратегии
```

**Тесты:** `tests/test_core/test_base_strategy.py`
```
[ ] test_cannot_instantiate_abc — BaseStrategy() → TypeError
[ ] test_concrete_strategy — наследник с реализацией → работает
[ ] test_generate_signals_returns_list — list[Signal]
[ ] test_position_size_positive — > 0
[ ] test_stop_loss_below_entry_long — stop < entry для long
[ ] test_stop_loss_above_entry_short — stop > entry для short
[ ] test_get_params — возвращает dict
[ ] test_set_params — обновляет параметры
[ ] test_warm_up_period — int ≥ 0
[ ] test_repr — строковое представление
```

```bash
pytest tests/test_core/ -v  # 0 failures
pytest tests/ -v --tb=short  # ВСЕ тесты
```

**Коммит:** `feat(core): add BaseStrategy ABC + strategy registry`

---

## Задача 1.4: Пример стратегии — `src/strategies/trend/ema_crossover.py`

Напиши ОДНУ простую стратегию как reference implementation BaseStrategy.
EMA crossover: fast EMA(20) > slow EMA(50) → LONG, наоборот → SHORT.

Она должна:
1. Наследовать BaseStrategy
2. Использовать существующие индикаторы из `src/indicators/` или `src/analysis/features.py`
3. Возвращать Signal с правильной strength [-1, +1]
4. Position sizing через ATR (2% риск на сделку)
5. Stop-loss через ATR (2 × ATR)
6. Учитывать лотность и шаг цены из config/settings.yaml
7. Иметь warm_up_period = 50

**Тесты:** `tests/test_strategies/test_ema_crossover.py` — минимум 10 тестов:
```
[ ] test_creation — инстанцирование без ошибок
[ ] test_inherits_base — isinstance(strategy, BaseStrategy)
[ ] test_signals_on_uptrend — генерирует LONG сигнал
[ ] test_signals_on_downtrend — генерирует SHORT сигнал
[ ] test_signals_on_flat — нет сигнала или слабый
[ ] test_position_size_respects_lot — кратен лоту SBER (10)
[ ] test_stop_loss_long — stop < entry, кратен шагу цены
[ ] test_stop_loss_short — stop > entry
[ ] test_warm_up_period — 50
[ ] test_empty_data — пустой DataFrame → пустой список
[ ] test_short_data — < warm_up → пустой список
```

**Коммит:** `feat(strategies): add EMA crossover reference implementation`

---

## Задача 1.5: E2E тест — `tests/test_e2e/test_full_pipeline.py`

> Это САМЫЙ ВАЖНЫЙ тест проекта. Он проверяет что все модули работают вместе.

```python
"""End-to-end test: data → indicators → strategy → backtest → metrics.

This test uses synthetic data to verify the complete pipeline works.
No external API calls. No network. Pure logic.
"""

# Тест должен:
# 1. Создать синтетические OHLCV данные (500 баров с трендом + шумом)
# 2. Инстанцировать EMA crossover стратегию
# 3. Сгенерировать сигналы
# 4. Прогнать простой бэктест (iterate bars, apply signals, track P&L)
# 5. Рассчитать метрики через src/backtest/metrics.py
# 6. Проверить что:
#    - Sharpe ≠ 0 (стратегия что-то делает)
#    - Max DD < 100% (не обнулился)
#    - Количество сделок > 0
#    - Комиссии > 0 (учитываются)
#    - Все TradeResult имеют валидные поля
```

Дополнительный E2E: `test_full_pipeline_with_ml.py`
```python
# 1. Синтетические данные (1000 баров)
# 2. Feature engineering через src/analysis/features.py
# 3. Label generation через src/ml/label_generators.py
# 4. Train ML model через src/ml/trainer.py
# 5. Predict через src/ml/predictor.py
# 6. Сгенерировать сигналы
# 7. Бэктест
# 8. Метрики
# 9. Assert: pipeline не падает, метрики вычисляются
```

**Коммит:** `test: add E2E pipeline tests (rule-based + ML)`

---

# ═══════════════════════════════════════════
# ФАЗА 2: ДАННЫЕ (MOEX ISS коннектор)
# ═══════════════════════════════════════════

## Задача 2.1: MOEX ISS клиент — `src/data/moex_iss.py`

```python
"""MOEX ISS REST API client for market data.

Endpoints:
- Candles: /iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json
- Instruments: /iss/engines/stock/markets/shares/boards/TQBR/securities.json
- Orderbook: /iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/orderbook.json
- Futures candles: /iss/engines/futures/markets/forts/boards/RFUD/securities/{ticker}/candles.json
- Index: /iss/engines/stock/markets/index/securities/{ticker}/candles.json

Rate limit: 50 requests/sec. Implement with asyncio semaphore.
"""

# Класс MoexISSClient:
# 1. async fetch_candles(ticker, start, end, timeframe="1d", board="TQBR") → list[Bar]
# 2. async fetch_instruments(board="TQBR") → list[dict]
# 3. async fetch_orderbook(ticker, board="TQBR", depth=20) → dict
# 4. async fetch_index(ticker="IMOEX", start, end) → list[Bar]
# 5. Rate limiting: asyncio.Semaphore(50)
# 6. Retry: 3 попытки с exponential backoff
# 7. Caching: optional diskcache
# 8. Pagination: MOEX ISS возвращает max 500 свечей за запрос → автопагинация
# 9. Конвертация в Polars DataFrame
# 10. Все параметры из config/settings.yaml
```

**Тесты:** `tests/test_data/test_moex_iss.py`

> Для тестов используй РЕАЛЬНЫЕ запросы к MOEX ISS (API бесплатный, без ключа).
> Если нет сети — пометь тесты `@pytest.mark.skipif(no_network)`.

```
[ ] test_fetch_candles_sber — загрузка свечей SBER за последний месяц
[ ] test_fetch_candles_si — загрузка фьючерса Si
[ ] test_fetch_candles_pagination — > 500 свечей (автопагинация)
[ ] test_candles_have_all_fields — timestamp, OHLCV, instrument
[ ] test_candles_sorted_by_time — хронологический порядок
[ ] test_fetch_instruments — список инструментов TQBR не пустой
[ ] test_fetch_imoex — индекс IMOEX загружается
[ ] test_invalid_ticker — несуществующий тикер → пустой результат или ошибка
[ ] test_rate_limiting — 100 запросов не вызывают 429
[ ] test_to_polars — результат конвертируется в Polars DataFrame
```

**Коммит:** `feat(data): add MOEX ISS REST API client with pagination and rate limiting`

---

## Задача 2.2: Загрузчик исторических данных — `scripts/download_history.py`

```bash
# Скрипт для массовой загрузки истории:
python scripts/download_history.py --tickers SBER,GAZP,LKOH,Si,RTS --start 2020-01-01 --end 2025-12-31 --timeframe 1d --output data/history/
```

Должен:
1. Использовать MoexISSClient из задачи 2.1
2. Скачивать свечи для списка тикеров
3. Сохранять в Parquet файлы (один файл на тикер)
4. Показывать прогресс
5. Пропускать уже скачанные данные (инкрементальная загрузка)

**Коммит:** `feat(scripts): add historical data downloader for MOEX`

---

## Задача 2.3: Бэктест на реальных данных

После загрузки данных — прогони E2E тест на реальных данных SBER за 2023-2024:

```python
# tests/test_e2e/test_real_data_backtest.py
# @pytest.mark.skipif(not data_exists)
# 1. Загрузить data/history/SBER.parquet
# 2. EMA crossover стратегия
# 3. Бэктест с комиссиями MOEX
# 4. Assert: Sharpe != NaN, trades > 10, DD < 50%
# 5. Сравнить с buy&hold SBER
# 6. Вывести отчёт
```

**Коммит:** `test: add real data backtest for SBER 2023-2024`

---

# ═══════════════════════════════════════════
# ФАЗА 3: ML PIPELINE
# ═══════════════════════════════════════════

## Задача 3.1: Walk-forward оркестратор — `src/ml/walk_forward.py`

```python
"""Walk-forward ML pipeline orchestrator.

Cycle: train(window_N) → predict(window_N+1) → shift → retrain(window_N+1) → predict(window_N+2) → ...

This is the CRITICAL missing piece that connects:
- src/ml/trainer.py (model training)
- src/ml/predictor.py (prediction)
- src/ml/processors.py (Qlib-style feature processing)
- src/ml/label_generators.py (target generation)
- src/backtest/metrics.py (evaluation)
"""

class WalkForwardML:
    """
    Args:
        strategy: BaseStrategy с ML-компонентом
        n_windows: количество окон (default: 5)
        train_ratio: доля train в каждом окне (default: 0.7)
        gap_bars: зазор между train и test (default: 1)
        retrain_every: пересчитывать модель каждые N баров (default: 60)

    Методы:
        run(data: pl.DataFrame) → WalkForwardResult
        - Разбивает данные на окна
        - В каждом окне: feature engineering → train → gap → predict → evaluate
        - Собирает OOS predictions
        - Считает метрики по OOS
        - Возвращает:
          - equity_curve (только OOS участки)
          - trades (только OOS)
          - metrics_per_window
          - aggregate_metrics
          - overfitting_score (train Sharpe / test Sharpe — если > 2, 🚩)
    """
```

**Тесты:** `tests/test_ml/test_walk_forward.py` — минимум 10 тестов:
```
[ ] test_splits_data_correctly — правильное количество окон
[ ] test_no_data_leakage — test start > train end + gap
[ ] test_train_ratio — ~70% данных в train
[ ] test_returns_metrics — Sharpe, DD, Win Rate для каждого окна
[ ] test_aggregate_metrics — средние по всем окнам
[ ] test_overfitting_detection — train Sharpe >> test Sharpe → warning
[ ] test_short_data — < min_bars → ошибка / пропуск
[ ] test_predictions_length — OOS predictions совпадают с OOS данными
[ ] test_retrain_interval — модель обновляется каждые N баров
[ ] test_with_ensemble — работает с ensemble из src/ml/ensemble.py
```

**Коммит:** `feat(ml): add walk-forward ML pipeline orchestrator`

---

## Задача 3.2: Полный ML-бэктест — `scripts/run_ml_backtest.py`

```python
# Скрипт:
# 1. Загрузить данные SBER + GAZP + LKOH (2020-2025)
# 2. Feature engineering (все индикаторы + Qlib processors)
# 3. Label generation (triple barrier)
# 4. Walk-forward ML (CatBoost + LightGBM ensemble)
# 5. Сравнить с:
#    a) Buy & hold IMOEX
#    b) EMA crossover (rule-based)
# 6. Вывести HTML-отчёт через src/backtest/report.py
# 7. Monte Carlo CI для OOS метрик
```

**Коммит:** `feat(scripts): add full ML backtest pipeline with walk-forward`

---

# ═══════════════════════════════════════════
# ФАЗА 4: LIVE TRADING
# ═══════════════════════════════════════════

## Задача 4.1: Broker adapter — `src/execution/adapters/tinkoff.py`

```python
"""Tinkoff Invest API adapter.

Uses tinkoff-investments SDK.
Supports: sandbox (paper trading) and production modes.

Methods:
    connect() — подключение к API
    place_order(order: Order) → OrderResult
    cancel_order(order_id: str)
    get_positions() → list[Position]
    get_portfolio() → Portfolio
    get_orderbook(ticker: str) → dict
    subscribe_candles(ticker: str, callback) — WebSocket подписка
"""
```

Должен:
1. Работать в sandbox режиме по умолчанию (paper trading)
2. Конвертировать наши Order/Position модели ↔ Tinkoff SDK модели
3. Учитывать лотность (Tinkoff API принимает лоты, не штуки)
4. Логировать каждый ордер через structlog
5. Retry при сетевых ошибках

**Тесты:** `tests/test_execution/test_tinkoff_adapter.py`
```
[ ] test_connect_sandbox — подключение к sandbox
[ ] test_order_conversion — наш Order → Tinkoff order → наш Order
[ ] test_position_conversion — Tinkoff position → наша Position
[ ] test_lot_conversion — 100 акций SBER = 10 лотов
[ ] test_error_handling — сетевая ошибка → retry
[ ] test_portfolio_snapshot — Portfolio с позициями и кэшем
[ ] test_cancel_order — отмена существующего ордера
```

> Тесты с реальным API пометь `@pytest.mark.integration` и `@pytest.mark.skipif(no_tinkoff_token)`.

**Коммит:** `feat(execution): add Tinkoff Invest API adapter (sandbox + live)`

---

## Задача 4.2: Telegram бот — `src/monitoring/telegram_bot.py`

```python
"""Telegram bot for alerts and manual control.

Alerts:
- Новый сигнал сгенерирован
- Ордер исполнен
- Стоп сработал
- Circuit breaker активирован
- Дневной P&L отчёт

Commands:
- /status — текущие позиции и P&L
- /stop — остановить торговлю
- /start — возобновить торговлю
- /positions — список позиций
- /pnl — P&L за сегодня/неделю/месяц
"""
```

**Тесты:** `tests/test_monitoring/test_telegram.py`
```
[ ] test_format_signal_message — Signal → красивый текст
[ ] test_format_trade_message — TradeResult → текст с P&L
[ ] test_format_pnl_report — дневной отчёт
[ ] test_format_circuit_breaker — предупреждение
[ ] test_command_parsing — /status, /stop, /start
[ ] test_no_token — graceful degradation без токена
[ ] test_message_length — < 4096 символов (лимит Telegram)
```

**Коммит:** `feat(monitoring): add Telegram bot for alerts and control`

---

## Задача 4.3: Paper trading runner — `scripts/paper_trading.py`

```python
"""Paper trading loop.

1. Подключиться к Tinkoff sandbox
2. Загрузить конфиг из settings.yaml
3. Инстанцировать стратегии (EMA crossover + ML ensemble)
4. Запустить loop:
   a. Каждые N минут:
      - Загрузить свежие свечи через MoexISSClient
      - Сгенерировать сигналы
      - Пропустить через risk engine
      - Если сигнал → разместить ордер через Tinkoff sandbox
      - Отправить алерт в Telegram
   b. Не торговать во время клирингов (14:00-14:05, 18:45-19:00)
   c. Закрыть позиции перед концом сессии (18:30 для акций)
   d. Ежедневный P&L отчёт в Telegram в 19:00
5. Circuit breaker: остановка при DD > 5% за день
6. Graceful shutdown по Ctrl+C
"""
```

**Тесты:** `tests/test_e2e/test_paper_trading.py`
```
[ ] test_creates_loop — loop инстанцируется без ошибок
[ ] test_clearing_check — не торгует в 14:00-14:05
[ ] test_session_end — закрывает позиции перед 18:30
[ ] test_circuit_breaker — останавливается при DD > 5%
[ ] test_graceful_shutdown — корректное завершение
```

**Коммит:** `feat(scripts): add paper trading runner with Tinkoff sandbox`

---

## Задача 4.4: Мониторинг — `scripts/dashboard.py` (Streamlit)

```python
"""Streamlit dashboard for monitoring live/paper trading.

Panels:
1. Portfolio overview — total value, cash, exposure %
2. Open positions — table with P&L, stops, time in trade
3. Equity curve — daily chart
4. Drawdown chart — underwater plot
5. Today's trades — list with entry/exit/P&L
6. Strategy performance — Sharpe, DD, Win Rate per strategy
7. Risk status — circuit breaker state, exposure limits
8. Last signals — recent signals with confidence
"""
```

**Коммит:** `feat(monitoring): add Streamlit dashboard`

---

# ═══════════════════════════════════════════
# ФИНАЛЬНАЯ ПРОВЕРКА
# ═══════════════════════════════════════════

После всех 4 фаз:

```bash
# 1. Все тесты
pytest tests/ -v --tb=long 2>&1 | tail -10
# Должно быть: 700+ passed, 0 failed

# 2. Все импорты
python -c "
from src.core.config import Settings, get_config
from src.core.models import Bar, Signal, Order, Position, Portfolio, TradeResult, Side
from src.core.base_strategy import BaseStrategy
from src.strategies.trend.ema_crossover import EMACrossoverStrategy
from src.data.moex_iss import MoexISSClient
from src.ml.walk_forward import WalkForwardML
from src.execution.adapters.tinkoff import TinkoffAdapter
from src.monitoring.telegram_bot import TradingTelegramBot
print('ALL IMPORTS OK')
"

# 3. Lint
ruff check src/ --fix
mypy src/core/ --ignore-missing-imports

# 4. Финальный коммит
git add -A && git commit -m "milestone: all 4 phases complete — ready for paper trading"
```

**Финальный отчёт:**
```
═══════════════════════════════════════
ИТОГИ РЕАЛИЗАЦИИ
═══════════════════════════════════════

Фаза 1 — Фундамент:
[ ] settings.yaml + config loader
[ ] Pydantic модели (7 моделей)
[ ] BaseStrategy ABC + registry
[ ] EMA crossover reference strategy
[ ] E2E тесты (rule-based + ML)

Фаза 2 — Данные:
[ ] MOEX ISS клиент (candles, instruments, orderbook, index)
[ ] Скрипт загрузки истории
[ ] Бэктест на реальных данных SBER

Фаза 3 — ML:
[ ] Walk-forward оркестратор
[ ] Полный ML бэктест с HTML-отчётом

Фаза 4 — Live:
[ ] Tinkoff adapter (sandbox + live)
[ ] Telegram бот (алерты + команды)
[ ] Paper trading runner
[ ] Streamlit dashboard

Всего тестов: [N]
Passed: [N]
Failed: 0

СТАТУС: ГОТОВ К PAPER TRADING
═══════════════════════════════════════
```

---

# ПРАВИЛА (повторение)

1. НЕ ЛОМАЙ 599 существующих тестов
2. Каждая зависимость: install + import check
3. Каждый файл: ≥ 7 тестов с assert
4. Каждый коммит: pytest tests/ = 0 failures
5. MOEX специфика: T+1, лоты, шаг цены, клиринги, ГО
6. ЗАПРЕЩЕНО: pass, TODO, NotImplementedError, "потом доделаем"
7. Существующий код: импортируй, не дублируй
8. Config: всё через settings.yaml, не хардкод
9. Логи: structlog, не print
10. Секреты: .env, не в коде
