# Обзор репозиториев для MOEX Trading Bot

Сводная таблица в конце файла.

---

## 1. ghostfolio/ghostfolio

**URL:** https://github.com/ghostfolio/ghostfolio
**Дата анализа:** 2026-03-21

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: ghostfolio                                 ║
║  URL: github.com/ghostfolio/ghostfolio                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐        3/5                ║
║  Качество кода:        ⭐⭐⭐⭐⭐    5/5                ║
║  Применимость к MOEX:  ⭐⭐          2/5                ║
║  Risk management:      ⭐⭐⭐        3/5 (портфельный)  ║
║  Стратегии:            ⭐            0/5 (нет)          ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ (как ИДЕИ, не код — AGPL!):          ║
║  1. X-Ray Rules → src/risk/rules/ — кластерный анализ   ║
║  2. DataProvider контракт → src/data/ — унификация API  ║
║  3. FX History Cache → src/data/ — курсы валют          ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. AGPL v3 — нельзя копировать код → только идеи       ║
║  2. Не торговая система — 0 стратегий, 0 бэктестинга    ║
║  3. TypeScript/Angular — стек не совместим с нашим       ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Написать src/risk/rules/ с нуля,        ║
║  вдохновившись паттерном X-Ray (6 часов)                ║
╚══════════════════════════════════════════════════════════╝
```

### Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | DataProvider Interface | `services/data-provider/interfaces/` | ⭐⭐⭐⭐ | Низкое | Контракт для подключения провайдеров данных |
| 2 | Exchange Rate Service | `services/exchange-rate-data/` | ⭐⭐⭐⭐ | Среднее | Мультивалютная конвертация с историей |
| 3 | X-Ray Rules (12 правил) | `models/rules/` | ⭐⭐⭐⭐ | Низкое | Анализ диверсификации портфеля |
| 4 | Rule\<T\> абстракция | `models/rule.ts` | ⭐⭐⭐⭐ | Низкое | Паттерн для расширяемых проверок |
| 5 | Portfolio Calculator (ROAI) | `portfolio/calculator/roai/` | ⭐⭐⭐ | Высокое | Расчёт доходности с валютным эффектом |
| 6 | Yahoo Finance Service | `data-provider/yahoo-finance/` | ⭐⭐⭐ | Среднее | Обёртка над yahoo-finance2 |

### Планы интеграции (идеи, не копирование — AGPL!)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Risk Rules Engine (по мотивам X-Ray)
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 6 часов
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из models/rules/ (НЕ копируем — AGPL!)
КУДА: src/risk/rules/
ЧТО НАПИСАТЬ С НУЛЯ:
- BaseRule(ABC) с evaluate() → RuleResult
- ConcentrationRule — макс. доля одного инструмента
- CurrencyClusterRule — валютная диверсификация
- SectorClusterRule — секторная концентрация
- DrawdownRule — макс. просадка
- Настраиваемые пороги через Pydantic Settings
ТЕСТЫ:
- Unit: каждое правило с edge cases
- Integration: RulesEngine.evaluate_all()
ЗАВИСИМОСТИ: нет новых
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Exchange Rate History Cache
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 3 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из ExchangeRateDataService
КУДА: src/data/exchange_rates.py
ЧТО НАПИСАТЬ С НУЛЯ:
- Кэш курсов RUB/USD, EUR/RUB через MOEX ISS
- getExchangeRatesByCurrency() аналог
- Конвертация P&L в базовую валюту (RUB)
ТЕСТЫ: Unit: конвертация с историей
ЗАВИСИМОСТИ: нет
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 2. jesse-ai/jesse

**URL:** https://github.com/jesse-ai/jesse
**Дата анализа:** 2026-03-21

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: jesse-ai/jesse                             ║
║  URL: github.com/jesse-ai/jesse                          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ИНТЕГРИРОВАТЬ (частично)                      ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐⭐      4/5                ║
║  Качество кода:        ⭐⭐⭐⭐      4/5                ║
║  Применимость к MOEX:  ⭐⭐⭐        3/5                ║
║  Risk management:      ⭐⭐⭐        3/5                ║
║  Стратегии:            ⭐⭐          2/5 (фреймворк)    ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ:                                       ║
║  1. metrics.py → src/backtest/metrics.py                ║
║     — 10+ метрик (Sharpe/Sortino/CVaR/Serenity/...)    ║
║  2. optimize_mode/ → src/backtest/optimizer.py           ║
║     — Optuna + fitness + train/test split               ║
║  3. monte_carlo/ → src/backtest/monte_carlo.py           ║
║     — Trade shuffling + candle noise + bootstrap        ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. Крипто-ориентирован — T+0, 24/7, нет лотности      ║
║     → Митигация: адаптировать под MOEX параметры        ║
║  2. Нет встроенного slippage model (только stop→market) ║
║     → Митигация: добавить tick-based slippage           ║
║  3. NumPy arrays вместо DataFrames                       ║
║     → Митигация: обернуть в Polars адаптер              ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Копировать metrics.py, адаптировать     ║
║  periods=252, добавить Profit/Recovery Factor (4ч)      ║
╚══════════════════════════════════════════════════════════╝
```

### Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | **Metrics system** | `services/metrics.py` (464 строки) | ⭐⭐⭐⭐⭐ | Низкое | Sharpe, Sortino, Calmar, Omega, Serenity, CAGR, Max DD, CVaR, streaks |
| 2 | **Strategy ABC** | `strategies/Strategy.py` | ⭐⭐⭐⭐⭐ | Среднее | Жизненный цикл стратегии, ордера, partial fills |
| 3 | **Indicators (175шт)** | `indicators/*.py` | ⭐⭐⭐⭐⭐ | Низкое | Все основные индикаторы, NumPy-реализация |
| 4 | **Optimization (Optuna)** | `modes/optimize_mode/` | ⭐⭐⭐⭐ | Среднее | Train/test split, fitness function, walk-forward |
| 5 | **Monte Carlo** | `modes/monte_carlo_mode/`, `research/monte_carlo/` | ⭐⭐⭐⭐ | Среднее | Trade shuffling, candle noise, bootstrap |
| 6 | **Backtest engine** | `modes/backtest_mode.py` | ⭐⭐⭐⭐ | Высокое | Event-driven loop без lookahead bias |
| 7 | **Position model** | `models/Position.py` | ⭐⭐⭐⭐ | Низкое | ROI, PnL, liquidation, leverage |
| 8 | **Order model** | `models/Order.py` | ⭐⭐⭐ | Низкое | Статусы, partial fills, queued orders |
| 9 | **ML integration** | `strategies/Strategy.py` (record_features) | ⭐⭐⭐ | Среднее | Паттерн для сбора ML-фичей из бэктеста |
| 10 | **Exchange drivers** | `modes/import_candles_mode/drivers/` | ⭐⭐ | — | Крипто-специфичны, не для MOEX |

### Планы интеграции (MIT — можно копировать)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Comprehensive Metrics Module
ПРИОРИТЕТ: 🔴 ВЫСОКИЙ
ОЦЕНКА ВРЕМЕНИ: 4 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: jesse/services/metrics.py (MIT — можно копировать)
КУДА: src/backtest/metrics.py
ЧТО СКОПИРОВАТЬ/АДАПТИРОВАТЬ:
- sharpe_ratio() — адаптировать periods=252
- sortino_ratio() с autocorrelation penalty (smart sortino)
- calmar_ratio() (CAGR / Max DD)
- omega_ratio() (с threshold)
- serenity_index() (returns / ulcer_index * pitfall)
- max_drawdown()
- calculate_max_underwater_period()
- cagr()
- conditional_value_at_risk() (expected shortfall)
- autocorr_penalty() — для smart metrics
- trades() — полный набор trade-level метрик
ЧТО АДАПТИРОВАТЬ:
- pd.Series → Polars (или оставить Pandas для metrics)
- periods=365 → 252 (акции MOEX) или параметризовать
- Добавить Profit Factor (gross_profit / abs(gross_loss))
- Добавить Recovery Factor (net_profit / max_dd)
ТЕСТЫ:
- Unit: каждая метрика с known values
- Edge cases: 0 trades, 1 trade, all wins, all losses
ЗАВИСИМОСТИ: numpy, pandas (уже есть)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Optuna Strategy Optimizer
ПРИОРИТЕТ: 🔴 ВЫСОКИЙ
ОЦЕНКА ВРЕМЕНИ: 6 часов
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: jesse/modes/optimize_mode/ (MIT)
КУДА: src/backtest/optimizer.py
ЧТО СКОПИРОВАТЬ/АДАПТИРОВАТЬ:
- fitness.py → get_fitness() логика
- 7 objective functions (sharpe, calmar, sortino, omega, serenity, smart*)
- Training/testing split
- total_effect_rate * ratio_normalized scoring
ЧТО АДАПТИРОВАТЬ:
- Вместо jesse isolated_backtest → наш engine
- Ray → joblib (проще для первой версии)
- Добавить walk-forward (rolling window)
- Добавить MOEX-специфичные периоды (без клирингов)
ТЕСТЫ:
- Unit: fitness function с mock metrics
- Integration: optimize simple strategy
ЗАВИСИМОСТИ: optuna (pip install)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Monte Carlo Simulation
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 5 часов
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: jesse/research/monte_carlo/ (MIT)
КУДА: src/backtest/monte_carlo.py
ЧТО СКОПИРОВАТЬ/АДАПТИРОВАТЬ:
- monte_carlo_trades() — перетасовка сделок
- GaussianNoiseCandlesPipeline — шум на свечах
- MovingBlockBootstrapCandlesPipeline — блочный бутстрэп
ЧТО АДАПТИРОВАТЬ:
- Ray → multiprocessing Pool (проще)
- NumPy array candles → Polars DataFrame
- Добавить confidence intervals (5%, 50%, 95%)
ТЕСТЫ:
- Unit: distribution of shuffled results
ЗАВИСИМОСТИ: scipy (уже есть)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: 175 Technical Indicators (выборочно)
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 2 часа (cherry-pick)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: jesse/indicators/ (MIT)
КУДА: src/indicators/custom/
ЧТО СКОПИРОВАТЬ (выборочно):
- squeeze_momentum.py — TTM Squeeze
- supertrend.py — SuperTrend
- waddah_attr_explosion.py — Waddah Attar Explosion
- support_resistance_with_break.py — SR levels
- damiani_volatmeter.py — Damiani volatility
- voss.py, bandpass.py, reflex.py — Ehlers DSP indicators
ЧТО АДАПТИРОВАТЬ:
- jesse ta.* API → наш BaseIndicator интерфейс
- NumPy arrays → Polars Series
ТЕСТЫ: Unit: known values сравнение
ЗАВИСИМОСТИ: numpy (уже есть)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 3. kernc/backtesting.py

**URL:** https://github.com/kernc/backtesting.py
**Дата анализа:** 2026-03-21

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: kernc/backtesting.py                       ║
║  URL: github.com/kernc/backtesting.py                    ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐        3/5                ║
║  Качество кода:        ⭐⭐⭐⭐⭐    5/5                ║
║  Применимость к MOEX:  ⭐⭐          2/5                ║
║  Risk management:      ⭐⭐          2/5                ║
║  Стратегии:            ⭐            0/5 (фреймворк)    ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ (как ИДЕИ — AGPL!):                  ║
║  1. Alpha+Beta → src/backtest/metrics.py — CAPM метрики ║
║  2. SQN+Kelly → src/backtest/metrics.py — качество      ║
║  3. crossover/barssince → src/indicators/utils.py       ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. AGPL v3 — нельзя копировать код                     ║
║  2. Нет slippage/лотности/MOEX-специфики                ║
║  3. Grid search optimizer уступает Optuna                ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Дописать Alpha/Beta/SQN/Kelly в        ║
║  существующий metrics.py (2 часа, с нуля)               ║
╚══════════════════════════════════════════════════════════╝
```

### Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | Alpha + Beta (CAPM) | `_stats.py:156-165` | ⭐⭐⭐⭐ | Низкое | Jensen Alpha, Beta через cov matrix |
| 2 | SQN | `_stats.py:181` | ⭐⭐⭐⭐ | Низкое | System Quality Number |
| 3 | Kelly Criterion | `_stats.py:182` | ⭐⭐⭐⭐ | Низкое | Optimal position fraction |
| 4 | Geometric mean | `_stats.py:30-34` | ⭐⭐⭐ | Низкое | Correct compound return |
| 5 | crossover/barssince | `lib.py:73-115` | ⭐⭐⭐ | Низкое | Strategy utilities |
| 6 | resample_apply | `lib.py:207+` | ⭐⭐⭐ | Среднее | Multi-timeframe |

### Планы интеграции (AGPL — писать с нуля)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Metrics Expansion (Alpha, Beta, SQN, Kelly)
ПРИОРИТЕТ: 🔴 ВЫСОКИЙ
ОЦЕНКА ВРЕМЕНИ: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из _stats.py (НЕ копируем — AGPL!)
КУДА: src/backtest/metrics.py (дополнить TradeMetrics)
ЧТО НАПИСАТЬ С НУЛЯ:
- alpha_beta(equity_returns, benchmark_returns) → (alpha, beta)
- sqn(pnls) → sqrt(N) * mean(PnL) / std(PnL)
- kelly_criterion(win_rate, avg_win_loss_ratio) → optimal fraction
- geometric_mean(returns) → exp(mean(log(1+r))) - 1
- exposure_time(entry_bars, exit_bars, total_bars) → float
- buy_and_hold_return(close_prices) → float
ТЕСТЫ: Unit с known values
ЗАВИСИМОСТИ: нет
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Strategy Utilities (crossover, barssince)
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 1 час
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из lib.py (НЕ копируем — AGPL!)
КУДА: src/indicators/utils.py
ЧТО НАПИСАТЬ С НУЛЯ:
- crossover(series1, series2) → bool
- barssince(condition) → int
- quantile_rank(series) → float
ТЕСТЫ: Unit
ЗАВИСИМОСТИ: нет
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. StockSharp/StockSharp

**URL:** https://github.com/StockSharp/StockSharp
**Дата анализа:** 2026-03-21

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: StockSharp/StockSharp                      ║
║  URL: github.com/StockSharp/StockSharp                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ПРОПУСТИТЬ                                    ║
║                                                          ║
║  Общая ценность:       ⭐⭐          2/5                ║
║  Качество кода:        ⭐⭐⭐⭐      4/5                ║
║  Применимость к MOEX:  ⭐⭐⭐⭐      4/5 (Tinkoff, рус) ║
║  Risk management:      ⭐⭐⭐        3/5                ║
║  Стратегии:            ⭐⭐          2/5 (quoting only)  ║
║                                                          ║
║  ПРИЧИНА ПРОПУСКА:                                       ║
║  C# (.NET) — полностью другой стек. 1809 .cs файлов,   ║
║  21 .py файл (аналитика). Портировать нереально.        ║
║  Идеи хорошие, но всё нужно писать с нуля на Python.    ║
║                                                          ║
║  ПОЛЕЗНЫЕ ИДЕИ (для вдохновения):                       ║
║  1. CommissionRule pattern — 13 правил комиссий          ║
║     (по обороту, по кол-ву, по тикеру, по типу)        ║
║  2. ProtectiveController — SL/TP с trailing и timeout   ║
║  3. QuotingProcessor — 9 стратегий котирования           ║
║     (BestByPrice, BestByVolume, TWAP, VWAP, Level)     ║
║  4. GeneticOptimizer — генетический алгоритм + fitness  ║
║  5. MatchingEngine — эмулятор биржи с OrderBook         ║
║  6. 190 индикаторов на C#                               ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Нет. Стек не совместим.                 ║
╚══════════════════════════════════════════════════════════╝
```

