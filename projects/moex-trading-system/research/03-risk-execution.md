# Deep Research: Продвинутый риск-менеджмент, исполнение ордеров и инфраструктура

> Дата исследования: 2026-03-18
> Домен: алготрейдинг, Python, MOEX
> Контекст: moex-trading-system (Python 3.12, SQLite, Claude API, aiomoex, Polars)

---

## Статистика исследования

| Метрика | Значение |
|---------|---------|
| Поисковых запросов | 10 |
| Источников найдено | 45+ |
| Источников проанализировано | 18 |
| Вариантов/библиотек обнаружено | 25+ |
| Противоречий между источниками | 2 |

---

## 1. ПРОДВИНУТЫЙ РИСК-МЕНЕДЖМЕНТ

### 1.1 Riskfolio-Lib -- РЕКОМЕНДОВАН для портфельного риска

| Параметр | Значение |
|----------|---------|
| GitHub | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) |
| Stars | 3.8k |
| Лицензия | BSD-3-Clause |
| Python | 3.9+ |
| Последнее обновление | 2024 (стабильный релиз) |
| PyPI | pip install Riskfolio-Lib |
| Уверенность | ВЫСОКАЯ (3+ источника) |

**Ключевые возможности:**
- 24 выпуклые меры риска: CVaR, EVaR, CDaR, MaxDrawdown, Ulcer Index
- Kelly Criterion через Logarithmic Mean Risk оптимизацию
- Monte Carlo VaR/CVaR через интеграцию с scipy
- Factor risk models (Ross APT)
- Black-Litterman, HRP, HERC, NCO кластерные методы
- Risk Parity / Risk Budgeting

**Плюсы:**
- Максимальное количество risk measures из всех Python-библиотек (24)
- Встроенный Kelly Criterion (Logarithmic Mean Risk)
- Отличная документация с визуализациями
- Построен на CVXPY -- можно подключить промышленные солверы (MOSEK, GUROBI)

**Минусы:**
- Тяжёлые зависимости (CVXPY, scikit-learn, statsmodels)
- BSD-3 с дополнительной коммерческой лицензией (LICENSE-XL)
- Не предназначен для real-time; скорее для ребалансировки портфеля

**Когда выбирать:** Нужна портфельная оптимизация с продвинутыми мерами риска, Kelly Criterion для позиционирования.

---

### 1.2 QuantStats -- РЕКОМЕНДОВАН для аналитики и отчётности

| Параметр | Значение |
|----------|---------|
| GitHub | [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) |
| Stars | 6.9k |
| Лицензия | Apache 2.0 |
| Python | 3.10+ |
| Последнее обновление | Январь 2026 (v0.0.81) |
| PyPI | pip install quantstats |
| Уверенность | ВЫСОКАЯ (5+ источников) |

**Ключевые возможности:**
- 54+ аналитических метрик: Sharpe, Sortino, Calmar, CAGR, MaxDD, VaR, CVaR
- Monte Carlo симуляция в модуле stats
- HTML tear sheets (одним вызовом qs.reports.html())
- Графики: drawdown, rolling Sharpe, monthly returns heatmap
- Сравнение с бенчмарком

**Плюсы:**
- Самая популярная Python-библиотека для торговой аналитики (6.9k stars)
- Генерация HTML-отчётов одной строкой
- Активно обновляется (январь 2026)
- Легко интегрируется -- принимает pandas Series доходностей

**Минусы:**
- Только пост-анализ (не real-time risk management)
- Зависимость от yfinance (для бенчмарков; для MOEX нужен свой источник)
- Не рассчитывает Kelly Criterion

**Когда выбирать:** Аналитика торговых результатов, генерация отчётов, визуализация drawdown.

---

### 1.3 Empyrical-Reloaded -- для вычисления метрик в коде

| Параметр | Значение |
|----------|---------|
| GitHub | [stefan-jansen/empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) |
| Stars | 101 |
| Лицензия | Apache 2.0 |
| Python | 3.10+ |
| Последнее обновление | Июнь 2025 (v0.5.12) |
| PyPI | pip install empyrical-reloaded |
| Уверенность | СРЕДНЯЯ (2 источника) |

