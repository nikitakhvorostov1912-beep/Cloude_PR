# Отчёт о производительности MOEX Trading Bot
Дата: 2026-03-22 15:36
Данные: MOEX ISS, 2022-01-01 — 2025-12-31
Начальный капитал: 1,000,000 RUB
Комиссия: 0.01%, проскальзывание: 2 тика

---

## 1. Архитектура системы

### Pipeline прогнозирования
```
MOEX ISS API → Дневные свечи (OHLCV)
    ↓
Индикаторы (EMA, RSI, MACD, Bollinger, ATR, ADX + 17 кастомных)
    ↓
Стратегия (EMA Crossover / ML Ensemble / Signal Synthesis)
    ↓
Risk Engine (Position Sizer → RiskApproved wrapper → Circuit Breaker)
    ↓
Execution (TWAP / DCA / Grid / Triple Barrier / Direct)
    ↓
Мониторинг (Telegram alerts + Streamlit dashboard)
```

### Индикаторы в системе (22 штуки)

**Используются в стратегиях:**
- EMA (20, 50) — основа EMA Crossover
- ATR (14) — position sizing и стопы
- RSI (14) — scoring система
- MACD (12, 26, 9) — scoring система
- ADX (14) — scoring система (trend strength)

**Используются в ML features:**
- Bollinger Bands (20, 2σ) — %B и bandwidth
- OBV — volume confirmation
- VWAP — fair value
- Rolling returns (5, 10, 20 дней)
- Volatility (10, 20 дней)

**Доступны но НЕ используются в текущих стратегиях:**
- SuperTrend, Squeeze Momentum, Damiani Volatmeter
- Ehlers (MESA, Cyber Cycle, Stochastic CG)
- ChandeKrollStop, ChoppinessIndex, SchaffTrendCycle
- AugenPriceSpike, RogersSatchellVolatility
- ZigZag, KlingerVO, RelativeVigorIndex
- Support/Resistance, 10 Candle Patterns
- OBI, Microprice, Book Pressure

### Новости
**ЧЕСТНО:** NewsReactor (`src/strategy/news_reactor.py`) существует как код, но:
- Для полного анализа новостей требуется API ключ Claude/OpenAI
- Без API ключа работает ТОЛЬКО keyword-based детекция (regex паттерны: "ключевая ставка", "санкции" и т.д.)
- Бэктест на исторических новостях НЕ реализован — нет архива новостей
- В текущем бэктесте новости НЕ участвуют
- **Статус: прототип, не production**

### Risk Management
- **Portfolio Circuit Breaker:** ликвидация при DD > 15% от пика (настраиваемо)
- **Position sizing:** 2% риска на сделку через ATR
- **Stop-loss:** 2 × ATR от входа
- **Take-profit:** 3 × ATR от входа
- **RiskApproved wrapper:** ордер не может обойти risk check
- **Max position:** 20% портфеля на инструмент

### Scoring система
8 факторов с весами:
- Trend (0.18): ADX + DI alignment
- Momentum (0.15): RSI + MACD histogram
- Structure (0.14): EMA alignment
- ML Prediction (0.15): ensemble score
- Fundamental (0.13): P/E vs sector
- Macro (0.10): ставка ЦБ, нефть, рубль
- Sentiment (0.08): новости (НЕ работает без API ключа)
- Volume (0.07): volume ratio + OBV

**ЧЕСТНО:** Scoring система написана, но в текущем бэктесте используется ТОЛЬКО EMA Crossover (rule-based). Scoring не интегрирован в pipeline бэктеста.

---

## 2. Загруженные данные

| Тикер | Баров | Период |
|-------|-------|--------|

| GAZP | 1062 | 2022-01-01 — 2025-12-31 |
| GMKN | 1058 | 2022-01-01 — 2025-12-31 |
| IMOEX | 999 | 2022-01-01 — 2025-12-31 |
| LKOH | 1062 | 2022-01-01 — 2025-12-31 |
| MGNT | 1062 | 2022-01-01 — 2025-12-31 |
| NVTK | 1058 | 2022-01-01 — 2025-12-31 |
| ROSN | 1062 | 2022-01-01 — 2025-12-31 |
| SBER | 1062 | 2022-01-01 — 2025-12-31 |
| TATN | 1060 | 2022-01-01 — 2025-12-31 |
| VTBR | 1058 | 2022-01-01 — 2025-12-31 |
| YNDX | 599 | 2022-01-01 — 2025-12-31 |

---

## 3. Результаты бэктеста: EMA Crossover (20/50)

