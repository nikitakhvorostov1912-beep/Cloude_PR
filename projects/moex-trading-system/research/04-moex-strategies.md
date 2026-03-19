# DEEP RESEARCH -- Стратегии и подходы специфичные для MOEX

**ДАТА:** 2026-03-18  |  **ДОМЕН:** Алгоритмическая торговля, MOEX, Python
**КОНТЕКСТ:** Дневной таймфрейм, 10 акций (SBER, GAZP, LKOH, YDEX, TCSG, VTBR, NVTK, GMKN, ROSN, MGNT)

---

## Статистика исследования

| Метрика | Значение |
|---------|----------|
| Поисковых запросов | 11 |
| Источников найдено | 45+ |
| Источников проанализировано | 16 |
| Стратегий обнаружено | 6 |
| Противоречий | 2 |

---

## СТРАТЕГИЯ 1: Дивидендный гэп -- покупка после отсечки (РЕКОМЕНДОВАНА)

**Подход:** Покупка акций сразу после дивидендной отсечки с расчетом на закрытие гэпа.

**Уверенность:** ВЫСОКАЯ (5+ источников, статистика по годам)

### Статистика SBER

| Год | Дивиденд | Гэп | Дней до закрытия |
|-----|----------|-----|------------------|
| 2017 | 6 руб | ~2.5% | 23 |
| 2018 | 12 руб | ~5% | 23 |
| 2019 | 16 руб | ~6.5% | 198 |
| 2020 | 18.7 руб | ~7% | 36 |
| 2021 | 18.7 руб | ~6% | 85 |
| 2023 | 25 руб | ~9% | 11 |
| 2024 | 33.3 руб | ~10% | 153 |

**Среднее:** 78 дней, **медиана:** 24 дня

### Другие тикеры

| Тикер | Среднее закрытие | Див. доходность |
|-------|-----------------|-----------------|
| SBER | 78 дней (мед. 24) | ~10% |
| LKOH | ~275 дней | 8-9% |
| SNGSP | Быстро | 16-17% |
| MOEX | ~60 дней | ~13% |

### Сезонность выплат

- **Апрель--Июль:** ~52% (пик мае-июне)
- **Сентябрь--Октябрь:** ~23%
- **Декабрь--Январь:** ~25%

### Источники данных

| Источник | URL |
|----------|-----|
| MOEX школа | school.moex.com/articles/dividendnyy-kalendar |
| Investmint | investmint.ru/moex/ |
| FinanceMarker | financemarker.ru |
| Smart-lab | smart-lab.ru/dividends |

### Плюсы: медиана 24 дня SBER, доходность 8-17%, простая логика
### Минусы: разброс 11-275 дней, гэпы могут не закрыться, сезонная

---

## СТРАТЕГИЯ 2: Парный трейдинг (Statistical Arbitrage)

**Подход:** Коинтегрированные пары, торговля отклонениями спреда.

**Уверенность:** ВЫСОКАЯ (10+ источников)

### Пары для портфеля

| Пара | Связь | Коинтеграция |
|------|-------|-------------|
| SBER / VTBR | Госбанки | Высокая |
| LKOH / ROSN | Нефтяные | Высокая |
| LKOH / NVTK | Энергетика | Средняя |
| GAZP / NVTK | Газ | Средняя |
| SBER / TCSG | Банки | Средняя-Низкая |

### Метод: statsmodels coint(), ADF-тест, OLS hedge ratio, Z-score сигналы
### Библиотеки: statsmodels>=0.14, scipy>=1.11, hurst>=0.0.5

### Плюсы: рыночно-нейтральная, академически обоснована
### Минусы: мало ликвидных пар MOEX, ломается в кризисы, нужен шорт

### Источники

