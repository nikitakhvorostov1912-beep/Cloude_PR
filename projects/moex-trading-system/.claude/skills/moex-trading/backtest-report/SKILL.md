---
name: backtest-report
description: "Запускает бэктест торговой системы MOEX и генерирует QuantStats HTML tear sheet с 54+ метриками. Используй когда пользователь говорит 'запусти бэктест', 'покажи результаты', 'tear sheet', 'как работает стратегия'."
---

# /backtest-report — Бэктест + QuantStats отчёт

## Шаги

1. Перейди в директорию проекта: `C:\CLOUDE_PR\projects\moex-trading-system`

2. Запусти бэктест:
```bash
venv/Scripts/python.exe scripts/run_enhanced_backtest.py 2>&1
```

3. Если QuantStats установлен, сгенерируй HTML-отчёт:
```bash
venv/Scripts/python.exe -c "
from src.backtest.report import generate_html_report
# Пример: equity curve из бэктеста
import json
with open('data/last_backtest.json', 'r') as f:
    data = json.load(f)
path = generate_html_report(data['equity_curve'])
print(f'Отчёт: {path}')
"
```

4. Выведи ключевые метрики:

```
=== BACKTEST REPORT ===

Доходность:
  Total Return: +XX.X%
  Annual Return: +XX.X%
  CAGR: XX.X%

Риск:
  Sharpe Ratio: X.XXX
  Sortino Ratio: X.XXX
  Max Drawdown: -XX.X%
  Calmar Ratio: X.XXX

Торговля:
  Total Trades: XXX
  Win Rate: XX.X%
  Profit Factor: X.XX
  Avg Trade PnL: +/-X,XXX ₽

HTML-отчёт: data/backtest_report.html
```

5. Если HTML-отчёт сгенерирован, открой его:
```bash
start "" "data/backtest_report.html"
```