### Краткий анализ

- **Стек:** C# .NET, WPF/Avalonia/MAUI, 1809 .cs файлов
- **Лицензия:** Apache 2.0 (можно использовать)
- **Активность:** Коммит 20 марта 2026 — живой проект
- **MOEX:** Есть коннектор Tinkoff, знакомы с MOEX (логотипы)
- **Архитектура:** Отличная — модульная, паттерны Strategy/Rule/Adapter
- **Стратегии котирования:** BestByPrice, BestByVolume, LastTrade, Level, Limit, Market, TheorPrice, Volatility — 9 типов. Это уникально для нашего проекта.
- **Комиссии:** 13 правил (по обороту, по кол-ву ордеров, по кол-ву сделок, по цене сделки, по типу инструмента, по board code) — хорошая архитектура ICommissionRule
- **MatchingEngine:** Полная эмуляция биржи с OrderBook, MarginController, StopOrderManager
- **Но:** Всё на C#, портирование слишком трудозатратно

### Карта ценности

| # | Компонент | Ценность | Проблема |
|---|-----------|----------|----------|
| 1 | QuotingProcessor (9 типов) | ⭐⭐⭐ | C# — надо писать с нуля |
| 2 | CommissionRule (13 правил) | ⭐⭐⭐ | C# — наш cost_model проще |
| 3 | MatchingEngine | ⭐⭐⭐ | C# — огромный объём |
| 4 | ProtectiveController | ⭐⭐⭐ | C# — trailing+timeout идея |
| 5 | GeneticOptimizer | ⭐⭐ | У нас Optuna лучше |
| 6 | 190 индикаторов | ⭐⭐ | C#, у нас есть jesse (175) |

---

## 6. edtechre/pybroker

**URL:** https://github.com/edtechre/pybroker
**Дата анализа:** 2026-03-21

### 2.1 Общее

PyBroker — Python-фреймворк для алго-трейдинга с фокусом на ML-стратегии. Написан Edward West, 25081 строк (11.7K src + 12.9K tests). Основная задача — дать возможность разрабатывать стратегии на базе ML-моделей с правильной walk-forward валидацией, чтобы избежать переоптимизации. Движок bar-by-bar (event-driven), не vectorized — это медленнее, но точнее моделирует реальное исполнение. Все финансовые расчёты через Python `Decimal` — исключает float-ошибки при P&L.

- **Стек:** Python 3.9+, NumPy 2.0+, Numba 0.64+ (JIT-ускорение eval/vect), Pandas 2.2+, diskcache (кэш данных), joblib (параллелизм), alpaca-py, yfinance, yahooquery, akshare
- **Лицензия:** ⚠️ **Apache 2.0 with Commons Clause** — можно использовать, модифицировать, форкать. НЕЛЬЗЯ продавать как продукт или SaaS. Для внутреннего использования и вдохновения идеями — подходит. Для копирования кода в коммерческий продукт — рискованно, лучше писать с нуля.
- **Активность:** Последний коммит 4 марта 2026, до этого регулярные обновления. Один основной автор. Проект живой, но не массово поддерживаемый.
- **Популярность:** Средняя для ниши, используется в образовательных целях и индивидуальными трейдерами. По issues — реальные пользователи запускают стратегии.
- **Документация:** Sphinx-docs на pybroker.com, Jupyter notebooks с примерами (Quick Start, ML Trading, Custom Data, Walk-forward), Google-style docstrings на каждой публичной функции. Качество документации — **отличное**, одно из лучших среди анализированных репо.
- **Тесты:** 12.9K LOC тестов, pytest + pytest-cov + pytest-randomly + pytest-xdist. Тестовые файлы для каждого модуля. Покрытие оценочно ~75%. Тестируется: portfolio P&L, stops, fees, order execution, walk-forward, bootstrap, indicators, caching. Это **самое протестированное** репо из всех анализированных.
- **CI/CD:** GitHub Actions (Python 3.9-3.12), tox, mypy strict mode, ruff linter.

### 2.2 Архитектура и структура кода

**Общая архитектура:** Модульная, с чистым разделением ответственности. Текстовая схема зависимостей:

```
strategy.py (движок бэктеста)
  ├── portfolio.py (позиции, P&L, ордера, стопы)
  │   └── common.py (Entry, Trade, Position, FeeMode, Order — dataclasses)
  ├── context.py (ExecContext — API для стратегий)
  │   └── scope.py (ColumnScope, IndicatorScope, PredictionScope — данные)
  ├── model.py (ML-модели, walk-forward training)
  ├── indicator.py (регистрация и вычисление индикаторов)
  ├── eval.py (метрики, bootstrap CI)
  │   └── vect.py (Numba-ускоренные функции)
  ├── data.py (YFinance, Alpaca, AKShare — провайдеры данных)
  │   └── cache.py (diskcache — кэширование данных на диск)
  ├── config.py (StrategyConfig — frozen dataclass)
  ├── slippage.py (модель проскальзывания)
  └── log.py (logging с цветной консолью)
```

**Паттерны:** Scope Pattern (изоляция данных по символу/индикатору/модели), Strategy Pattern (exec_fn — пользовательская функция), Factory (indicator/model registration через декораторы), FIFO (учёт лотов в позициях).

**Разделение ответственности:** Чёткое. Data → Indicators → Models → Strategy → Portfolio → Eval. Каждый модуль импортирует только от зависимостей, нет циклов. `context.py` — единственный мост между пользовательским кодом и движком.

**Конфигурация:** `StrategyConfig` — frozen dataclass с 18 полями (`config.py:16-104`). Все параметры типизированы. Нет хардкода — всё через конфиг. Пример: `buy_delay=1` (default), `fee_mode=FeeMode.ORDER_PERCENT`, `bars_per_year=252`.

**Логирование:** Собственный logger (`log.py`, 473 строки) с цветной консолью, уровнями, форматированием прогресса. Не structlog, но качественный.

**Обработка ошибок:** Валидация входных данных в каждой публичной функции (`_verify_input` в portfolio.py:454-465). Raise ValueError с конкретным сообщением. Нет голых except. Пример: `if shares < 0: raise ValueError(f"Shares cannot be negative: {shares}")`.

**Type hints:** Полные (~95%). Union, Optional, Literal, NDArray. Mypy strict mode в CI. Один из лучших примеров типизации среди Python trading frameworks.

**Docstrings:** Google-style на КАЖДОЙ публичной функции и классе. С описанием Args, Returns, Attributes. Sphinx-совместимые. Оценка: 98% покрытия.

### 2.3 Торговые стратегии

**Стратегий-примеров в репо нет** — это фреймворк. Но API для создания стратегий уникально мощный и заслуживает детального разбора, потому что содержит паттерны которых нет у jesse и backtesting.py.

```
СТРАТЕГИЯ: ExecContext API (фреймворк для пользовательских стратегий)
ТИП: универсальный — rule-based + ML
ФАЙЛ: src/pybroker/context.py (1425 строк)

ПРИНЦИП РАБОТЫ:
Пользователь пишет функцию exec_fn(ctx), которая вызывается на каждом баре
для каждого инструмента. Через объект ctx доступны: текущие OHLCV, индикаторы,
ML-предсказания, состояние портфеля, открытые позиции. Пользователь устанавливает
ctx.buy_shares / ctx.sell_shares для входа/выхода. Уникальные фичи: ctx.hold_bars
автоматически закрывает позицию через N баров (time-stop), ctx.score позволяет
ранжировать инструменты для position allocation при ограниченном числе позиций
(max_long_positions), ctx.session — персистентный dict между барами для хранения
состояния стратегии.

ДОСТУПНЫЕ СТОПЫ В КОНТЕКСТЕ (context.py:850-950):
- ctx.stop_loss = 5.0            # абсолютный стоп в деньгах
- ctx.stop_loss_pct = 2.0        # стоп в % от entry
- ctx.stop_profit = 10.0         # тейк в деньгах
- ctx.stop_profit_pct = 5.0      # тейк в %
- ctx.stop_trailing = 3.0        # trailing stop в деньгах
- ctx.stop_trailing_pct = 1.5    # trailing stop в %
- ctx.hold_bars = 5              # авто-выход через 5 баров

КЛЮЧЕВЫЕ ОТЛИЧИЯ ОТ JESSE:
1. hold_bars — time-stop на уровне контекста (у jesse нет)
2. score — ранжирование для position allocation (у jesse нет)
3. session — персистентное состояние (у jesse через self.vars, менее формализовано)
4. buy_delay/sell_delay — задержка исполнения (у jesse — immediate)
5. preds() — прямой доступ к ML-предсказаниям (у jesse через record_features/load_model)

ОЦЕНКА:
Это один из лучших API для написания стратегий среди Python-фреймворков.
Комбинация rule-based и ML подхода в одном контексте — мощная идея.
Для MOEX отлично подходит паттерн hold_bars (закрытие перед клирингом)
и score (ранжирование SBER vs GAZP vs LKOH по ML-скорам).
Слабость: нет поддержки лотности и шага цены — ctx.buy_shares = 100 может
означать 100 акций, что для SBER = 10 лотов, но для VTBR = 0.01 лота.

ПРИМЕНИМОСТЬ К MOEX:
Паттерн ctx.session полезен для хранения состояния между барами (накопленная
информация о клирингах, сессиях). hold_bars можно адаптировать для закрытия
перед клирингом 14:00. score полезен для ранжирования инструментов портфеля.
Нужно добавить: лотность, шаг цены, клиринги.
```

### 2.4 Работа с данными

Поддерживаются три встроенных провайдера: **YFinance** (yfinance + yahooquery), **Alpaca** (alpaca-py с API key), **AKShare** (китайские рынки). Плюс базовый класс `DataSource` для кастомных провайдеров — нужно реализовать `_fetch_data()` → DataFrame с колонками symbol/date/open/high/low/close/volume/vwap. Кэширование через `diskcache` на диск — при повторных запусках данные берутся из кэша мгновенно. Схема хранения: ключ = (symbol, timeframe_seconds, start_date, end_date, adjust), значение = pandas DataFrame.

Пайплайн данных: `DataSource.query()` → проверка кэша → fetch с биржи → сохранение в кэш → merge DataFrame. Индикаторы вычисляются после загрузки данных, тоже кэшируются (`IndicatorScope`). ML-предсказания кэшируются через `ModelScope`.

**Адаптация к MOEX ISS:** Нужно написать класс `MoexISSDataSource(DataSource)` — реализовать `_fetch_data(symbols, start_date, end_date)` через `https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{symbol}/candles.json`. Оценка: ~200 строк, ~4 часа с тестами. Формат MOEX ISS (candles: open/close/high/low/volume + begin timestamp) хорошо маппится на pybroker формат.

**Real-time:** Нет WebSocket. Только исторические данные для бэктеста. Для live нужен отдельный слой.

### 2.5 Risk Management

**Position sizing:** Не встроен формально. Пользователь сам рассчитывает `ctx.buy_shares` в exec_fn. Есть `ctx.score` для ранжирования — при max_long_positions=5 портфель выбирает top-5 по score. Но Kelly, ATR-based, vol-target — нет.

**Stop-loss:** Три типа — фиксированный (в деньгах), процентный (от entry), trailing (следует за ценой). Задаются через `ctx.stop_loss`, `ctx.stop_loss_pct`, `ctx.stop_trailing_pct`. Проверяются каждый бар в `portfolio.check_stops()`. Можно задать exit_price (по какой цене исполнять стоп: OPEN/CLOSE/MIDDLE).

**Take-profit:** Аналогично стопу: `ctx.stop_profit`, `ctx.stop_profit_pct`. Limit price для отложенного тейка через `ctx.stop_profit_limit`.

**Exposure control:** `max_long_positions` / `max_short_positions` в конфиге. Нет лимитов по инструменту, сектору, валюте. Нет correlation-aware position sizing.

**Drawdown protection:** Нет circuit breaker. Нет daily loss limit. Нет portfolio-level DD stop. Если позиция падает на 50% — портфель продолжает торговать. Для live-торговли на MOEX это критичный пробел — при гэпе на открытии (MOEX гэпит часто из-за ночных новостей) стоп может сработать далеко от заданной цены, а портфель не имеет глобальной защиты.

### 2.6 Execution

Движок bar-by-bar. Ордера размещаются через `ctx.buy_shares` / `ctx.sell_shares`. Ключевая особенность — **delay исполнения**: `buy_delay=1` (default) означает что сигнал на баре N исполняется на баре N+1. Это предотвращает lookahead bias — стратегия не может купить по цене бара на котором приняла решение. Fill price берётся из следующего бара по конфигурируемому PriceType: OPEN (реалистично), CLOSE (оптимистично), MIDDLE (компромисс), VWAP (объёмно-взвешенная средняя).

**Slippage:** `RandomSlippageModel(min_pct=0.1, max_pct=0.5)` — уменьшает КОЛИЧЕСТВО акций на случайный %, а не изменяет ЦЕНУ. Это нереалистично: на MOEX проскальзывание = сдвиг цены на N тиков, а не уменьшение объёма. Наш подход (`slippage_ticks` в cost_model) правильнее.

**Smart execution:** Нет TWAP/VWAP/iceberg. Все ордера исполняются как market orders. Для крупных позиций на MOEX (>1% дневного оборота) это приведёт к значительному market impact, который не моделируется.

**Broker adapters:** Только для данных (Alpaca, YFinance). Нет live-торговли. Нет отправки ордеров на биржу.

### 2.7 Бэктестинг

**Движок:** Собственный, bar-by-bar event-driven (`strategy.py:142-380`, функция `backtest_executions`). Для каждого бара: обновляются данные → проверяются стопы → исполняются отложенные ордера → вызывается пользовательский exec_fn → применяется slippage → планируются новые ордера. Warmup: первые N баров пропускаются (для индикаторов).

**Комиссии:** 4 режима через `FeeMode` (config.py:21-30): ORDER_PERCENT (% от оборота), PER_ORDER (фикс за ордер), PER_SHARE (за акцию), custom Callable. Пример для MOEX: `FeeMode.ORDER_PERCENT` с `fee_amount=0.01` = 0.01% от оборота — это правильно для акций. Для фьючерсов нужен PER_ORDER с 2 RUB — тоже возможно. Callable позволяет реализовать любую модель (наш `InstrumentTypeRule` аналог).

