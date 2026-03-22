# FULL SYSTEM AUDIT REPORT
# Date: 2026-03-22 15:47
# Data: MOEX ISS, 2022-01-01 -- 2025-12-31
# Capital: 1,000,000 RUB

======================================================================
  STEP 1: LOAD DATA FROM MOEX ISS
======================================================================

  SBER...
    1062 bars (2022-01-03 -> 2025-12-30)
  GAZP...
    1062 bars (2022-01-03 -> 2025-12-30)
  LKOH...
    1062 bars (2022-01-03 -> 2025-12-30)
  ROSN...
    1062 bars (2022-01-03 -> 2025-12-30)
  GMKN...
    1058 bars (2022-01-03 -> 2025-12-30)
  YNDX...
    599 bars (2022-01-03 -> 2024-06-14)
  VTBR...
    1058 bars (2022-01-03 -> 2025-12-30)
  NVTK...
    1058 bars (2022-01-03 -> 2025-12-30)
  MGNT...
    1062 bars (2022-01-03 -> 2025-12-30)
  TATN...
    1060 bars (2022-01-03 -> 2025-12-30)
  IMOEX...
    999 bars

======================================================================
  STEP 2.1: INDICATORS
======================================================================

  features.py FAILED: cannot import name 'calculate_adx' from 'src.analysis.features' (D:\Cloude_PR\projects\moex-trading-system\src\analysis\features.py)
    ATR/ADX/OBV FAILED: cannot access local variable 'calculate_adx' where it is not associated with a value
  advanced.py FAILED: 'ChandeKrollResult' object is not subscriptable
  ehlers.py FAILED: cannot import name 'mesa_adaptive_moving_average' from 'src.indicators.ehlers' (D:\Cloude_PR\projects\moex-trading-system\src\indicators\ehlers.py)
  damiani.py FAILED: 'DamianiResult' object is not subscriptable
  squeeze_momentum.py FAILED: 'SqueezeResult' object is not subscriptable
  supertrend.py FAILED: 'SuperTrendResult' object is not subscriptable
  support_resistance.py FAILED: cannot import name 'detect_support_resistance' from 'src.indicators.support_resistance' (D:\Cloude_PR\projects\moex-trading-system\src\indicators\support_resistance.py)
  trend_quality.py FAILED: cannot import name 'zigzag' from 'src.indicators.trend_quality' (D:\Cloude_PR\projects\moex-trading-system\src\indicators\trend_quality.py)
  candle_patterns.py FAILED: cannot import name 'detect_all_patterns' from 'src.indicators.candle_patterns' (D:\Cloude_PR\projects\moex-trading-system\src\indicators\candle_patterns.py)
  garch_forecast.py: SKIP (arch library not installed)
  order_book.py FAILED: cannot import name 'microprice' from 'src.indicators.order_book' (D:\Cloude_PR\projects\moex-trading-system\src\indicators\order_book.py)

======================================================================
  STEP 2.2: SCORING
======================================================================

  scoring.py FAILED: cannot import name 'calculate_adx' from 'src.analysis.features' (D:\Cloude_PR\projects\moex-trading-system\src\analysis\features.py)
  Traceback (most recent call last):
  File "D:\Cloude_PR\projects\moex-trading-system\scripts\full_system_audit.py", line 297, in test_scoring
    from src.analysis.features import calculate_ema, calculate_rsi, calculate_macd, calculate_atr, calculate_adx
ImportError: cannot import name 'calculate_ad

======================================================================
  STEP 2.3: REGIME DETECTION
======================================================================

  regime.py FAILED: detect_regime() missing 2 required positional arguments: 'index_adx' and 'index_atr_pct'
  Traceback (most recent call last):
  File "D:\Cloude_PR\projects\moex-trading-system\scripts\full_system_audit.py", line 347, in test_regime
    regime = detect_regime(close[-252:])
             ^^^^^

======================================================================
  STEP 2.4: ML PIPELINE
======================================================================

  ensemble: import OK
  trainer: import OK
  predictor: import OK
  processors: import OK
  label_generators: import OK
  walk_forward: import OK
  ump_filter: import OK
  WalkForwardML: class imported OK
  NOTE: Full walk-forward requires trained models + feature pipeline
  NOTE: Not running E2E ML backtest - needs catboost/lightgbm training
  processors FAILED: cannot import name 'CSRankNorm' from 'src.ml.processors' (D:\Cloude_PR\projects\moex-trading-system\src\ml\processors.py)

======================================================================
  STEP 2.5: SIGNAL SYNTHESIS
======================================================================

  Decision: action=Action.HOLD, confidence=0.60
  Reasoning: HOLD: score=+0.000 in neutral zone [-0.2, 0.2].
  NOTE: Works without LLM in pure-quant mode