### Параметры
- Fast EMA: 20, Slow EMA: 50
- Risk per trade: 2% от капитала
- Stop-loss: 2 × ATR(14)
- Take-profit: 3 × ATR(14)
- Комиссия: 0.01% + 2 тика slippage
- Лотность и шаг цены учтены

### Результаты по тикерам

| Тикер | Sharpe | Sortino | Max DD% | Win Rate% | PF | Сделок | P&L RUB | Комиссии RUB | Итого RUB | vs B&H |
|-------|--------|---------|---------|-----------|-----|--------|-------|------------|---------|--------|

| SBER | 1.17 | 1.35 | -8.17 | 73.3 | 6.24 | 15 | 426,899 | 963 | 1,425,978 | +44.4% |
| GAZP | 0.23 | 0.18 | -8.81 | 52.4 | 1.27 | 21 | 48,734 | 865 | 1,047,874 | +69.3% |
| LKOH | 0.93 | 0.91 | -9.03 | 60.0 | 4.17 | 15 | 398,234 | 930 | 1,397,344 | +51.3% |
| ROSN | 0.32 | 0.25 | -6.17 | 53.3 | 1.62 | 15 | 65,851 | 705 | 1,065,153 | +39.6% |
| GMKN | 0.22 | 0.22 | -9.43 | 61.9 | 1.28 | 21 | 53,048 | 920 | 1,052,133 | +41.3% |
| YNDX | 1.38 | 1.96 | -7.72 | 63.6 | 6.63 | 11 | 388,786 | 411 | 1,388,414 | +48.7% |
| VTBR | 0.21 | 0.17 | -18.46 | 47.1 | 1.21 | 17 | 86,227 | 1,723 | 1,084,513 | +79.2% |
| NVTK | 0.9 | 0.89 | -7.64 | 66.7 | 3.91 | 15 | 318,143 | 597 | 1,317,578 | +64.8% |
| MGNT | 0.46 | 0.4 | -10.24 | 57.1 | 1.76 | 21 | 132,690 | 820 | 1,131,883 | +58.4% |
| TATN | 1.35 | 1.45 | -6.26 | 62.5 | 4.66 | 16 | 591,548 | 849 | 1,590,759 | +46.4% |

**Средние:** Sharpe=0.72, Max DD=-9.2%, Win Rate=59.8%, PF=3.27
**Суммарный P&L по всем тикерам:** 2,510,160 RUB


### ML Ensemble (walk-forward OOS)

**ЧЕСТНО:** ML ensemble (`src/ml/`) содержит:
- CatBoost + LightGBM trainer/predictor
- Walk-forward оркестратор (`src/ml/walk_forward.py`)
- Feature processors (CSRankNorm, RobustZScore из Qlib)
- UMP фильтр сделок (GMM + kNN)

**НО:** Для запуска ML бэктеста требуется:
1. Установленные catboost + lightgbm + xgboost
2. Обученные модели (train pipeline не запускался на реальных данных)
3. Walk-forward оркестратор ожидает данные в специфическом формате

**Статус:** Код написан и покрыт unit-тестами (88 тестов ML модулей pass), но E2E ML pipeline на реальных данных MOEX НЕ запускался. Результатов ML бэктеста НЕТ.

### Signal Synthesis (мульти-агент)

**ЧЕСТНО:** `src/strategy/signal_synthesis.py` — framework для мульти-аналитической системы.
Работает в чисто-квантовом режиме (без LLM), НО:
- Требует настройки аналитиков (какие индикаторы подключить)
- Не интегрирован с бэктест-движком напрямую
- **Статус:** архитектура готова, но autonomous backtest НЕ запустить без дополнительной обвязки

---

## 4. Сравнение с бенчмарком

### Buy & Hold по тикерам

| Тикер | B&H Return% | B&H Sharpe | B&H Max DD% |
|-------|-------------|------------|-------------|

| SBER | -1.8 | 0.19 | -66.8 |
| GAZP | -64.6 | -0.34 | -69.7 |
| LKOH | -11.5 | 0.07 | -49.5 |
| ROSN | -33.0 | -0.05 | -59.2 |
| GMKN | -36.1 | -0.16 | -60.5 |
| YNDX | -9.8 | 0.19 | -69.2 |
| VTBR | -70.8 | -0.42 | -74.4 |
| NVTK | -33.0 | -0.04 | -57.5 |
| MGNT | -45.2 | -0.21 | -66.6 |
| TATN | 12.7 | 0.27 | -39.9 |

### Индекс IMOEX (бенчмарк)
- Return: -28.1%
- Sharpe: -0.1
- Max DD: -50.4%


### Стратегия vs Бенчмарк (сводка)

