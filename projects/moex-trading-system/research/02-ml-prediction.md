# Deep Research: ML/AI методы предсказания цен акций (2024-2026)

> Дата: 2026-03-18 | Домен: ML/AI | Контекст: MOEX trading system, Python 3.12, Claude API

---

## Статистика

| Метрика | Значение |
|---------|----------|
| Поисковых запросов | 12 |
| Источников проанализировано | 22 |
| Инструментов обнаружено | 28 |
| Противоречий | 3 |
---

## 1. TRANSFORMER-МОДЕЛИ

### 1.1 Chronos (Amazon) -- РЕКОМЕНДОВАН

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/amazon-science/chronos-forecasting |
| Stars | 4 900+ |
| Обновление | Декабрь 2025 (v2.2.2) |
| Модели | Chronos-2: 28M, 120M; Bolt: 9M-205M; T5: 8M-710M |
| Лицензия | Apache 2.0 |
| Уверенность | ВЫСОКАЯ |

Zero-shot прогнозирование. Bolt в 250x быстрее. Probabilistic forecasts. SOTA zero-shot.
Минусы: не для финансов специально. Для MOEX: baseline на CPU (Bolt 9M).

### 1.2 TimesFM (Google Research)

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/google-research/timesfm |
| Stars | 10 100+ |
| Обновление | Октябрь 2025 |
| Модель | 200M (v2.5) |
| Уверенность | ВЫСОКАЯ (ICML 2024) |

Decoder-only foundation model. 100 млрд точек. 16K контекст. Fork timesfm_fin для финансов.
Минусы: требует PyTorch/JAX, на коротких горизонтах уступает LSTM.

### 1.3 PatchTST

GitHub: https://github.com/yuqinie98/PatchTST (~2K stars)

Transformer с патч-токенизацией. Лучшая univariate модель. Превосходит LSTM для цен активов.

### 1.4 TSMixer (Google)

MLP-Mixer. Лучшая multivariate, но для <30 бумаг уступает NHITS/NBEATS.

### Сводная таблица

| Модель | Stars | Zero-shot | Multi | Для MOEX |
|--------|-------|-----------|-------|----------|
| Chronos-2 | 4.9K | Да | Да | 4/5 |
| TimesFM 2.5 | 10.1K | Да | Да | 5/5 |
| PatchTST | ~2K | Нет | Нет | 4/5 |
| TSMixer | -- | Нет | Да | 3/5 |
| NHITS/NBEATS | -- | Нет | Да | 4/5 |
---

## 2. REINFORCEMENT LEARNING

### 2.1 FinRL -- РЕКОМЕНДОВАН

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/AI4Finance-Foundation/FinRL |
| Stars | 14 200+ |
| Forks | 3 200+ |
| Python | 3.6+, pip install finrl |
| Лицензия | MIT |
| Уверенность | ВЫСОКАЯ (NeurIPS 2020) |

Первый open-source финансовый RL. ElegantRL/RLlib/SB3. Train-test-trade. Docker. FinRL-DeepSeek (LLM).
Минусы: сложная настройка, нет MOEX из коробки, policy instability.

### 2.2 PrimoGPT

GitHub: https://github.com/ivebotunac/PrimoGPT

FinRL + NLP. Aug 2024-Feb 2025: returns выше рынка, высокие Sharpe.

---

## 3. LLM ДЛЯ ТРЕЙДИНГА

### 3.1 TradingAgents -- РЕКОМЕНДОВАН (паттерн)

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/TauricResearch/TradingAgents |
| Stars | 32 800+ |
| Обновление | Март 2026 (v0.2.1) |
| LLM | GPT-5.x, Gemini 3.x, Claude 4.x, Grok 4.x, Ollama |
| Лицензия | Apache 2.0 |

Мульти-агентный фреймворк: Fundamental/Sentiment/News/Technical Analyst + Bull/Bear Debate + Trader + Risk Manager.
Плюсы: 32K+ stars, Claude 4.x, bull/bear debate, SOTA Sharpe, LangGraph.
Минусы: research-only, дорого, Python 3.13, нет backtesting.
Для MOEX: заимствовать паттерн дебатов под Claude API.

### 3.2 FinRobot

GitHub: https://github.com/AI4Finance-Foundation/FinRobot (814 stars)

AI Agent платформа. Financial Chain-of-Thought. Perception->Thinking->Action.
---

## 4. NLP И СЕНТИМЕНТ

### 4.1 FinGPT -- РЕКОМЕНДОВАН

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/AI4Finance-Foundation/FinGPT |
| Stars | 18 900+ |
| Модели | Llama-2 (7B/13B), Falcon-7B, Qwen-7B |
| Fine-tuning | <300 USD |
| Лицензия | MIT |

FinGPT-Forecaster. SOTA sentiment (v3). LoRA fine-tuning. Требует GPU, англоязычный.

### 4.2 FinBERT

| Параметр | Значение |
|----------|----------|
| GitHub/HF | ProsusAI/finbert |
| Stars | 2 000+ |
| Размер | ~110M |

Стандарт финансового sentiment. CPU. Только английский.

### Сводная таблица NLP

| Инструмент | Размер | CPU | Русский | MOEX |
|-----------|--------|-----|---------|------|
| Claude API | API | Да | Да | 5/5 |
| FinBERT | 110M | Да | Нет | 3/5 |
| FinGPT v3 | 7B+ | Нет | Нет | 3/5 |
| VADER | <1M | Да | Нет | 2/5 |

---

## 5. FEATURE ENGINEERING

### 5.1 TSFRESH -- РЕКОМЕНДОВАН

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/blue-yonder/tsfresh |
| Stars | 9 100+ |
| Обновление | Август 2025 (v0.21.1) |
| Фичей | 794 |
| Python | 3.8+, pip install tsfresh |