**Walk-forward:** `strategy.walkforward(windows=5, lookahead=1, train_size=0.7)`. Данные разбиваются на 5 окон, в каждом 70% train / 30% test с gap в 1 бар для предотвращения утечки. ML-модели переобучаются на каждом окне. Это правильный подход — единственный фреймворк из проанализированных с **встроенным** walk-forward для ML.

**Bootstrap CI:** BCa bootstrap (`eval.py:42-141`) с Numba JIT. 10000 bootstrap samples по умолчанию. Bias-corrected and accelerated — статистически корректнее чем percentile bootstrap (который мы используем в monte_carlo.py). Вычисляет CI для Sharpe, Profit Factor, Max Drawdown. Уникальная фича среди всех проанализированных фреймворков.

**Out-of-sample:** Через walk-forward — каждое test window = OOS. Нет отдельного "holdout" периода за пределами walk-forward.

**Визуализация:** Нет встроенных графиков. Пользователь получает DataFrame с equity curve и рисует сам. Слабее чем backtesting.py (Bokeh) и jesse (web UI).

**Benchmark:** Нет встроенного сравнения с buy&hold или индексом.

### ШАГ 3: Красные флаги 🚩

```
1. Lookahead bias:
   [✅] buy_delay=1 (default) в config.py:90 гарантирует что ордер
   исполняется на СЛЕДУЮЩЕМ баре. strategy.py:355: delay=config.buy_delay.
   Walk-forward с lookahead=1 в model training (strategy.py:664-680).
   Корректная защита.

2. Survivorship bias:
   [⚠️] Фреймворк не контролирует — пользователь сам приносит данные.
   Если пользователь загружает текущий S&P 500 через YFinance, делистинги
   не включены. Для MOEX: нужно включать MFON, AFLT-old и др.

3. Нереалистичные комиссии:
   [⚠️] По умолчанию fee_mode=None (config.py:84) → комиссия 0%.
   Это опасный default — пользователь должен явно задать комиссии.
   Для MOEX: fee_mode=FeeMode.ORDER_PERCENT, fee_amount=0.01.
   Кто забудет — получит завышенные результаты.

4. Нет проскальзывания:
   [🚩] slippage.py:47-58: RandomSlippageModel уменьшает КОЛИЧЕСТВО
   акций, а не сдвигает ЦЕНУ. На реальном рынке проскальзывание =
   сдвиг цены исполнения на N тиков от заявленной. Модель pybroker
   нереалистична. Пример: ctx.buy_shares=100, slippage 1% → покупается
   99 акций по заявленной цене. Реально: покупается 100 акций по цене
   entry + 2 тика.

5. Overfitting:
   [✅] Walk-forward с 5 окнами и lookahead gap = хорошая защита.
   Bootstrap CI позволяют видеть разброс метрик. Но walk-forward
   доступен только для ML-моделей, rule-based стратегии не защищены.

6. Утечка train→test:
   [✅] strategy.py:726: test_start = train_end + lookahead.
   Gap между train и test предотвращает утечку. Lookahead >= 1.

7. Нет OOS:
   [⚠️] Walk-forward test windows = quasi-OOS, но нет отдельного
   holdout периода за пределами walk-forward. Для финальной валидации
   стратегии нужен отдельный holdout set.

8. Нет лотности:
   [🚩] portfolio.py не проверяет лотность. ctx.buy_shares = 15 для
   SBER (лот=10) создаст позицию 15 акций, что невозможно на MOEX.
   enable_fractional_shares=False (config.py:85) только запрещает
   дробные акции (0.5), но не проверяет кратность лоту.

9. Нет шага цены:
   [🚩] round_fill_price=True (config.py:86) округляет до цента (0.01),
   но на MOEX шаг цены разный: SBER=0.01, Si=1, LKOH=0.5. Нет
   инструмент-специфичного рounding.

10. Игнор MOEX-специфики:
    [🚩] Нет T+1 settlement — при продаже акций деньги доступны сразу.
    Нет клирингов (14:00-14:05, 18:45-19:00) — ордера могут
    исполняться в клиринговый перерыв. Нет ГО для фьючерсов.
    Нет вечерней сессии. Нет аукционов открытия/закрытия.

11. Нереалистичные результаты:
    [✅] Bootstrap CI с 10000 samples показывает реальный разброс.
    Но по умолчанию комиссии=0, что завышает результаты на ~5-15%
    годовой доходности для активных стратегий.
```

### ШАГ 4: Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | **BCa Bootstrap CI** | `eval.py:42-141` | ⭐⭐⭐⭐ | Среднее | Bias-corrected accelerated bootstrap — точнее percentile CI. Jackknife для acceleration. Numba-ускоренный. Уникально среди проанализированных. |
| 2 | **MAE/MFE per trade** | `portfolio.py` Entry/Trade dataclass | ⭐⭐⭐⭐ | Низкое | Max Adverse/Favorable Excursion на каждой сделке. Позволяет оценить качество входов: если MFE >> MAE, входы хорошие. |
| 3 | **Walk-forward ML split** | `strategy.py:649-730` | ⭐⭐⭐⭐ | Среднее | Правильная реализация walk-forward для ML с lookahead gap. 5 окон, 70/30 train/test, gap=1 бар. |
| 4 | **EvalMetrics dataclass** | `eval.py:684-791` | ⭐⭐⭐⭐ | Низкое | 40+ метрик в одном frozen dataclass. Включает Ulcer Index, UPI, equity R², annual_volatility — того чего нет у нас. |
| 5 | **Relative Entropy** | `eval.py:418-447` | ⭐⭐⭐ | Низкое | Информационная энтропия доходностей — мера "хаотичности" результатов. Высокая энтропия = непредсказуемые доходности. |
| 6 | **Equity R²** | `eval.py:645-661` | ⭐⭐⭐ | Низкое | R² линейной регрессии equity curve. 1.0 = идеально стабильный рост. Полезно для скрининга стратегий. |
| 7 | **FeeMode callable** | `portfolio.py:423-452` | ⭐⭐⭐ | Низкое | Custom fee function через Callable. Гибче наших правил — можно реализовать любую модель комиссий. |
| 8 | **Decimal P&L** | `portfolio.py` (весь модуль) | ⭐⭐⭐ | Высокое | Точные финрасчёты через Decimal. Исключает float drift. Для production-бэктеста важно, но у нас пока float достаточен. |
| 9 | **Slippage ABC** | `slippage.py:16-27` | ⭐⭐ | Низкое | Абстракция правильная (SlippageModel ABC), но реализация (shares, не цена) — неправильная для MOEX. |
| 10 | **diskcache** | `cache.py` (244 строки) | ⭐⭐ | Низкое | Кэширование данных и индикаторов на диск. У нас Redis — мощнее. |

### ШАГ 5: Полезность для нашего проекта

#### 5.1 Новые стратегии для ансамбля
Стратегий в репо нет. Но паттерн `ctx.score` для ранжирования инструментов по ML-скорам — мощная идея для нашего portfolio.py (мета-ансамбля). Можно применить: каждая стратегия ансамбля выдаёт score для каждого тикера MOEX (SBER, GAZP, LKOH...), portfolio.py выбирает top-N по агрегированному score и распределяет капитал. Ожидаемый Sharpe: 1.2-1.8 (за счёт диверсификации + ранжирования). На MOEX top-10 ликвидных акций достаточно для такого подхода.

#### 5.2 Улучшение существующих модулей
Наш `src/backtest/metrics.py` можно расширить тремя компонентами из pybroker:
1. **BCa Bootstrap** (`eval.py:42-141`) — заменить наш percentile bootstrap в monte_carlo.py на BCa. Bias correction через z0 = Φ⁻¹(proportion below θ̂) и acceleration через jackknife значительно точнее при малых выборках и ассиметричных распределениях.
2. **MAE/MFE** (portfolio.py Entry dataclass) — добавить в TradeMetrics: avg_mae, avg_mfe, mae_mfe_ratio. Позволяет оценить: если средняя MFE = 5% а средняя MAE = 2%, входы хорошие (стратегия быстро уходит в плюс). Если наоборот — входы плохие (стратегия сначала уходит в минус).
3. **Equity R²** (`eval.py:645-661`) + UPI (`eval.py:484-499`) — R² equity curve показывает стабильность роста (1.0 = идеально ровная equity). UPI = средний return / Ulcer Index — лучше Sharpe при наличии длинных просадок.

#### 5.3 Новые идеи и подходы
1. **Delay-based lookahead prevention** — buy_delay=1 проще и надёжнее чем наш подход (мы не моделируем задержку). Стоит добавить в наш backtest engine.
2. **FIFO lot accounting с MAE/MFE** — каждый лот (Entry) отслеживается отдельно, с максимальной бумажной просадкой и прибылью. Для налоговой отчётности НДФЛ в России (FIFO обязателен) это критично.
3. **Score-based position allocation** — при max_positions=N, инструменты ранжируются по score и входят только лучшие. Можно комбинировать с нашим risk rules engine.

#### 5.4 Антипаттерны — чего НЕ делать
1. **Slippage на количество, не на цену** (`slippage.py:56-58`): `ctx.buy_shares = buy_shares - slippage_pct * buy_shares`. Это математически неверно — на реальном рынке проскальзывание сдвигает ЦЕНУ, а не объём. Наш подход (`slippage_ticks * price_step`) правильнее. Урок: всегда проверяй соответствие модели реальности.
2. **Комиссия 0% по умолчанию** (`config.py:84`): `fee_mode=None`. Опасный default — большинство пользователей забудут задать комиссии и получат завышенные результаты. Урок: дефолты должны быть консервативными. В нашем проекте: MOEX комиссии включены по умолчанию через `CommissionManager.moex_default()`.
3. **Отсутствие лотности в portfolio.py**: Позиция `shares=15` для SBER (лот=10) невозможна на MOEX, но pybroker это не проверяет. Урок: валидация данных на уровне portfolio — обязательна. Наш подход: лотность через конфиг `instruments.equities[].lot`.

#### 5.5 Что НЕ брать и почему
- **SlippageModel** — неправильная модель (shares вместо цены). Наш tick-based подход лучше.
- **Data providers** — Yahoo/Alpaca бесполезны для MOEX. Нужен свой MoexISSDataSource.
- **diskcache** — мы используем Redis, который мощнее (TTL, pub/sub, distributed).
- **Bar-by-bar loop** — Python loop слишком медленный для tick data. Наш Polars-подход быстрее.
- **Decimal P&L** — overhead не оправдан для бэктеста (float precision достаточна для ±0.01 RUB).

### ШАГ 6: Планы интеграции

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: BCa Bootstrap Confidence Intervals
ПРИОРИТЕТ: 🔴 ВЫСОКИЙ
ОЦЕНКА ВРЕМЕНИ: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из eval.py:42-141 (НЕ копируем — Commons Clause!)
КУДА: src/backtest/metrics.py (дополнить)
ЧТО НАПИСАТЬ С НУЛЯ:
- bca_bootstrap(data, stat_fn, n_boot=10000) → BootstrapCI
- Bias correction: z0 = Φ⁻¹(count(θ* < θ̂) / B)
- Acceleration: jackknife leave-one-out → a = Σ(θ̄ - θ̂ᵢ)³ / (6 * (Σ(θ̄ - θ̂ᵢ)²)^1.5)
- Corrected quantiles: α* = Φ(z0 + (z0 + zα) / (1 - a(z0 + zα)))
- 90%, 95%, 97.5% CI для Sharpe, Sortino, Profit Factor, Max DD
ТЕСТЫ: Unit с known normal distribution (CI должен покрывать true mean)
ЗАВИСИМОСТИ: numpy (уже есть), scipy.stats.norm (для ppf/cdf)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: MAE/MFE + Equity R² + UPI
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идеи из eval.py и portfolio.py
КУДА: src/backtest/metrics.py (дополнить TradeMetrics)
ЧТО НАПИСАТЬ С НУЛЯ:
- mae_mfe(trades, price_history) → (avg_mae, avg_mfe, ratio)
  MAE = max(entry_price - min_price_during_trade) для long
  MFE = max(max_price_during_trade - entry_price) для long
- equity_r2(equity_curve) → float
  R² = 1 - SS_res / SS_tot линейной регрессии equity
- ulcer_performance_index(equity, period=14)
  UPI = mean(returns) / sqrt(mean(drawdown²))
- relative_entropy(returns) → float
  H = -Σ(p * log(p)) / log(n_bins) — нормализованная энтропия