======================================================================
  STEP 2.6: NEWS REACTOR
======================================================================

  news_reactor FAILED: cannot import name 'detect_news_impact' from 'src.strategy.news_reactor' (D:\Cloude_PR\projects\moex-trading-system\src\strategy\news_reactor.py)
  Traceback (most recent call last):
  File "D:\Cloude_PR\projects\moex-trading-system\scripts\full_system_audit.py", line 428, in test_news_reactor
    from src.strategy.news_reactor import NewsReactor

======================================================================
  STEP 2.7: RISK MANAGEMENT
======================================================================

  CircuitBreaker: equity=950K, DD=0.0%, triggered=False
  CircuitBreaker: equity=930K, DD=0.0%, triggered=True
  position_sizer FAILED: cannot import name 'PositionSizer' from 'src.risk.position_sizer' (D:\Cloude_PR\projects\moex-trading-system\src\risk\position_sizer.py)
  PositionTracker: opened 100@300 + 50@310, sold 80@320
  position_tracker FAILED: 'PositionTracker' object has no attribute 'net_quantity'
  RiskApproved/RiskRefused: import OK
  ProtectiveController: import OK

======================================================================
  STEP 2.8: EXECUTION
======================================================================

  twap FAILED: TWAPExecutor.__init__() got an unexpected keyword argument 'total_qty'
  triple_barrier FAILED: cannot import name 'TripleBarrierExecutor' from 'src.execution.triple_barrier' (D:\Cloude_PR\projects\moex-trading-system\src\execution\triple_barrier.py)
  DCA: import OK (Fibonacci DCA)
  Grid: import OK
  quoting FAILED: cannot import name 'AvellanedaStoikovQuoter' from 'src.execution.quoting' (D:\Cloude_PR\projects\moex-trading-system\src\execution\quoting.py)

======================================================================
  STEP 2.9: BACKTEST TOOLS
======================================================================

  CommissionManager: import OK

======================================================================
  STEP 3: EMA CROSSOVER BACKTEST (MONTHLY)
======================================================================

  SBER: Sharpe=1.17, DD=-8.17%, WR=73.3%, Trades=15, PnL=+425,978
  GAZP: Sharpe=0.23, DD=-8.81%, WR=52.4%, Trades=21, PnL=+47,874
  LKOH: Sharpe=0.93, DD=-9.03%, WR=60.0%, Trades=15, PnL=+397,344
  ROSN: Sharpe=0.32, DD=-6.17%, WR=53.3%, Trades=15, PnL=+65,153
  GMKN: Sharpe=0.22, DD=-9.43%, WR=61.9%, Trades=21, PnL=+52,133
  YNDX: Sharpe=1.38, DD=-7.72%, WR=63.6%, Trades=11, PnL=+388,414
  VTBR: Sharpe=0.21, DD=-18.46%, WR=47.1%, Trades=17, PnL=+84,513
  NVTK: Sharpe=0.9, DD=-7.64%, WR=66.7%, Trades=15, PnL=+317,578
  MGNT: Sharpe=0.46, DD=-10.24%, WR=57.1%, Trades=21, PnL=+131,883
  TATN: Sharpe=1.35, DD=-6.26%, WR=62.5%, Trades=16, PnL=+590,759

======================================================================
  STEP 4: MONTHLY P&L TABLES
======================================================================


### SBER -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | 0 | 0 | -1 |
| 2023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +306 | +306 |
| 2024 | 0 | 0 | 0 | 0 | 0 | 0 | +53 | 0 | 0 | 0 | 0 | 0 | +53 |
| 2025 | 0 | 0 | 0 | +46 | -1 | 0 | +18 | +4 | 0 | 0 | 0 | +2 | +69 |

### GAZP -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | -20 | +19 | 0 | -20 | +20 | 0 | 0 | -1 |
| 2023 | 0 | 0 | -20 | 0 | +19 | 0 | -20 | 0 | +19 | 0 | 0 | 0 | -1 |
| 2024 | 0 | +10 | 0 | -20 | +20 | 0 | 0 | 0 | 0 | -20 | +19 | 0 | +8 |
| 2025 | 0 | 0 | 0 | +50 | 0 | 0 | 0 | -21 | +21 | 0 | 0 | -6 | +43 |

### LKOH -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | 0 | +10 | +9 |
| 2023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +355 | +355 |
| 2024 | 0 | 0 | 0 | 0 | 0 | +48 | 0 | 0 | 0 | -28 | 0 | +27 | +47 |
| 2025 | 0 | 0 | +17 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | 0 | -29 | -12 |

