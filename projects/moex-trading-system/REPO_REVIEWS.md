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

## Сводная таблица

| # | Репо | Вердикт | Ценность | Код | MOEX | Лучший компонент | Приоритет |
|---|------|---------|----------|-----|------|------------------|-----------|
| 1 | ghostfolio | ВДОХНОВИТЬСЯ | 3/5 | 5/5 | 2/5 | X-Ray Rules → src/risk/rules/ | 🟡 |
| 2 | jesse-ai/jesse | ИНТЕГРИРОВАТЬ | 4/5 | 4/5 | 3/5 | metrics.py → src/backtest/metrics.py | 🔴 |