- [Smart-lab: Парный трейдинг](https://smart-lab.ru/blog/392195.php)
- [Smart-lab: Поиск пар](https://smart-lab.ru/blog/393545.php)
- [Quantrum](https://quantrum.me/875-parnyj-trejding-opisanie-strategii-na-python/)
- [PyQuant](https://www.pyquantnews.com/the-pyquant-newsletter/build-a-pairs-trading-strategy-python)
- [QuantConnect](https://github.com/QuantConnect/Research/blob/master/Analysis/05%20Pairs%20Trading%20Strategy%20Based%20on%20Cointegration.ipynb)

---

## СТРАТЕГИЯ 3: Макроэкономические фильтры

**Подход:** Макропоказатели как фильтры для существующих стратегий.

**Уверенность:** ВЫСОКАЯ

### Корреляции IMOEX

| Показатель | Корреляция | Лаг | Направление |
|------------|-----------|-----|-------------|
| Ключевая ставка ЦБ | -0.65 | 14 дн | Рост = падение акций |
| Нефть Brent | +0.85 | 1-3 дн | Рост = рост нефтегаза |
| USD/RUB | -0.70 | 2-5 дн | Ослабление = давление |
| ИПЦ | +0.83 | 30 дн | Сложная зависимость |
| ВВП | +0.79 | 60 дн | Рост = рост рынка |
| M2 | +0.75 | 30 дн | Рост = ликвидность |

**Реакция на ставку ЦБ: 95% вероятность, 2 часа.**

### Секторальная чувствительность

| Сектор | К нефти | К ставке ЦБ | К USD/RUB |
|--------|---------|-------------|-----------|
| Нефтегаз (LKOH, ROSN, GAZP, NVTK) | 0.85 | -0.45 | -0.68 |
| Финансы (SBER, VTBR, TCSG) | 0.30 | -0.78 | -0.55 |
| Ритейл (MGNT) | 0.15 | -0.60 | -0.40 |
| Металлы (GMKN) | 0.40 | -0.50 | -0.65 |
| IT (YDEX) | 0.10 | -0.55 | -0.30 |

### Реализация: MacroFilter

Веса: cbr_rate=0.30, brent=0.25, usdrub=0.20, imoex_sma200=0.25
Режимы: BULLISH (>0.3) / BEARISH (<-0.3) / NEUTRAL
BEARISH + BUY = SKIP, BULLISH + SELL = REDUCE

### API (все бесплатные)

| Показатель | Источник |
|------------|----------|
| Ставка ЦБ | cbr.ru XML/JSON API |
| Brent | MOEX ISS API |
| USD/RUB | MOEX ISS API / CBR |
| IMOEX | MOEX ISS API |

### Источники

- [Smart-lab: Корреляция IMOEX](https://smart-lab.ru/blog/1163353.php)
- [RBC: Ключевая ставка](https://quote.rbc.ru/news/article/6290aaf09a79472af98d807e)

---

## СТРАТЕГИЯ 4: Сезонные паттерны

**Уверенность:** СРЕДНЯЯ

| Паттерн | Период | Подтверждение |
|---------|--------|---------------|
| Sell in May | Май-Окт | +4.52% зима vs лето (108 рынков) |
| Ноябрь-Апрель | Нояб-Апр | 8.8% за период |
| Дивидендный сезон | Май-Июль | 52% выплат |
| Сентябрьская слабость | Сентябрь | 36/37 рынков |

Использовать как фильтр размера позиции. НЕ самостоятельная стратегия.

- [Quantpedia: Seasonality](https://quantpedia.com/strategies/market-seasonality-effect-in-world-equity-indexes)

---

## СТРАТЕГИЯ 5: Фьючерсные стратегии (Si, BR, SBRF)

**Уверенность:** СРЕДНЯЯ

| Тикер | Актив | ГО | Ликвидность |
|-------|-------|-----|-------------|
| Si | USD/RUB | ~15% | Очень высокая |
| BR | Brent | ~15% | Высокая |
| SBRF | SBER | ~20% | Высокая |
| RTS | Индекс | ~15% | Высокая |

Инфраструктура: backtrader_moexalgo, FinamPy, AlorPy, QuikPy, moexalgo (PyPI).
Применение: хедж валютного (Si) и нефтяного (BR) риска.

---

## СТРАТЕГИЯ 6: Новостной/сентимент анализ

**Уверенность:** НИЗКАЯ

Источники: MOEX ISS, RBC RSS, ТАСС, Telegram (Telethon), MarketAux API.
NLP: blanchefort/rubert-base-cased-sentiment. Экспериментальное.

---

## Инфраструктура: Python-библиотеки для MOEX

| Библиотека | Stars | Обновление | Назначение |
|------------|-------|-----------|-----------|
| poptimizer | 164 | Мар 2026 | ML портфельная оптимизация |
| apimoex | 128 | Янв 2024 | Синхронный клиент MOEX ISS |
| aiomoex | 102 | Май 2025 | Асинхронный клиент (в нашем проекте) |
| backtrader_moexalgo | 70 | Янв 2024 | Бэктест + Live trading |
| finam-export | 104 | Май 2023 | Исторические данные Финам |

### MOEX AlgoPack

Super Candles, Orderbook snapshots, Ticks. Бесплатно (data.moex.com).
pip install moexalgo / pip install backtrader-moexalgo

### Рекомендуемые дополнения в requirements.txt

    statsmodels>=0.14.0
    scipy>=1.11.0
    lxml>=5.0.0

---

## СРАВНИТЕЛЬНАЯ ТАБЛИЦА

| Критерий | Див.гэп | Пар.трейд | Макро | Сезон | Фьючерсы | Новости |
|----------|---------|-----------|-------|-------|----------|---------|
| Релевантность | 5 | 4 | 5 | 3 | 4 | 3 |
| Зрелость | 4 | 5 | 4 | 4 | 3 | 2 |
| Простота | 5 | 3 | 4 | 5 | 2 | 1 |
| Актуальность | 5 | 4 | 5 | 3 | 4 | 4 |
| Совместимость | 5 | 4 | 5 | 5 | 3 | 2 |
| Сообщество | 4 | 4 | 3 | 3 | 3 | 2 |
| **ИТОГО** | **28** | **24** | **26** | **23** | **19** | **14** |

---

## ПРОТИВОРЕЧИЯ

1. **Парный трейдинг:** Smart-lab -- спреды умерли к 2002. Академия -- работает. Вывод: на MOEX может работать из-за меньшей эффективности рынка.
2. **Сезонность:** Out-of-sample отрицательная, но 319 лет данных подтверждают. Только как фильтр.

### MOEX -- менее эффективный рынок

- Меньше алготрейдеров чем NYSE/NASDAQ
- SBER+GAZP+LKOH = 40%+ индекса
- Сильное влияние геополитики
- Дивидендная доходность 8-17% (выше мировой)

Стратегии, ослабшие на развитых рынках, могут работать на MOEX.

---

## ВЕРДИКТ

| P | Стратегия | Обоснование | Сложность |
|---|-----------|-------------|-----------|
| P0 | **Макро-фильтры** | Улучшает ВСЕ стратегии, бесплатные API | Низкая |
| P1 | **Дивидендный гэп** | Уникальна для MOEX, ~10%/сделку | Низкая |
| P2 | **Парный трейдинг** | Рыночно-нейтральная, диверсификация | Средняя |
| P3 | **Сезонные фильтры** | Модификатор размера позиции | Очень низкая |
| P4 | Фьючерсы | Хеджирование, отдельный счет | Высокая |
| P5 | Новости | Экспериментальный | Очень высокая |

### Рекомендация

1. **Немедленно (P0):** Макро-фильтр (ставка ЦБ + Brent + IMOEX vs SMA200). MOEX ISS API.
2. **Следующий спринт (P1):** Дивидендный гэп. Активна 3 раза/год. ~10%/сделку.
3. **После бэктеста (P2):** Парный трейдинг SBER/VTBR и LKOH/ROSN на 3+ годах.
4. **Параллельно (P3):** Сезонный фильтр как модификатор позиции.

---

## Полный список источников

### Официальные
- [MOEX ISS API](https://iss.moex.com/iss/reference/)
- [MOEX AlgoPack](https://data.moex.com/products/algopack)
- [MOEX: Дивидендный календарь](https://school.moex.com/articles/dividendnyy-kalendar)
- [MOEX: Фьючерсы](https://www.moex.com/ru/derivatives/select.aspx)
- [MOEX: Brent](https://www.moex.com/a2074)

### GitHub
- [apimoex](https://github.com/WLM1ke/apimoex) (128 stars)
- [aiomoex](https://github.com/WLM1ke/aiomoex) (102 stars)
- [poptimizer](https://github.com/WLM1ke/poptimizer) (164 stars)
- [backtrader_moexalgo](https://github.com/WISEPLAT/backtrader_moexalgo) (70 stars)
- [Pairs-Trading-With-Python](https://github.com/KidQuant/Pairs-Trading-With-Python)

### Статьи
- [Smart-lab: Парный трейдинг](https://smart-lab.ru/blog/392195.php)
- [Smart-lab: Поиск пар](https://smart-lab.ru/blog/393545.php)
- [Smart-lab: Корреляция IMOEX](https://smart-lab.ru/blog/1163353.php)
- [RBC: Ключевая ставка](https://quote.rbc.ru/news/article/6290aaf09a79472af98d807e)
- [RBC: Див.гэп SBER](https://www.rbc.ru/quote/news/article/668d248c9a79474e7b168069)
- [T-Bank: Закрытие гэпа SBER](https://www.tbank.ru/invest/social/profile/Russian_Stocks/43a0d65f-f189-4e4d-a9d6-366fa76f6195/)
- [Alfa: Закрытие гэпа SBER](https://alfabank.ru/alfa-investor/t/sberbank-kak-bystro-zakroetsya-dividendnyy-gep/)

### Академические
- [Quantpedia: Seasonality](https://quantpedia.com/strategies/market-seasonality-effect-in-world-equity-indexes)
- [ScienceDirect: Calendar anomalies](https://www.sciencedirect.com/science/article/abs/pii/S1059056023002228)
- [ScienceDirect: Monthly anomalies](https://www.sciencedirect.com/science/article/abs/pii/S0275531919307743)

### PyPI
- [apimoex](https://pypi.org/project/apimoex/)
- [aiomoex](https://pypi.org/project/aiomoex/)
- [backtrader-moexalgo](https://pypi.org/project/backtrader-moexalgo/)