**Ключевые возможности:**
- Sharpe, Sortino, Calmar, Alpha, Beta, VaR, Max Drawdown
- Rolling window агрегации метрик
- Лёгкий -- минимум зависимостей (numpy, pandas, scipy)
- Используется как backend для pyfolio/zipline

**Плюсы:**
- Лёгкий и быстрый -- идеален для встраивания в Risk Gateway
- Чистый API для программного вычисления метрик
- Активный форк оригинального Quantopian empyrical

**Минусы:**
- Малое комьюнити (101 star)
- Нет визуализации (только числа)
- Нет Kelly Criterion

**Когда выбирать:** Нужен лёгкий вычислитель метрик для встраивания в Risk Gateway.

---

### 1.4 Собственная реализация Kelly / VaR / CVaR

| Параметр | Значение |
|----------|---------|
| Сложность | Средняя |
| Зависимости | numpy, scipy (уже есть через другие пакеты) |
| Уверенность | ВЫСОКАЯ (хорошо документированные формулы) |

**Реализуемые формулы:**



**Когда выбирать:** Для базового Kelly sizing и VaR/CVaR в Risk Gateway без внешних зависимостей.


---

## 2. ПОРТФЕЛЬНАЯ ОПТИМИЗАЦИЯ

### 2.1 Сравнительная таблица библиотек

