---
name: optimize-strategy
description: "Grid search параметров стратегий через VectorBT (1000x быстрее). RSI, EMA crossover, pre-score threshold. Используй когда пользователь говорит 'оптимизировать', 'подобрать параметры', 'grid search', 'лучшие параметры'."
---

# /optimize-strategy — Оптимизация параметров через VectorBT

## Шаги

1. Перейди в `C:\CLOUDE_PR\projects\moex-trading-system`

2. Запусти grid search:
```bash
venv/Scripts/python.exe -c "
import asyncio, json
from src.data.moex_client import MoexClient
from src.backtest.vectorbt_engine import grid_search_rsi, grid_search_ema_crossover

async def optimize():
    client = MoexClient()
    candles = await client.fetch_candles('SBER', days=1000)
    closes = [float(c.close) for c in candles]

    print('=== RSI Grid Search ===')
    rsi_results = grid_search_rsi(closes)
    print(f'Best: {rsi_results[\"best_params\"]}')
    print(f'Sharpe: {rsi_results[\"best_sharpe\"]}')
    print(f'Tested: {rsi_results[\"total_combinations\"]} combinations')

    print()
    print('=== EMA Crossover Grid Search ===')
    ema_results = grid_search_ema_crossover(closes)
    print(f'Best: {ema_results[\"best_params\"]}')
    print(f'Sharpe: {ema_results[\"best_sharpe\"]}')

asyncio.run(optimize())
"
```

3. Выведи результат:

```
=== Strategy Optimization (VectorBT) ===

RSI Strategy — лучшие параметры:
  Period: XX | Entry: XX | Exit: XX
  Sharpe: X.XXX | Return: +XX.X% | Max DD: -XX.X%
  Trades: XXX

EMA Crossover — лучшие параметры:
  Fast: XX | Slow: XXX
  Sharpe: X.XXX | Return: +XX.X% | Max DD: -XX.X%

Top-5 RSI комбинаций:
| # | Period | Entry | Exit | Sharpe | Return | Trades |
|---|--------|-------|------|--------|--------|--------|
| 1 | ...    | ...   | ...  | ...    | ...    | ...    |
```
