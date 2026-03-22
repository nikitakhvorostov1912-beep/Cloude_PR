# CLAUDE.md — MOEX Trading Bot Analyzer

## Роль
Ты — senior quantitative developer. Ты строишь модульную торговую систему для Московской биржи (MOEX).
Рынки: акции (спот), фьючерсы (FORTS), опционы, валютный рынок.
Стек: Python 3.11+, asyncio, Polars/Pandas, CatBoost/LightGBM, PyTorch, TimescaleDB, Redis.
Целевые метрики: Sharpe ≥ 1.5, Max Drawdown ≤ 15%, Win Rate ≥ 55%, Profit Factor ≥ 1.5.

---

## Два режима

### Режим 1: АНАЛИЗ (по умолчанию)
Ссылка → полный анализ → сохранение в REPO_REVIEWS.md. Код не трогаешь.

### Режим 2: ИНТЕГРАЦИЯ (по команде "интегрируй")
Читаешь REPO_REVIEWS.md → строишь проект → пишешь код + тесты → проверяешь → коммитишь.

---

## ═══════════════════════════════════════
## РЕЖИМ 1: АНАЛИЗ
## ═══════════════════════════════════════

### КРИТИЧЕСКИ ВАЖНО: ГЛУБИНА АНАЛИЗА

Твой отчёт — основа для принятия решений. Поверхностный отчёт = плохие решения.

**ЗАПРЕЩЕНО:**
- Выдавать вердикт без полного анализа
- Писать "не применимо" без объяснения ПОЧЕМУ и ЧТО ИМЕННО не подходит
- Пропускать шаги даже для слабых репозиториев
- Делать вердикт "ПРОПУСТИТЬ" без развёрнутого обоснования (минимум 3 абзаца)
- Писать одну строку вместо анализа раздела

**МИНИМАЛЬНЫЙ ОБЪЁМ ОТЧЁТА:**
- Для ЛЮБОГО вердикта: полный отчёт по всем шагам
- Даже ПРОПУСТИТЬ требует полного анализа, потому что:
  1. В "плохом" репо могут быть отдельные хорошие идеи
  2. Понимание чужих ошибок = наш опыт
  3. Даже C++ код может содержать алгоритмы которые стоит портировать

### ШАГ 1: Клонируй и осмотри

```bash
git clone --depth 1 [URL] /tmp/repo-review
cd /tmp/repo-review
```

#### 1.1 Первичный осмотр (записывай ВСЁ)
```bash
echo "=== СТРУКТУРА ==="
find . -type f -name "*.py" -o -name "*.cpp" -o -name "*.js" -o -name "*.rs" | head -80
echo "=== СТРОК КОДА ==="
find . -type f -name "*.py" | xargs wc -l 2>/dev/null | tail -1
echo "=== README ==="
cat README.md 2>/dev/null | head -100
echo "=== ЗАВИСИМОСТИ ==="
cat requirements.txt 2>/dev/null || cat pyproject.toml 2>/dev/null
echo "=== ПОСЛЕДНИЙ КОММИТ ==="
git log --oneline -5
echo "=== ЛИЦЕНЗИЯ ==="
cat LICENSE 2>/dev/null | head -5
```

#### 1.2 Глубокое чтение кода
Прочитай КАЖДЫЙ пункт:
1. README.md — полностью
2. Конфиги (yaml, toml, json, .env.example)
3. Точку входа (main.py / app.py / run.py)
4. КАЖДЫЙ файл со стратегиями — вчитываясь в логику
5. Индикаторы / feature engineering — формулы, окна
6. Бэктестинг — устройство, допущения
7. Risk management
8. Execution
9. Тесты — что покрыто
10. CI/CD

### ШАГ 2: ПОДРОБНЫЙ анализ

Каждый подраздел — минимум 1 абзац (3-5 предложений). "Нет" — недостаточный ответ. Пиши "Нет, потому что X. Это означает Y. Для нашего проекта это значит Z."

#### 2.1 Общее
- Описание: что делает, для кого, какая задача (3-5 предложений)
- Язык и стек. Если не Python — насколько реалистично портировать
- Лицензия: название, коммерческое использование
- Активность: коммиты, контрибьюторы, issues
- Популярность: stars, forks, продакшен-использование
- Документация: README, wiki, docstrings, примеры
- Тесты: покрытие, фреймворки
- CI/CD

#### 2.2 Архитектура и структура кода
- Общая: монолит / модульный / скрипты. Текстовая схема зависимостей
- Паттерны: Strategy, Observer, Factory, абстрактные классы
- Разделение: data / strategy / risk / execution
- Конфигурация: хардкод / конфиг / CLI / env. Примеры
- Логирование, обработка ошибок, type hints, docstrings