| Критерий | PyPortfolioOpt | Riskfolio-Lib | skfolio | cvxportfolio |
|----------|---------------|---------------|---------|-------------|
| **GitHub** | [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | [skfolio](https://github.com/skfolio/skfolio) | [cvxportfolio](https://github.com/cvxgrp/cvxportfolio) |
| **Stars** | 5.6k | 3.8k | 1.8k | 1.2k |
| **Лицензия** | MIT | BSD-3 | BSD-3 | GPL-3.0 |
| **Risk measures** | 5-6 | 24 | 15+ | 5-6 |
| **Kelly Criterion** | Нет | Да (Log Mean Risk) | Нет | Нет |
| **Black-Litterman** | Да | Да | Да | Нет |
| **HRP/HERC** | Да | Да | Да | Нет |
| **sklearn API** | Нет | Нет | Да | Нет |
| **Cross-validation** | Нет | Нет | Да | Нет |
| **Transaction costs** | Нет | Нет | Нет | Да |
| **Multi-period** | Нет | Нет | Нет | Да |
| **Простота входа** | Высокая | Средняя | Средняя | Низкая |
| **Документация** | Отличная | Хорошая | Хорошая | Средняя |

### 2.2 Рекомендации по выбору

1. **PyPortfolioOpt** -- простая портфельная оптимизация (Efficient Frontier, BL). MIT лицензия.
2. **Riskfolio-Lib** -- продвинутые риск-меры и Kelly. Больше математики.
3. **skfolio** -- ML-пайплайн, sklearn API, cross-validation для финансовых данных.
4. **cvxportfolio** -- multi-period бэктестинг с transaction costs. GPL лицензия.

---

## 3. EXECUTION АЛГОРИТМЫ

### 3.1 TWAP (Time-Weighted Average Price)

Разбить ордер на равные части, отправлять через равные интервалы.

Применимость для MOEX:
- Подходит для дневного таймфрейма (разбить на 5-10 частей в течение сессии)
- Не требует данных об объёмах
- Простая реализация на asyncio

### 3.2 VWAP (Volume-Weighted Average Price)

Размер каждого слайса пропорционален историческому объёму в этот период.

Применимость для MOEX:
- Требует исторический volume profile (доступен через MOEX ISS / aiomoex)
- Лучше чем TWAP при высокой ликвидности (голубые фишки MOEX)
- Для малоликвидных бумаг может быть хуже TWAP

### 3.3 Iceberg Orders

Показывать в стакане только часть ордера, пополняя по мере исполнения.

Применимость для MOEX:
- Многие брокеры MOEX поддерживают iceberg orders нативно
- Через Tinkoff API: нет прямой поддержки, реализуется программно
- Полезно для позиций > 1% дневного объёма тикера

### 3.4 Брокерские API для MOEX

| API | GitHub | Stars | Фьючерсы | Тип |
|-----|--------|-------|----------|-----|
| [Tinkoff invest-python](https://github.com/Tinkoff/invest-python) | Tinkoff/invest-python | 345 | Да | gRPC (sync/async) |
| [TKSBrokerAPI](https://github.com/Tim55667757/TKSBrokerAPI) | Tim55667757/TKSBrokerAPI | 37 | Да | REST |
| [MOEX ISS](https://www.moex.com/a2193) | Официальный | -- | Данные | REST |
| [aiomoex](https://pypi.org/project/aiomoex/) | В проекте | -- | Данные | async REST |

**Рекомендация:** Tinkoff invest-python для исполнения ордеров (gRPC, async, фьючерсы). Для данных оставить aiomoex.

---

## 4. МОНИТОРИНГ И АЛЕРТЫ

### 4.1 Telegram-бот -- РЕКОМЕНДОВАН (MVP)

| Параметр | Значение |
|----------|---------|
| Библиотека | aiogram 3.x |
| Сложность | Низкая |
| Зависимости | 1 пакет |

**Что мониторить:** открытие/закрытие позиций, срабатывание риск-правил, ежедневный PnL, ошибки системы, утренний брифинг.

**Уровни алертов:**
- INFO: открытие позиции, ежедневный отчёт
- WARNING: drawdown 10%, приближение к лимитам
- CRITICAL: drawdown 20%, остановка торговли
- ERROR: системные ошибки

### 4.2 Grafana + Prometheus -- для продвинутого мониторинга

Стек: Grafana + Prometheus + Docker Compose. Метрики через prometheus-client:
portfolio_value, daily_pnl, drawdown_pct, open_positions, risk_utilization, order_latency.

Grafana -> Telegram алерты: нативная интеграция.

**Когда выбирать:** Когда система стабильна и нужен visual monitoring. Не для MVP.

### 4.3 OpenAlgo -- reference architecture

| Параметр | Значение |
|----------|---------|
| GitHub | [marketcalls/openalgo](https://github.com/marketcalls/openalgo) |
| Stars | 1.5k |
| Стек | Flask + React + SQLAlchemy |

Ориентирован на индийских брокеров. Для MOEX потребуется адаптер. Использовать как reference.


---

## 5. ИНФРАСТРУКТУРА

### 5.1 База данных: SQLite vs DuckDB vs TimescaleDB vs ClickHouse

| Критерий | SQLite (текущий) | DuckDB | TimescaleDB | ClickHouse |
|----------|-----------------|--------|-------------|------------|
| **Тип** | Встроенная | Встроенная | Серверная (PG) | Серверная |
| **OLAP** | Слабо | Отлично | Хорошо | Отлично |
| **OLTP** | Хорошо | Слабо | Хорошо (ACID) | Слабо |
| **Time-series** | Нет | Нет | Нативно | Хорошо |
| **Concurrent writes** | 1 writer | 1 writer | Много | Много |
| **Сжатие** | Нет | Отличное | Хорошее | Отличное |
| **Python async** | aiosqlite | duckdb (sync) | asyncpg | clickhouse-driver |
| **Развёртывание** | Файл | Файл | Docker/сервер | Docker/сервер |
| **RAM** | ~0 | ~50MB+ | ~256MB+ | ~512MB+ |
| **Для бэктестинга** | Медленно | Очень быстро | Быстро | Очень быстро |
| **Для торговли** | Достаточно | Не идеально | Хорошо | Избыточно |

**Рекомендация по фазам:**

1. **MVP (сейчас):** SQLite -- уже работает, достаточно для D1, 1 writer. Менять не нужно.
2. **Аналитика/бэктестинг:** DuckDB как read-only движок. Читает SQLite напрямую.
3. **Масштабирование:** TimescaleDB -- PostgreSQL-совместимая, ACID, хорошо для tick data.
4. **Тяжёлая аналитика:** ClickHouse -- если > 100GB данных.

### 5.2 Docker-инфраструктура

docker-compose.yml (Phase 2): trading-system + prometheus + grafana.

### 5.3 VPS и отказоустойчивость

| Провайдер | Тариф | RAM | CPU | Рекомендация |
|-----------|-------|-----|-----|-------------|
| Timeweb Cloud | ~500 руб/мес | 2GB | 1 vCPU | MVP |
| Selectel | ~700 руб/мес | 2GB | 1 vCPU | Продвинутый |
| Yandex Cloud | ~800 руб/мес | 2GB | 2 vCPU | Enterprise |

**Fallback стратегия:**
1. Основной: VPS в Москве (минимальная латенция до MOEX)
2. Резервный: Локальная машина с auto-failover
3. Мониторинг: Telegram-бот проверяет heartbeat каждые 5 минут
4. При падении VPS: автоматическое закрытие всех позиций

---

## 6. QUANTSTATS -- ПОДРОБНЫЙ РАЗБОР

### 6.1 Ключевые метрики (54+)

| Категория | Метрики |
|-----------|---------|
| **Доходность** | CAGR, MTD, YTD, Total return, Rolling returns |
| **Риск** | Sharpe, Sortino, Calmar, Omega, VaR, CVaR, Max Drawdown |
| **Drawdown** | Max DD, DD Duration, Recovery time, Underwater plot |
| **Торговля** | Win rate, Avg win/loss, Profit factor, Payoff ratio |
| **Сравнение** | Alpha, Beta, R-squared, Tracking error, Info ratio |
| **Распределение** | Skewness, Kurtosis, Best/Worst day/month/year |

---

## СРАВНИТЕЛЬНАЯ ТАБЛИЦА -- РИСК-МЕНЕДЖМЕНТ

| Критерий | Riskfolio-Lib | QuantStats | empyrical-reloaded | Своя реализация |
|----------|:------------:|:----------:|:------------------:|:--------------:|
| Релевантность | 5/5 | 4/5 | 3/5 | 4/5 |
| Зрелость | 4/5 | 5/5 | 3/5 | 2/5 |
| Простота | 3/5 | 5/5 | 4/5 | 4/5 |
| Актуальность | 4/5 | 5/5 | 4/5 | 5/5 |
| Совместимость | 4/5 | 4/5 | 5/5 | 5/5 |
| Сообщество | 4/5 | 5/5 | 2/5 | 1/5 |
| **ИТОГО** | **24/30** | **28/30** | **21/30** | **21/30** |

## СРАВНИТЕЛЬНАЯ ТАБЛИЦА -- ПОРТФЕЛЬНАЯ ОПТИМИЗАЦИЯ

| Критерий | PyPortfolioOpt | Riskfolio-Lib | skfolio | cvxportfolio |
|----------|:-------------:|:------------:|:-------:|:-----------:|
| Релевантность | 4/5 | 5/5 | 4/5 | 3/5 |
| Зрелость | 5/5 | 4/5 | 3/5 | 4/5 |
| Простота | 5/5 | 3/5 | 3/5 | 2/5 |
| Актуальность | 3/5 | 4/5 | 5/5 | 4/5 |
| Совместимость | 5/5 | 4/5 | 4/5 | 3/5 |
| Сообщество | 5/5 | 4/5 | 3/5 | 2/5 |
| **ИТОГО** | **27/30** | **24/30** | **22/30** | **18/30** |

---

## ПРОТИВОРЕЧИЯ И НЮАНСЫ

### Противоречие 1: DuckDB скорость
- Один бенчмарк: DuckDB в 3.5x быстрее TimescaleDB и 7.3x быстрее ClickHouse
- Другой бенчмарк: ClickHouse быстрее для OHLCV-агрегаций
- **Вывод:** Зависит от типа запросов. Для аналитических scan -- DuckDB. Для streaming inserts -- ClickHouse/TimescaleDB.

### Противоречие 2: Kelly Criterion applicability
- Академия: Kelly для максимизации long-term growth
- Практики: Half Kelly или Quarter Kelly для снижения волатильности
- **Вывод:** Использовать fractional Kelly (0.25-0.5) -- стандарт в индустрии.

### Нюанс: MOEX-специфика execution
- MOEX не поддерживает нативные TWAP/VWAP через стандартный API
- Нужна программная реализация поверх limit/market orders
- Тинькофф API поддерживает фьючерсы, но без продвинутых order types

---

## ВЕРДИКТ И ПЛАН ДЕЙСТВИЙ

### Phase 1: MVP Enhancement (сейчас)

| Действие | Библиотека | Приоритет |
|----------|-----------|-----------|
| Kelly sizing в Risk Gateway | Своя реализация | ВЫСОКИЙ |
| VaR/CVaR расчёт | Своя реализация (numpy/scipy) | ВЫСОКИЙ |
| Telegram-бот для алертов | aiogram>=3.0.0 | ВЫСОКИЙ |
| QuantStats для отчётов | quantstats>=0.0.81 | СРЕДНИЙ |
| TWAP execution | Своя реализация (asyncio) | СРЕДНИЙ |

**Добавить в requirements.txt:**


### Phase 2: Продвинутый риск (после стабилизации)

| Действие | Библиотека | Приоритет |
|----------|-----------|-----------|
| Портфельная оптимизация | PyPortfolioOpt или Riskfolio-Lib | СРЕДНИЙ |
| Monte Carlo бэктестинг | scipy + numpy | СРЕДНИЙ |
| DuckDB для аналитики | duckdb | НИЗКИЙ |
| VWAP execution | Своя реализация + volume profile | НИЗКИЙ |

### Phase 3: Инфраструктура (при масштабировании)

| Действие | Инструмент | Приоритет |
|----------|-----------|-----------|
| Docker-контейнеризация | Docker Compose | СРЕДНИЙ |
| VPS deploy (Москва) | Timeweb/Selectel | СРЕДНИЙ |
| Grafana мониторинг | Grafana + Prometheus | НИЗКИЙ |
| TimescaleDB миграция | Только если нужен tick data | НИЗКИЙ |

---

## ИСТОЧНИКИ

### Риск-менеджмент и портфельная оптимизация
- [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) -- 3.8k stars, 24 risk measures, Kelly
- [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) -- 5.6k stars, MIT, EF + BL
- [skfolio](https://skfolio.org/) -- 1.8k stars, sklearn API
- [cvxportfolio](https://github.com/cvxgrp/cvxportfolio) -- 1.2k stars, multi-period
- [QuantStats](https://github.com/ranaroussi/quantstats) -- 6.9k stars, 54+ метрик
- [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) -- 101 stars
- [IBKR VaR/CVaR Guide](https://www.interactivebrokers.com/campus/ibkr-quant-news/risk-metrics-in-python-var-and-cvar-guide/)
- [Monte Carlo VaR](https://trader-algoritmico.com/blog/monte-carlo-for-var-calculating-risk-exposure-in-python)

### Execution и MOEX API
- [Tinkoff invest-python](https://github.com/Tinkoff/invest-python) -- 345 stars, gRPC
- [TKSBrokerAPI](https://github.com/Tim55667757/TKSBrokerAPI) -- REST
- [MOEX ISS API](https://www.moex.com/a2193) -- официальные данные
- [Alpaca TWAP/VWAP](https://alpaca.markets/learn/algorithmic-trading-with-twap-and-vwap-using-alpaca)
- [QuantConnect VWAP](https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Execution/VolumeWeightedAveragePriceExecutionModel.py)

### Мониторинг
- [Grafana Telegram](https://grafana.com/blog/how-to-integrate-grafana-alerting-and-telegram/)
- [OpenAlgo](https://github.com/marketcalls/openalgo) -- 1.5k stars

### Базы данных
- [CH vs TimescaleDB Benchmark](https://sanj.dev/post/clickhouse-timescaledb-influxdb-time-series-comparison)
- [TS DB Benchmarks 2025](https://www.timestored.com/data/time-series-database-benchmarks)
- [7 DB Performance Test](https://medium.com/@ev_kozloski/timeseries-databases-performance-testing-7-alternatives-56a3415e6e9e)

### MOEX
- [Алготрейдинг.рф](https://xn--80agadetfnxfwx.xn--p1ai/)
- [MOEX Non-display](https://www.moex.com/ru/products/nondisplay)
- [Smart-Lab](https://smart-lab.ru/blog/1229593.php)
