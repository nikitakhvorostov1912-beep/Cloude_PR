# AI-агенты, скиллы, MCP-серверы и плагины для алготрейдинга

> Deep Research — 2026-03-18
> Домен: алготрейдинг, AI-агенты, MCP, Python
> Контекст: MOEX Trading System (Python, asyncio, Claude API)

---

## Статистика исследования

| Метрика | Значение |
|---------|----------|
| Поисковых запросов | 10 |
| Источников найдено | ~40 |
| Источников проанализировано (WebFetch) | 12 |
| Вариантов/инструментов обнаружено | 30+ |
| Противоречий между источниками | 2 |

---

## 1. AI Trading Agents (готовые агенты на GitHub)

### 1.1 TradingAgents — РЕКОМЕНДОВАН

| Параметр | Значение |
|----------|----------|
| GitHub | https://github.com/TauricResearch/TradingAgents |
| Stars | 32.8k |
| Forks | 6.3k |
| Последний релиз | v0.2.1 (март 2026) |
| Python | 3.13 |
| Фреймворк | LangGraph |
| Уверенность | ВЫСОКАЯ |

**Архитектура (зеркалирует реальную трейдинговую фирму):**
- **Analyst Team** — фундаментальный, сентиментальный, новостной, технический аналитики
- **Researcher Team** — бычий и медвежий исследователи ведут дебаты
- **Trader Agent** — синтезирует отчеты и принимает решения
- **Risk Management + Portfolio Manager** — оценивает волатильность, утверждает/отклоняет сделки

**Поддержка LLM:** OpenAI, Google (Gemini), Anthropic (Claude), xAI (Grok), OpenRouter, Ollama

**Плюсы:**
+ Самый популярный проект (32k+ stars)
+ Мультиагентная архитектура как в реальной фирме
+ Поддержка Claude 4.6 из коробки
+ Настраиваемые раунды дебатов между агентами
+ CLI + Python API

**Минусы:**
- Python 3.13 (может потребовать обновление)
- Ориентирован на US рынки, нужна адаптация под MOEX
- Зависит от Alpha Vantage для данных (нет MOEX)

**Когда выбирать:** Когда нужна полноценная мультиагентная система. Лучший кандидат для адаптации под MOEX.

---

### 1.2 FinRobot (AI4Finance Foundation)

GitHub: https://github.com/AI4Finance-Foundation/FinRobot | 6.4k stars | Python 3.10

4-layer architecture: Financial AI Agents (Financial CoT) > LLM Algorithms > LLMOps/DataOps > Multi-source LLM
Agents: Market Forecaster, Financial Analyst, Trade Strategist, Document Analysis
Data: Finnhub, Financial Modeling Prep, SEC API, YFinance, FinNLP

+ Academic foundation (arxiv), Smart Scheduler, Financial CoT
- US market focus, no built-in backtesting

---

### 1.3 FinMem -- LLM Agent with Layered Memory

GitHub: https://github.com/pipiku915/FinMem-LLM-StockTrading | Python 3.10 | GPT-4, HuggingFace

Innovation: Layered Memory -- mimics trader cognitive processes
+ Unique cognitive architecture, customizable agent character
- No Claude support, depends on OpenAI embeddings

---

### 1.4 OpenProphet + claude_prophet MCP

Site: https://openprophet.io/ | MCP: claude_prophet | 40+ tools | Alpaca
Result: $100k paper trading -- beat S&P 500 in 1 month autonomous trading
+ Native Claude MCP, local-first, 294+ LLM providers
- Paid ($49.99), Alpaca only (US)
Best as: Reference for building MOEX MCP server

---

### 1.5 Polymarket AI Trading Bot

GitHub: https://github.com/dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot | Python 3.9+
Multi-model ensemble: GPT-4o (40%), Claude 3.5 Sonnet (35%), Gemini 1.5 Pro (25%)
Risk: 15+ checks, kill switches, 20% drawdown halt, Fractional Kelly
Best as: Reference for multi-model ensemble and risk management

---

### 1.6 AI-Trader v2 (HKUDS) -- 11.8k stars

GitHub: https://github.com/HKUDS/AI-Trader | Signal marketplace + copy trading

---

## 2. MCP Servers for Financial Data

