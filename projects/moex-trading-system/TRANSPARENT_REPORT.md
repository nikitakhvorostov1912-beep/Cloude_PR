# TRANSPARENT BACKTEST REPORT
Date: 2026-03-22 17:40
Data: MOEX ISS 2022-01-01 -- 2025-12-31
Capital: 1,000,000 RUB per ticker

## 1. Instrument Selection

### Market Scanner
- Scanned MOEX TQBR: **236 equities** found
- Loaded for backtest: **38 instruments**
- Including futures: **7**

### Selector Output (latest data):
| # | Ticker | Sector | Score | Direction |
|---|--------|--------|-------|-----------|
| 1 | GMKN | metals | 63.1 | LONG |
| 2 | OZON | tech | 61.8 | LONG |
| 3 | PLZL | metals | 61.6 | LONG |
| 4 | RIH5 | other | 60.4 | LONG |
| 5 | LKOH | oil_gas | 60.0 | LONG |
| 6 | SiZ5 | other | 59.3 | neutral |
| 7 | X5 | other | 58.2 | neutral |
| 8 | TRNFP | other | 58.2 | neutral |
| 9 | UGLD | other | 57.8 | neutral |
| 10 | YDEX | other | 57.5 | neutral |
| 11 | VKCO | tech | 56.9 | neutral |
| 12 | PHOR | chemicals | 55.9 | neutral |
| 13 | NVTK | oil_gas | 55.6 | neutral |
| 14 | T | other | 55.6 | neutral |
| 15 | SNGSP | oil_gas | 55.6 | neutral |

## 2. Futures

- Futures trades: **0**
- Equity trades: **233**
- NOTE: Futures data may not have loaded (MOEX ISS RFUD can be inconsistent)

## 3. Trade Journal

### Total trades: 233
### Full journal (every trade):