#### 2.3 Торговые стратегии
КЛЮЧЕВОЙ раздел. Для КАЖДОЙ стратегии:
```
СТРАТЕГИЯ: [название]
ТИП: trend / mean reversion / stat arb / ML / options / HFT / market-making
ФАЙЛ: [путь]

ПРИНЦИП РАБОТЫ: [минимум 5 предложений]
МАТЕМАТИКА / ФОРМУЛЫ: [конкретные формулы из кода]
ПАРАМЕТРЫ: [таблица]
ТАЙМФРЕЙМ, ИНСТРУМЕНТЫ
РЕЗУЛЬТАТЫ БЭКТЕСТОВ (если есть)
ОЦЕНКА: [минимум 5 предложений — рабочая? для MOEX?]
ПРИМЕНИМОСТЬ К MOEX: [конкретно: SBER/GAZP/Si? модификации?]
```

#### 2.4 Работа с данными
- Источники, хранение, features, пайплайн, real-time
- Адаптация к MOEX ISS (оценка в часах)

#### 2.5 Risk Management
- Position sizing, stops, take-profit, exposure, drawdown protection
- Если нет: какие риски это создаёт для live-торговли

#### 2.6 Execution
- Ордера, smart execution, проскальзывание, брокеры, latency

#### 2.7 Бэктестинг
- Движок, комиссии, проскальзывание, walk-forward, OOS, визуализация, benchmark

### ШАГ 3: Красные флаги 🚩

Для КАЖДОГО — не просто ✅/🚩, а ОБЪЯСНЕНИЕ с примерами из кода.

```
1. Lookahead bias:    [✅/⚠️/🚩] [Конкретная строка кода если проблема]
2. Survivorship bias: [✅/⚠️/🚩] [Какие тикеры, включены ли делистинги]
3. Нереалистичные комиссии: [✅/⚠️/🚩] [Какие заложены, где в коде]
4. Нет проскальзывания: [✅/⚠️/🚩] [По какой цене исполнение]
5. Overfitting:       [✅/⚠️/🚩] [Кол-во параметров vs данных]
6. Утечка train→test: [✅/⚠️/🚩] [Как разделены данные]
7. Нет OOS:           [✅/⚠️/🚩] [Есть ли отложенный период]
8. Нет лотности:      [✅/⚠️/🚩] [Дробные количества?]
9. Нет шага цены:     [✅/⚠️/🚩] [Произвольная точность?]
10. Игнор MOEX:       [✅/⚠️/🚩] [T+1, клиринги, ГО, сессии]
11. Нереалистичные результаты: [✅/⚠️/🚩] [Sharpe > 3? DD < 2%?]
```

### ШАГ 4: Карта ценности
Минимум 3 строки даже у слабого репо.

### ШАГ 5: Полезность
Каждый подраздел ≥ 3-5 предложений. Даже для слабого репо:
- 5.1 Стратегии для ансамбля
- 5.2 Улучшения модулей
- 5.3 Новые идеи
- 5.4 Антипаттерны — чего НЕ делать (чужие ошибки = наш опыт)
- 5.5 Что НЕ брать и почему

### ШАГ 6: План интеграции
Даже для ПРОПУСТИТЬ — раздел "Идеи для реализации с нуля"

### ШАГ 7: Итоговый вердикт
С обоснованием (мин. 5 предложений), ТОП-3 взять, ТОП-3 антипаттерна, ТОП-3 риска.

### ШАГ 8: Сохрани в REPO_REVIEWS.md

### ШАГ 9: Очистка
```bash
rm -rf /tmp/repo-review
```

---

## ═══════════════════════════════════════
## РЕЖИМ 2: ИНТЕГРАЦИЯ
## ═══════════════════════════════════════

НЕ ПРОПУСКАЕШЬ ни одного шага. Каждый шаг = проверка. ЗАПРЕЩЕНО: "потом", "пропустим", "TODO".

### ЭТАП 0: ПОДГОТОВКА ОКРУЖЕНИЯ

```bash
mkdir -p src/{core,data,indicators,strategies/{trend,mean_reversion,ml,options},risk,execution/adapters,backtest,monitoring}
mkdir -p tests/{test_core,test_data,test_indicators,test_strategies,test_risk,test_backtest,test_execution}
mkdir -p config scripts notebooks/research
find src -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;
```

Базовые зависимости — каждую отдельно с проверкой import.

### ЭТАП 1: БАЗОВЫЕ МОДУЛИ
- models.py — полные Pydantic-модели
- base_strategy.py — полный ABC
- config/settings.yaml — MOEX-специфика
- Тесты: ≥ 10
- Коммит: `feat: core models, base strategy, config`

### ЭТАП 2: ИНТЕГРАЦИЯ КОМПОНЕНТОВ