ТЕСТЫ: Unit с known values
ЗАВИСИМОСТИ: нет новых
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### ШАГ 7: Итоговый вердикт

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: edtechre/pybroker                          ║
║  URL: github.com/edtechre/pybroker                       ║
║  Язык: Python | Последний коммит: 2026-03-04             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐⭐      4/5                ║
║  Качество кода:        ⭐⭐⭐⭐⭐    5/5                ║
║  Применимость к MOEX:  ⭐⭐⭐        3/5                ║
║  Risk management:      ⭐⭐⭐        3/5                ║
║  Стратегии:            ⭐⭐          2/5 (фреймворк)    ║
║  Бэктестинг:           ⭐⭐⭐⭐⭐    5/5                ║
║  Архитектура:          ⭐⭐⭐⭐⭐    5/5                ║
║                                                          ║
║  ОБОСНОВАНИЕ: Отличная архитектура (25K LOC, тесты 75%),║
║  уникальные компоненты (BCa bootstrap, MAE/MFE, walk-   ║
║  forward ML, Decimal P&L). Лицензия Commons Clause       ║
║  ограничивает коммерческое использование, но идеи        ║
║  и алгоритмы можно реализовать с нуля. У нас уже есть   ║
║  metrics, optimizer, monte_carlo — pybroker дополняет    ║
║  BCa bootstrap (точнее наших percentile CIs) и MAE/MFE. ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ (как идеи — Commons Clause!):         ║
║  1. BCa Bootstrap CI → src/backtest/metrics.py           ║
║     — точнее чем percentile bootstrap, Numba-ускоренный ║
║  2. MAE/MFE tracking → src/backtest/metrics.py           ║
║     — max adverse/favorable excursion per trade           ║
║  3. Walk-forward ML pipeline → src/backtest/optimizer.py ║
║     — train/test windows с lookahead gap для ML          ║
║                                                          ║
║  ТОП-3 АНТИПАТТЕРНА:                                    ║
║  1. Slippage на shares (не на цену) — нереалистично.    ║
║     У нас: slippage_ticks на цену (правильно для MOEX)  ║
║  2. Нет лотности/шага цены — дробные акции невозможны   ║
║     на MOEX. Наш проект правильно учитывает лоты.       ║
║  3. Нет portfolio drawdown protection — стоп только на   ║
║     позицию, нет circuit breaker. У нас: rules.py       ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. Commons Clause — нельзя копировать код для продажи  ║
║     → Писать с нуля, вдохновляясь алгоритмами           ║
║  2. Numba зависимость — тяжёлая, долгая компиляция      ║
║     → Использовать для критичных функций (bootstrap)     ║
║  3. Bar-by-bar Python loop — медленно для tick data      ║
║     → Наш vectorized approach (Polars) быстрее           ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Реализовать BCa bootstrap и MAE/MFE    ║
║  с нуля в src/backtest/metrics.py (~3 часа)              ║
╚══════════════════════════════════════════════════════════╝
```

### Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | **BCa Bootstrap CI** | `eval.py:42-141` | ⭐⭐⭐⭐ | Среднее | Точнее percentile bootstrap, bias correction + acceleration |
| 2 | **MAE/MFE per trade** | `portfolio.py` (Entry/Trade) | ⭐⭐⭐⭐ | Низкое | Max adverse/favorable excursion — оценка качества входов |
| 3 | **Walk-forward ML** | `strategy.py` (walkforward_split) | ⭐⭐⭐⭐ | Среднее | Train/test windows с lookahead gap для ML-моделей |
| 4 | **Relative Entropy** | `eval.py:418-447` | ⭐⭐⭐ | Низкое | Мера разнообразия доходностей (информационная энтропия) |
| 5 | **Ulcer Performance Index** | `eval.py:484-499` | ⭐⭐⭐ | Низкое | return / ulcer_index — risk-adjusted без Sharpe bias |
| 6 | **Decimal P&L** | `portfolio.py` | ⭐⭐⭐ | Высокое | Точные финрасчёты без float ошибок |
| 7 | **FeeMode (callable)** | `portfolio.py` | ⭐⭐⭐ | Низкое | Custom fee function — гибче наших правил |
| 8 | **Equity R²** | `eval.py` | ⭐⭐⭐ | Низкое | R² equity curve — мера стабильности роста |
| 9 | **hold_bars (time-stop)** | `context.py` | ⭐⭐ | — | У нас уже есть timeout в protective.py |
| 10 | **Slippage model** | `slippage.py` | ⭐⭐ | — | На shares, не на цену — неправильный подход для MOEX |

### Планы интеграции (идеи, с нуля — Commons Clause)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: BCa Bootstrap Confidence Intervals
ПРИОРИТЕТ: 🔴 ВЫСОКИЙ
ОЦЕНКА ВРЕМЕНИ: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из eval.py:42-141 (НЕ копируем — Commons Clause!)
КУДА: src/backtest/metrics.py (дополнить)
ЧТО НАПИСАТЬ С НУЛЯ:
- bca_bootstrap(data, stat_fn, n_boot=10000) → BootstrapCI
- Bias correction (z0) + acceleration (jackknife)
- 90%, 95%, 97.5% confidence intervals
- Применить к Sharpe, Sortino, Profit Factor, Max DD
ТЕСТЫ: Unit с known distributions
ЗАВИСИМОСТИ: numpy (уже есть)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: MAE/MFE Trade Tracking
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 1 час
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из portfolio.py Entry/Trade
КУДА: src/backtest/metrics.py (дополнить TradeMetrics)
ЧТО НАПИСАТЬ С НУЛЯ:
- mae (max adverse excursion) — макс. просадка сделки от входа
- mfe (max favorable excursion) — макс. бумажная прибыль от входа
- Ratio mfe/mae — качество входов (>2 = хорошие входы)
- Добавить в TradeMetrics: avg_mae, avg_mfe, mae_mfe_ratio
ТЕСТЫ: Unit
ЗАВИСИМОСТИ: нет
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
КОМПОНЕНТ: Equity R² + Relative Entropy + UPI
ПРИОРИТЕТ: 🟡 СРЕДНИЙ
ОЦЕНКА ВРЕМЕНИ: 1 час
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИК: Идея из eval.py
КУДА: src/backtest/metrics.py
ЧТО НАПИСАТЬ С НУЛЯ:
- equity_r2(equity_curve) — R² линейной регрессии (1.0 = идеальный рост)
- relative_entropy(returns) — разнообразие доходностей
- ulcer_performance_index(equity, period=14)
ТЕСТЫ: Unit
ЗАВИСИМОСТИ: нет
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. barter-rs/barter-rs

**URL:** https://github.com/barter-rs/barter-rs
**Дата анализа:** 2026-03-21

### 2.1 Общее

Barter — экосистема Rust-крейтов для алго-трейдинга: live-trading, paper-trading и бэктестинг. 6 крейтов в Cargo workspace, 40K строк Rust, 256 файлов .rs. Автор — команда Barter Ecosystem Contributors, MIT лицензия, 2000+ stars. Основной фокус — производительность (Rust native, Numba-уровень для критичных путей), type-safety (generic Strategy/Risk/Clock), и масштабируемость (Tokio async, concurrent backtests). Уникальная особенность — единая архитектура для live и backtest (MockExecution подменяет реальную биржу, Engine идентичен).

- **Стек:** Rust, Tokio (async runtime), rust_decimal (Decimal арифметика для финансов — НЕ float!), serde, reqwest + tokio-tungstenite (HTTP/WS), tracing, criterion (бенчмарки). `#![forbid(unsafe_code)]` на всех крейтах.
- **Лицензия:** MIT — свободное коммерческое использование, можно портировать алгоритмы без ограничений.
- **Активность:** Последний коммит март 2026 (refactor интеграции), активная разработка. Discord с ~1000 участников.
- **Популярность:** 2000+ stars, используется индивидуальными трейдерами для крипто. По issues видно реальное использование в live-trading.
- **Документация:** Doc-comments на каждом публичном типе и функции. Примеры в doc-tests (компилируемые). 18 файлов примеров. Sphinx/API docs нет — только cargo doc. Качество документации **хорошее**, но не отличное (нет user guide за пределами examples).
- **Тесты:** Юнит-тесты в каждом модуле метрик (sharpe, sortino, drawdown, etc). Интеграционный тест engine loop. НО: нет E2E тестов бэктеста, нет тестов MockExchange fill logic. Покрытие оценочно ~50%.
- **CI/CD:** GitHub Actions, cargo test + clippy + fmt.

### 2.2 Архитектура и структура кода

**Общая архитектура:** Workspace из 6 крейтов с чётким разделением ответственности:

```
barter-instrument (типы: Exchange, Asset, Instrument, Index)
    ↑
barter-integration (REST/WS фреймворк, reconnection)
    ↑
barter-data (WebSocket streams: trades, L1, L2, liquidations)
    ↑                           ↑
barter-execution (order mgmt, mock/live execution, fills)
    ↑                           ↑
barter (Engine, Strategy, Risk, Statistics, Backtest)
    ↑
barter-macro (derive macros для serde)
```

**Паттерны:** Processor (единый `process()` trait), Builder, Newtype (индексы ExchangeIndex/AssetIndex/InstrumentIndex — O(1) lookups), Strategy Pattern (pluggable Strategy + Risk + Clock), Type-state (lifecycle ордеров через phantom types), Observer/Audit (AuditTick channel для мониторинга).

**Разделение ответственности:** Образцовое. Data/Strategy/Risk/Execution — полностью изолированы. Engine — единственная точка связи. State management — centralized, cache-friendly (Vec с integer indexing, не HashMap со String-ключами).

**Конфигурация:** SystemConfig через JSON. StrategyConfig/MockExecutionConfig — typed Rust structs с serde. Нет хардкода.

**Логирование:** tracing (structured logging), не println. Уровни, spans, instruments. Production-quality.

**Обработка ошибок:** Result/Option повсеместно, thiserror для typed errors, checked_div/checked_mul для Decimal. Нет unwrap() в production code (только в тестах). NoneOneOrMany для 0/1/Many errors без heap allocation.

**Type hints:** 100% (Rust обязывает). Generics на Engine: `Engine<Clock, State, ExecutionTxs, Strategy, Risk>` — compile-time dispatch, не runtime vtable.

**Docstrings:** На каждом публичном типе и функции. Doc-tests с компилируемыми примерами (Position, Sharpe, etc).

### 2.3 Торговые стратегии

```
СТРАТЕГИЯ: AlgoStrategy trait (фреймворк)
ТИП: универсальный — rule-based / ML / HFT / market-making
ФАЙЛ: barter/src/strategy/algo.rs

ПРИНЦИП РАБОТЫ:
Пользователь реализует trait AlgoStrategy с единственным методом
generate_algo_orders(&self, state: &Self::State) → (cancel_requests, open_requests).
Engine вызывает его на каждом Market/Account событии когда trading enabled.
State содержит ВСЕ: позиции, балансы, market data, connectivity, user-defined data.
Strategy возвращает пару (отмены, новые ордера) — разделение cancel/open на уровне типов.
Дополнительные traits: ClosePositionsStrategy (закрытие по команде),
OnDisconnectStrategy (действие при обрыве), OnTradingDisabled (реакция на стоп).
DefaultStrategy — пустая реализация с WARNING "NEVER USE IN PRODUCTION".

ОТЛИЧИЯ ОТ PYTHON-ФРЕЙМВОРКОВ:
1. Compile-time dispatch — Strategy не virtual, а monomorphized (нет overhead vtable)
2. Type-safe ордера — OrderRequestCancel и OrderRequestOpen разные типы, нельзя спутать
3. RiskApproved<T> wrapper — ордер не может попасть в execution без прохождения risk check
4. State read-only — стратегия не может мутировать state (immutable borrow)
5. Multi-exchange native — Strategy видит состояние всех бирж одновременно

ОЦЕНКА:
Это самый type-safe API для стратегий из всех проанализированных. Rust's type system
гарантирует корректность на уровне компиляции (не runtime). Для Python-порта ценность
в паттерне: разделение cancel/open, RiskApproved wrapper, immutable state access.
Слабость: нет built-in indicators, нет ML-интеграции (всё на пользователе).
Для MOEX: паттерн multi-exchange native полезен (SBER на TQBR + Si на FORTS одновременно).

ПРИМЕНИМОСТЬ К MOEX:
Прямая интеграция невозможна (Rust). Но архитектурные паттерны ценны:
- RiskApproved<Order> wrapper → портировать в Python (dataclass-обёртка)
- Separate cancel/open types → уже есть аналог в нашем OrderManager
- Immutable state snapshot → Polars DataFrame freeze перед generate_signals
```

### 2.4 Работа с данными

8 бирж: Binance (spot+futures), Bitfinex, BitMEX, Bybit, Coinbase, Gate.io, Kraken, OKX. Все крипто. Данные: PublicTrades, OrderBookL1 (best bid/ask), OrderBook L2 (full depth), Candles (OHLCV), Liquidations. WebSocket с auto-reconnect (exponential backoff + jitter). Нормализация: ExchangeTransformer конвертирует wire format в единый MarketEvent. OrderBook: BTreeMap для Bids/Asks с binary search, mid_price() и volume_weighted_mid_price().

**Адаптация к MOEX ISS:** Невозможно напрямую — Rust crate. Но паттерн BacktestMarketData (Arc<Vec<MarketEvent>>, shared across backtests) — мощная идея для нашего Python: pd.DataFrame в shared memory для concurrent backtests. Оценка порта концепции: 8 часов.

**Real-time:** Полная WebSocket поддержка с reconnection. Но MOEX ISS не поддерживается (только крипто биржи).

### 2.5 Risk Management

**Position sizing:** Нет встроенного. Пользователь задаёт quantity в OrderRequestOpen.

**Stop-loss/Take-profit:** Нет встроенных стопов. Стратегия сама генерирует cancel/open при достижении цены.

**Risk checks:** RiskManager trait с единственной реализацией `CheckHigherThan` (input <= limit). Утилиты: quote_notional_value, absolute_percentage_difference, delta (для опционов). DefaultRiskManager = approve all (WARNING: "NEVER USE IN PRODUCTION").

**Exposure control:** Нет max position size, нет portfolio heat, нет daily loss limit, нет correlation-aware sizing. Всё на пользователе.

**Drawdown protection:** Нет circuit breaker. Нет auto-shutdown при DD%.

**Если ничего нет:** Фреймворк предоставляет ТРАССУ (RiskManager trait + approved/refused types + utility math), но ни одного production-ready правила. Для live-торговли на MOEX это означает что пользователь ОБЯЗАН реализовать: max position size per instrument, portfolio DD stop (наш circuit_breaker.py), T+1 settlement check, ГО проверку для фьючерсов. Без этого — один runaway order и весь капитал на одной позиции.

### 2.6 Execution

**Типы ордеров:** Market (единственный поддерживаемый в MockExchange). OrderKind enum в коде содержит Market/Limit/StopLimit/StopMarket, но MockExchange реализует только Market. Live Binance поддерживает все.

**Mock execution:** Мгновенное исполнение по запрошенной цене, 100% fill, zero slippage, zero latency (параметр latency_ms есть в конфиге, но не используется в fill logic). Fees: фиксированный % от notional. Проверка баланса перед fill — это хорошо (InsufficientBalance error).

**Smart execution:** Нет TWAP/VWAP/iceberg.

**Broker adapters:** Binance (live). Mock (in-memory). Нет MOEX-адаптеров.

### 2.7 Бэктестинг

**Движок:** Тот же Engine что и для live, но с HistoricalClock + MockExecution. `run_backtests()` — concurrent через Tokio `try_join_all`. BacktestMarketData: Arc<Vec<Event>> (shared, zero-copy).

**Комиссии:** fees_percent в MockExecutionConfig. Flat %. Нет maker/taker.

**Проскальзывание:** Нет. Fill по запрошенной цене.

**Walk-forward:** Нет. Нет train/test split. Нет OOS.

**Визуализация:** Нет.

**Benchmark:** Нет сравнения с buy&hold.

**Уникальное:** Concurrent backtests с shared data (Arc<Vec>). Benchmarks через criterion crate.

### ШАГ 3: Красные флаги 🚩