| # | Open | Close | Ticker | Side | Entry | Exit | Qty | Net P&L | Ret% | Days | Exit | Score | Indicators | Regime |
|---|------|-------|--------|------|-------|------|-----|---------|------|------|------|-------|------------|--------|
| 1 | 2022-05-30 | 2022-06-30 | GAZP | long | 300.82 | 278.79 | 80 | -1,765 | -7.3% | 22d | stop_loss | 44 | 6L/1S/4N of 11 | range |
| 2 | 2022-07-04 | 2022-08-31 | GAZP | short | 186.23 | 220.19 | 150 | -5,097 | -18.2% | 42d | stop_loss | 64 | 3L/6S/2N of 11 | range |
| 3 | 2022-09-06 | 2022-09-20 | GAZP | long | 246.02 | 230.72 | 240 | -3,678 | -6.2% | 10d | stop_loss | 49 | 6L/2S/3N of 11 | range |
| 4 | 2022-10-07 | 2025-12-30 | GAZP | short | 195.13 | 125.36 | 180 | +12,556 | +35.8% | 887d | end_of_data | 61 | 0L/8S/3N of 11 | range |
| 5 | 2022-09-02 | 2022-09-06 | ROSN | long | 385.20 | 369.50 | 240 | -3,777 | -4.1% | 2d | stop_loss | 50 | 7L/2S/2N of 11 | range |
| 6 | 2022-09-21 | 2022-10-27 | ROSN | short | 312.45 | 345.25 | 159 | -5,221 | -10.5% | 26d | stop_loss | 64 | 4L/4S/3N of 11 | range |
| 7 | 2022-11-08 | 2022-11-15 | ROSN | long | 352.05 | 332.45 | 190 | -3,730 | -5.6% | 5d | stop_loss | 48 | 7L/1S/3N of 11 | range |
| 8 | 2023-12-14 | 2023-12-15 | ROSN | short | 535.60 | 561.10 | 136 | -3,476 | -4.8% | 1d | stop_loss | 48 | 3L/7S/1N of 11 | uptrend |
| 9 | 2023-12-20 | 2024-02-22 | ROSN | long | 578.70 | 559.05 | 188 | -3,705 | -3.4% | 44d | stop_loss | 52 | 5L/2S/4N of 11 | range |
| 10 | 2024-02-26 | 2024-05-14 | ROSN | short | 575.45 | 593.45 | 95 | -1,716 | -3.1% | 54d | stop_loss | 34 | 6L/3S/2N of 11 | range |
| 11 | 2024-05-31 | 2024-07-02 | ROSN | short | 556.55 | 579.25 | 303 | -6,896 | -4.1% | 21d | stop_loss | 58 | 2L/6S/3N of 11 | downtrend |
| 12 | 2024-12-18 | 2024-12-20 | ROSN | long | 487.80 | 521.25 | 90 | +3,006 | +6.8% | 2d | take_profit | 36 | 4L/3S/4N of 11 | range |
| 13 | 2025-03-14 | 2025-12-30 | ROSN | short | 530.50 | 409.00 | 107 | +12,996 | +22.9% | 266d | end_of_data | 46 | 4L/3S/4N of 11 | uptrend |
| 14 | 2022-09-02 | 2022-09-06 | SBER | long | 143.82 | 137.64 | 600 | -3,716 | -4.3% | 2d | stop_loss | 50 | 9L/0S/2N of 11 | range |
| 15 | 2022-09-23 | 2022-11-07 | SBER | short | 119.37 | 130.90 | 450 | -5,194 | -9.7% | 30d | stop_loss | 62 | 3L/6S/2N of 11 | range |
| 16 | 2022-11-08 | 2022-12-05 | SBER | long | 131.31 | 142.45 | 270 | +3,004 | +8.5% | 19d | take_profit | 44 | 9L/0S/2N of 11 | range |
| 17 | 2023-12-14 | 2023-12-15 | SBER | short | 256.62 | 268.72 | 280 | -3,396 | -4.7% | 1d | stop_loss | 45 | 4L/5S/2N of 11 | uptrend |
| 18 | 2024-01-03 | 2024-02-12 | SBER | long | 274.58 | 286.70 | 510 | +6,167 | +4.4% | 28d | take_profit | 52 | 7L/3S/1N of 11 | range |
| 19 | 2024-07-15 | 2024-07-26 | SBER | short | 284.36 | 298.78 | 480 | -6,936 | -5.1% | 9d | stop_loss | 57 | 3L/7S/1N of 11 | downtrend |
| 20 | 2024-12-27 | 2025-02-10 | SBER | long | 271.22 | 291.38 | 300 | +6,039 | +7.4% | 28d | take_profit | 57 | 7L/1S/3N of 11 | downtrend |
| 21 | 2025-04-08 | 2025-04-11 | SBER | short | 282.01 | 299.66 | 190 | -3,359 | -6.3% | 3d | stop_loss | 58 | 3L/6S/2N of 11 | uptrend |
| 22 | 2025-04-22 | 2025-05-02 | SBER | long | 312.27 | 300.60 | 310 | -3,627 | -3.8% | 9d | stop_loss | 53 | 7L/1S/3N of 11 | range |
| 23 | 2025-05-27 | 2025-06-02 | SBER | short | 298.68 | 310.93 | 280 | -3,439 | -4.1% | 6d | stop_loss | 51 | 0L/5S/6N of 11 | uptrend |
| 24 | 2025-07-28 | 2025-08-07 | SBER | short | 303.95 | 313.75 | 170 | -1,671 | -3.2% | 8d | stop_loss | 41 | 2L/8S/1N of 11 | uptrend |
| 25 | 2025-08-12 | 2025-08-16 | SBER | long | 318.02 | 310.57 | 610 | -4,563 | -2.4% | 4d | stop_loss | 57 | 8L/1S/2N of 11 | uptrend |
| 26 | 2025-08-30 | 2025-12-30 | SBER | short | 309.90 | 299.90 | 230 | +2,293 | +3.2% | 112d | end_of_data | 38 | 4L/4S/3N of 11 | range |
| 27 | 2022-08-31 | 2022-09-01 | LKOH | long | 4271.00 | 4540.00 | 23 | +6,177 | +6.3% | 1d | take_profit | 54 | 7L/2S/2N of 11 | range |
| 28 | 2022-09-28 | 2022-10-18 | LKOH | short | 3906.50 | 4297.00 | 13 | -5,082 | -10.0% | 14d | stop_loss | 63 | 4L/4S/3N of 11 | range |
| 29 | 2022-10-19 | 2022-10-27 | LKOH | long | 4205.50 | 4653.50 | 6 | +2,685 | +10.6% | 6d | take_profit | 38 | 5L/3S/3N of 11 | range |
| 30 | 2022-12-22 | 2023-03-21 | LKOH | short | 4026.50 | 4249.00 | 47 | -10,477 | -5.5% | 60d | stop_loss | 60 | 3L/5S/3N of 11 | downtrend |
| 31 | 2023-12-18 | 2024-01-31 | LKOH | short | 6722.50 | 7064.50 | 10 | -3,427 | -5.1% | 30d | stop_loss | 50 | 5L/3S/3N of 11 | uptrend |
| 32 | 2024-02-02 | 2024-02-21 | LKOH | long | 7115.00 | 6979.50 | 27 | -3,677 | -1.9% | 13d | stop_loss | 60 | 8L/0S/3N of 11 | uptrend |
| 33 | 2024-06-03 | 2024-06-07 | LKOH | short | 7251.00 | 7567.00 | 10 | -3,168 | -4.4% | 4d | stop_loss | 50 | 3L/5S/3N of 11 | uptrend |
| 34 | 2024-09-26 | 2024-10-28 | LKOH | long | 6891.00 | 6664.50 | 16 | -3,635 | -3.3% | 22d | stop_loss | 54 | 6L/1S/4N of 11 | downtrend |
| 35 | 2024-12-16 | 2024-12-26 | LKOH | short | 6778.50 | 7033.50 | 13 | -3,324 | -3.8% | 8d | stop_loss | 56 | 3L/2S/6N of 11 | range |
| 36 | 2024-12-30 | 2025-01-09 | LKOH | long | 7236.00 | 6969.50 | 26 | -6,947 | -3.7% | 4d | stop_loss | 52 | 9L/1S/1N of 11 | uptrend |
| 37 | 2025-03-27 | 2025-12-30 | LKOH | short | 7107.50 | 5908.50 | 6 | +7,190 | +16.9% | 255d | end_of_data | 34 | 0L/6S/5N of 11 | range |
| 38 | 2022-08-11 | 2022-08-17 | NVTK | long | 1020.20 | 1117.70 | 32 | +3,116 | +9.6% | 4d | take_profit | 36 | 4L/2S/5N of 11 | range |
| 39 | 2022-09-27 | 2022-10-28 | NVTK | short | 984.60 | 1103.90 | 44 | -5,254 | -12.1% | 23d | stop_loss | 63 | 5L/5S/1N of 11 | range |
| 40 | 2022-11-02 | 2022-11-28 | NVTK | long | 1102.60 | 1042.50 | 31 | -1,866 | -5.5% | 17d | stop_loss | 33 | 7L/2S/2N of 11 | range |
| 41 | 2022-12-07 | 2023-02-06 | NVTK | short | 1035.80 | 1088.30 | 133 | -6,997 | -5.1% | 42d | stop_loss | 58 | 2L/4S/5N of 11 | downtrend |
| 42 | 2023-02-09 | 2023-02-15 | NVTK | long | 1072.20 | 1040.10 | 184 | -5,926 | -3.0% | 4d | stop_loss | 52 | 7L/2S/2N of 11 | uptrend |
| 43 | 2023-02-20 | 2023-03-06 | NVTK | short | 1033.00 | 1078.80 | 75 | -3,443 | -4.4% | 9d | stop_loss | 47 | 5L/3S/3N of 11 | range |
| 44 | 2023-11-14 | 2025-12-30 | NVTK | short | 1593.80 | 1188.00 | 51 | +20,690 | +25.4% | 603d | end_of_data | 48 | 2L/6S/3N of 11 | uptrend |
| 45 | 2022-08-18 | 2022-08-22 | T | long | 2480.02 | 2757.22 | 22 | +6,092 | +11.2% | 2d | take_profit | 50 | 7L/1S/3N of 11 | range |
| 46 | 2022-12-15 | 2023-01-11 | T | short | 2496.48 | 2697.53 | 8 | -1,611 | -8.1% | 18d | stop_loss | 58 | 2L/6S/3N of 11 | crisis |
| 47 | 2023-02-20 | 2023-02-24 | T | short | 2476.48 | 2621.25 | 36 | -5,221 | -5.9% | 3d | stop_loss | 62 | 4L/5S/2N of 11 | uptrend |
| 48 | 2023-04-13 | 2023-04-28 | T | long | 2653.52 | 2829.37 | 71 | +12,465 | +6.6% | 11d | take_profit | 50 | 7L/2S/2N of 11 | uptrend |
| 49 | 2023-09-25 | 2023-10-16 | T | short | 3273.48 | 3505.19 | 3 | -696 | -7.1% | 15d | stop_loss | 44 | 4L/4S/3N of 11 | crisis |
| 50 | 2023-10-23 | 2023-10-31 | T | long | 3480.52 | 3352.04 | 29 | -3,736 | -3.7% | 6d | stop_loss | 50 | 4L/3S/4N of 11 | range |
| 51 | 2023-12-01 | 2025-02-13 | T | short | 3298.98 | 3452.66 | 11 | -1,694 | -4.7% | 286d | stop_loss | 34 | 2L/5S/4N of 11 | range |
| 52 | 2025-04-08 | 2025-04-22 | T | short | 2999.58 | 3260.11 | 6 | -1,565 | -8.7% | 12d | stop_loss | 47 | 4L/7S/0N of 11 | crisis |
| 53 | 2025-04-28 | 2025-05-02 | T | long | 3279.82 | 3145.75 | 28 | -3,763 | -4.1% | 3d | stop_loss | 50 | 4L/3S/4N of 11 | range |
| 54 | 2025-06-04 | 2025-06-09 | T | long | 3286.62 | 3167.79 | 31 | -3,694 | -3.6% | 5d | stop_loss | 52 | 6L/1S/4N of 11 | range |
| 55 | 2025-07-13 | 2025-07-14 | T | short | 3092.98 | 3184.03 | 19 | -1,736 | -3.0% | 1d | stop_loss | 44 | 2L/5S/4N of 11 | uptrend |
| 56 | 2025-09-14 | 2025-12-11 | T | short | 3187.98 | 3268.53 | 62 | -5,014 | -2.5% | 76d | stop_loss | 50 | 3L/6S/2N of 11 | downtrend |
| 57 | 2025-05-03 | 2025-06-23 | X5 | short | 3299.98 | 3439.48 | 25 | -3,496 | -4.2% | 45d | stop_loss | 49 | 2L/3S/6N of 11 | range |
| 58 | 2025-07-10 | 2025-07-20 | X5 | short | 2885.48 | 3081.35 | 17 | -3,335 | -6.8% | 10d | stop_loss | 58 | 4L/5S/2N of 11 | range |
| 59 | 2025-11-26 | 2025-12-03 | X5 | long | 2695.02 | 2613.81 | 22 | -1,792 | -3.0% | 7d | stop_loss | 34 | 6L/0S/5N of 11 | range |
| 60 | 2022-05-20 | 2024-04-03 | PLZL | short | 1198.00 | 1308.00 | 32 | -3,524 | -9.2% | 476d | stop_loss | 52 | 4L/6S/1N of 11 | range |
| 61 | 2024-06-07 | 2024-09-17 | PLZL | short | 1234.75 | 1334.00 | 17 | -1,690 | -8.1% | 71d | stop_loss | 48 | 4L/5S/2N of 11 | crisis |
| 62 | 2024-12-20 | 2025-01-09 | PLZL | short | 1358.00 | 1459.00 | 8 | -809 | -7.5% | 11d | stop_loss | 41 | 3L/5S/3N of 11 | crisis |
| 63 | 2025-05-03 | 2025-06-05 | PLZL | short | 1717.40 | 1831.00 | 15 | -1,707 | -6.6% | 30d | stop_loss | 42 | 3L/5S/3N of 11 | uptrend |
| 64 | 2025-06-28 | 2025-07-04 | PLZL | long | 1798.20 | 1909.00 | 57 | +6,305 | +6.2% | 6d | take_profit | 47 | 3L/1S/7N of 11 | range |
| 65 | 2025-10-22 | 2025-12-11 | PLZL | short | 2041.80 | 2209.00 | 10 | -1,674 | -8.2% | 42d | stop_loss | 47 | 2L/6S/3N of 11 | crisis |
| 66 | 2022-09-05 | 2022-09-06 | VTBR | long | 103.35 | 99.85 | 10000 | -35,141 | -3.4% | 1d | stop_loss | 50 | 9L/0S/2N of 11 | range |
| 67 | 2022-09-23 | 2023-03-20 | VTBR | short | 85.07 | 92.17 | 10000 | -71,011 | -8.3% | 122d | stop_loss | 62 | 3L/6S/2N of 11 | range |
| 68 | 2023-10-04 | 2023-10-17 | VTBR | short | 124.45 | 132.12 | 10000 | -76,851 | -6.2% | 9d | stop_loss | 39 | 3L/4S/4N of 11 | uptrend |
| 69 | 2023-10-24 | 2023-10-26 | VTBR | long | 133.08 | 128.36 | 10000 | -47,297 | -3.5% | 2d | stop_loss | 53 | 8L/1S/2N of 11 | range |
| 70 | 2023-10-27 | 2025-12-30 | VTBR | short | 126.65 | 72.22 | 10000 | +544,228 | +43.0% | 615d | end_of_data | 36 | 3L/3S/5N of 11 | range |
| 71 | 2022-08-02 | 2022-08-17 | PHOR | short | 7209.00 | 7717.00 | 3 | -1,526 | -7.1% | 11d | stop_loss | 34 | 1L/6S/4N of 11 | range |
| 72 | 2022-09-23 | 2023-08-14 | PHOR | short | 7186.00 | 7843.00 | 5 | -3,289 | -9.2% | 224d | stop_loss | 50 | 4L/5S/2N of 11 | range |
| 73 | 2023-09-05 | 2025-12-30 | PHOR | short | 7215.00 | 6369.00 | 6 | +5,072 | +11.7% | 655d | end_of_data | 32 | 3L/6S/2N of 11 | range |
| 74 | 2024-10-28 | 2024-12-23 | YDEX | short | 3742.98 | 3972.53 | 22 | -5,059 | -6.1% | 40d | stop_loss | 62 | 1L/6S/4N of 11 | range |
| 75 | 2024-12-30 | 2025-01-06 | YDEX | long | 3994.02 | 3797.78 | 19 | -3,736 | -4.9% | 2d | stop_loss | 57 | 8L/1S/2N of 11 | range |
| 76 | 2025-04-07 | 2025-04-22 | YDEX | short | 4068.98 | 4389.49 | 10 | -3,209 | -7.9% | 13d | stop_loss | 55 | 3L/5S/3N of 11 | range |
| 77 | 2025-07-01 | 2025-07-07 | YDEX | long | 4168.52 | 4057.28 | 33 | -3,684 | -2.7% | 6d | stop_loss | 56 | 3L/3S/5N of 11 | range |
| 78 | 2025-07-10 | 2025-07-11 | YDEX | long | 4167.52 | 4058.21 | 33 | -3,621 | -2.6% | 1d | stop_loss | 52 | 3L/3S/5N of 11 | range |
| 79 | 2025-07-16 | 2025-07-28 | YDEX | long | 4329.52 | 4196.20 | 45 | -6,018 | -3.1% | 12d | stop_loss | 66 | 7L/1S/3N of 11 | uptrend |
| 80 | 2025-09-15 | 2025-12-05 | YDEX | short | 4149.98 | 4280.23 | 46 | -6,011 | -3.1% | 71d | stop_loss | 57 | 2L/7S/2N of 11 | downtrend |
| 81 | 2022-07-20 | 2022-09-01 | SMLT | long | 2762.02 | 3135.32 | 8 | +2,984 | +13.5% | 31d | take_profit | 38 | 5L/1S/5N of 11 | range |
| 82 | 2022-09-26 | 2022-11-15 | SMLT | short | 2199.98 | 2600.15 | 13 | -5,206 | -18.2% | 35d | stop_loss | 62 | 4L/6S/1N of 11 | range |
| 83 | 2023-01-16 | 2023-02-10 | SMLT | long | 2532.02 | 2698.04 | 18 | +2,984 | +6.5% | 19d | take_profit | 34 | 6L/1S/4N of 11 | range |
| 84 | 2023-03-22 | 2023-03-27 | SMLT | short | 2482.98 | 2594.54 | 31 | -3,466 | -4.5% | 3d | stop_loss | 48 | 2L/3S/6N of 11 | range |
| 85 | 2023-03-29 | 2023-04-26 | SMLT | long | 2620.52 | 2796.00 | 71 | +12,439 | +6.7% | 20d | take_profit | 52 | 5L/2S/4N of 11 | uptrend |
| 86 | 2023-12-13 | 2023-12-21 | SMLT | short | 3851.48 | 4000.15 | 11 | -1,640 | -3.9% | 6d | stop_loss | 40 | 4L/2S/5N of 11 | uptrend |
| 87 | 2023-12-28 | 2025-12-30 | SMLT | short | 3885.48 | 985.00 | 18 | +52,207 | +74.7% | 575d | end_of_data | 49 | 3L/3S/5N of 11 | uptrend |
| 88 | 2022-08-26 | 2022-08-31 | SPBE | long | 200.02 | 167.93 | 116 | -3,724 | -16.1% | 3d | stop_loss | 53 | 6L/3S/2N of 11 | range |
| 89 | 2022-09-06 | 2025-02-14 | SPBE | short | 165.38 | 204.61 | 88 | -3,454 | -23.7% | 622d | stop_loss | 46 | 3L/3S/5N of 11 | range |
| 90 | 2025-04-13 | 2025-04-22 | SPBE | short | 230.38 | 271.38 | 21 | -862 | -17.8% | 7d | stop_loss | 34 | 3L/4S/4N of 11 | crisis |
| 91 | 2025-05-27 | 2025-08-08 | SPBE | short | 232.58 | 262.02 | 59 | -1,739 | -12.7% | 68d | stop_loss | 50 | 2L/5S/4N of 11 | crisis |
| 92 | 2025-09-23 | 2025-10-17 | SPBE | short | 227.38 | 247.30 | 87 | -1,735 | -8.8% | 24d | stop_loss | 58 | 4L/4S/3N of 11 | crisis |
| 93 | 2025-11-19 | 2025-11-25 | SPBE | long | 239.42 | 262.64 | 199 | +4,616 | +9.7% | 4d | take_profit | 65 | 3L/3S/5N of 11 | crisis |
| 94 | 2022-11-18 | 2022-11-29 | GMKN | long | 151.86 | 142.00 | 116 | -1,145 | -6.5% | 7d | stop_loss | 38 | 6L/1S/4N of 11 | crisis |
| 95 | 2023-02-16 | 2023-03-01 | GMKN | short | 141.98 | 150.00 | 1237 | -9,939 | -5.7% | 8d | stop_loss | 59 | 2L/4S/5N of 11 | downtrend |
| 96 | 2023-03-27 | 2023-03-29 | GMKN | long | 153.84 | 148.00 | 1302 | -7,623 | -3.8% | 2d | stop_loss | 49 | 7L/1S/3N of 11 | uptrend |
| 97 | 2023-05-05 | 2023-05-11 | GMKN | short | 141.52 | 149.00 | 1367 | -10,246 | -5.3% | 3d | stop_loss | 60 | 5L/4S/2N of 11 | downtrend |
| 98 | 2023-06-16 | 2023-06-20 | GMKN | long | 155.62 | 150.00 | 1264 | -7,123 | -3.6% | 2d | stop_loss | 52 | 7L/1S/3N of 11 | uptrend |
| 99 | 2023-07-04 | 2023-07-06 | GMKN | short | 145.44 | 153.00 | 650 | -4,924 | -5.2% | 2d | stop_loss | 50 | 5L/3S/3N of 11 | range |
| 100 | 2023-12-12 | 2023-12-15 | GMKN | short | 162.78 | 171.00 | 262 | -2,158 | -5.1% | 3d | stop_loss | 36 | 2L/4S/5N of 11 | range |
| 101 | 2023-12-19 | 2023-12-21 | GMKN | long | 174.02 | 167.00 | 780 | -5,489 | -4.0% | 2d | stop_loss | 53 | 5L/3S/3N of 11 | range |
| 102 | 2023-12-27 | 2024-04-12 | GMKN | short | 161.10 | 169.00 | 531 | -4,204 | -4.9% | 69d | stop_loss | 52 | 3L/5S/3N of 11 | uptrend |
| 103 | 2024-05-10 | 2024-05-17 | GMKN | short | 150.78 | 159.00 | 578 | -4,760 | -5.5% | 5d | stop_loss | 48 | 4L/3S/4N of 11 | range |
| 104 | 2024-12-02 | 2024-12-03 | GMKN | long | 116.10 | 108.00 | 136 | -1,103 | -7.0% | 1d | stop_loss | 38 | 5L/1S/5N of 11 | crisis |
| 105 | 2024-12-04 | 2024-12-26 | GMKN | short | 102.20 | 113.00 | 180 | -1,946 | -10.6% | 16d | stop_loss | 50 | 5L/2S/4N of 11 | crisis |
| 106 | 2025-01-03 | 2025-01-17 | GMKN | long | 114.68 | 127.00 | 146 | +1,797 | +10.7% | 9d | take_profit | 36 | 7L/3S/1N of 11 | crisis |
| 107 | 2025-03-30 | 2025-04-01 | GMKN | short | 117.42 | 127.00 | 407 | -3,904 | -8.2% | 2d | stop_loss | 50 | 2L/5S/4N of 11 | uptrend |
| 108 | 2025-07-19 | 2025-07-25 | GMKN | long | 119.30 | 112.00 | 1446 | -10,572 | -6.1% | 6d | stop_loss | 54 | 8L/0S/3N of 11 | uptrend |
| 109 | 2025-10-04 | 2025-10-06 | GMKN | short | 116.66 | 125.00 | 495 | -4,134 | -7.2% | 2d | stop_loss | 45 | 1L/4S/6N of 11 | range |
| 110 | 2025-10-07 | 2025-10-08 | GMKN | long | 127.96 | 121.00 | 698 | -4,867 | -5.5% | 1d | stop_loss | 56 | 4L/1S/6N of 11 | range |
| 111 | 2025-11-17 | 2025-11-18 | GMKN | short | 121.02 | 128.00 | 311 | -2,175 | -5.8% | 1d | stop_loss | 38 | 3L/4S/4N of 11 | range |
| 112 | 2022-06-03 | 2022-06-22 | SNGSP | long | 35.94 | 34.19 | 2100 | -3,672 | -4.9% | 12d | stop_loss | 50 | 4L/2S/5N of 11 | range |
| 113 | 2022-07-18 | 2023-04-06 | SNGSP | short | 33.10 | 34.91 | 2900 | -5,259 | -5.5% | 184d | stop_loss | 64 | 1L/6S/4N of 11 | range |
| 114 | 2024-01-15 | 2024-02-01 | SNGSP | short | 54.91 | 57.30 | 700 | -1,677 | -4.4% | 13d | stop_loss | 36 | 4L/3S/4N of 11 | range |
| 115 | 2024-06-21 | 2024-07-02 | SNGSP | short | 64.27 | 68.69 | 700 | -3,099 | -6.9% | 7d | stop_loss | 48 | 3L/4S/4N of 11 | uptrend |
| 116 | 2024-10-01 | 2024-11-27 | SNGSP | long | 55.66 | 59.68 | 700 | +2,813 | +7.2% | 41d | take_profit | 38 | 7L/1S/3N of 11 | range |
| 117 | 2025-03-02 | 2025-12-30 | SNGSP | short | 57.24 | 41.97 | 600 | +9,159 | +26.7% | 276d | end_of_data | 33 | 5L/3S/3N of 11 | range |
| 118 | 2022-07-04 | 2022-07-13 | AFKS | long | 15.02 | 13.94 | 3523 | -3,810 | -7.2% | 7d | stop_loss | 45 | 6L/2S/3N of 11 | range |
| 119 | 2022-07-20 | 2022-07-26 | AFKS | short | 13.18 | 14.51 | 2651 | -3,538 | -10.1% | 4d | stop_loss | 52 | 2L/5S/4N of 11 | range |
| 120 | 2022-07-27 | 2022-09-21 | AFKS | long | 14.02 | 13.02 | 1905 | -1,907 | -7.1% | 40d | stop_loss | 34 | 2L/6S/3N of 11 | range |
| 121 | 2022-09-22 | 2023-02-07 | AFKS | short | 12.76 | 13.99 | 4316 | -5,310 | -9.6% | 96d | stop_loss | 61 | 2L/6S/3N of 11 | range |
| 122 | 2023-09-22 | 2024-02-09 | AFKS | short | 17.07 | 18.17 | 3192 | -3,517 | -6.5% | 98d | stop_loss | 45 | 4L/4S/3N of 11 | uptrend |
| 123 | 2024-06-27 | 2025-12-30 | AFKS | short | 23.40 | 13.23 | 388 | +3,945 | +43.4% | 451d | end_of_data | 44 | 1L/5S/5N of 11 | crisis |
| 124 | 2022-07-19 | 2022-07-25 | OZON | long | 1173.90 | 1359.20 | 33 | +6,110 | +15.8% | 4d | take_profit | 50 | 7L/1S/3N of 11 | range |
| 125 | 2022-09-28 | 2022-10-18 | OZON | short | 1069.60 | 1294.60 | 23 | -5,178 | -21.1% | 14d | stop_loss | 62 | 3L/5S/3N of 11 | range |
| 126 | 2022-10-31 | 2022-11-14 | OZON | long | 1338.40 | 1519.20 | 17 | +3,071 | +13.5% | 9d | take_profit | 36 | 5L/2S/4N of 11 | range |
| 127 | 2023-05-11 | 2023-05-24 | OZON | short | 1648.60 | 1763.80 | 15 | -1,731 | -7.0% | 9d | stop_loss | 38 | 3L/4S/4N of 11 | range |
| 128 | 2023-12-14 | 2023-12-19 | OZON | short | 2538.60 | 2729.00 | 4 | -763 | -7.5% | 3d | stop_loss | 44 | 4L/5S/2N of 11 | crisis |
| 129 | 2023-12-29 | 2024-01-15 | OZON | long | 2804.90 | 3015.60 | 29 | +6,102 | +7.5% | 9d | take_profit | 60 | 7L/2S/2N of 11 | range |
| 130 | 2024-07-09 | 2025-02-17 | OZON | short | 3777.60 | 4110.00 | 5 | -1,664 | -8.8% | 156d | stop_loss | 50 | 4L/6S/1N of 11 | crisis |
| 131 | 2025-04-09 | 2025-06-04 | OZON | short | 3578.60 | 3945.80 | 4 | -1,470 | -10.3% | 38d | stop_loss | 54 | 6L/2S/3N of 11 | crisis |
| 132 | 2025-11-12 | 2025-12-19 | OZON | short | 3963.60 | 4243.00 | 3 | -839 | -7.1% | 33d | stop_loss | 34 | 3L/5S/3N of 11 | crisis |
| 133 | 2022-06-16 | 2022-07-07 | TATN | long | 440.20 | 415.00 | 149 | -3,761 | -5.7% | 15d | stop_loss | 46 | 5L/2S/4N of 11 | range |
| 134 | 2022-07-14 | 2022-07-15 | TATN | short | 366.40 | 398.70 | 162 | -5,239 | -8.8% | 1d | stop_loss | 62 | 3L/6S/2N of 11 | range |
| 135 | 2022-08-16 | 2022-09-20 | TATN | long | 437.20 | 412.50 | 151 | -3,736 | -5.7% | 25d | stop_loss | 54 | 9L/2S/0N of 11 | range |
| 136 | 2022-09-26 | 2022-10-03 | TATN | short | 344.80 | 383.00 | 136 | -5,200 | -11.1% | 5d | stop_loss | 64 | 3L/7S/1N of 11 | range |
| 137 | 2023-03-22 | 2023-03-28 | TATN | long | 350.60 | 367.90 | 357 | +6,163 | +4.9% | 4d | take_profit | 49 | 7L/1S/3N of 11 | downtrend |
| 138 | 2024-06-04 | 2025-02-12 | TATN | short | 693.80 | 725.20 | 110 | -3,462 | -4.5% | 177d | stop_loss | 49 | 5L/4S/2N of 11 | uptrend |
| 139 | 2025-03-31 | 2025-04-25 | TATN | short | 673.10 | 711.50 | 90 | -3,462 | -5.7% | 23d | stop_loss | 48 | 2L/4S/5N of 11 | uptrend |
| 140 | 2025-06-02 | 2025-08-06 | TATN | short | 656.30 | 696.90 | 84 | -3,416 | -6.2% | 60d | stop_loss | 58 | 4L/6S/1N of 11 | uptrend |
| 141 | 2025-09-01 | 2025-12-30 | TATN | short | 650.80 | 580.70 | 258 | +18,071 | +10.8% | 110d | end_of_data | 50 | 5L/6S/0N of 11 | downtrend |
| 142 | 2022-12-20 | 2022-12-21 | RUAL | long | 41.17 | 39.23 | 1960 | -3,800 | -4.7% | 1d | stop_loss | 47 | 6L/1S/4N of 11 | downtrend |
| 143 | 2023-02-22 | 2023-04-10 | RUAL | short | 40.03 | 42.31 | 3090 | -7,058 | -5.7% | 31d | stop_loss | 56 | 4L/4S/3N of 11 | downtrend |
| 144 | 2023-05-08 | 2023-07-06 | RUAL | short | 39.73 | 41.64 | 3650 | -6,987 | -4.8% | 41d | stop_loss | 53 | 4L/5S/2N of 11 | downtrend |
| 145 | 2023-07-10 | 2023-07-24 | RUAL | long | 41.37 | 43.49 | 4750 | +10,073 | +5.1% | 10d | take_profit | 47 | 7L/1S/3N of 11 | uptrend |
| 146 | 2023-09-22 | 2024-04-15 | RUAL | short | 40.66 | 43.01 | 1490 | -3,500 | -5.8% | 142d | stop_loss | 50 | 3L/4S/4N of 11 | range |
| 147 | 2024-07-11 | 2025-02-25 | RUAL | short | 40.38 | 42.99 | 1330 | -3,477 | -6.5% | 160d | stop_loss | 48 | 3L/4S/4N of 11 | uptrend |
| 148 | 2025-04-05 | 2025-12-30 | RUAL | short | 34.36 | 33.97 | 580 | +230 | +1.1% | 246d | end_of_data | 50 | 5L/4S/2N of 11 | crisis |
| 149 | 2022-06-28 | 2022-06-29 | PIKK | long | 794.52 | 734.48 | 62 | -3,727 | -7.6% | 1d | stop_loss | 50 | 6L/1S/4N of 11 | range |
| 150 | 2022-09-23 | 2023-04-25 | PIKK | short | 594.78 | 680.48 | 61 | -5,232 | -14.4% | 148d | stop_loss | 62 | 2L/7S/2N of 11 | range |
| 151 | 2023-09-21 | 2024-02-08 | PIKK | short | 737.28 | 792.31 | 31 | -1,708 | -7.5% | 98d | stop_loss | 48 | 4L/4S/3N of 11 | crisis |
| 152 | 2024-05-15 | 2024-05-17 | PIKK | short | 833.48 | 868.22 | 99 | -3,448 | -4.2% | 2d | stop_loss | 52 | 1L/3S/7N of 11 | uptrend |
| 153 | 2024-05-20 | 2024-05-30 | PIKK | short | 845.38 | 886.42 | 42 | -1,727 | -4.9% | 8d | stop_loss | 36 | 4L/2S/5N of 11 | range |
| 154 | 2024-06-04 | 2024-06-20 | PIKK | short | 842.78 | 897.28 | 31 | -1,692 | -6.5% | 11d | stop_loss | 42 | 2L/2S/7N of 11 | uptrend |
| 155 | 2024-07-24 | 2025-12-30 | PIKK | short | 846.18 | 477.80 | 32 | +11,787 | +43.5% | 432d | end_of_data | 34 | 2L/6S/3N of 11 | range |
| 156 | 2024-05-30 | 2024-06-05 | SVCB | short | 17.40 | 18.52 | 3186 | -3,574 | -6.5% | 4d | stop_loss | 46 | 4L/6S/1N of 11 | range |
| 157 | 2024-12-26 | 2025-01-15 | SVCB | long | 13.71 | 15.19 | 1065 | +1,580 | +10.8% | 11d | take_profit | 41 | 7L/2S/2N of 11 | crisis |
| 158 | 2025-04-09 | 2025-12-30 | SVCB | short | 16.22 | 12.61 | 1024 | +3,695 | +22.2% | 242d | end_of_data | 52 | 4L/2S/5N of 11 | crisis |
| 159 | 2022-08-01 | 2022-08-10 | VKCO | long | 391.02 | 448.96 | 107 | +6,195 | +14.8% | 7d | take_profit | 51 | 4L/3S/4N of 11 | range |
| 160 | 2022-10-05 | 2022-11-01 | VKCO | short | 389.98 | 464.71 | 47 | -3,514 | -19.2% | 19d | stop_loss | 57 | 6L/3S/2N of 11 | range |
| 161 | 2022-12-27 | 2023-01-16 | VKCO | short | 453.18 | 488.23 | 50 | -1,755 | -7.8% | 13d | stop_loss | 51 | 2L/3S/6N of 11 | crisis |
| 162 | 2023-04-07 | 2023-04-11 | VKCO | short | 461.18 | 482.14 | 167 | -3,508 | -4.6% | 2d | stop_loss | 48 | 2L/5S/4N of 11 | range |
| 163 | 2023-04-25 | 2023-05-15 | VKCO | long | 478.62 | 508.72 | 103 | +3,095 | +6.3% | 12d | take_profit | 35 | 3L/2S/6N of 11 | range |
| 164 | 2023-10-23 | 2024-01-31 | VKCO | short | 619.58 | 691.35 | 24 | -1,724 | -11.6% | 70d | stop_loss | 50 | 6L/3S/2N of 11 | crisis |
| 165 | 2024-03-22 | 2024-05-20 | VKCO | short | 604.98 | 640.38 | 197 | -6,986 | -5.9% | 40d | stop_loss | 55 | 2L/6S/3N of 11 | downtrend |
| 166 | 2025-01-15 | 2025-02-04 | VKCO | long | 338.62 | 314.25 | 76 | -1,855 | -7.2% | 14d | stop_loss | 54 | 10L/0S/1N of 11 | crisis |
| 167 | 2025-03-24 | 2025-07-10 | VKCO | short | 284.48 | 309.71 | 103 | -2,602 | -8.9% | 99d | stop_loss | 64 | 4L/6S/1N of 11 | crisis |
| 168 | 2025-09-16 | 2025-12-30 | VKCO | short | 310.68 | 302.30 | 221 | +1,845 | +2.7% | 95d | end_of_data | 56 | 4L/4S/3N of 11 | uptrend |
| 169 | 2025-01-10 | 2025-02-14 | IVAT | long | 220.92 | 209.27 | 322 | -3,758 | -5.3% | 25d | stop_loss | 46 | 8L/0S/3N of 11 | range |
| 170 | 2025-02-21 | 2025-07-25 | IVAT | short | 203.78 | 215.50 | 297 | -3,487 | -5.8% | 129d | stop_loss | 52 | 3L/5S/3N of 11 | range |
| 171 | 2025-10-10 | 2025-10-31 | IVAT | short | 161.98 | 181.22 | 90 | -1,733 | -11.9% | 19d | stop_loss | 48 | 3L/6S/2N of 11 | crisis |
| 172 | 2025-11-07 | 2025-12-30 | IVAT | long | 166.97 | 167.35 | 176 | +64 | +0.2% | 49d | end_of_data | 57 | 3L/3S/5N of 11 | crisis |
| 173 | 2022-09-01 | 2022-09-20 | FLOT | long | 41.98 | 39.70 | 1657 | -3,785 | -5.4% | 13d | stop_loss | 54 | 8L/0S/3N of 11 | range |
| 174 | 2022-09-26 | 2022-10-13 | FLOT | short | 31.83 | 36.18 | 1206 | -5,250 | -13.7% | 13d | stop_loss | 62 | 3L/7S/1N of 11 | range |
| 175 | 2022-11-07 | 2022-12-16 | FLOT | long | 38.72 | 36.19 | 739 | -1,872 | -6.5% | 29d | stop_loss | 36 | 8L/1S/2N of 11 | range |
| 176 | 2022-12-29 | 2023-01-09 | FLOT | short | 37.52 | 39.93 | 1448 | -3,495 | -6.4% | 6d | stop_loss | 51 | 4L/2S/5N of 11 | range |
| 177 | 2024-03-15 | 2025-12-30 | FLOT | short | 135.41 | 76.19 | 515 | +30,494 | +43.7% | 523d | end_of_data | 46 | 4L/2S/5N of 11 | uptrend |
| 178 | 2022-06-14 | 2022-06-29 | TRNFP | long | 1302.52 | 1227.48 | 49 | -3,683 | -5.8% | 11d | stop_loss | 54 | 6L/2S/3N of 11 | range |
| 179 | 2022-07-19 | 2023-04-06 | TRNFP | short | 1122.98 | 1204.65 | 64 | -5,235 | -7.3% | 183d | stop_loss | 62 | 2L/7S/2N of 11 | range |
| 180 | 2023-07-28 | 2023-08-31 | TRNFP | short | 1231.98 | 1296.56 | 53 | -3,430 | -5.2% | 24d | stop_loss | 46 | 3L/5S/3N of 11 | uptrend |
| 181 | 2023-09-05 | 2023-09-08 | TRNFP | long | 1398.52 | 1346.98 | 141 | -7,286 | -3.7% | 3d | stop_loss | 63 | 8L/1S/2N of 11 | uptrend |
| 182 | 2023-12-11 | 2023-12-18 | TRNFP | short | 1362.98 | 1407.44 | 77 | -3,434 | -3.3% | 5d | stop_loss | 50 | 3L/6S/2N of 11 | uptrend |
| 183 | 2023-12-25 | 2024-01-16 | TRNFP | long | 1448.52 | 1507.56 | 103 | +6,066 | +4.1% | 14d | take_profit | 58 | 5L/2S/4N of 11 | range |
| 184 | 2024-06-20 | 2025-12-30 | TRNFP | short | 1540.48 | 1378.00 | 36 | +5,844 | +10.5% | 456d | end_of_data | 50 | 1L/6S/4N of 11 | uptrend |
| 185 | 2022-11-16 | 2023-02-01 | NLMK | long | 107.16 | 119.52 | 120 | +1,482 | +11.5% | 54d | take_profit | 38 | 5L/2S/4N of 11 | crisis |
| 186 | 2023-10-31 | 2023-11-06 | NLMK | short | 189.72 | 198.84 | 190 | -1,737 | -4.8% | 4d | stop_loss | 39 | 3L/5S/3N of 11 | uptrend |
| 187 | 2024-01-12 | 2024-02-20 | NLMK | long | 198.30 | 191.30 | 1000 | -7,019 | -3.5% | 27d | stop_loss | 64 | 8L/0S/3N of 11 | uptrend |
| 188 | 2024-06-04 | 2025-12-30 | NLMK | short | 191.50 | 106.72 | 100 | +8,477 | +44.3% | 467d | end_of_data | 55 | 5L/4S/2N of 11 | crisis |
| 189 | 2024-06-18 | 2025-12-30 | UGLD | short | 0.86 | 0.54 | 22654 | +7,266 | +37.1% | 449d | end_of_data | 44 | 4L/6S/1N of 11 | range |
| 190 | 2022-07-07 | 2022-07-14 | SNGS | long | 26.15 | 24.15 | 1800 | -3,595 | -7.6% | 5d | stop_loss | 49 | 4L/2S/5N of 11 | range |
| 191 | 2022-09-21 | 2023-03-27 | SNGS | short | 21.69 | 24.03 | 2200 | -5,142 | -10.8% | 129d | stop_loss | 64 | 4L/5S/2N of 11 | range |
| 192 | 2023-12-04 | 2024-04-01 | SNGS | short | 29.90 | 31.50 | 2100 | -3,356 | -5.3% | 81d | stop_loss | 48 | 2L/6S/3N of 11 | uptrend |
| 193 | 2024-04-02 | 2024-04-16 | SNGS | long | 30.90 | 32.98 | 6300 | +13,083 | +6.7% | 10d | take_profit | 68 | 7L/1S/3N of 11 | uptrend |
| 194 | 2024-05-31 | 2025-12-30 | SNGS | short | 28.57 | 21.71 | 700 | +4,797 | +24.0% | 469d | end_of_data | 55 | 5L/4S/2N of 11 | crisis |
| 195 | 2022-10-27 | 2022-11-02 | MAGN | long | 32.37 | 30.04 | 1624 | -3,789 | -7.2% | 4d | stop_loss | 48 | 10L/1S/0N of 11 | range |
| 196 | 2023-11-20 | 2023-12-27 | MAGN | short | 51.42 | 53.14 | 2055 | -3,546 | -3.4% | 27d | stop_loss | 50 | 2L/2S/7N of 11 | uptrend |
| 197 | 2024-01-03 | 2024-01-11 | MAGN | long | 52.78 | 55.27 | 3762 | +9,347 | +4.7% | 6d | take_profit | 65 | 7L/2S/2N of 11 | uptrend |
| 198 | 2024-05-07 | 2024-05-13 | MAGN | short | 54.67 | 56.81 | 1657 | -3,555 | -3.9% | 3d | stop_loss | 47 | 1L/6S/4N of 11 | uptrend |
| 199 | 2024-06-13 | 2025-12-30 | MAGN | short | 54.99 | 28.55 | 1042 | +27,548 | +48.1% | 461d | end_of_data | 51 | 4L/4S/3N of 11 | uptrend |
| 200 | 2022-09-08 | 2022-09-20 | RNFT | long | 98.42 | 89.03 | 400 | -3,760 | -9.6% | 8d | stop_loss | 50 | 8L/0S/3N of 11 | range |
| 201 | 2022-09-26 | 2022-10-14 | RNFT | short | 67.58 | 82.44 | 235 | -3,494 | -22.0% | 14d | stop_loss | 58 | 3L/6S/2N of 11 | range |
| 202 | 2022-11-14 | 2022-11-21 | RNFT | long | 79.52 | 74.28 | 356 | -1,868 | -6.6% | 5d | stop_loss | 36 | 0L/4S/7N of 11 | range |
| 203 | 2022-12-26 | 2023-01-09 | RNFT | long | 83.72 | 92.32 | 360 | +3,093 | +10.3% | 9d | take_profit | 54 | 7L/1S/3N of 11 | crisis |
| 204 | 2023-09-27 | 2024-03-18 | RNFT | short | 160.18 | 179.13 | 45 | -854 | -11.8% | 119d | stop_loss | 39 | 3L/4S/4N of 11 | crisis |
| 205 | 2024-06-05 | 2025-12-30 | RNFT | short | 200.78 | 97.10 | 35 | +3,628 | +51.6% | 462d | end_of_data | 34 | 3L/4S/4N of 11 | crisis |
| 206 | 2022-05-17 | 2022-05-23 | MGNT | long | 4829.50 | 4466.50 | 5 | -1,817 | -7.5% | 4d | stop_loss | 38 | 4L/2S/5N of 11 | range |
| 207 | 2022-06-03 | 2022-07-29 | MGNT | short | 4381.00 | 4800.50 | 8 | -3,360 | -9.6% | 39d | stop_loss | 54 | 3L/3S/5N of 11 | range |
| 208 | 2022-09-30 | 2022-10-21 | MGNT | short | 4721.00 | 5187.50 | 7 | -3,269 | -9.9% | 15d | stop_loss | 56 | 5L/3S/3N of 11 | range |
| 209 | 2022-10-25 | 2022-11-09 | MGNT | long | 5316.00 | 5018.50 | 12 | -3,576 | -5.6% | 10d | stop_loss | 50 | 8L/0S/3N of 11 | range |
| 210 | 2022-11-21 | 2023-06-28 | MGNT | short | 4855.00 | 5162.50 | 11 | -3,388 | -6.3% | 151d | stop_loss | 56 | 4L/3S/4N of 11 | uptrend |
| 211 | 2023-10-03 | 2023-10-10 | MGNT | short | 5460.00 | 5777.50 | 5 | -1,590 | -5.8% | 5d | stop_loss | 43 | 3L/4S/4N of 11 | uptrend |
| 212 | 2023-10-17 | 2023-10-25 | MGNT | long | 5765.50 | 6130.50 | 34 | +12,389 | +6.3% | 6d | take_profit | 67 | 7L/1S/3N of 11 | uptrend |
| 213 | 2024-06-03 | 2025-12-30 | MGNT | short | 6696.00 | 3012.00 | 3 | +11,051 | +55.0% | 468d | end_of_data | 58 | 3L/5S/3N of 11 | crisis |
| 214 | 2024-01-04 | 2024-03-01 | SiZ4 | short | 98073.98 | 99821.65 | 1 | -1,758 | -1.8% | 40d | stop_loss | 36 | 1L/5S/5N of 11 | range |
| 215 | 2024-03-21 | 2024-05-21 | SiZ4 | long | 97588.02 | 96028.67 | 2 | -3,138 | -1.6% | 42d | stop_loss | 72 | 5L/2S/4N of 11 | uptrend |
| 216 | 2024-09-16 | 2024-10-03 | SiZ4 | long | 91978.02 | 94684.07 | 2 | +5,393 | +2.9% | 13d | take_profit | 47 | 8L/1S/2N of 11 | downtrend |
| 217 | 2023-11-27 | 2023-11-29 | SiH5 | short | 97426.98 | 100635.48 | 1 | -3,219 | -3.3% | 2d | stop_loss | 49 | 4L/1S/6N of 11 | range |
| 218 | 2024-02-08 | 2024-04-02 | SiH5 | short | 99299.98 | 101052.12 | 1 | -1,762 | -1.8% | 36d | stop_loss | 32 | 2L/3S/6N of 11 | range |
| 219 | 2024-04-25 | 2024-11-14 | SiH5 | short | 98227.98 | 99708.00 | 2 | -2,980 | -1.5% | 143d | stop_loss | 48 | 3L/5S/3N of 11 | downtrend |
| 220 | 2025-02-04 | 2025-03-20 | SiH5 | short | 100421.98 | 84389.00 | 1 | +16,025 | +16.0% | 32d | end_of_data | 32 | 3L/4S/4N of 11 | range |
| 221 | 2024-04-26 | 2024-04-27 | SiM5 | short | 100314.98 | 101311.89 | 1 | -1,007 | -1.0% | 1d | stop_loss | 48 | 3L/7S/1N of 11 | range |
| 222 | 2024-10-01 | 2024-10-07 | SiM5 | long | 94698.02 | 96588.74 | 1 | +1,881 | +2.0% | 4d | take_profit | 38 | 7L/0S/4N of 11 | range |
| 223 | 2025-02-10 | 2025-06-19 | SiM5 | short | 101969.98 | 78473.00 | 1 | +23,489 | +23.0% | 90d | end_of_data | 44 | 3L/5S/3N of 11 | uptrend |
| 224 | 2024-04-30 | 2024-08-14 | SiU5 | short | 104466.98 | 105679.73 | 1 | -1,223 | -1.2% | 65d | stop_loss | 34 | 3L/5S/3N of 11 | range |
| 225 | 2024-10-07 | 2024-10-11 | SiU5 | long | 98698.02 | 97205.56 | 2 | -3,004 | -1.5% | 4d | stop_loss | 47 | 8L/0S/3N of 11 | downtrend |
| 226 | 2025-02-12 | 2025-09-18 | SiU5 | short | 103899.98 | 83169.00 | 1 | +20,723 | +19.9% | 153d | end_of_data | 50 | 1L/6S/4N of 11 | uptrend |
| 227 | 2024-05-20 | 2024-11-07 | SiZ5 | short | 105714.98 | 107017.83 | 1 | -1,314 | -1.2% | 115d | stop_loss | 35 | 2L/5S/4N of 11 | range |
| 228 | 2025-02-14 | 2025-12-18 | SiZ5 | short | 106899.98 | 80030.00 | 1 | +26,862 | +25.1% | 216d | end_of_data | 42 | 4L/5S/2N of 11 | uptrend |
| 229 | 2024-06-05 | 2024-06-19 | RIZ4 | short | 111809.98 | 115078.01 | 1 | -3,280 | -2.9% | 9d | stop_loss | 53 | 5L/4S/2N of 11 | range |
| 230 | 2024-06-26 | 2024-07-04 | RIZ4 | long | 116850.02 | 113594.11 | 1 | -3,267 | -2.8% | 6d | stop_loss | 60 | 7L/2S/2N of 11 | range |
| 231 | 2024-07-09 | 2024-07-24 | RIZ4 | short | 110139.98 | 114160.49 | 1 | -4,032 | -3.7% | 11d | stop_loss | 46 | 4L/4S/3N of 11 | range |
| 232 | 2024-07-17 | 2024-07-24 | RIH5 | short | 109749.98 | 113705.66 | 1 | -3,967 | -3.6% | 4d | stop_loss | 34 | 5L/3S/3N of 11 | range |
| 233 | 2024-08-02 | 2025-02-17 | RIH5 | short | 110339.98 | 114161.18 | 1 | -3,833 | -3.5% | 134d | stop_loss | 33 | 3L/4S/4N of 11 | range |