794 признаков из временных рядов. Встроенная фильтрация (hypothesis testing).

### 5.2 TA (уже в стеке)

ta>=0.11.0 в requirements.txt. 42+ индикатора.

### Pipeline

OHLCV -> ta (42) + TSFRESH (794) + Claude sentiment + Calendar -> Feature Selection -> 50-100 фич -> модель
---

## 6. ENSEMBLE -- РЕКОМЕНДОВАННЫЙ ПОДХОД

Stacking (90-100%) превосходит bagging (53-98%) и boosting (52-96%).

**Архитектура для MOEX:**

Layer 1 (Base): Chronos-Bolt + LightGBM/XGBoost + PatchTST/LSTM + Claude Sentiment + FinRL

Layer 2 (Meta): Stacking (Ridge/Logistic) или Weighted Average (MVP)

Layer 3 (Risk): 10 правил + Kelly * 0.5 + Drawdown management

| Метод | Результат | Источник |
|-------|----------|----------|
| Hybrid LSTM+attn | MAPE 2.72% | arXiv 2505.05325 |
| NHITS/NBEATS | MAE 0.013-0.014 | tandfonline 2025 |
| Stacking | 90-100% direction | JBD 2020 |
| PatchTST | > LSTM | SSRN 2024 |

---

## 7. ALTERNATIVE DATA

| Тип | Инструмент | MOEX |
|-----|-----------|------|
| Telegram | telethon | 5/5 |
| RSS | feedparser (в стеке) | 4/5 |
| Twitter/X | snscrape | 3/5 |
| Finnhub | API | 3/5 |
| Reddit | PRAW | 2/5 |
| Satellite | GEE | 2/5 |

Рекомендация: Telegram (@markettwits, @smartlab_news) + RSS (РБК, Коммерсант) + Claude

---

## 8. ИНФРАСТРУКТУРА

- [OpenBB](https://github.com/OpenBB-finance/OpenBB) -- 34K stars, open-source Bloomberg
- [awesome-ai-in-finance](https://github.com/georgezouq/awesome-ai-in-finance) -- 200+ tools

---

## ИТОГОВАЯ ТАБЛИЦА

| Критерий | Transform. | RL | LLM | NLP | FeatEng | Ensemble |
|----------|-----------|-----|-----|-----|---------|----------|
| Релевантность | 4/5 | 4/5 | 5/5 | 5/5 | 4/5 | 5/5 |
| Зрелость | 4/5 | 4/5 | 3/5 | 5/5 | 5/5 | 5/5 |
| Простота | 4/5 | 2/5 | 3/5 | 5/5 | 4/5 | 3/5 |
| Актуальность | 5/5 | 4/5 | 5/5 | 4/5 | 4/5 | 4/5 |
| Совместимость | 4/5 | 3/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Для MOEX | 4/5 | 3/5 | 5/5 | 5/5 | 4/5 | 5/5 |
| **ИТОГО** | **25** | **20** | **26** | **29** | **26** | **27** |

---

## ПРОТИВОРЕЧИЯ

1. ML не предсказывает цены точно, но direction accuracy +5-15%
2. Foundation models как baseline + ensemble с domain-specific
3. LLM полезны для анализа, финальное решение -- Risk Gateway

---

## ПЛАН ВНЕДРЕНИЯ

### Фаза 1: MVP
- FinBERT (CPU sentiment EN), TSFRESH (794 фичи), telethon (Telegram)

### Фаза 2: ML-усиление
- Chronos-Bolt (zero-shot), LightGBM/XGBoost, weighted average ensemble

### Фаза 3: Продвинутый
- TimesFM fine-tuning, TradingAgents паттерн, FinRL, stacking meta-learner

### Dependencies

Фаза 1: transformers>=4.40.0, tsfresh>=0.21.0, telethon>=1.36.0

Фаза 2: chronos-forecasting>=2.0, lightgbm>=4.0.0, scikit-learn>=1.5.0

Фаза 3: torch>=2.0.0, timesfm, finrl

---

## ИСТОЧНИКИ

### Репозитории
- [FinRL](https://github.com/AI4Finance-Foundation/FinRL) -- 14.2K stars
- [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) -- 18.9K stars
- [TradingAgents](https://github.com/TauricResearch/TradingAgents) -- 32.8K stars
- [Chronos](https://github.com/amazon-science/chronos-forecasting) -- 4.9K stars
- [TimesFM](https://github.com/google-research/timesfm) -- 10.1K stars
- [TSFRESH](https://github.com/blue-yonder/tsfresh) -- 9.1K stars
- [FinBERT](https://github.com/ProsusAI/finBERT) -- 2K stars
- [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) -- 814 stars
- [OpenBB](https://github.com/OpenBB-finance/OpenBB) -- 34K stars
- [awesome-ai-in-finance](https://github.com/georgezouq/awesome-ai-in-finance)

### Исследования
- [TimesFM (TDS)](https://towardsdatascience.com/timesfm-the-boom-of-foundation-models-in-time-series-forecasting-29701e0b20b5/)
- [PatchTST (arXiv)](https://arxiv.org/html/2408.16707v1)
- [Ensemble Methods (JBD)](https://journalofbigdata.springeropen.com/articles/10.1186/s40537-020-00299-5)
- [LLMs in Equity (Frontiers)](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1608365/full)
- [FinGPT (arXiv)](https://arxiv.org/html/2306.06031v2)

### Русскоязычные
- [Habr: ML прогнозирование](https://habr.com/ru/companies/netologyru/articles/428227/)
- [ВШЭ: Нейросети](https://www.hse.ru/expertise/news/968830517.html)
- [Stock-price-predictor MOEX](https://github.com/iaidarf/Stock-price-predictor_public)