```
1. Lookahead bias:
   [✅] Архитектурно предотвращён. Engine::process() получает события
   последовательно. HistoricalClock только вперёд. Strategy видит
   только текущий state, не будущие события.

2. Survivorship bias:
   [⚠️] Не контролируется — пользователь приносит свои данные.
   BacktestMarketData = Vec<Event> без проверки на делистинги.

3. Нереалистичные комиссии:
   [⚠️] По умолчанию fees_percent задаётся пользователем, нет default.
   Если пользователь задаст 0 — результаты завышены. Нет предупреждения.

4. Нет проскальзывания:
   [🚩] MockExchange: fill по request.price, 100% quantity.
   exchange/mock/mod.rs:269-330: order_value_quote = price * quantity,
   никакого сдвига цены. На реальном рынке Limit orders могут не
   исполниться, Market orders получат slippage.

5. Overfitting:
   [🚩] run_backtests() запускает N параметризаций на ОДНИХ данных.
   Нет walk-forward, нет OOS split, нет combinatorial testing.
   Пользователь легко переоптимизирует.

6. Утечка train→test:
   [⚠️] Нет train/test split вообще. Все данные = один набор.

7. Нет OOS:
   [🚩] Нет holdout period. Все бэктесты на полном наборе.

8. Нет лотности:
   [🚩] quantity — Decimal без проверки кратности лоту.
   Для MOEX: SBER=10шт, VTBR=10000шт не проверяется.

9. Нет шага цены:
   [🚩] price — Decimal без rounding. round_fill_price отсутствует.

10. Игнор MOEX-специфики:
    [🚩] Нет T+1, нет клирингов, нет ГО, нет вечерней сессии.
    Все биржи = крипто (24/7, T+0, нет лотности).

11. Нереалистичные результаты:
    [⚠️] Комиссии заданы, но zero slippage + 100% fill rate =
    систематически завышенные результаты. Для HFT/MM стратегий
    расхождение с реальностью будет значительным.
```

### ШАГ 4: Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | **Welford Online Algorithm** | `statistic/algorithm.rs` | ⭐⭐⭐⭐ | Низкое | Streaming mean/variance в один проход. O(1) memory. Для real-time метрик. |
| 2 | **Position lifecycle** | `engine/state/position.rs` (1227 стр.) | ⭐⭐⭐⭐ | Среднее | Open/increase/reduce/close/flip — полный lifecycle с FIFO PnL. Decimal arithmetic. Doc-tests. |
| 3 | **RiskApproved wrapper** | `risk/mod.rs` | ⭐⭐⭐⭐ | Низкое | Type-level маркер "ордер прошёл risk check". Предотвращает bypass risk на уровне типов. |
| 4 | **Concurrent backtests (Arc shared data)** | `backtest/mod.rs` | ⭐⭐⭐ | Среднее | Параллельные бэктесты на shared Vec данных. Для Python: multiprocessing + shared memory. |
| 5 | **NoneOneOrMany** | `engine/action/mod.rs` | ⭐⭐⭐ | Низкое | Enum для 0/1/N элементов без heap allocation. Паттерн для hot path. |
| 6 | **InFlightRequestRecorder** | `engine/state/order/` | ⭐⭐⭐ | Среднее | Отслеживание in-flight ордеров. Timeout tracking. |
| 7 | **TearSheet per instrument** | `statistic/summary/` | ⭐⭐⭐ | Низкое | Streaming metrics по инструменту. Welford update на каждом close. |
| 8 | **Volume-weighted mid price** | `barter-data/src/books/` | ⭐⭐ | Низкое | VWMP из L1/L2 order book. |
| 9 | **Connectivity state machine** | `engine/state/connectivity/` | ⭐⭐ | Среднее | Per-exchange, per-channel health tracking. |
| 10 | **Audit trail** | `engine/audit/` | ⭐⭐ | Среднее | Sequence-numbered audit events для мониторинга. |

### ШАГ 5: Полезность для нашего проекта

#### 5.1 Новые стратегии для ансамбля
Стратегий нет — это чистый фреймворк. Но паттерн "стратегия возвращает (cancels, opens)" чище чем наш "generate_signals → position_size → order" pipeline. Можно упростить наш signal flow: стратегия сразу возвращает готовые ордера, а не промежуточные сигналы. Для MOEX: не применимо напрямую, но архитектурная идея ценна.

#### 5.2 Улучшение существующих модулей
1. **Welford Online Algorithm** → `src/backtest/metrics.py`: наш `calculate_trade_metrics()` пересчитывает все метрики заново по полному массиву. Welford позволяет инкрементально обновлять mean/variance при каждом новом trade, без пересчёта. Для live-мониторинга Sharpe/Sortino — критично (O(1) вместо O(N) на каждом trade).
2. **Position lifecycle с FIFO PnL** → `src/risk/`: наш position tracking проще. barter-rs отслеживает quantity_abs_max, pnl_realised, pnl_unrealised, fees_enter/fees_exit для каждой позиции. Position flip (long→short одной сделкой) обрабатывается корректно — у нас такого нет.
3. **RiskApproved<Order> pattern** → добавить dataclass-обёртку в Python: `@dataclass(frozen=True) class RiskApproved(Generic[T]): order: T, approved_by: str, timestamp: datetime`. Предотвращает отправку непроверенных ордеров.

#### 5.3 Новые идеи и подходы
1. **Streaming metrics (Welford)** — вместо пересчёта массива на каждом баре, обновлять mean/variance/M инкрементально. Для 10000+ баров экономит значительное время.
2. **Concurrent backtests с shared data** — вместо копирования DataFrame для каждого бэктеста, использовать multiprocessing.shared_memory (Python 3.8+). Arc<Vec> в Rust ≈ shared_memory в Python.
3. **Type-state pattern для ордеров** — OpenInFlight → Open → CancelInFlight → Cancelled/Filled. В Python: Enum + state machine с запретом невалидных переходов.

#### 5.4 Антипаттерны — чего НЕ делать
1. **100% fill rate в MockExchange** (`exchange/mock/mod.rs:280-320`): Каждый ордер исполняется полностью по запрошенной цене. На MOEX Limit ордер может не исполниться (нет ликвидности на цене), Market ордер получит slippage. Урок: наш mock должен моделировать partial fills и price impact.
2. **DefaultRiskManager approves all** (`risk/mod.rs`): Единственная built-in реализация — пропускает всё. Один баг в стратегии = catastroic loss. Урок: наш default risk ВСЕГДА должен иметь hard limits (max position size, max DD, max exposure).
3. **Linear rate-of-return scaling** (`statistic/metric/rate_of_return.rs`): daily * 252 вместо (1+daily)^252-1. Систематически завышает годовую доходность. У нас уже правильно (CAGR), но это напоминание не упрощать.

#### 5.5 Что НЕ брать и почему
- **Весь Rust код** — не портируемо напрямую (языковой барьер). Берём только алгоритмы и архитектурные паттерны.
- **MockExchange** — unrealistic fills (100%, no slippage). Наш mock лучше.
- **Data layer** — крипто-only, MOEX не поддерживается.
- **RiskManager** — пустой shell, нет production-ready правил.
- **HistoricalClock** — не прыгает к event time, а пропорционально сдвигается. Семантически некорректно для бэктеста.

### ШАГ 6: План интеграции

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИДЕЯ: Welford Online Algorithm для streaming метрик
ВДОХНОВЛЕНО: barter/src/statistic/algorithm.rs
РЕАЛИЗОВАТЬ В: src/backtest/metrics.py (новый раздел)
СУТЬ: Реализовать WelfordAccumulator: update(value) → обновляет
running mean, variance, M. Методы: mean(), sample_variance(),
population_variance(), std_dev(). Интегрировать в StreamingMetrics
класс который считает Sharpe/Sortino инкрементально.
ОТЛИЧИЕ ОТ ОРИГИНАЛА: Python с numpy, а не Rust. Добавить
downside variance для Sortino. Добавить max drawdown tracking.
ПРИОРИТЕТ: 🟡
ОЦЕНКА: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИДЕЯ: RiskApproved<Order> wrapper pattern
ВДОХНОВЛЕНО: barter/src/risk/mod.rs (RiskApproved/RiskRefused)
РЕАЛИЗОВАТЬ В: src/risk/rules.py (расширить)
СУТЬ: Добавить @dataclass(frozen=True) class RiskApproved(Generic[T])
и RiskRefused(Generic[T]) обёртки. RulesEngine.check() возвращает
(List[RiskApproved[Order]], List[RiskRefused[Order]]) вместо
простого List[Order]. Execution layer принимает ТОЛЬКО RiskApproved.
ОТЛИЧИЕ: В Python нет compile-time enforcement, но runtime проверка
isinstance(order, RiskApproved) перед отправкой.
ПРИОРИТЕТ: 🟢
ОЦЕНКА: 1 час
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИДЕЯ: Position lifecycle (FIFO PnL + flip)
ВДОХНОВЛЕНО: barter/src/engine/state/position.rs (1227 строк)
РЕАЛИЗОВАТЬ В: src/risk/position_sizer.py (расширить)
СУТЬ: Полный lifecycle позиции: open → increase → partial reduce →
close → flip (long→short одной сделкой). FIFO PnL: каждый entry
отслеживается отдельно, PnL считается при выходе. Для НДФЛ РФ
(FIFO обязателен) это критично. Добавить quantity_abs_max, fees.
ОТЛИЧИЕ: Python + Decimal, а не Rust. Добавить лотность MOEX.
ПРИОРИТЕТ: 🟡
ОЦЕНКА: 3 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### ШАГ 7: Итоговый вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: barter-rs/barter-rs                        ║
║  URL: github.com/barter-rs/barter-rs                     ║
║  Язык: Rust | Stars: 2000+ | Последний коммит: 2026-03  ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐⭐      4/5                ║
║  Качество кода:        ⭐⭐⭐⭐⭐    5/5                ║
║  Применимость к MOEX:  ⭐⭐          2/5                ║
║  Risk management:      ⭐⭐          2/5 (shell only)   ║
║  Стратегии:            ⭐⭐          2/5 (фреймворк)    ║
║  Бэктестинг:           ⭐⭐⭐        3/5                ║
║  Архитектура:          ⭐⭐⭐⭐⭐    5/5                ║
║                                                          ║
║  ОБОСНОВАНИЕ:                                            ║
║  Лучшая архитектура среди всех проанализированных.       ║
║  Type-safety на уровне Rust (compile-time гарантии),     ║
║  Decimal arithmetic, zero unsafe code, O(1) state        ║
║  lookups через integer indexing. Но: Rust не портируем   ║
║  напрямую, крипто-only биржи, zero slippage в бэктесте,  ║
║  нет walk-forward, нет built-in risk rules. Ценность —   ║
║  в алгоритмах (Welford, Position FIFO) и паттернах       ║
║  (RiskApproved, concurrent backtests, audit trail).      ║
║  Для MOEX применимость низкая из-за языкового барьера.   ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ (алгоритмы и паттерны):               ║
║  1. Welford Online → src/backtest/metrics.py             ║
║     — streaming mean/variance, O(1) per update           ║
║  2. Position FIFO lifecycle → position tracking          ║
║     — open/increase/reduce/close/flip с FIFO PnL        ║
║  3. RiskApproved<T> wrapper → src/risk/rules.py         ║
║     — type-level маркер прохождения risk check           ║
║                                                          ║
║  ТОП-3 АНТИПАТТЕРНА:                                    ║
║  1. 100% fill rate — нереалистично для MOEX limit       ║
║     ордеров. Наш mock должен моделировать partial fills  ║
║  2. DefaultRiskManager = approve all — один баг =        ║
║     catastrophic loss. Наш default ВСЕГДА с hard limits  ║
║  3. Linear return scaling — завышает годовую доходность. ║
║     У нас CAGR (правильно), но напоминание полезно.     ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. Языковой барьер Rust→Python — только идеи, не код   ║
║     → Писать с нуля на Python, вдохновляясь алгоритмами ║
║  2. Крипто-only — нет MOEX ISS/T+1/клирингов/ГО        ║
║     → Все MOEX-специфичные модули — наши собственные    ║
║  3. Zero slippage в бэктесте — завышенные результаты    ║
║     → Наш tick-based slippage model остаётся основным   ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Реализовать Welford Online streaming    ║
║  metrics в src/backtest/metrics.py (~2 часа)             ║
╚══════════════════════════════════════════════════════════╝
```

---

## 8. shobrook/BitVision

**URL:** https://github.com/shobrook/BitVision
**Дата анализа:** 2026-03-21

### 2.1 Общее

BitVision — терминальный dashboard для торговли Bitcoin на Bitstamp с встроенным ML-ботом. Node.js (blessed-contrib) для UI + Python (922 строки) для ML/торговли. Автор: Jonathan Shobrook, Aaron Lichtman. Проект заброшен с февраля 2019 года (7 лет без коммитов). Один коммит в shallow clone. MIT лицензия.

- **Стек:** Node.js (blessed, blessed-contrib — TUI), Python 3.7 (sklearn, pandas, scipy, bs4, realtime-talib). 922 строки Python + 1425 строк JS.
- **Лицензия:** MIT — свободное использование.
- **Активность:** Мёртв. Последний коммит: 2019-02-10. Зависимости устарели (sklearn deprecated import, Quandl API ключи захардкожены в коде, realtime-talib возможно не работает).
- **Популярность:** ~1200 stars (за UI dashboard, не за ML). По issues видно что бот не работает уже давно.
- **Документация:** README описывает установку и использование UI. Нет документации ML-модели, feature engineering, или стратегии. Docstrings отсутствуют.
- **Тесты:** Нет. Ни одного файла тестов.
- **CI/CD:** Нет.

### 2.2 Архитектура и структура кода

**Общая архитектура:** Монолит из двух частей — Node.js TUI dashboard + Python backend через subprocess. Зависимости:

```
index.js (TUI dashboard)
  ├── modals/ (login, order, help — blessed-contrib UI)
  └── services/ (Python subprocess)
        ├── __main__.py (CLI router: action → handler)
        ├── retriever.py (скрапинг данных: Quandl, Coindesk)
        ├── trader.py (Bitstamp API client + prediction + trade)
        └── engine/ (ML pipeline)
              ├── data_bus.py (fetch CSV from Quandl)
              ├── transformers.py (feature engineering: TA indicators + lag + boxcox)
              └── model.py (LogisticRegression L1, 27 строк)
```

**Паттерны:** Нет паттернов. Процедурный код. Нет классов (кроме Model и BitstampClient). Нет абстракций. Нет конфигурации (хардкод везде).

**Разделение ответственности:** Минимальное. trader.py содержит и Bitstamp client, и prediction, и fund allocation — всё в одном файле.

**Конфигурация:** Хардкод. Quandl API ключ прямо в коде (`data_bus.py:17-29`). Risk = 0.3 хардкод (`trader.py:40`). Параметры модели хардкод (`model.py:18`).

**Логирование:** Нет. Ни print, ни logging.

**Обработка ошибок:** Голый except в `__main__.py:44`: `except: logged_in = False`. Нет обработки ошибок API, сетевых проблем, невалидных данных.

**Type hints:** Нет. Python 3.7 era, pre-typing.

**Docstrings:** Нет (кроме копипасты из bitstamp-python-client).

### 2.3 Торговые стратегии

```
СТРАТЕГИЯ: ML Trend Prediction (LogisticRegression)
ТИП: ML (binary classification — trend direction)
ФАЙЛ: services/engine/model.py (27 строк) + services/trader.py:20-38

