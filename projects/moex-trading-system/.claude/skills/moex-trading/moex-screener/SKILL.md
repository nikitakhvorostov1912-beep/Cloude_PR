---
name: moex-screener
description: "Скрининг 10 акций MOEX по техническим индикаторам, pre-score и макро-фильтрам. Используй когда пользователь говорит 'скрининг', 'какие акции покупать', 'рейтинг акций', 'что интересного на MOEX'."
---

# /moex-screener — Скрининг акций MOEX

## Шаги

1. Перейди в директорию проекта: `C:\CLOUDE_PR\projects\moex-trading-system`

2. Загрузи данные и рассчитай скоринг для всех 10 тикеров:
```bash
venv/Scripts/python.exe -c "
import asyncio
from src.data.moex_client import MoexClient
from src.analysis.features import calculate_all_features
from src.analysis.scoring import calculate_pre_score
from src.analysis.regime import detect_regime_from_index

TICKERS = ['SBER', 'GAZP', 'LKOH', 'YDEX', 'TCSG', 'VTBR', 'NVTK', 'GMKN', 'ROSN', 'MGNT']

async def screen():
    client = MoexClient()
    results = []
    for ticker in TICKERS:
        candles = await client.fetch_candles(ticker, days=250)
        if not candles:
            continue
        features = calculate_all_features(candles)
        last = features[-1] if features else {}
        score_long, _ = calculate_pre_score(
            adx=float(last.get('adx', 0)),
            di_plus=float(last.get('di_plus', 0)),
            di_minus=float(last.get('di_minus', 0)),
            rsi=float(last.get('rsi_14', 50)),
            macd_hist=float(last.get('macd_histogram', 0)),
            close=float(last.get('close', 0)),
            ema20=float(last.get('ema_20', 0)),
            ema50=float(last.get('ema_50', 0)),
            ema200=float(last.get('ema_200', 0)),
            volume_ratio=float(last.get('volume_ratio_20', 1)),
            obv_trend=last.get('obv_trend', 'flat'),
            sentiment_score=0.0,
            direction='long',
        )
        results.append({
            'ticker': ticker,
            'close': last.get('close'),
            'rsi': round(float(last.get('rsi_14', 0)), 1),
            'adx': round(float(last.get('adx', 0)), 1),
            'score_long': round(score_long, 1),
        })
    results.sort(key=lambda x: x['score_long'], reverse=True)
    for r in results:
        print(f\"{r['ticker']:6s} | {r['close']:>10.2f} | RSI {r['rsi']:5.1f} | ADX {r['adx']:5.1f} | Score {r['score_long']:5.1f}\")

asyncio.run(screen())
"
```

3. Выведи результат в виде таблицы:

```
=== MOEX Screener ===

Режим рынка: UPTREND / DOWNTREND / RANGE / CRISIS

| Тикер | Цена    | RSI  | ADX  | Score | Рекомендация |
|-------|---------|------|------|-------|-------------|
| SBER  | 285.50  | 55.2 | 28.5 | 72.3  | BUY         |
| LKOH  | 7250.00 | 48.1 | 32.0 | 68.5  | BUY         |
| GAZP  | 155.20  | 62.3 | 22.0 | 45.2  | HOLD        |
| ...   |         |      |      |       |             |

Рекомендация: Score >= 60 → BUY, 40-60 → HOLD, < 40 → AVOID
```
