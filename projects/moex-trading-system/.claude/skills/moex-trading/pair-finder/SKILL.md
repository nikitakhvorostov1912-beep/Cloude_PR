---
name: pair-finder
description: "Поиск коинтегрированных пар акций MOEX для парного трейдинга. ADF-тест, z-score спреда, визуализация. Используй когда пользователь говорит 'пары', 'коинтеграция', 'парный трейдинг', 'спред'."
---

# /pair-finder — Поиск коинтегрированных пар MOEX

## Шаги

1. Перейди в `C:\CLOUDE_PR\projects\moex-trading-system`

2. Запусти тест коинтеграции:
```bash
venv/Scripts/python.exe -c "
import asyncio
from src.strategy.pairs_trading import find_cointegrated_pairs

PAIRS = [('SBER','VTBR'), ('LKOH','ROSN'), ('GAZP','NVTK'), ('SBER','TCSG'), ('LKOH','NVTK')]

async def check():
    # Загрузить данные и проверить коинтеграцию
    for a, b in PAIRS:
        print(f'{a}/{b}: проверка...')

asyncio.run(check())
"
```

3. Для каждой пары выведи:

```
=== Pair Finder MOEX ===

| Пара | p-value ADF | Коинтегрирована? | Z-score | Сигнал |
|------|-------------|------------------|---------|--------|
| SBER/VTBR | 0.023 | ДА (p<0.05) | +1.8 | Ждать |
| LKOH/ROSN | 0.041 | ДА (p<0.05) | -2.3 | LONG spread |
| GAZP/NVTK | 0.156 | НЕТ | — | — |

Сигналы:
  |z| > 2.0 → Вход (short spread если z>2, long spread если z<-2)
  |z| < 0.5 → Выход
  Потеря коинтеграции (p>0.10) → Закрыть всё

Hedge ratio: LKOH = 1.34 * ROSN + alpha
```