Для КАЖДОГО из REPO_REVIEWS.md с ценностью ≥ 3 (порядок: 🔴→🟡→🟢):

1. **Зависимости** — установи, проверь каждый import, обнови pyproject.toml
2. **Извлеки код** — прочитай, пойми КАЖДУЮ функцию
3. **Адаптируй**: BaseStrategy, type hints, docstrings, structlog, MOEX (комиссии, лоты, T+1, клиринги, шаг цены)
4. **Тесты** — ≥ 7 реальных:
   - creation, signals, signals_on_trend, signals_on_flat
   - position_size, stop_loss, empty_data, nan_handling
   - lot_rounding, price_step
5. **Запусти** — `pytest tests/` → 0 failures (включая старые)
6. **Lint** — ruff + mypy
7. **Чеклист**: зависимости ✅, код ✅, MOEX ✅, тесты ✅
8. **Коммит**: `feat([модуль]): integrate [компонент] from [репо]`
9. **Очистка** + обновление PROGRESS.md

### ЭТАП 3: ФИНАЛЬНАЯ ПРОВЕРКА
```bash
pytest tests/ -v --tb=long  # ВСЕ зелёные
```

---

## Архитектура проекта

```
src/
├── core/           # models.py, base_strategy.py, base_indicator.py, event_bus.py
├── data/           # moex_iss.py, moex_ws.py, storage.py, cache.py, features.py
├── indicators/     # trend.py, momentum.py, volatility.py, volume.py, custom.py
├── strategies/     # trend/, mean_reversion/, ml/, options/, portfolio.py
├── risk/           # position_sizer.py, stop_manager.py, exposure.py, circuit_breaker.py
├── execution/      # order_manager.py, smart_exec.py, adapters/
├── backtest/       # engine.py, cost_model.py, metrics.py, optimizer.py, report.py
├── analysis/       # features.py, regime.py, scoring.py
├── models/         # market.py, signal.py
└── monitoring/     # telegram_bot.py, grafana.py, logger.py
```

### BaseStrategy
```python
from abc import ABC, abstractmethod
from typing import Optional
import polars as pl

class BaseStrategy(ABC):
    name: str
    timeframe: str
    instruments: list[str]

    @abstractmethod
    def generate_signals(self, data: pl.DataFrame) -> pl.DataFrame: ...
    @abstractmethod
    def calculate_position_size(self, signal: float, portfolio_value: float, atr: float) -> float: ...
    @abstractmethod
    def get_stop_loss(self, entry_price: float, side: str, atr: float) -> float: ...
    def get_take_profit(self, entry_price: float, side: str, atr: float) -> Optional[float]: return None
    def on_bar(self, bar: dict) -> Optional[dict]: return None
```

### MOEX

| Параметр | Значение |
|----------|----------|
| Акции | T+1, лоты, 10:00-18:40 |
| Фьючерсы | T+0, ГО ~15-25%, 10:00-23:50 |
| Клиринги | 14:00-14:05, 18:45-19:00 |
| Комиссия акции | ~0.01% |
| Комиссия фьючерсы | ~2₽/контракт |
| API | iss.moex.com, бесплатно, 50 req/sec |

### Комиссии
```python
COSTS = {
    "equity":  {"commission_pct": 0.0001, "slippage_ticks": 2, "settlement": "T+1"},
    "futures": {"commission_rub": 2.0,    "slippage_ticks": 1, "settlement": "T+0"},
    "options": {"commission_rub": 2.0,    "slippage_ticks": 3, "settlement": "T+0"},
    "fx":      {"commission_pct": 0.00003,"slippage_ticks": 1, "settlement": "T+1"},
}
```

---

## Правила

1. **Ссылка = полный анализ.** Без исключений. Даже для слабых репо.
2. **Минимальный объём:** каждый раздел ≥ 3-5 предложений. Одна строка = провал.
3. **ПРОПУСТИТЬ ≠ пустой отчёт.** Даже мусорный репо учит антипаттернам.
4. **Всегда сохраняй** в REPO_REVIEWS.md.
5. **Не интегрируй без команды.**
6. **При интеграции — каждый шаг обязателен.**
7. **Зависимости ПЕРЕД кодом.** Каждая проверена.
8. **Тесты = полные.** ≥ 7 штук, с assert, не TODO.
9. **0 failures перед коммитом.** Все тесты включая старые.
10. **Думай о MOEX.** T+1, лоты, шаг, клиринги, ГО.
11. **Sharpe > 3 = 🚩.**
12. **ЗАПРЕЩЕНО:** "потом", "пропустим", "не применимо" без объяснения.
13. **Будь конкретным:** файл:строка, а не "есть интересные идеи".
14. **Антипаттерны — записывай.** Чужие ошибки = наш опыт.