### 2.1 Alpha Vantage MCP -- RECOMMENDED

Site: https://mcp.alphavantage.co/ | 150+ tools | Claude Desktop/Code/VS Code/Cursor
Categories: Core Stock APIs, Options (Greeks), Alpha Intelligence (sentiment), Fundamentals, Forex/Crypto, Commodities, Economic Indicators, 40+ Technical Indicators

Install: `uvx marketdata-mcp-server YOUR_API_KEY`

### 2.2 Yahoo Finance MCP

GitHub: https://github.com/Alex2Yang97/yahoo-finance-mcp | Python 3.11+
Tools: get_historical_stock_prices, get_stock_info, get_yahoo_finance_news, get_financial_statement, get_option_chain, get_recommendations
Note: Yahoo Finance has some MOEX data (tickers .ME)

### 2.3 Binance MCP: https://github.com/AnalyticAce/binance-mcp-server
### 2.4 Crypto Trading MCP: https://github.com/vkdnjznd/crypto-trading-mcp (Upbit, Gate.io, Binance)

### 2.5 MOEX MCP Server -- NEEDS TO BE CREATED

**No MCP server for MOEX exists!** Architecture: MOEX ISS API, quotes/candles/orderbook/history/indices/bonds, Python + FastMCP, Alor/Tinkoff/Finam integration

---

## 3. Multi-Agent Frameworks

### 3.1 CrewAI -- role-based orchestration
Example: data_analyst > trading_strategy > execution > risk_management
Reference: https://github.com/botextractai/ai-crewai-multi-agent

### 3.2 LangGraph -- granular control
TradingAgents (32k stars) built on LangGraph. State machine for trading workflows.

### 3.3 Claude Agent SDK
GitHub: https://github.com/anthropics/claude-agent-sdk-python | Native Claude, in-process MCP, hooks, async

---

## 4. Backtesting with LLM Integration

### 4.1 Backtest Kit -- RECOMMENDED for LLM signals
https://backtest-kit.github.io/ | https://github.com/tripolskypetr/backtest-kit
Architecture: LLM in scoring layer, NOT execution. Adds conviction weight to signals.

### 4.2 Python Backtesting Frameworks

| Framework | Stars | LLM | Note |
|-----------|-------|-----|------|
| Backtrader | 14k+ | No | Mature, not updated |
| VectorBT | 4k+ | Partial | Fast, numpy |
| Backtesting.py | 5k+ | No | Simple |
| Zipline | 17k+ | No | Archived |
| QuantConnect | 9k+ | No | C#/Python |

Recommendation: VectorBT + custom LLM wrapper (Claude for scoring)

### 4.3 LLM Integration Pattern

```
Market Data --> Technical Indicators --> Raw Signals
                                          |
                                    LLM Scoring <-- Claude API
                                          |
                                    Risk Management
                                          |
                                    Execution Engine
```

IMPORTANT: LLM NEVER controls execution directly. Scoring/conviction only.

---

## 5. Prompt Engineering for Finance

| Technique | Accuracy | Hallucinations | Best for |
|-----------|----------|----------------|----------|
| Graph-of-Thought | +20-25% | -25-30% | Complex financial reasoning |
| Tree-of-Thought | +15-20% | -20-25% | Multi-variant analysis |
| Chain-of-Thought | +10-15% | -15-20% | Step-by-step analysis |
| Meta-Cognition | Varies | -10-15% | Bias awareness |
| Few-Shot | +5-10% | -5-10% | Standard tasks |

### System Prompt for MOEX Trading Agent

```
Role: Senior Quantitative Analyst
Context: MOEX market, Russian equities and bonds
Protocol: CoT analysis, confidence 0-100%, 3+ scenarios always
Macro: CBR key rate, USD/RUB, oil prices, sanctions risk
Output: Bull/Base/Bear cases, key levels, risk/reward, position sizing
```

---

## 6. Awesome Lists