### ROSN -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | -20 | 0 | -21 |
| 2023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +19 | +19 |
| 2024 | 0 | +17 | -1 | 0 | -21 | +20 | 0 | 0 | 0 | 0 | 0 | 0 | +16 |
| 2025 | 0 | 0 | +53 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | 0 | -1 | +51 |

### GMKN -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0 |
| 2023 | 0 | -5 | 0 | -28 | +11 | -29 | +13 | 0 | 0 | 0 | 0 | +32 | -5 |
| 2024 | 0 | 0 | 0 | -26 | +14 | 0 | 0 | 0 | 0 | 0 | 0 | -11 | -23 |
| 2025 | 0 | 0 | +20 | 0 | 0 | 0 | 0 | 0 | 0 | -22 | +11 | +72 | +81 |

### YNDX -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -20 | +19 | 0 | 0 | +14 | +13 |
| 2023 | 0 | -20 | +20 | 0 | 0 | 0 | 0 | 0 | +132 | 0 | -23 | +22 | +131 |
| 2024 | 0 | 0 | 0 | 0 | 0 | +244 | 0 | 0 | 0 | 0 | 0 | 0 | +244 |
| 2025 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0 |

### VTBR -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +24 | 0 | 0 | 0 | +24 |
| 2023 | 0 | +5 | -47 | 0 | 0 | 0 | 0 | 0 | 0 | +80 | 0 | 0 | +37 |
| 2024 | 0 | +3 | 0 | +5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +8 |
| 2025 | 0 | 0 | 0 | +32 | 0 | 0 | -8 | 0 | 0 | 0 | 0 | -6 | +18 |

### NVTK -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | 0 | +3 | +2 |
| 2023 | 0 | -1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +263 | 0 | +262 |
| 2024 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0 |
| 2025 | 0 | 0 | 0 | +44 | -1 | 0 | 0 | 0 | -1 | 0 | 0 | +11 | +54 |

### MGNT -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | -20 | +19 | 0 | 0 | -20 | +19 | -1 | 0 | -2 |
| 2023 | 0 | -1 | 0 | 0 | -1 | 0 | 0 | 0 | 0 | +56 | 0 | 0 | +55 |
| 2024 | 0 | 0 | 0 | 0 | 0 | +89 | 0 | 0 | 0 | 0 | 0 | -23 | +66 |
| 2025 | +22 | 0 | -1 | 0 | 0 | 0 | 0 | +7 | 0 | 0 | 0 | -15 | +13 |

### TATN -- Monthly P&L (thousands RUB)
| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2022 | 0 | 0 | 0 | 0 | 0 | 0 | -1 | 0 | -1 | 0 | 0 | 0 | -1 |
| 2023 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0 |
| 2024 | 0 | 0 | 0 | 0 | 0 | +529 | 0 | 0 | 0 | -1 | 0 | 0 | +528 |
| 2025 | 0 | 0 | +32 | +31 | 0 | -1 | 0 | -32 | +31 | 0 | 0 | +4 | +65 |

======================================================================
  STEP 5: STRATEGY COMPARISON
======================================================================

| Ticker | EMA Sharpe | EMA DD% | EMA CAGR% | EMA PnL | B&H Ret% | B&H Sharpe | vs B&H |
|--------|-----------|---------|-----------|---------|----------|------------|--------|
| SBER | 1.17 | -8.17 | 9.25 | +425,978 | -1.82 | 0.19 | +9.7% |
| GAZP | 0.23 | -8.81 | 1.17 | +47,874 | -64.56 | -0.34 | +23.0% |
| LKOH | 0.93 | -9.03 | 8.7 | +397,344 | -11.59 | 0.07 | +11.6% |
| ROSN | 0.32 | -6.17 | 1.59 | +65,153 | -33.06 | -0.05 | +10.7% |
| GMKN | 0.22 | -9.43 | 1.28 | +52,133 | -36.07 | -0.16 | +11.4% |
| YNDX | 1.38 | -7.72 | 16.29 | +388,414 | -9.83 | 0.19 | +20.6% |
| VTBR | 0.21 | -18.46 | 2.05 | +84,513 | -70.79 | -0.42 | +27.5% |
| NVTK | 0.9 | -7.64 | 7.15 | +317,578 | -33.05 | -0.04 | +16.3% |
| MGNT | 0.46 | -10.24 | 3.14 | +131,883 | -45.33 | -0.21 | +16.5% |
| TATN | 1.35 | -6.26 | 12.29 | +590,759 | 12.67 | 0.27 | +9.4% |

**IMOEX B&H:** Return=-28.19%, Sharpe=-0.1, DD=-50.51%

**Portfolio average:** Sharpe=0.72, DD=-9.2%, CAGR=6.3%
**Total PnL across 10 tickers:** +2,501,629 RUB