### Detailed Trade Explanations (first 10):

#### Trade #1: GAZP LONG
- **Entry:** 2022-05-30 at 300.82
- **Exit:** 2022-06-30 at 278.79 (stop_loss)
- **P&L:** -1,764.63 RUB (-7.33%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=262.58 > EMA50=261.59
  - Indicators: 6L/1S/4N of 11
  - Scoring: 44/100 -> weight 0.25
  - Regime: range
  - Composite: 53.1
- **WHY EXITED:** SL hit at 278.79 (set at 278.81)

#### Trade #2: GAZP SHORT
- **Entry:** 2022-07-04 at 186.23
- **Exit:** 2022-08-31 at 220.19 (stop_loss)
- **P&L:** -5,097.30 RUB (-18.25%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=270.98 < EMA50=275.05
  - Indicators: 3L/6S/2N of 11
  - Scoring: 64/100 -> weight 0.75
  - Regime: range
  - Composite: 55.9
- **WHY EXITED:** SL hit at 220.19

#### Trade #3: GAZP LONG
- **Entry:** 2022-09-06 at 246.02
- **Exit:** 2022-09-20 at 230.72 (stop_loss)
- **P&L:** -3,677.54 RUB (-6.23%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=211.49 > EMA50=211.45
  - Indicators: 6L/2S/3N of 11
  - Scoring: 49/100 -> weight 0.50
  - Regime: range
  - Composite: 53.8
- **WHY EXITED:** SL hit at 230.72 (set at 230.74)

#### Trade #4: GAZP SHORT
- **Entry:** 2022-10-07 at 195.13
- **Exit:** 2025-12-30 at 125.36 (end_of_data)
- **P&L:** +12,556.34 RUB (+35.75%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=217.66 < EMA50=218.45
  - Indicators: 0L/8S/3N of 11
  - Scoring: 61/100 -> weight 0.75
  - Regime: range
  - Composite: 65.6
- **WHY EXITED:** End of backtest period

#### Trade #5: ROSN LONG
- **Entry:** 2022-09-02 at 385.20
- **Exit:** 2022-09-06 at 369.50 (stop_loss)
- **P&L:** -3,776.87 RUB (-4.09%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=356.76 > EMA50=356.42
  - Indicators: 7L/2S/2N of 11
  - Scoring: 50/100 -> weight 0.50
  - Regime: range
  - Composite: 56.7
- **WHY EXITED:** SL hit at 369.50 (set at 369.60)

#### Trade #6: ROSN SHORT
- **Entry:** 2022-09-21 at 312.45
- **Exit:** 2022-10-27 at 345.25 (stop_loss)
- **P&L:** -5,220.69 RUB (-10.51%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=357.98 < EMA50=358.89
  - Indicators: 4L/4S/3N of 11
  - Scoring: 64/100 -> weight 0.75
  - Regime: range
  - Composite: 50.7
- **WHY EXITED:** SL hit at 345.25

#### Trade #7: ROSN LONG
- **Entry:** 2022-11-08 at 352.05
- **Exit:** 2022-11-15 at 332.45 (stop_loss)
- **P&L:** -3,730.32 RUB (-5.58%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=327.51 > EMA50=326.08
  - Indicators: 7L/1S/3N of 11
  - Scoring: 48/100 -> weight 0.50
  - Regime: range
  - Composite: 57.0
- **WHY EXITED:** SL hit at 332.45 (set at 332.55)

#### Trade #8: ROSN SHORT
- **Entry:** 2023-12-14 at 535.60
- **Exit:** 2023-12-15 at 561.10 (stop_loss)
- **P&L:** -3,475.63 RUB (-4.77%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=566.86 < EMA50=567.73
  - Indicators: 3L/7S/1N of 11
  - Scoring: 48/100 -> weight 0.50
  - Regime: uptrend
  - Composite: 62.5
- **WHY EXITED:** SL hit at 561.10

#### Trade #9: ROSN LONG
- **Entry:** 2023-12-20 at 578.70
- **Exit:** 2024-02-22 at 559.05 (stop_loss)
- **P&L:** -3,704.71 RUB (-3.41%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=568.20 > EMA50=568.14
  - Indicators: 5L/2S/4N of 11
  - Scoring: 52/100 -> weight 0.50
  - Regime: range
  - Composite: 48.4
- **WHY EXITED:** SL hit at 559.05 (set at 559.15)

#### Trade #10: ROSN SHORT
- **Entry:** 2024-02-26 at 575.45
- **Exit:** 2024-05-14 at 593.45 (stop_loss)
- **P&L:** -1,715.64 RUB (-3.14%)
- **WHY ENTERED:**
  - EMA crossover: EMA20=580.02 < EMA50=580.12
  - Indicators: 6L/3S/2N of 11
  - Scoring: 34/100 -> weight 0.25
  - Regime: range
  - Composite: 57.1
- **WHY EXITED:** SL hit at 593.45


## 4. MiMo Analysis — 10 Key Dates

| Date | Event | Banks | Oil | Metals | Tech | Overall | Reasoning |
|------|-------|-------|-----|--------|------|---------|-----------|
| 2022-02-24 | Start of military operation in Ukraine,  | -0.9 | -0.5 | -0.6 | -0.7 | -0.7 | The military operation and sanctions have triggered widespre |
| 2022-03-24 | MOEX reopened after 1 month closure, sho | -0.7 | 0.5 | 0.3 | -0.8 | 0.1 | Reopening with short selling ban may provide temporary stabi |
| 2022-09-21 | Partial mobilization announced in Russia | -0.7 | -0.2 | -0.3 | -0.9 | -0.5 | Partial mobilization escalates geopolitical tensions and eco |
| 2023-02-01 | Market recovering, CBR rate 7.5%, oil st | 0.7 | 0.6 | 0.4 | 0.2 | 0.5 | Market recovery and stable oil prices create a positive envi |
| 2023-08-15 | CBR raised rate from 8.5% to 12% emergen | 0.3 | -0.2 | -0.4 | -0.6 | -0.4 | The emergency rate hike raises borrowing costs and signals e |
| 2023-12-15 | CBR raised rate to 16% | 0.8 | -0.1 | -0.5 | -0.7 | -0.3 | The CBR's rate hike to 16% is likely to boost bank margins b |
| 2024-06-14 | US sanctions on MOEX (NCC clearing cente | -0.8 | -0.5 | -0.6 | -0.7 | -0.6 | Sanctions on MOEX's NCC clearing center will disrupt market  |
| 2024-10-25 | CBR raised rate to 21% | 0.3 | -0.1 | -0.4 | -0.6 | -0.3 | The CBR's aggressive rate hike to 21% is expected to dampen  |
| 2025-02-14 | CBR kept rate at 21% | 0.2 | 0.0 | -0.3 | -0.5 | -0.4 | The CBR keeping the rate at 21% tightens monetary policy, in |
| 2025-06-20 | Peace negotiations news, market rally | 0.8 | 0.7 | 0.6 | 0.9 | 0.7 | Peace negotiations reduce geopolitical risks and sanctions,  |

## 5. Monthly Detail — 2024

### Jan 2024: +16,363 RUB (9 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-01-11 | CLOSE | MAGN | long | 55.27 | +9,347 | take_profit |
| 2024-01-15 | CLOSE | OZON | long | 3015.60 | +6,102 | take_profit |
| 2024-01-16 | CLOSE | TRNFP | long | 1507.56 | +6,066 | take_profit |
| 2024-01-31 | CLOSE | LKOH | short | 7064.50 | -3,427 | stop_loss |
| 2024-01-31 | CLOSE | VKCO | short | 691.35 | -1,724 | stop_loss |

### Feb 2024: -15,137 RUB (9 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-02-01 | CLOSE | SNGSP | short | 57.30 | -1,677 | stop_loss |
| 2024-02-08 | CLOSE | PIKK | short | 792.31 | -1,708 | stop_loss |
| 2024-02-09 | CLOSE | AFKS | short | 18.17 | -3,517 | stop_loss |
| 2024-02-12 | CLOSE | SBER | long | 286.70 | +6,167 | take_profit |
| 2024-02-20 | CLOSE | NLMK | long | 191.30 | -7,019 | stop_loss |
| 2024-02-21 | CLOSE | LKOH | long | 6979.50 | -3,677 | stop_loss |
| 2024-02-22 | CLOSE | ROSN | long | 559.05 | -3,705 | stop_loss |

### Mar 2024: -2,611 RUB (5 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-03-01 | CLOSE | SiZ4 | short | 99821.65 | -1,758 | stop_loss |
| 2024-03-18 | CLOSE | RNFT | short | 179.13 | -854 | stop_loss |

### Apr 2024: -4,271 RUB (9 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-04-01 | CLOSE | SNGS | short | 31.50 | -3,356 | stop_loss |
| 2024-04-02 | CLOSE | SiH5 | short | 101052.12 | -1,762 | stop_loss |
| 2024-04-03 | CLOSE | PLZL | short | 1308.00 | -3,524 | stop_loss |
| 2024-04-12 | CLOSE | GMKN | short | 169.00 | -4,204 | stop_loss |
| 2024-04-15 | CLOSE | RUAL | short | 43.01 | -3,500 | stop_loss |
| 2024-04-16 | CLOSE | SNGS | long | 32.98 | +13,083 | take_profit |
| 2024-04-27 | CLOSE | SiM5 | short | 101311.89 | -1,007 | stop_loss |

### May 2024: -25,331 RUB (11 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-05-13 | CLOSE | MAGN | short | 56.81 | -3,555 | stop_loss |
| 2024-05-14 | CLOSE | ROSN | short | 593.45 | -1,716 | stop_loss |
| 2024-05-17 | CLOSE | GMKN | short | 159.00 | -4,760 | stop_loss |
| 2024-05-17 | CLOSE | PIKK | short | 868.22 | -3,448 | stop_loss |
| 2024-05-20 | CLOSE | VKCO | short | 640.38 | -6,986 | stop_loss |
| 2024-05-21 | CLOSE | SiZ4 | long | 96028.67 | -3,138 | stop_loss |
| 2024-05-30 | CLOSE | PIKK | short | 886.42 | -1,727 | stop_loss |

### Jun 2024: -11,714 RUB (15 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-06-05 | CLOSE | SVCB | short | 18.52 | -3,574 | stop_loss |
| 2024-06-07 | CLOSE | LKOH | short | 7567.00 | -3,168 | stop_loss |
| 2024-06-19 | CLOSE | RIZ4 | short | 115078.01 | -3,280 | stop_loss |
| 2024-06-20 | CLOSE | PIKK | short | 897.28 | -1,692 | stop_loss |

### Jul 2024: -28,197 RUB (9 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-07-02 | CLOSE | ROSN | short | 579.25 | -6,896 | stop_loss |
| 2024-07-02 | CLOSE | SNGSP | short | 68.69 | -3,099 | stop_loss |
| 2024-07-04 | CLOSE | RIZ4 | long | 113594.11 | -3,267 | stop_loss |
| 2024-07-24 | CLOSE | RIZ4 | short | 114160.49 | -4,032 | stop_loss |
| 2024-07-24 | CLOSE | RIH5 | short | 113705.66 | -3,967 | stop_loss |
| 2024-07-26 | CLOSE | SBER | short | 298.78 | -6,936 | stop_loss |

### Aug 2024: -1,223 RUB (2 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-08-14 | CLOSE | SiU5 | short | 105679.73 | -1,223 | stop_loss |

### Sep 2024: -1,690 RUB (3 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-09-17 | CLOSE | PLZL | short | 1334.00 | -1,690 | stop_loss |

### Oct 2024: +635 RUB (6 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-10-03 | CLOSE | SiZ4 | long | 94684.07 | +5,393 | take_profit |
| 2024-10-07 | CLOSE | SiM5 | long | 96588.74 | +1,881 | take_profit |
| 2024-10-11 | CLOSE | SiU5 | long | 97205.56 | -3,004 | stop_loss |
| 2024-10-28 | CLOSE | LKOH | long | 6664.50 | -3,635 | stop_loss |

### Nov 2024: -1,480 RUB (3 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-11-07 | CLOSE | SiZ5 | short | 107017.83 | -1,314 | stop_loss |
| 2024-11-14 | CLOSE | SiH5 | short | 99708.00 | -2,980 | stop_loss |
| 2024-11-27 | CLOSE | SNGSP | long | 59.68 | +2,813 | take_profit |

### Dec 2024: -8,426 RUB (10 trades)
| Date | Action | Ticker | Side | Price | P&L | Reason |
|------|--------|--------|------|-------|-----|--------|
| 2024-12-03 | CLOSE | GMKN | long | 108.00 | -1,103 | stop_loss |
| 2024-12-20 | CLOSE | ROSN | long | 521.25 | +3,006 | take_profit |
| 2024-12-23 | CLOSE | YDEX | short | 3972.53 | -5,059 | stop_loss |
| 2024-12-26 | CLOSE | LKOH | short | 7033.50 | -3,324 | stop_loss |
| 2024-12-26 | CLOSE | GMKN | short | 113.00 | -1,946 | stop_loss |


## 6. Trade Statistics

- **Total trades:** 233
- **Long trades:** 87 (37%)
- **Short trades:** 146 (63%)
- **Win rate (all):** 25.8%
- **Win rate (long):** 37.9%
- **Win rate (short):** 18.5%
- **Average win:** +17,834 RUB
- **Average loss:** -4,867 RUB
- **Total P&L:** +227,977 RUB
- **Total commission:** +2,202 RUB
- **Profit factor:** 1.27
- **Avg hold time:** 74.1 days

### Exit Reasons:
- stop_loss: 173 (74%)
- take_profit: 32 (14%)
- end_of_data: 28 (12%)

### By Sector:
| Sector | Trades | Win Rate | Total P&L |
|--------|--------|----------|-----------|
| banks | 18 | 28% | +295,530 |
| realestate | 14 | 36% | +54,554 |
| transport | 5 | 20% | +16,092 |
| retail | 8 | 25% | +6,439 |
| chemicals | 3 | 33% | +257 |
| other | 80 | 25% | -2,935 |
| tech | 19 | 32% | -7,172 |
| oil_gas | 51 | 27% | -33,856 |
| metals | 35 | 17% | -100,931 |

### TOP-10 Best Trades:
| # | Ticker | Side | Entry->Exit | P&L | Ret% | Days | Why |
|---|--------|------|-------------|-----|------|------|-----|
| 1 | VTBR | short | 127->72 | +544,228 | +43.0% | 615d | 3L/3S/5N of 11 |
| 2 | SMLT | short | 3885->985 | +52,207 | +74.7% | 575d | 3L/3S/5N of 11 |
| 3 | FLOT | short | 135->76 | +30,494 | +43.7% | 523d | 4L/2S/5N of 11 |
| 4 | MAGN | short | 55->29 | +27,548 | +48.1% | 461d | 4L/4S/3N of 11 |
| 5 | SiZ5 | short | 106900->80030 | +26,862 | +25.1% | 216d | 4L/5S/2N of 11 |
| 6 | SiM5 | short | 101970->78473 | +23,489 | +23.0% | 90d | 3L/5S/3N of 11 |
| 7 | SiU5 | short | 103900->83169 | +20,723 | +19.9% | 153d | 1L/6S/4N of 11 |
| 8 | NVTK | short | 1594->1188 | +20,690 | +25.4% | 603d | 2L/6S/3N of 11 |
| 9 | TATN | short | 651->581 | +18,071 | +10.8% | 110d | 5L/6S/0N of 11 |
| 10 | SiH5 | short | 100422->84389 | +16,025 | +16.0% | 32d | 3L/4S/4N of 11 |

### TOP-10 Worst Trades:
| # | Ticker | Side | Entry->Exit | P&L | Ret% | Days | What went wrong |
|---|--------|------|-------------|-----|------|------|-----------------|
| 1 | VTBR | short | 124->132 | -76,851 | -6.2% | 9d | stop_loss, uptrend regime |
| 2 | VTBR | short | 85->92 | -71,011 | -8.3% | 122d | stop_loss, range regime |
| 3 | VTBR | long | 133->128 | -47,297 | -3.5% | 2d | stop_loss, range regime |
| 4 | VTBR | long | 103->100 | -35,141 | -3.4% | 1d | stop_loss, range regime |
| 5 | GMKN | long | 119->112 | -10,572 | -6.1% | 6d | stop_loss, uptrend regime |
| 6 | LKOH | short | 4026->4249 | -10,477 | -5.5% | 60d | stop_loss, downtrend regime |
| 7 | GMKN | short | 142->149 | -10,246 | -5.3% | 3d | stop_loss, downtrend regime |
| 8 | GMKN | short | 142->150 | -9,939 | -5.7% | 8d | stop_loss, downtrend regime |
| 9 | GMKN | long | 154->148 | -7,623 | -3.8% | 2d | stop_loss, uptrend regime |
| 10 | TRNFP | long | 1399->1347 | -7,286 | -3.7% | 3d | stop_loss, uptrend regime |

---
*753+ tests pass, all numbers from real MOEX ISS data*