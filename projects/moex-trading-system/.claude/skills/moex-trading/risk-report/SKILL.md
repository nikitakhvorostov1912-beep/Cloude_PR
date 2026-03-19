---
name: risk-report
description: "Полный отчёт о рисках портфеля: VaR/CVaR, Kelly sizing, exposure по секторам, корреляции. Используй когда пользователь говорит 'риски', 'VaR', 'Kelly', 'exposure', 'отчёт по рискам'."
---

# /risk-report — Отчёт по рискам портфеля

## Шаги

1. Перейди в `C:\CLOUDE_PR\projects\moex-trading-system`

2. Рассчитай метрики:
```bash
venv/Scripts/python.exe -c "
from src.risk.position_sizer import (
    calculate_kelly_fraction,
    calculate_historical_var,
    calculate_monte_carlo_var,
)

# Kelly (пример с реальными данными из trade_journal)
kelly = calculate_kelly_fraction(win_rate=0.55, avg_win=15000, avg_loss=8000, fraction=0.5)
print(f'Half Kelly: {kelly*100:.2f}%')

# VaR/CVaR (пример)
returns = [-0.02, 0.01, -0.005, 0.015, -0.03, 0.008, -0.01, 0.02, -0.025, 0.005] * 25
var, cvar = calculate_historical_var(returns, confidence=0.95)
print(f'VaR(95%): {var*100:.2f}%')
print(f'CVaR(95%): {cvar*100:.2f}%')

mc_var, mc_cvar = calculate_monte_carlo_var(returns, confidence=0.95)
print(f'MC VaR(95%): {mc_var*100:.2f}%')
print(f'MC CVaR(95%): {mc_cvar*100:.2f}%')
"
```

3. Выведи отчёт:

```
=== Risk Report ===

Position Sizing:
  Kelly fraction (half): X.XX%
  Текущий risk_per_trade: 1.50%
  Рекомендация: min(Kelly, 2.0%) = X.XX%

Value at Risk (95%, 1 day):
  Historical VaR: X.XX% (макс. убыток с 95% вероятностью)
  Monte Carlo VaR: X.XX%
  CVaR (Expected Shortfall): X.XX% (средний убыток в хвосте)

Exposure по секторам:
  Нефтегаз: XX% (лимит 30%)
  Банки: XX% (лимит 30%)
  IT: XX%
  Металлы: XX%
  Ритейл: XX%

Статус:
  Drawdown: X.X% (лимит 20%)
  Circuit Breaker: ON / YELLOW / RED
```
