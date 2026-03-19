# 01 — Trading Systems & GitHub: Open-source инструменты для алготрейдинга

> Дата: 2026-03-18 | Поисковых запросов: 8 | Источников: 35+

## A. Бэктест-фреймворки

### A1. VectorBT — РЕКОМЕНДОВАН для research
- **GitHub:** https://github.com/polakowo/vectorbt | ~4.5K stars
- **Подход:** Векторизированный бэктест на NumPy/Pandas/Numba. До 1000x быстрее event-driven.
- **Плюсы:** Молниеносная скорость, нативная интеграция с Pandas, Plotly визуализация
- **Минусы:** Нет live-trading, free-версия не развивается, PRO платная
- **Применимость:** ★★★★★ — идеален для массового перебора параметров стратегий

### A2. NautilusTrader — РЕКОМЕНДОВАН для production
- **GitHub:** https://github.com/nautechsystems/nautilus_trader | 15K stars
- **Подход:** Event-driven платформа институционального уровня. Ядро Rust, API Python. Asyncio-нативный.
- **Плюсы:** Единый код backtest == live, встроенный risk management, async (tokio + uvloop)
- **Минусы:** Крутая кривая обучения, нет готовой интеграции с MOEX
- **Применимость:** ★★★★★ — лучший долгосрочный выбор для asyncio-стека

### A3. Backtrader
- **GitHub:** https://github.com/mementum/backtrader | 21K stars
- **Подход:** Классический event-driven. Де-факто стандарт 10 лет.
- **Плюсы:** Есть backtrader_moexalgo + коннекторы Алор/Финам, огромная документация
- **Минусы:** Не поддерживается (проблемы с Python 3.10+), медленный
- **Применимость:** ★★★★☆ — быстрый старт с MOEX, но не для долгосрочной системы

### A4. Backtesting.py
- **GitHub:** https://github.com/kernc/backtesting.py | ~5K stars
- **Подход:** Минималистичный, лёгкий. HTML-отчёты.
- **Применимость:** ★★★☆☆ — для быстрого прототипирования

### A5. Zipline-Reloaded
- **GitHub:** https://github.com/stefan-jansen/zipline-reloaded | 1.6K stars
- **Подход:** Форк Zipline (Quantopian). Pipeline API.
- **Применимость:** ★★★☆☆ — для факторного анализа

### A6. Lean (QuantConnect)
- **GitHub:** https://github.com/QuantConnect/Lean | 18K stars
- **Подход:** Полный алго-движок. Python + C#.
- **Применимость:** ★★☆☆☆ — тяжеловесный, нет прямой поддержки MOEX

## B. MOEX-специфичные инструменты

### B1. moexalgo — РЕКОМЕНДОВАН
- **GitHub:** https://github.com/moexalgo/moexalgo | 135 stars | v2.5.9 (февраль 2026)
- **Подход:** Официальная Python-библиотека MOEX AlgoPack. 100+ метрик.
- **Плюсы:** Официальный продукт биржи, Super Candles, FUTOI, HI2
- **Минусы:** Требует подписку AlgoPack, Python >= 3.12
- **Применимость:** ★★★★★

### B2. backtrader_moexalgo
- **GitHub:** https://github.com/WISEPLAT/backtrader_moexalgo | 70 stars
- **Подход:** Мост Backtrader ↔ MOEX AlgoPack
- **Применимость:** ★★★☆☆ — для прототипирования

### B3. MOEX ISS API (бесплатный)
- **URL:** https://www.moex.com/a2193
- **Подход:** REST API. Свечи, котировки, история. Бесплатно.
- **Применимость:** ★★★★☆ — MVP-уровень, уже используется через aiomoex

## C. Брокерские API

### C1. Tinkoff invest-python
- **GitHub:** https://github.com/Tinkoff/invest-python | 345 stars | АРХИВ
- **Подход:** gRPC, async. Sandbox.
- **Применимость:** ★★★☆☆ — репо архивирован

### C2. FinamPy
- **GitHub:** https://github.com/cia76/FinamPy | 64 stars
- **Подход:** Finam Trade API v2.11.0
- **Применимость:** ★★★☆☆

### C3. AlorPy
- **GitHub:** https://github.com/cia76/AlorPy | 35 stars
- **Подход:** Alor Open API V2
- **Применимость:** ★★★☆☆ — низкие комиссии

### C4. OsEngine (C#)
- **GitHub:** https://github.com/AlexWan/OsEngine | 959 stars
- **Подход:** Полная торговая платформа. 8+ MOEX-коннекторов.
- **Применимость:** ★☆☆☆☆ — C#, не наш стек

## D. Библиотеки технического анализа

| Библиотека | Индикаторов | Установка | Скорость | Рекомендация |
|------------|:-----------:|-----------|----------|:------------:|
| **TA-Lib** | 200+ | Сложная (C) | ★★★★★ | Для production |
| **pandas-ta** | 150+ | pip install | ★★★★☆ | Для research |
| **ta** (bukosabino) | ~80 | pip install | ★★★☆☆ | Уже в стеке |

## E. Сравнительная таблица бэктест-фреймворков

| Критерий | VectorBT | Nautilus | Backtrader | Backtesting.py |
|----------|:--------:|:--------:|:----------:|:--------------:|
| MOEX-совместимость | ★★★ | ★★ | ★★★★★ | ★★ |
| Asyncio | ★★ | ★★★★★ | ★ | ★ |
| Скорость бэктеста | ★★★★★ | ★★★★★ | ★★ | ★★★★ |
| Live-trading | — | ★★★★★ | ★★★★ | — |
| Простота | ★★★ | ★★ | ★★★★ | ★★★★★ |

## Вердикт

**Рекомендуемый стек:**
1. **Данные:** moexalgo (платный) + MOEX ISS (бесплатный fallback)
2. **Research бэктест:** VectorBT (free) — массовый перебор параметров
3. **Production бэктест + live:** NautilusTrader — asyncio-нативный, единый код
4. **ТА:** pandas-ta (простая установка) или TA-Lib (скорость)
5. **Брокер:** FinamPy или AlorPy + BackTrader-коннекторы как reference
