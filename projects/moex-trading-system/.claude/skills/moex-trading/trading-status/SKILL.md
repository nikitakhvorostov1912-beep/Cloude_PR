---
name: trading-status
description: "Показывает текущий статус торговой системы MOEX: позиции, PnL, drawdown, макро-режим, последние сигналы Claude. Используй когда пользователь спрашивает 'что с портфелем', 'какие позиции', 'статус торговли', 'как дела на рынке'."
---

# /trading-status — Статус торговой системы MOEX

## Шаги

1. Перейди в директорию проекта: `C:\CLOUDE_PR\projects\moex-trading-system`

2. Запусти скрипт статуса:
```bash
venv/Scripts/python.exe scripts/trading_status.py
```

3. Если скрипт недоступен, загрузи данные вручную:
```bash
venv/Scripts/python.exe -c "
import asyncio, json
from src.data.macro_fetcher import fetch_all_macro
macro = asyncio.run(fetch_all_macro())
print(json.dumps(macro, indent=2, ensure_ascii=False))
"
```

4. Прочитай SQLite базу для позиций и сигналов:
```bash
venv/Scripts/python.exe -c "
import sqlite3, json
conn = sqlite3.connect('data/trading.db')
# Последние 5 сигналов
signals = conn.execute('SELECT * FROM signals ORDER BY created_at DESC LIMIT 5').fetchall()
for s in signals:
    print(s)
conn.close()
"
```

5. Выведи отчёт в формате:

```
=== MOEX Trading System — Статус ===

Макро-среда:
  Ставка ЦБ: XX% (EASING/TIGHTENING/NEUTRAL)
  USD/RUB: XX.XX
  Brent: $XX.XX
  Режим: EASING / TIGHTENING / NEUTRAL / STRESS

Портфель:
  Equity: X,XXX,XXX ₽
  Дневной PnL: +/-X,XXX ₽
  Drawdown: X.X% (OK / YELLOW / RED)
  Circuit Breaker: ON / YELLOW / RED

Открытые позиции:
  SBER LONG  10 лотов @ 285.50  PnL: +2.3%  (5 дней)
  ...

Последние сигналы Claude:
  2026-03-18 SBER BUY long  conf=0.72  "Bullish EMA alignment..."
  ...
```