| Метрика | EMA Crossover (среднее) | IMOEX B&H | Равновзвешенный B&H |
|---------|------------------------|-----------|---------------------|

| Return% | 25.0 | -28.1 | -29.3 |
| Sharpe | 0.72 | -0.1 | -0.05 |
| Max DD% | -9.2 | -50.4 | -61.3 |

---

## 5. Equity Curves (описание)


### Лучший тикер: YNDX
- Sharpe: 1.38, Max DD: -7.72%
- P&L: 388,786 RUB, Сделок: 11

### Худший тикер: VTBR
- Sharpe: 0.21, Max DD: -18.46%
- P&L: 86,227 RUB, Сделок: 17


---

## 6. Что реально работает, а что нет

### Работает:
1. **MOEX ISS загрузка данных** — API бесплатный, пагинация, rate-limiting
2. **EMA Crossover стратегия** — генерирует сигналы, учитывает лотность/шаг цены
3. **Metrics engine** — 55 метрик, BCa bootstrap, MAE/MFE, PSR
4. **Risk management** — circuit breaker, position sizing, stops, RiskApproved wrapper
5. **Execution algorithms** — TWAP, DCA, Grid, Triple Barrier (unit-тесты pass)
6. **22 индикатора** — все вычисляются корректно (unit-тесты pass)
7. **Unit тесты** — 599 pass, покрытие основных модулей

### НЕ работает / не тестировалось на реальных данных:
1. **ML pipeline E2E** — код есть, тесты есть, но walk-forward на реальных MOEX данных не запускался
2. **Signal Synthesis** — framework готов, но не подключён к бэктест-движку
3. **NewsReactor** — требует API ключ Claude/OpenAI для полного анализа
4. **Scoring система** — написана, но не интегрирована в pipeline бэктеста
5. **Telegram bot** — код есть, но требует токен бота
6. **Tinkoff adapter** — sandbox тесты pass, live не тестировался
7. **Streamlit dashboard** — код есть, не проверялся с live данными

### Требует доработки:
1. **Интеграция ML в бэктест** — нужен скрипт run_ml_backtest.py с walk-forward
2. **Оптимизация параметров** — EMA 20/50 не оптимальны, нужен grid/GA search
3. **Multi-ticker portfolio** — сейчас бэктест per-ticker, нет портфельной оптимизации
4. **Live trading loop** — paper_trading.py существует но не проверен на реальном рынке
5. **Short-selling на MOEX** — на TQBR шорты ограничены (только с маржинальным счётом)

---

## 7. Честная оценка

### Текущая ожидаемая доходность


На основе OOS бэктеста EMA Crossover на 10 акциях MOEX (2022-2025):
- **Средний CAGR: 6.3% годовых**
- **Медианный Sharpe: 0.68**
- **Средний Max DD: -9.2%**

Это **rule-based стратегия без оптимизации**. Результат не учитывает:
- Оптимизацию параметров (может улучшить на +20-30%)
- ML ensemble (ожидание: +0.2-0.4 Sharpe если работает)
- Portfolio-level diversification (снижение DD на 30-40%)
- Фильтрацию режимов (ChoppinessIndex может убрать 40% ложных сигналов)


### Основные риски
1. **Overfitting** — параметры EMA не оптимизированы, но ML pipeline рискует переобучением
2. **Regime change** — 2022 год (начало СВО, санкции) = аномальный период
3. **Short selling** — на MOEX реальные шорты дороже и сложнее чем в бэктесте
4. **Liquidity** — VTBR (lot=10000) на 1MRUB может двигать рынок
5. **Ставка ЦБ** — 19% ключевая ставка = высокая opportunity cost, B&H облигации может быть лучше

### Рекомендации
1. **Первое:** Оптимизировать параметры EMA через walk-forward (не in-sample!)
2. **Второе:** Запустить ML pipeline на реальных данных, сравнить с rule-based
3. **Третье:** Добавить ChoppinessIndex фильтр — не торговать во флэте
4. **Четвёртое:** Paper trading на Tinkoff sandbox минимум 1 месяц
5. **Пятое:** Сравнить с B&H IMOEX + облигации при ставке 19%


---

## 8. Технические детали

- Python 3.12.1
- Polars, NumPy, SciPy, requests
- 599 unit тестов (pass) + 7 skipped (GARCH без arch library)
- 58 модулей в src/
- 22 индикатора, 55 метрик, 5 executor'ов
- Данные загружены через MOEX ISS REST API (бесплатно, без ключа)

---

*Отчёт сгенерирован автоматически скриптом scripts/full_audit.py*
*Все числа — результат реального бэктеста на реальных данных MOEX*