| Resource | Stars | Description |
|----------|-------|-------------|
| [awesome-ai-in-finance](https://github.com/georgezouq/awesome-ai-in-finance) | 3k+ | Main LLM/DL finance catalog |
| [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | 14k+ | Open-source financial LLMs |
| [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 10k+ | Deep RL for trading |

---

## Comparison: AI Trading Agents

| Criteria | TradingAgents | FinRobot | OpenProphet | FinMem | Polymarket |
|----------|:---:|:---:|:---:|:---:|:---:|
| MOEX Relevance | 4/5 | 3/5 | 4/5 | 3/5 | 3/5 |
| Maturity | 5/5 | 4/5 | 3/5 | 3/5 | 2/5 |
| Simplicity | 4/5 | 3/5 | 4/5 | 3/5 | 4/5 |
| Claude | 5/5 | 3/5 | 5/5 | 2/5 | 4/5 |
| Multi-Agent | 5/5 | 4/5 | 3/5 | 2/5 | 4/5 |
| Backtesting | 2/5 | 2/5 | 2/5 | 4/5 | 2/5 |
| Risk Mgmt | 3/5 | 2/5 | 3/5 | 2/5 | 5/5 |
| **TOTAL** | **28/35** | **21/35** | **24/35** | **19/35** | **24/35** |

## Comparison: MCP Servers

| MCP Server | Tools | MOEX | Trading | Free |
|-----------|:---:|:---:|:---:|:---:|
| Alpha Vantage | 150+ | No | No | Yes |
| Yahoo Finance | ~10 | Partial | No | Yes |
| claude_prophet | 40+ | No | Yes | No |
| Binance MCP | ~20 | No | Yes | Yes |
| **MOEX MCP** | Plan | **Yes** | Plan | Yes |

---

## Contradictions

**1: LLM as trader vs advisor** -- TradingAgents/OpenProphet: autonomous. Backtest Kit/academia: scoring only. Our position: LLM for analysis/scoring, execution = deterministic code.

**2: Autonomy vs Control** -- OpenProphet: full autonomy (beat S&P 500). Polymarket: 15+ safety checks. Our position: Hybrid with hard limits.

---

## Verdict and Action Plan

### Connect immediately:
1. **Alpha Vantage MCP** -- global data
2. **Yahoo Finance MCP** -- additional data
3. **Claude Agent SDK** -- agent foundation

### Adapt architecture from:
4. **TradingAgents** -- multi-agent structure
5. **Polymarket Bot** -- ensemble + risk checks
6. **Backtest Kit** -- LLM in scoring pattern

### Create:
7. **MOEX MCP Server** -- first MCP for MOEX ISS API

### Prompt engineering:
8. Graph-of-Thought (+20-25% accuracy)
9. Bull/Base/Bear scenarios
10. Meta-Cognition for bias

---

## Sources

### AI Trading Agents
- [TradingAgents](https://github.com/TauricResearch/TradingAgents) -- 32.8k stars
- [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) -- 6.4k stars
- [FinMem](https://github.com/pipiku915/FinMem-LLM-StockTrading)
- [OpenProphet](https://openprophet.io/) + claude_prophet MCP
- [AI-Trader](https://github.com/HKUDS/AI-Trader) -- 11.8k stars
- [Polymarket Bot](https://github.com/dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot)

### MCP Servers
- [Alpha Vantage MCP](https://mcp.alphavantage.co/) -- 150+ tools
- [Yahoo Finance MCP](https://github.com/Alex2Yang97/yahoo-finance-mcp)
- [Binance MCP](https://github.com/AnalyticAce/binance-mcp-server)
- [Crypto Trading MCP](https://github.com/vkdnjznd/crypto-trading-mcp)

### Frameworks
- [Awesome AI in Finance](https://github.com/georgezouq/awesome-ai-in-finance)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
- [Backtest Kit](https://backtest-kit.github.io/)
- [CrewAI Financial](https://github.com/botextractai/ai-crewai-multi-agent)

### Prompt Engineering
- [PE Techniques in Finance](https://www.ijircst.org/view_abstract.php?title=Review-of-Prompt-Engineering-Techniques-in-Finance)
- [Prompting Guide CoT](https://www.promptingguide.ai/techniques/cot)

### Russian Sources
- [MOEX AI Copilot](https://www.moex.com/n90417)
- [AI Trading 2026](https://vc.ru/top_rating/2730194)
- [Algotrading with AI](https://zerocoder.ru/algo-trading-with-ai)