ПРИНЦИП РАБОТЫ:
Ежедневно скачивает OHLCV с Bitstamp (через Quandl CSV) + blockchain данные
(confirmation time, block size, hash rate, difficulty, etc — 12 метрик).
Считает 17 технических индикаторов (ROCR, ATR, OBV, TRIX, MOM, ADX, WILLR,
RSI, MACD, EMA). Добавляет lag-3 переменные (каждая фича дублируется
со сдвигом 1,2,3). Box-Cox трансформация для нормализации. Бинаризация:
если Close[t] > Close[t+1] → Trend = 1 (рост), иначе -1 (падение).
LogisticRegression(L1, C=1000, tol=0.001, max_iter=150) обучается на ВСЕХ
данных кроме последней строки. Предсказание для последней строки →
BUY или SELL. Размер позиции: 30% от balance (хардкод). Ордер: instant
market order на Bitstamp.

МАТЕМАТИКА / ФОРМУЛЫ:
features = [Close, Volume, MOM(1), MOM(3), ADX(14), ADX(20), WILLR(14),
            RSI(6), RSI(12), MACD, MACD_signal, MACD_hist, EMA(6), EMA(12),
            ROCR(3), ROCR(6), ATR(14), OBV, TRIX(20),
            + 12 blockchain metrics,
            + lag-1/2/3 для каждой фичи]
total features ≈ (19 TA + 12 blockchain) * 4 (original + 3 lags) = ~124 фичи
target: Trend = sign(Close[t] - Close[t+1])
model: LogisticRegression(penalty="l1", C=1000, max_iter=150)
scaler: StandardScaler

ПАРАМЕТРЫ:
| Параметр | Значение | Описание |
|----------|----------|----------|
| penalty | l1 | LASSO regularization |
| C | 1000 | Inverse regularization (очень слабая) |
| tol | 0.001 | Convergence tolerance |
| max_iter | 150 | Max iterations |
| lag | 3 | Лаг-переменные |
| risk | 0.3 | 30% капитала на сделку (хардкод) |

ТАЙМФРЕЙМ: Daily (Bitstamp OHLCV)
ИНСТРУМЕНТЫ: BTC/USD (Bitstamp only)

РЕЗУЛЬТАТЫ БЭКТЕСТОВ: Нет. Ни одного бэктеста. Ни одной метрики.

ОЦЕНКА:
Стратегия принципиально НЕРАБОЧАЯ по нескольким причинам:
1. Обучение на ВСЕХ данных включая test point (data_bus/transformers — нет
   train/test split в production mode). Modель видит future.
2. binarize_labels() (`transformers.py:137`) использует shift(-1) —
   заглядывает в будущее (Close[t+1]) для создания target. Это
   lookahead bias в чистом виде.
3. C=1000 с ~124 фичами на нескольких тысячах строк = severe overfitting.
   L1 penalty слишком слабая чтобы компенсировать.
4. 30% капитала на сделку без стопа = catastrophic risk.
5. Нет cross-validation, нет walk-forward, нет OOS.
6. Box-Cox применяется ко всему набору включая test — data leakage.

ПРИМЕНИМОСТЬ К MOEX:
Нет. Стратегия нерабочая. Идея "blockchain data + TA → LogReg" наивна
и не имеет edge. Для MOEX: blockchain данные неприменимы к акциям.
Единственная ценность — список blockchain фич как пример alternative data.
```

### 2.4 Работа с данными

**Источники:** Quandl CSV API (BCHARTS/BITSTAMPUSD) для OHLCV, Quandl BCHAIN/* для 12 blockchain метрик, Coindesk RSS для новостей. API ключ ЗАХАРДКОЖЕН в исходном коде (`data_bus.py:17-29`) — **критическая уязвимость безопасности**.

**Хранение:** Нет. Данные скачиваются каждый раз заново. Нет кэширования.

**Feature engineering:** 17 TA индикаторов через realtime-talib + 12 blockchain метрик + lag-3 = ~124 фичи. Box-Cox power transform. StandardScaler. Всё в одном пайплайне без разделения fit/transform.

**Адаптация к MOEX ISS:** Не имеет смысла — стратегия нерабочая. Quandl API для MOEX нет. Blockchain данные к MOEX не применимы.

### 2.5 Risk Management

**Position sizing:** `allocate_funds()` = 30% капитала, хардкод (`trader.py:40`). TODO комментарий "Implement Kelly Criterion" — не реализован.

**Stop-loss:** Нет.

**Take-profit:** Нет.

**Exposure control:** Нет.

**Drawdown protection:** Нет.

**Что это значит:** Один неверный сигнал → мгновенный market order на 30% капитала без стопа. При трёх подряд неверных сигналах — потеря 90% капитала. На MOEX при гэпе на открытии — loss beyond position size. Абсолютно неприемлемо для live-торговли.

### 2.6 Execution

**Типы ордеров:** Только instant market orders (Bitstamp `buy_instant_order` / `sell_instant_order`).

**Smart execution:** Нет.

**Проскальзывание:** Не моделируется, не учитывается. Instant orders на Bitstamp = fill по рыночной цене + slippage.

**Broker adapters:** Только Bitstamp. Клиент скопирован из kmadac/bitstamp-python-client с минимальными изменениями.

### 2.7 Бэктестинг

Нет. Полностью отсутствует. Нет ни бэктест-движка, ни исторического тестирования, ни метрик, ни equity curve, ни benchmarks. Модель обучается и сразу торгует.

### ШАГ 3: Красные флаги 🚩

```
1. Lookahead bias:
   [🚩🚩🚩] КРИТИЧЕСКИЙ. transformers.py:137-143: binarize_labels()
   использует df.iloc[idx+1]["Close"] для создания target Trend.
   Но эта же строка ВКЛЮЧЕНА в training data (model.py:18-19:
   Model(processed_data.drop(processed_data.index[0]))). Модель
   ОБУЧАЕТСЯ на данных содержащих будущую информацию.

2. Survivorship bias:
   [⚠️] Только BTC/USD — один инструмент, survivorship N/A.

3. Нереалистичные комиссии:
   [🚩] Комиссии ВООБЩЕ не учитываются. Ни в модели, ни при торговле.
   Bitstamp берёт 0.25-0.5%. При daily trading это 60-120% годовых
   в комиссиях.

4. Нет проскальзывания:
   [🚩] Instant market orders. Проскальзывание не моделируется.

5. Overfitting:
   [🚩🚩🚩] КРИТИЧЕСКИЙ. ~124 фичи, C=1000 (почти нет регуляризации),
   нет train/test split, нет cross-validation, нет walk-forward.
   Модель переобучена на 100%.

6. Утечка train→test:
   [🚩🚩🚩] КРИТИЧЕСКИЙ. Нет train/test split вообще. Box-Cox
   fit на всех данных. StandardScaler fit на всех данных.
   Модель видит ВСЕ данные включая "test" point.

7. Нет OOS:
   [🚩] Полностью отсутствует.

8. Нет лотности:
   [⚠️] Bitcoin делится дробно — не применимо.

9. Нет шага цены:
   [⚠️] Bitstamp принимает 2 decimal places — не критично.

10. Игнор MOEX-специфики:
    [🚩] Полностью. Крипто-only. MOEX не упоминается.

11. Нереалистичные результаты:
    [🚩] Результатов НЕТ ВООБЩЕ. Ни одного бэктеста. Ни одной метрики.
    Модель никогда не была протестирована на исторических данных.

ДОПОЛНИТЕЛЬНЫЕ ФЛАГИ:
12. API ключ в исходном коде:
    [🚩🚩🚩] data_bus.py:17-29: Quandl API key "iKmHLdjz-ghzaWVKyEfw"
    захардкожен 12 раз. Это КРИТИЧЕСКАЯ уязвимость — ключ доступен
    всем кто видит код.

13. Голый except:
    [🚩] __main__.py:44: except: logged_in = False — маскирует
    любые ошибки включая сетевые, парсинга, авторизации.
```

### ШАГ 4: Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | Feature набор (17 TA + blockchain) | `transformers.py:12-100` | ⭐⭐ | Низкое | Список TA-индикаторов как checklist — у нас 90% уже есть. |
| 2 | Box-Cox transform | `transformers.py:129-133` | ⭐ | Низкое | Идея power transform — но у нас уже есть нормализация в features.py. |
| 3 | Lag variables | `transformers.py:110-125` | ⭐ | Низкое | Lag-3 как feature augmentation — тривиальный приём, у нас уже есть. |

### ШАГ 5: Полезность для нашего проекта

#### 5.1 Новые стратегии для ансамбля
Нет ценных стратегий. LogisticRegression с L1 и C=1000 на 124 фичах без validation — это учебный пример overfitting. Идея "предсказать направление цены бинарной классификацией" не нова и без proper validation не имеет edge. Для нашего ансамбля: у нас уже есть CatBoost/LightGBM/XGBoost с walk-forward — принципиально лучше.

#### 5.2 Улучшение существующих модулей
Нечего улучшать. Наш код превосходит BitVision по каждому параметру: архитектура, тесты, метрики, risk management, execution.

#### 5.3 Новые идеи и подходы
Единственная нетривиальная идея: **blockchain data как alternative data для crypto**. Confirmation time, hash rate, difficulty, miner revenue — эти метрики коррелируют с сетевой активностью и могут быть leading indicators для BTC. Для MOEX аналога нет (мы не торгуем крипто). Если бы торговали — стоило бы исследовать.

#### 5.4 Антипаттерны — чего НЕ делать

1. **Lookahead bias в binarize_labels** (`transformers.py:137-143`): `diff = df.iloc[idx]["Close"] - df.iloc[idx + 1]["Close"]` — target использует будущую цену, и эти же строки попадают в training set. Урок: ВСЕГДА проверять что target не содержит future information. В нашем проекте: target = return[t+1], но train set обрезается на t-1 (buy_delay=1 аналог).

2. **API ключи в исходном коде** (`data_bus.py:17-29`): Quandl API key захардкожен 12 раз. Урок: ВСЕГДА через environment variables. В нашем проекте: `os.environ["MOEX_API_KEY"]` + `.env.example`.

3. **30% капитала без стопа** (`trader.py:40`): `return buying_power * 0.3`. Один неверный сигнал = -30% портфеля. Три подряд = -90%. Урок: НИКОГДА фиксированный % без стопа. В нашем проекте: risk_per_trade=1.5%, max_position=15%, ATR-stop, drawdown multiplier.

4. **Нет бэктестинга перед live** — модель обучается и сразу торгует. Урок: ВСЕГДА backtest → walk-forward → paper trade → live. В нашем проекте: vectorbt engine + monte carlo + bootstrap CI.

#### 5.5 Что НЕ брать и почему
- **Всё.** Ни один компонент не имеет ценности ≥ 3. ML pipeline порочен (lookahead + no validation). Feature engineering тривиален. Risk management отсутствует. Код не поддерживается 7 лет.

### ШАГ 6: План интеграции

Нет компонентов для интеграции. Все компоненты ценность ≤ 2.

Раздел "Идеи для реализации с нуля" — тоже пуст: все идеи (TA indicators, lag features, BoxCox) уже реализованы в нашем проекте.

### ШАГ 7: Итоговый вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: shobrook/BitVision                         ║
║  URL: github.com/shobrook/BitVision                      ║
║  Язык: Python+JS | Stars: ~1200 | Последний: 2019-02   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ПРОПУСТИТЬ                                    ║
║                                                          ║
║  Общая ценность:       ⭐              1/5              ║
║  Качество кода:        ⭐              1/5              ║
║  Применимость к MOEX:  ⭐              1/5              ║
║  Risk management:      ⭐              1/5 (нет)        ║
║  Стратегии:            ⭐              1/5 (сломана)    ║
║  Бэктестинг:           ⭐              1/5 (нет)        ║
║  Архитектура:          ⭐              1/5              ║
║                                                          ║
║  ОБОСНОВАНИЕ:                                            ║
║  BitVision — учебный проект 2018-2019 года, заброшенный  ║
║  7 лет назад. ML-модель содержит КРИТИЧЕСКИЙ lookahead   ║
║  bias (binarize_labels использует future close).         ║
║  Нет бэктестинга, нет тестов, нет risk management.      ║
║  API ключ захардкожен в коде (12 раз). 30% капитала на  ║
║  сделку без стопа. LogisticRegression(C=1000) на 124    ║
║  фичах без validation = гарантированный overfitting.    ║
║  Единственная ценность — как каталог антипаттернов.     ║
║  Код не подлежит интеграции ни в каком виде.            ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ:                                      ║
║  1. Ничего — нет компонентов ценностью ≥ 3              ║
║  2. —                                                    ║
║  3. —                                                    ║
║                                                          ║
║  ТОП-3 АНТИПАТТЕРНА:                                    ║
║  1. Lookahead bias в target (shift(-1) в train data)    ║
║     → Наш buy_delay=1 + proper train/test split        ║
║  2. API ключи в исходном коде (12 раз!)                ║
║     → Наш подход: os.environ + .env.example             ║
║  3. 30% капитала без стопа на одну сделку               ║
║     → Наш подход: risk_per_trade=1.5%, ATR-stop         ║
║                                                          ║
║  ТОП-3 РИСКА (если бы что-то брали):                    ║
║  1. Lookahead bias заразит наши результаты              ║
║  2. Зависимости устарели (sklearn import deprecated)    ║
║  3. Нет тестов — невозможно верифицировать              ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Пропустить. Кидай следующий репо.       ║
╚══════════════════════════════════════════════════════════╝
```

---

## 9. amor71/LiuAlgoTrader

**URL:** https://github.com/amor71/LiuAlgoTrader
**Дата анализа:** 2026-03-21

### 2.1 Общее

LiuAlgoTrader — полноценная торговая платформа для US Equities и Crypto. Multi-process async architecture (producer-consumer через multiprocessing.Queue), PostgreSQL для persistence, Alpaca/Polygon/Gemini/Tradier для данных и исполнения. 17.4K строк Python, 39 тестовых файлов, Sphinx docs, Streamlit UI для анализа. MIT лицензия. Автор: AMOR71. Проект зрелый (v0.4.35, PyPI package), но последний значимый коммит ~2023.

- **Стек:** Python 3.10+, asyncio, asyncpg (PostgreSQL), pandas, stockstats, empyrical, quantstats, scipy, alpaca-trade-api, polygon-api-client, streamlit (UI), pygit2 (git labels). PDM для пакетов.
- **Лицензия:** MIT — свободное использование.
- **Активность:** Мёртв/dormant. Последний merge 2023. Зависимости местами устарели.
- **Популярность:** ~700 stars, реальные пользователи по issues. YouTube demos с tear sheets.
- **Документация:** ReadTheDocs (liualgotrader.readthedocs.io), Medium статьи, Sphinx docs. Docstrings на всех публичных методах Strategy/Scanner. Качество **хорошее**.
- **Тесты:** 39 файлов, hypothesis-tested badge, codecov. Покрыты: data loaders, fincalcs, scanners, DB models. НЕ покрыты: consumer.py, producer.py, enhanced_backtest.py (критический execution path без тестов).
- **CI/CD:** GitHub Actions, mypy, black, bandit (security), isort.

### 2.2 Архитектура и структура кода

