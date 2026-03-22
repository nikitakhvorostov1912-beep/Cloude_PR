# Задача: Полностью прозрачный бэктест с журналом сделок

## Проблема

Предыдущий бэктест непрозрачен:
- Инструменты захардкожены (10 акций) — selector не выбирал
- Фьючерсы не торговались
- MiMo = neutral в бэктесте, не влиял ни на одну сделку
- ML не обучен
- Нет списка сделок — только P&L по месяцам
- Непонятно КАК и ПОЧЕМУ система приняла каждое решение

## Что нужно

Полностью прозрачный бэктест где КАЖДОЕ решение объяснено.

---

## Шаг 1: Запусти Instrument Selector РЕАЛЬНО

Не на хардкоженных 10 тикерах. А так:

```python
# 1. Загрузи ВСЕ ликвидные инструменты с MOEX
scanner = MarketScanner()
universe = await scanner.scan_universe()
print(f"Найдено инструментов: {len(universe)}")

# 2. Среди них АКЦИИ и ФЬЮЧЕРСЫ
equities = [i for i in universe if i.board == "TQBR"]
futures = [i for i in universe if i.board == "RFUD"]
print(f"Акции: {len(equities)}, Фьючерсы: {len(futures)}")

# 3. Загрузи данные по ВСЕМ
data = await scanner.load_all_candles(universe, "2022-01-01", "2025-12-31")

# 4. Запусти selector для КАЖДОГО торгового дня
for each trading day:
    selected = selector.select(universe, data_up_to_today)
    # selected.longs = ТОП-10 для покупки
    # selected.shorts = ТОП-5 для шорта
    # selected.skipped = что отфильтровано и ПОЧЕМУ
```

### В отчёте покажи:

```markdown
## Instrument Selection — пример дня 2024-01-15

### Scanned: 185 instruments
### Passed liquidity filter: 67

### TOP-10 LONG:
| # | Ticker | Type | Score | Technical | Scoring | ML | MiMo | Liquidity | Why selected |
|---|--------|------|-------|-----------|---------|-----|------|-----------|--------------|
| 1 | TATN   | Equity | 78 | 85 (strong uptrend) | 72 (macro OK) | N/A | +0.3 (oil sector) | 95 | Best composite |
| 2 | LKOH   | Equity | 75 | 80 | 68 | N/A | +0.3 | 98 | Oil sector strong |
| 3 | Si-3.24| Future | 71 | 75 | 65 | N/A | -0.1 | 99 | USD/RUB trend |
| ...

### TOP-5 SHORT:
| # | Ticker | Type | Score | Why selected |
| 1 | VTBR   | Equity | 22 | Bearish structure + weak sector |
| ...

### REJECTED (examples):
| Ticker | Score | Why rejected |
| GMKN   | 45    | Score between thresholds, no clear signal |
| FIVE   | 38    | Blacklisted (low liquidity days) |
| SBER   | 55    | Neutral — no strong signal either way |
```

---

## Шаг 2: Включи фьючерсы

Фьючерсы = 50% рынка. Они ДОЛЖНЫ торговаться.

### Что нужно:
1. Загрузи данные по фьючерсам: Si, RTS, BR, GOLD, NG (через MOEX ISS, board="RFUD")
2. Адаптируй комиссии: 2₽ за контракт (не 0.01%)
3. Адаптируй position sizing: учти ГО (15-25% от стоимости контракта)
4. Адаптируй расписание: фьючерсы торгуются до 23:50 (вечерняя сессия)
5. Шаг цены: Si=1, RTS=10, BR=0.01

### В отчёте:
- Сколько фьючерсов прошло ликвидный фильтр
- Какие были выбраны selector-ом
- Результаты по каждому фьючерсу отдельно
- Сравнение: акции vs фьючерсы (какой класс прибыльнее)

---

## Шаг 3: Журнал КАЖДОЙ сделки

Это ГЛАВНОЕ что отсутствует. Создай `TRADE_JOURNAL.md`:

```markdown
## Trade Journal — COMPLETE SYSTEM, 2022-2025

### Trade #1
- Date open: 2022-03-15
- Date close: 2022-03-22
- Instrument: SBER (equity, lot=10)
- Side: LONG
- Entry price: 145.30
- Exit price: 152.80
- Quantity: 300 shares (30 lots)
- Gross P&L: +2,250 RUB
- Commission: -4.35 RUB
- Slippage: -6.00 RUB
- Net P&L: +2,239.65 RUB
- Return: +1.54%
- Hold duration: 5 days
- Exit reason: Take Profit (Triple Barrier TP hit)

WHY ENTERED:
- EMA crossover: fast(20)=144.2 crossed above slow(50)=143.8 ✅
- Indicators: 8/11 bullish (SuperTrend UP, Squeeze releasing, RSI=58) ✅
- Scoring: 72/100 → weight 0.75 ✅
- Regime: uptrend ✅
- ML: N/A (not trained)
- MiMo: neutral (backtest mode)
- Composite: 72 → SELECTED as #3 long

WHY EXITED:
- Triple Barrier: TP at 152.95 (entry + 2.5×ATR) hit on day 5
- Stop was at: 139.15 (entry - 1.5×ATR) — never hit

### Trade #2
...
```

### Формат для КАЖДОЙ сделки:
```
| # | Date Open | Date Close | Ticker | Side | Entry | Exit | Qty | Net P&L | Return% | Duration | Exit Reason | Composite Score | Indicators Pro/Con |
```

### Итого в журнале:
- Все ~164 сделки за 2022-2025
- Для каждой: WHY ENTERED (какие факторы) и WHY EXITED
- Статистика: сколько закрыто по TP / SL / Time / Signal reverse

---

## Шаг 4: MiMo — покажи реальное влияние

В бэктесте MiMo = neutral. Но покажи КАК ОН БЫ повлиял если бы были новости:

### 4.1 Вызови MiMo для 10 ключевых дат 2022-2025

Для каждой даты дай MiMo контекст что происходило и попроси анализ:

```python
key_dates = [
    ("2022-02-24", "Начало СВО, санкции, MOEX закрыта"),
    ("2022-03-24", "MOEX открылась после месяца закрытия"),
    ("2022-09-21", "Мобилизация объявлена"),
    ("2023-02-01", "Рынок восстанавливается, ставка 7.5%"),
    ("2023-08-15", "ЦБ поднял ставку с 8.5% до 12%"),
    ("2023-12-15", "ЦБ поднял ставку до 16%"),
    ("2024-06-14", "Санкции против MOEX (НКЦ)"),
    ("2024-10-25", "ЦБ поднял ставку до 21%"),
    ("2025-02-14", "ЦБ сохранил ставку 21%"),
    ("2025-06-20", "Переговоры о мире, рынок растёт"),
]

for date, context in key_dates:
    response = await llm_client.chat_json(
        prompt=f"""Дата: {date}. Контекст: {context}.
        Ты — аналитик MOEX. Оцени влияние на каждый сектор.
        JSON: {{
            "banks": {{"sentiment": -1 to +1, "reasoning": "..."}},
            "oil_gas": {{"sentiment": -1 to +1, "reasoning": "..."}},
            "metals": {{"sentiment": -1 to +1, "reasoning": "..."}},
            "tech": {{"sentiment": -1 to +1, "reasoning": "..."}},
            "retail": {{"sentiment": -1 to +1, "reasoning": "..."}}
        }}""",
        system="Ты — профессиональный аналитик российского фондового рынка."
    )
    # Запиши ответ
```

### 4.2 Покажи: совпал ли MiMo с реальностью?

```markdown
## MiMo Accuracy Check

| Date | Event | MiMo said banks= | Real SBER next month | Match? |
|------|-------|-------------------|---------------------|--------|
| 2022-02-24 | СВО | -0.9 | -65% | ✅ Correct |
| 2023-08-15 | Ставка 12% | -0.6 | -8% | ✅ Correct |
| 2024-06-14 | Санкции MOEX | -0.7 | -15% | ✅ Correct |
| 2025-06-20 | Мир | +0.8 | +12% | ✅/❌ ? |
```

### 4.3 Посчитай: если бы MiMo влиял на бэктест

Для каждой из 10 дат: пересчитай что было бы если MiMo sentiment применить как множитель:
- MiMo = -0.9 для банков → позиция в SBER/VTBR уменьшена в 10 раз или закрыта
- MiMo = +0.8 для нефти → позиция в LKOH/ROSN увеличена

Покажи: Sharpe с MiMo vs без MiMo (на этих 10 ключевых точках).

---

## Шаг 5: Помесячный отчёт по прибыли — ПОДРОБНЫЙ

Не просто "SBER: январь +5K". А так:

```markdown
## Январь 2024 — Подробный отчёт

### Portfolio value: 1,045,230 → 1,052,780 (+7,550, +0.72%)

### Active positions on Jan 1:
| Ticker | Side | Entry | Current | Unrealized P&L |
| SBER   | Long | 268.5 | 272.1   | +10,800        |
| TATN   | Long | 645.0 | 641.2   | -3,800         |

### Trades in January:
| Date | Action | Ticker | Price | Qty | P&L | Reason |
| Jan 8 | CLOSE | TATN | 638.5 | 20 | -1,300 | Stop-loss hit |
| Jan 12| OPEN  | LKOH | 7,245 | 2 lots | — | EMA cross + 9/11 indicators |
| Jan 19| CLOSE | SBER | 275.3 | 30 lots | +6,800 | Take profit |
| Jan 25| OPEN  | Si-3.24 | 89,450 | 5 contr | — | USD weakness signal |

### Instrument selection changes in January:
| Date | Added | Removed | Reason |
| Jan 5 | LKOH | MGNT | LKOH: score 78, MGNT: score 41 |
| Jan 15 | Si-3.24 | — | Futures: strong USD/RUB trend |

### Risk events:
- None (max daily DD: -0.8% on Jan 8)

### MiMo analysis (live would produce):
- Banks: neutral (rate stable)
- Oil: positive (Brent $82 → $85)
```

Сделай такой отчёт для КАЖДОГО МЕСЯЦА за 2024 год (12 месяцев).
Для 2022-2023 и 2025 — сокращённый (только сводка).

---

## Шаг 6: Статистика сделок

```markdown
## Trade Statistics — Complete System

### Summary:
- Total trades: [N]
- Long trades: [N] ([%])
- Short trades: [N] ([%])
- Futures trades: [N] ([%])

### Win/Loss:
- Win rate (long): [%]
- Win rate (short): [%]
- Average win: [₽]
- Average loss: [₽]
- Largest win: [₽] ([ticker], [date])
- Largest loss: [₽] ([ticker], [date])
- Profit factor: [ratio]

### Exit reasons:
- Take Profit: [N] ([%])
- Stop Loss: [N] ([%])
- Time Limit: [N] ([%])
- Signal Reverse: [N] ([%])
- Circuit Breaker: [N] ([%])

### Duration:
- Average hold time: [days]
- Shortest trade: [days] ([ticker])
- Longest trade: [days] ([ticker])

### By instrument type:
| Type | Trades | Win Rate | Avg P&L | Total P&L | Sharpe |
| Equities | ... | ... | ... | ... | ... |
| Futures | ... | ... | ... | ... | ... |

### By sector:
| Sector | Trades | Win Rate | Total P&L |
| Banks | ... | ... | ... |
| Oil & Gas | ... | ... | ... |
| Metals | ... | ... | ... |
| Tech | ... | ... | ... |
| Retail | ... | ... | ... |

### TOP-10 best trades:
| # | Ticker | Side | Entry→Exit | P&L | Return% | Duration | Why it worked |

### TOP-10 worst trades:
| # | Ticker | Side | Entry→Exit | P&L | Return% | Duration | What went wrong |
```

---

## Шаг 7: Собери в TRANSPARENT_REPORT.md

Один файл со ВСЕМИ таблицами:
1. Instrument Selection — как выбирались (с примерами)
2. Futures — результаты по фьючерсам
3. Trade Journal — все сделки
4. MiMo Analysis — 10 ключевых дат + проверка на реальность
5. Monthly Detailed — помесячный отчёт за 2024
6. Trade Statistics — полная статистика
7. Component Impact — как каждый компонент повлиял на КАЖДУЮ сделку

---

## ПРАВИЛА

1. **КАЖДАЯ сделка объяснена** — почему вошёл, почему вышел, какие факторы
2. **Фьючерсы обязательны** — Si, RTS, BR минимум
3. **Selector работает РЕАЛЬНО** — не хардкоженный список
4. **MiMo вызывается для 10 ключевых дат** — с проверкой на реальность
5. **Помесячный отчёт ПОДРОБНЫЙ** — позиции, сделки, риск-события
6. **Числа РЕАЛЬНЫЕ** — из бэктеста, не придуманные
7. **753 теста не ломаются**
8. **Если чего-то нет** (фьючерсы не загрузились, ML не обучился) — честно напиши