======================================================================
  STEP 6: COMPONENT STATUS MAP
======================================================================

| Component | File | Status | In Backtest | Result |
|-----------|------|--------|-------------|--------|
| Features | src/analysis/features.py | FAIL | No | cannot import name 'calculate_adx' from 'src.analysis.features' (D:\Cloude_PR\pr |
| ATR/ADX/OBV | src/analysis/features.py | FAIL | No | cannot access local variable 'calculate_adx' where it is not associated with a v |
| Advanced indicators | src/indicators/advanced.py | FAIL | No | 'ChandeKrollResult' object is not subscriptable |
| Ehlers | src/indicators/ehlers.py | FAIL | No | cannot import name 'mesa_adaptive_moving_average' from 'src.indicators.ehlers' ( |
| Damiani | src/indicators/damiani.py | FAIL | No | 'DamianiResult' object is not subscriptable |
| Squeeze Momentum | src/indicators/squeeze_momentum.py | FAIL | No | 'SqueezeResult' object is not subscriptable |
| SuperTrend | src/indicators/supertrend.py | FAIL | No | 'SuperTrendResult' object is not subscriptable |
| Support/Resistance | src/indicators/support_resistance.py | FAIL | No | cannot import name 'detect_support_resistance' from 'src.indicators.support_resi |
| ZigZag/KlingerVO | src/indicators/trend_quality.py | FAIL | No | cannot import name 'zigzag' from 'src.indicators.trend_quality' (D:\Cloude_PR\pr |
| Candle Patterns | src/indicators/candle_patterns.py | FAIL | No | cannot import name 'detect_all_patterns' from 'src.indicators.candle_patterns' ( |
| GARCH Forecast | src/indicators/garch_forecast.py | SKIP | No | needs arch library |
| Order Book | src/indicators/order_book.py | FAIL | No | cannot import name 'microprice' from 'src.indicators.order_book' (D:\Cloude_PR\p |
| Scoring | src/analysis/scoring.py | FAIL | No | cannot import name 'calculate_adx' from 'src.analysis.features' (D:\Cloude_PR\pr |
| Regime Detection | src/analysis/regime.py | FAIL | No | detect_regime() missing 2 required positional arguments: 'index_adx' and 'index_ |
| ML Walk-Forward | src/ml/walk_forward.py | OK (import) | No (needs training) | imports OK, no E2E run |
| ML Processors | src/ml/processors.py | FAIL | No | cannot import name 'CSRankNorm' from 'src.ml.processors' (D:\Cloude_PR\projects\ |
| Signal Synthesis | src/strategy/signal_synthesis.py | OK | No (not in backtest) | action=Action.HOLD |
| News Reactor | src/strategy/news_reactor.py | FAIL | No | cannot import name 'detect_news_impact' from 'src.strategy.news_reactor' (D:\Clo |
| Circuit Breaker | src/risk/portfolio_circuit_breaker.py | OK | Yes (backtest) | triggers at 15% DD |
| Position Sizer | src/risk/position_sizer.py | FAIL | No | cannot import name 'PositionSizer' from 'src.risk.position_sizer' (D:\Cloude_PR\ |
| Position Tracker | src/risk/position_tracker.py | FAIL | No | 'PositionTracker' object has no attribute 'net_quantity' |
| RiskApproved Wrapper | src/risk/rules.py | OK | Yes (design pattern) | type-safe risk check |
| Protective Stops | src/risk/protective.py | OK | Yes (backtest) | trailing/fixed stops |
| TWAP | src/execution/twap.py | FAIL | No | TWAPExecutor.__init__() got an unexpected keyword argument 'total_qty' |
| Triple Barrier | src/execution/triple_barrier.py | FAIL | No | cannot import name 'TripleBarrierExecutor' from 'src.execution.triple_barrier' ( |
| DCA Executor | src/execution/dca.py | OK | No (needs live) | Fibonacci levels |
| Grid Executor | src/execution/grid.py | OK | No (needs live) | grid levels |
| A-S Quoter | src/execution/quoting.py | FAIL | No | cannot import name 'AvellanedaStoikovQuoter' from 'src.execution.quoting' (D:\Cl |
| Commission Manager | src/backtest/commissions.py | OK | Yes | MOEX commission rules |
| Monte Carlo | src/backtest/monte_carlo.py | FAIL | No | cannot import name 'monte_carlo_simulation' from 'src.backtest.monte_carlo' (D:\ |
| Optuna Optimizer | src/backtest/optimizer.py | FAIL | No | cannot import name 'OptunaOptimizer' from 'src.backtest.optimizer' (D:\Cloude_PR |
| Metrics | src/backtest/metrics.py | FAIL | No | 'numpy.ndarray' object has no attribute 'dropna' |