**Общая архитектура:** Multi-process producer-consumer через multiprocessing.Queue:

```
Market Data (Alpaca/Polygon WebSocket)
         ↓
    [Producer Process] — subscribes, dispatches bars to queues
         ↓
    multiprocessing.Queue × N
    /        |        \
[Consumer₁] [Consumer₂] [Consumer₃]  — N = CPU_FACTOR × cores
    ↓            ↓            ↓
    Strategy.run() / run_all()
         ↓
    Trader.submit_order()
         ↓
    PostgreSQL (asyncpg, new_trades, algo_run, gain_loss...)
```

**Паттерны:** Producer-Consumer (multiprocessing), Template Method (Strategy base class), Factory (DataFactory, StreamingFactory), Abstract Base (DataAPI, Scanner, Strategy, Trader, Miner), Dynamic Loading (importlib для стратегий и сканеров из TOML).

**Разделение ответственности:** Хорошее. data/ (провайдеры), strategies/ (логика), scanners/ (отбор тикеров), fincalcs/ (индикаторы), models/ (DB), analytics/ (анализ), scripts/ (CLI). Но consumer.py = 1000 строк монолит.

**Конфигурация:** `tradeplan.toml` для стратегий/сканеров, env vars для API keys, `config.py` для defaults. Нет хардкода ключей (в отличие от BitVision).

**Логирование:** `tlog()` — custom timestamped logger. Не structlog, но достаточный.

**Обработка ошибок:** Средняя. `try/except` в критических путях, но consumer.py глотает некоторые ошибки (stale data drops 99% warnings).

**Type hints:** Частичные (~70%). mypy в CI. Dict/List без generic parameters в старых модулях.

**Docstrings:** На всех публичных методах Strategy, Scanner. Google-style. Хорошие.

### 2.3 Торговые стратегии

```
СТРАТЕГИЯ: Strategy Framework (Template Method)
ТИП: универсальный — day trade / swing
ФАЙЛ: liualgotrader/strategies/base.py (200 строк)

ПРИНЦИП РАБОТЫ:
Пользователь наследует Strategy и реализует run(symbol, position, now,
minute_history) → (bool, dict). Dict содержит action: {side, qty, type,
limit_price}. Framework вызывает run() на каждом баре для каждого символа
из scanner watchlist. Альтернативно: should_run_all()=True → run_all()
вызывается раз в 5 минут с позициями по ВСЕМ символам (portfolio-level).
Callbacks: buy_callback/sell_callback при исполнении.
Unique: reject mechanism — return {reject: True} навсегда исключает символ.
global_var через PostgreSQL keystore — shared state между стратегиями.

ДОСТУПНЫЕ ACTIONS:
- {"side": "buy", "qty": 100, "type": "market"}
- {"side": "sell", "qty": 50, "type": "limit", "limit_price": 305.0}
- {"reject": True} — навсегда исключить символ

SCANNER (scanners/momentum.py):
Отбор тикеров перед торговлей: фильтр по цене, объёму, дневному изменению.
Live: snapshot с биржи → filter. Backtest: из DB trending_tickers.

ОЦЕНКА:
Хороший API для day trading стратегий. run_all() для portfolio-level —
мощная идея. Scanner как отдельный компонент — правильное разделение.
Слабости: нет встроенного position sizing (calc_qty = 100% капитала),
нет стопов на уровне framework, dynamic code loading без sandbox.
Для MOEX: run() per symbol подходит, но нет T+1, клирингов, лотности.

ПРИМЕНИМОСТЬ К MOEX:
Паттерн Scanner → Strategy → Execution переносим. Momentum scanner
можно адаптировать для MOEX (фильтр по IMOEX). run_all() полезен
для портфельных стратегий. Нужно: лотность, T+1, клиринги, MOEX ISS.
```

### 2.4 Работа с данными

5 провайдеров: Alpaca (REST + WebSocket), Polygon (REST + WS), Finnhub (REST), Gemini (REST + WS), Tradier (REST). DataLoader — lazy-loading кэш: `dl[symbol].close[timestamp]` загружает данные при первом обращении, автоматически расширяет диапазон. DataFactory/StreamingFactory — swap provider через config. PostgreSQL для persistence (stock_ohlc, trending_tickers).

**Адаптация к MOEX ISS:** Написать `MoexData(DataAPI)` — реализовать `get_symbol_data()`, `get_market_snapshot()`. DataLoader подхватит автоматически. Оценка: ~300 строк, ~6 часов. Scanner нужен свой (MOEX snapshot API отличается от Alpaca).

### 2.5 Risk Management

**Position sizing:** `calc_qty()` = buying_power / price — 100% капитала в одну позицию! `config.risk=0.001` существует но НИГДЕ не используется framework'ом.

**Stop-loss:** Нет на уровне framework. Стратегия сама отслеживает через `stop_prices` dict в trading_data.py (global mutable state).

**Exposure control:** Нет max position count, нет concentration limits, нет daily loss limit, нет circuit breaker.

**Что это значит для live:** Без кастомной реализации в стратегии — один баг = 100% капитала в одной позиции. Для MOEX при гэпе = catastrophic loss.

### 2.6 Execution

**Типы ордеров:** Market и Limit. time_in_force = "day" хардкод. Нет IOC/FOK/GTC.

**Order management:** `order_inflight()` — отменяет ордера старше 1 минуты. Partial fills обрабатываются корректно.

**Smart execution:** Нет TWAP/VWAP/iceberg.

**Broker adapters:** Alpaca (полный), Gemini (полный), Tradier (beta).

### 2.7 Бэктестинг

**Движок:** Event-driven, bar-by-bar (enhanced_backtest.py, 552 строки). Итерирует по торговому календарю, шаг = minute или day. DataLoader даёт исторические данные.

**Критические проблемы бэктеста:**
1. **Lookahead bias:** fill price = `close[T]` текущего бара, хотя сигнал на начале бара T.
2. **Static portfolio_value:** объявлен global, но НИКОГДА не обновляется — position sizing игнорирует P&L.
3. **Fees не вычитаются:** сохраняются в DB, но не из equity — P&L завышен.
4. **Limit orders crash:** unfillable limit → Exception вместо reject.
5. **Нет проверки объёма:** 10K shares на 500-volume bar fills at close.

**Walk-forward:** Нет. **Optimizer:** Grid search через multiprocessing, нет Bayesian/random search. Результаты в DB, нет auto-scoring.

**Визуализация:** Streamlit UI, quantstats tear sheets, Jupyter notebooks.

### ШАГ 3: Красные флаги 🚩

```
1. Lookahead bias:
   [🚩] enhanced_backtest.py: calculate_execution_price() использует
   close[T] для fill при сигнале на баре T. Стратегия не может
   знать close текущего бара в момент принятия решения.

2. Survivorship bias:
   [⚠️] Scanner из live DB. Backtest использует trending_tickers
   записанные при live-торговле. Если live не запускался — backtest
   пуст. Нет built-in survivorship-free universe.

3. Нереалистичные комиссии:
   [⚠️] Default --buy-fee=0.0 --sell-fee=0.0. Fees сохраняются
   в DB но НЕ вычитаются из portfolio_value при бэктесте.

4. Нет проскальзывания:
   [🚩] Fill at close. Нет bid/ask spread, market impact, partial fills.

5. Overfitting:
   [⚠️] Grid search optimizer без walk-forward. Нет OOS split.
   Пользователь может переоптимизировать не зная.

6. Утечка train→test:
   [⚠️] Нет train/test split в бэктесте. Один период.

7. Нет OOS:
   [⚠️] Нет отдельного holdout. Только through-time backtest.

8. Нет лотности:
   [🚩] qty = float, нет проверки кратности лоту MOEX.

9. Нет шага цены:
   [🚩] Нет rounding fill price.

10. Игнор MOEX:
    [🚩] US equities + crypto. Нет T+1, клирингов, ГО, вечерней сессии.

11. Нереалистичные результаты:
    [⚠️] Static portfolio_value + zero fees + fill at close =
    систематически завышенные результаты. YouTube demo "$4000
    daily profit" основан на этом biased бэктесте.
```

### ШАГ 4: Карта ценности

| # | Компонент | Файл(ы) | Ценность | Усилие | Что полезно |
|---|-----------|---------|----------|--------|-------------|
| 1 | **Support/Resistance** | `fincalcs/support_resistance.py` (176) | ⭐⭐⭐ | Низкое | Derivative-based peak detection, grouping by proximity %, resample to 5/15-min. |
| 2 | **Candle patterns** | `fincalcs/candle_patterns.py` (119) | ⭐⭐⭐ | Низкое | 7 single-candle + 2 multi-candle patterns. Gravestone/dragonfly doji, spinning top, bullish/bearish. |
| 3 | **Scanner architecture** | `scanners/base.py + momentum.py` | ⭐⭐⭐ | Среднее | ABC Scanner → momentum filter. Recurrence-based execution. DB persistence. |
| 4 | **DataLoader lazy cache** | `common/data_loader.py` | ⭐⭐⭐ | Среднее | `dl[symbol].close[timestamp]` — auto-fetch missing ranges. Удобный API. |
| 5 | **run_all() portfolio mode** | `strategies/base.py` | ⭐⭐ | Низкое | Batch strategy вызов для portfolio-level decisions. |
| 6 | **PostgreSQL audit trail** | `models/` (все) | ⭐⭐ | Высокое | Полная persistence: trades, runs, gain/loss, optimizer, keystore. |
| 7 | **VOI calculation** | `consumer.py` | ⭐⭐ | Низкое | Volume-Order-Imbalance EMA(k=2/101, window=10). |

### ШАГ 5: Полезность для нашего проекта

#### 5.1 Новые стратегии для ансамбля
Нет готовых стратегий — только framework. Но momentum scanner pattern ценен: snapshot → filter by price/volume/change → watchlist. Для MOEX: сканер IMOEX-компонентов по ATR > threshold + Volume > 2x avg.

#### 5.2 Улучшение существующих модулей
1. **Support/Resistance detection** (`support_resistance.py`) — derivative-based peak/trough detection с grouping по proximity. Наш проект не имеет S/R модуля. Алгоритм: resample → diff → np.where(sign change) → group by 2% margin. Полезен для stop placement и take-profit levels.
2. **Candle pattern recognition** (`candle_patterns.py`) — 9 паттернов. У нас нет. Gravestone/dragonfly doji, spinning top, bullish/bearish confirmation — полезны как фильтры входа.

#### 5.3 Новые идеи и подходы
1. **Scanner as first-class citizen** — отдельный процесс, recurring execution, DB persistence результатов. Наш проект: сканер как часть pipeline, не отдельная сущность.
2. **run_all() vs run()** — дуальность per-symbol и portfolio-level стратегий в одном framework. Наш BaseStrategy.generate_signals() — per-instrument. Добавить portfolio-level callback.

#### 5.4 Антипаттерны — чего НЕ делать
1. **Fill at close[T]** (`enhanced_backtest.py`) — classic lookahead. Наш подход: fill at open[T+1] (правильно).
2. **Static portfolio_value** — position sizing не учитывает P&L. Наш подход: equity обновляется после каждой сделки.
3. **Global mutable state** (`trading_data.py`) — все позиции/ордера в module-level dicts. Баг в одной стратегии ломает все. Наш подход: isolated state per strategy.
4. **calc_qty = 100% капитала** — дефолтный position sizing кладёт всё в одну позицию. Наш подход: risk_per_trade=1.5% с ATR-stop.

#### 5.5 Что НЕ брать и почему
- **Бэктест движок** — lookahead + static portfolio + unfillable limit crash. Наш vectorbt-based лучше.
- **Producer/consumer architecture** — Python multiprocessing.Queue медленнее чем наш single-process Polars pipeline.
- **PostgreSQL models** — overengineered для бэктеста (round-trip на каждую сделку). Наш in-memory + batch save быстрее.
- **DataLoader** — удобный API, но pandas-based. Наш Polars-based быстрее.
- **analytics/analysis.py** — только raw P&L, нет Sharpe/DD/Calmar. Наш metrics.py на порядок мощнее.

### ШАГ 6: План интеграции

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИДЕЯ: Support/Resistance Detection
ВДОХНОВЛЕНО: fincalcs/support_resistance.py
РЕАЛИЗОВАТЬ В: src/indicators/support_resistance.py (новый файл)
СУТЬ: Derivative-based peak/trough detection на resampled данных.
find_resistances(close_series, lookback=3d, resample='15min') → List[float]
find_supports(low_series, lookback=100bars, resample='5min') → List[float]
grouper(levels, margin=0.02) → clustered levels.
ОТЛИЧИЕ ОТ ОРИГИНАЛА: Polars вместо pandas, конфигурируемые
пороги (не хардкод), MOEX trading hours (10:00-18:40), добавить
volume profile для weighted S/R levels.
ПРИОРИТЕТ: 🟡
ОЦЕНКА: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИДЕЯ: Candle Pattern Recognition
ВДОХНОВЛЕНО: fincalcs/candle_patterns.py
РЕАЛИЗОВАТЬ В: src/indicators/candle_patterns.py (новый файл)
СУТЬ: 9 свечных паттернов из LiuAlgoTrader:
gravestone_doji, four_price_doji, doji, spinning_top,
bullish_candle, bearish_candle, dragonfly_candle,
spinning_top_bearish_followup, bullish_candle_followed_by_dragonfly.
Добавить: hammer, engulfing, morning/evening star.
ОТЛИЧИЕ: Vectorized numpy вместо per-candle functions.
Thresholds через конфиг, не хардкод.
ПРИОРИТЕТ: 🟢
ОЦЕНКА: 2 часа
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### ШАГ 7: Итоговый вердикт

