---
name: div-calendar
description: "Дивидендный календарь MOEX: ближайшие отсечки, размер дивидендов, рекомендации по входу после гэпа. Используй когда пользователь говорит 'дивиденды', 'отсечка', 'гэп', 'когда дивиденды'."
---

# /div-calendar — Дивидендный календарь MOEX

## Шаги

1. Перейди в `C:\CLOUDE_PR\projects\moex-trading-system`

2. Загрузи дивидендные данные:
```bash
venv/Scripts/python.exe -c "
import asyncio, json
from src.data.moex_client import MoexClient

TICKERS = ['SBER', 'GAZP', 'LKOH', 'YDEX', 'TCSG', 'VTBR', 'NVTK', 'GMKN', 'ROSN', 'MGNT']

async def divs():
    client = MoexClient()
    for t in TICKERS:
        try:
            divs = await client.fetch_dividends(t)
            if divs:
                for d in divs[-3:]:
                    print(f\"{t}: {d}\")
        except: pass

asyncio.run(divs())
"
```

3. Выведи таблицу:

```
=== Дивидендный календарь MOEX ===

| Тикер | Дата отсечки | Дивиденд | Доходность | Статус |
|-------|-------------|----------|------------|--------|
| SBER  | 2026-07-XX  | ~35 руб  | ~10%       | Ожидается |
| LKOH  | 2026-06-XX  | ~XXX руб | ~8%        | Ожидается |

Рекомендация по дивидендному гэпу:
- Покупка: на 1-3 день после отсечки (когда гэп максимален)
- Stop-loss: -5% от цены входа
- Take-profit: цена до гэпа (pre-gap price)
- Time stop: 90 дней
- Медиана закрытия гэпа SBER: 24 дня
```