```
╔══════════════════════════════════════════════════════════╗
║  РЕПОЗИТОРИЙ: amor71/LiuAlgoTrader                       ║
║  URL: github.com/amor71/LiuAlgoTrader                    ║
║  Язык: Python | Stars: ~700 | Последний: ~2023          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐        3/5                ║
║  Качество кода:        ⭐⭐⭐        3/5                ║
║  Применимость к MOEX:  ⭐⭐          2/5                ║
║  Risk management:      ⭐            1/5 (отсутствует)  ║
║  Стратегии:            ⭐⭐⭐        3/5 (framework)    ║
║  Бэктестинг:           ⭐⭐          2/5 (biased)       ║
║  Архитектура:          ⭐⭐⭐⭐      4/5                ║
║                                                          ║
║  ОБОСНОВАНИЕ:                                            ║
║  Зрелая торговая платформа с хорошей архитектурой        ║
║  (producer-consumer, async, PostgreSQL audit trail).     ║
║  Но бэктест содержит lookahead bias (fill at close[T]), ║
║  static portfolio_value (sizing не учитывает P&L),       ║
║  zero default fees. Risk management полностью            ║
║  отсутствует на уровне framework. Ценность — в           ║
║  S/R detection, candle patterns, scanner architecture.   ║
║  US equities only, MOEX не поддерживается.              ║
║                                                          ║
║  ТОП-3 ЧТО ВЗЯТЬ (идеи):                               ║
║  1. S/R detection → src/indicators/support_resistance.py ║
║     — derivative peaks + proximity grouping              ║
║  2. Candle patterns → src/indicators/candle_patterns.py  ║
║     — 9 patterns, vectorized numpy version               ║
║  3. Scanner pattern → вдохновить наш universe_selector   ║
║     — recurring filter, DB persistence results           ║
║                                                          ║
║  ТОП-3 АНТИПАТТЕРНА:                                    ║
║  1. Fill at close[T] — lookahead bias в бэктесте.       ║
║     Наш подход: fill at open[T+1] (buy_delay=1)         ║
║  2. calc_qty = 100% капитала — нет risk per trade.      ║
║     Наш подход: 1.5% risk с ATR-stop                    ║
║  3. Global mutable state (trading_data.py) — shared      ║
║     dicts без изоляции стратегий                         ║
║                                                          ║
║  ТОП-3 РИСКА:                                            ║
║  1. Бэктест biased — нельзя доверять результатам        ║
║     → Писать S/R и patterns с нуля, тестировать нашим   ║
║  2. US equities only — MOEX адаптация ~6 часов          ║
║     → Берём только алгоритмы, не интеграции             ║
║  3. Dormant проект — зависимости устаревают             ║
║     → Только идеи, не pip install                       ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Реализовать S/R detection и candle      ║
║  patterns в src/indicators/ (~4 часа)                    ║
╚══════════════════════════════════════════════════════════╝
```

---

## 10. QuantConnect/Lean

**URL:** https://github.com/QuantConnect/Lean
**Дата анализа:** 2026-03-21

### Краткое описание

QuantConnect LEAN — крупнейший open-source алго-трейдинг движок (95K строк C#, 4160 файлов, 12K+ stars, 400+ contributors). Event-driven professional-caliber platform: 168 индикаторов, полный Algorithm Framework (Alpha→Portfolio→Risk→Execution), 10+ брокеров, встроенный бэктест, Python API. Apache 2.0 лицензия. Ежедневные обновления, продакшен на QuantConnect.com.

### Что ценно для MOEX Trading Bot (топ по приоритету)

**🔴 9 уникальных индикаторов** (не в TA-Lib):

| Индикатор | Формула (ключевая) | Применение MOEX |
|-----------|-------------------|-----------------|
| ChandeKrollStop | 2-pass ATR stop: `high_stop = max(H,p) - mult×ATR`, `stop = max(high_stop,q)` | Trailing stops Si/SBER |
| SuperTrend | Ratchet bands: `lower = max(HL2-mult×ATR, prev_lower)` + direction FSM | Trend filter daily |
| ChoppinessIndex | `100×log₁₀(ΣTR/range)/log₁₀(n)`, 38.2=trend/61.8=chop | On/off trend strategies |
| SchaffTrendCycle | MACD → 2× stochastic smoothing, 0-100 range | Faster MACD (less lag) |
| AugenPriceSpike | `(C-C₋₁)/(σ_logret × C₋₁)` — normalized spike in sigmas | Event detection (ЦБ) |
| RogersSatchell | `√mean(ln(H/C)×ln(H/O) + ln(L/C)×ln(L/O))` — drift-adjusted vol | Options pricing Si/RTS |
| ZigZag | Pivot FSM: `H ≥ lastLow×(1+sens)` AND `bars ≥ minTrend` | S/R, wave patterns |
| KlingerVO | VolumeForce `V×|2DM/CM-1|×trend×100`, dual EMA | Volume confirmation |
| RelativeVigorIndex | Triangular `(C-O)/(H-L)` weighted + signal line | Momentum quality |

**🔴 4 Risk модели:**
- `MaxDrawdownPerPosition(5%)` — стоп по unrealized PnL% per position
- `PortfolioCircuitBreaker(15%, trailing=True)` — ликвидация всех при portfolio DD
- `TrailingStopManager(5%)` — trailing peak tracking per holding
- `UnrealizedProfitTaker(10%)` — фиксация прибыли для mean-reversion

**🔴 Метрики:**
- **Probabilistic Sharpe Ratio** — `Φ((√(T-1)×(SR-SR*)) / √(1-γ₃SR+(γ₄-1)/4×SR²))` — anti-overfitting
- **VolumeShareSlippage** — `slippage = (min(qty/vol, 0.025))² × 0.1` — quadratic impact
- **ProfitToMaxDD**, **MaxConsecutiveStreaks**, **TrackingError**

**🟡 Execution:**
- VWAP execution (fill only when bid < VWAP, max 1% bar volume)
- SpreadFilter (reject wide spreads > 0.5%)
- STD execution (buy below SMA-kσ, sell above SMA+kσ)

### Красные флаги
- ✅ Lookahead protection (IndicatorBase.Update проверяет временной порядок)
- ⚠️ Default fees = 0 → надо явно задавать MOEX fee model
- ⚠️ MarketImpact параметры (α,β) калиброваны под US 2005 → перекалибровать
- ⚠️ Ichimoku 9/26/52 для 6-дневной недели → адаптировать для MOEX 5-дневной

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ + ИНТЕГРИРОВАТЬ (формулы)        ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐⭐⭐    5/5                ║
║  Качество кода:        ⭐⭐⭐⭐⭐    5/5                ║
║  Применимость к MOEX:  ⭐⭐⭐        3/5                ║
║  Risk management:      ⭐⭐⭐⭐⭐    5/5                ║
║  Индикаторы:           ⭐⭐⭐⭐⭐    5/5 (168 шт)      ║
║  Бэктестинг:           ⭐⭐⭐⭐⭐    5/5                ║
║  Архитектура:          ⭐⭐⭐⭐⭐    5/5                ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Портировать 9 индикаторов (~12ч),       ║
║  затем 4 risk models (~6ч), затем PSR + slippage (~5ч)  ║
╚══════════════════════════════════════════════════════════╝
```

---

## 11. hummingbot/hummingbot

**URL:** https://github.com/hummingbot/hummingbot
**Дата анализа:** 2026-03-21

### Краткое описание

Hummingbot — open-source фреймворк для маркет-мейкинга и HFT (1459 Python файлов, 35K LOC, Apache 2.0, $34B+ reported trading volume). Strategy V2 framework с Controller/Executor архитектурой. Cython для hot path. 140+ бирж. Уникальная ценность: Avellaneda-Stoikov market making model, Triple Barrier execution, TWAP/DCA/Grid executors, Order Book Imbalance.

### Что ценно для MOEX (топ компоненты)

**🔴 Avellaneda-Stoikov Market Making:**
```
reservation_price = mid - q × γ × σ² × (T - t)
spread* = γ × σ² × (T-t) + (2/γ) × ln(1 + γ/κ)
```
Где q = инвентарь, γ = risk aversion, σ = volatility, κ = fill rate.
Inventory skew сдвигает котировки для разгрузки позиции.
→ Для MOEX: T = время до закрытия сессии (18:40), σ через RogersSatchell.

**🔴 Triple Barrier (PositionExecutor):**
```
Take Profit: price ≥ entry × (1 + tp_pct)
Stop Loss:   price ≤ entry × (1 - sl_pct)
Time Limit:  elapsed > max_seconds
+ Trailing Stop с activation delta
```
→ Стандарт de Prado. Прямо применимо.

**🔴 TWAP Executor:**
```
order_interval = total_duration / n_orders
each interval: place limit at best bid/ask, amount = total/n
```
→ Критичен для крупных заявок на MOEX (2-й эшелон).

**🟡 DCA Executor:** Серия ордеров с dynamic average entry, пересчёт TP/SL после каждого fill.

**🟡 Grid Executor:** N уровней между lower/upper price, dynamic range shift при breakout.

**🟡 Order Book Imbalance:** `OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)` — краткосрочный directional signal.

**🟡 Fibonacci/Geometric distributions:** Для скрытности ордеров в стакане.

### Красные флаги
- ✅ Бэктест с gap-aware fill logic (fill at min(limit, open))
- ⚠️ Slippage = fixed pct (не quadratic volume-share)
- ⚠️ Крипто-only коннекторы
- 🚩 Cython в hot path → не portируется, только алгоритмы

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  ВЕРДИКТ: ВДОХНОВИТЬСЯ                                  ║
║                                                          ║
║  Общая ценность:       ⭐⭐⭐⭐⭐    5/5                ║
║  Качество кода:        ⭐⭐⭐⭐      4/5                ║
║  Применимость к MOEX:  ⭐⭐⭐        3/5                ║
║  Risk management:      ⭐⭐⭐⭐      4/5 (inventory)    ║
║  Стратегии:            ⭐⭐⭐⭐⭐    5/5 (A-S, Grid)    ║
║  Бэктестинг:           ⭐⭐⭐⭐      4/5                ║
║  Архитектура:          ⭐⭐⭐⭐⭐    5/5                ║
║                                                          ║
║  СЛЕДУЮЩИЙ ШАГ: Портировать Triple Barrier + TWAP +     ║
║  Avellaneda-Stoikov формулу (~8ч)                        ║
╚══════════════════════════════════════════════════════════╝
```

---

## 12. freqtrade/freqtrade-strategies

**URL:** https://github.com/freqtrade/freqtrade-strategies
**Дата анализа:** 2026-03-21

### Краткое описание

Коллекция 65 шаблонных стратегий для freqtrade. 9K строк Python, GPL-3 лицензия. Крипто-only (Binance/etc). Стратегии уровня от учебных до community-contributed. Нет фреймворка, нет бэктест-движка, нет метрик — только файлы стратегий. Папка `lookahead_bias/` содержит стратегии с ИЗВЕСТНЫМ lookahead bias (помечены как примеры чего НЕ делать).

### Ценные паттерны

| Компонент | Файл | Ценность | Суть |
|-----------|------|----------|------|
| FixedRiskRewardLoss | `FixedRiskRewardLoss.py` | ⭐⭐⭐ | Dynamic stoploss через ATR + Risk/Reward ratio 3.5:1 + break-even adjustment |
| VolatilitySystem | `futures/VolatilitySystem.py` | ⭐⭐⭐ | ATR×2 breakout: buy when `close_change > ATR×2`, position DCA через adjust_trade |
| CustomStoplossWithPSAR | `CustomStoplossWithPSAR.py` | ⭐⭐ | Parabolic SAR как trailing stop |

### Что НЕ брать
- **Diamond, GodStra, Zeus** — оптимизированные на in-sample, нет OOS. `lookahead_bias/` папка.
- **Все berlinguyinca/** — простейшие MA/RSI/MACD кроссоверы, нет ничего нового.
- **GPL-3 лицензия** — copyleft, код нельзя использовать в non-GPL проекте. Только идеи.

### Красные флаги
- 🚩 GPL-3 — copyleft restriction, не совместимо с нашим MIT/proprietary
- 🚩 Нет бэктест результатов (кроме Diamond hyperopt output)
- 🚩 Нет тестов (ни одного)
- 🚩 `lookahead_bias/` — 4 стратегии с ИЗВЕСТНЫМ lookahead
- ⚠️ Крипто-only — 15m/1h таймфреймы, не MOEX

### Вердикт

```
╔══════════════════════════════════════════════════════════╗
║  ВЕРДИКТ: ПРОПУСТИТЬ                                    ║
║                                                          ║
║  Общая ценность:       ⭐⭐          2/5                ║
║  Качество кода:        ⭐⭐          2/5                ║
║  Применимость к MOEX:  ⭐            1/5                ║
║  Risk management:      ⭐⭐          2/5                ║
║  Стратегии:            ⭐⭐          2/5 (шаблонные)    ║
║  Бэктестинг:           ⭐            1/5 (нет)          ║
║  Архитектура:          ⭐            1/5 (нет)          ║
║                                                          ║
║  Нет компонентов ценностью ≥ 3 для интеграции.          ║
║  FixedRiskRewardLoss паттерн (ATR stop + R:R ratio)     ║
║  уже реализован лучше в нашем Triple Barrier +           ║
║  ProtectiveController. GPL-3 запрещает копирование.      ║
║                                                          ║
║  ТОП-3 АНТИПАТТЕРНА:                                    ║
║  1. lookahead_bias/ — стратегии с ИЗВЕСТНЫМ bias в репо  ║
║  2. stoploss = -0.9 (FixedRiskReward) — 90% DD default  ║
║  3. Hyperopt на in-sample без OOS validation              ║
╚══════════════════════════════════════════════════════════╝
```

---

## Сводная таблица

| # | Репо | Вердикт | Ценность | Код | MOEX | Лучший компонент | Приоритет |
|---|------|---------|----------|-----|------|------------------|-----------|
| 1 | ghostfolio | ВДОХНОВИТЬСЯ | 3/5 | 5/5 | 2/5 | X-Ray Rules → src/risk/rules/ | 🟡 |
| 2 | jesse-ai/jesse | ИНТЕГРИРОВАТЬ | 4/5 | 4/5 | 3/5 | metrics.py → src/backtest/metrics.py | 🔴 |
| 3 | backtesting.py | ВДОХНОВИТЬСЯ | 3/5 | 5/5 | 2/5 | Alpha/Beta/SQN/Kelly → metrics.py | 🔴 |
| 4 | StockSharp | ИНТЕГРИРОВАТЬ | 4/5 | 4/5 | 4/5 | QuotingEngine + Commissions + Protective | 🔴 |
| 5 | Krypto-trading-bot | ПРОПУСТИТЬ | 1/5 | 3/5 | 1/5 | — (C++, крипто MM) | — |
| 6 | pybroker | ВДОХНОВИТЬСЯ | 4/5 | 5/5 | 3/5 | BCa Bootstrap + MAE/MFE + Equity R² | 🔴 |
| 7 | barter-rs | ВДОХНОВИТЬСЯ | 4/5 | 5/5 | 2/5 | Welford Online + Position FIFO + RiskApproved | 🟡 |
| 8 | BitVision | ПРОПУСТИТЬ | 1/5 | 1/5 | 1/5 | — (lookahead bias, нет бэктеста, мёртв) | — |
| 9 | LiuAlgoTrader | ВДОХНОВИТЬСЯ | 3/5 | 3/5 | 2/5 | S/R Detection + Candle Patterns + Scanner | 🟡 |
| 10 | **LEAN** | **ИНТЕГРИРОВАТЬ** | **5/5** | **5/5** | **3/5** | **9 indicators + 4 risk models + PSR** | **🔴** |
| 11 | hummingbot | ВДОХНОВИТЬСЯ | 5/5 | 4/5 | 3/5 | Avellaneda-Stoikov + Triple Barrier + TWAP | 🔴 |
| 12 | freqtrade-strategies | ПРОПУСТИТЬ | 2/5 | 2/5 | 1/5 | — (GPL-3, шаблонные, нет OOS) | — |
