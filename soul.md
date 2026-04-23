# SmartTrader Soul

This file is the trading soul of the bot. It tells both the bot and the AI advisor how to behave, what matters, and what must never be ignored.

## Mission

Trade with discipline first, profit second. Stay alive, stay consistent, and let skill compound over time.

## Trading Constitution

1. Respect price, volatility, spread, and risk before chasing a signal.
2. A trade must have a reason, a stop-loss, and a take-profit.
3. High-impact news can pause execution even when the chart looks good.
4. Learning is allowed, but reckless improvisation is not.
5. Practice mode is where the bot earns the right to become smarter.

## Execution Rules

- Follow the active strategy stack from the codebase.
- Prefer clean setups over forced entries.
- Track what happened after every meaningful event.
- Use the diary below to remember outcomes, mistakes, and lessons.

## Diary

<!-- AUTO-DIARY:START -->
- 2026-04-16 14:05 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 42

- 2026-04-16 14:05 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout, vwap_bounce, rsi_exhaustion
  - Risk per trade: 3.0% | Max positions: 6
  - Granularity: M5 | Poll every 10s

- 2026-04-10 19:18 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 42

- 2026-04-10 18:08 | Learning cycle: Learning adopted rsi_oversold 30.0 -> 25.0.
  - Trades reviewed: 42 | win rate 26.2% | total P&L $-158.78
  - Best candidate score: 55.76 from backtest_rsi
  - AI suggestion: With 26% win rate and profit factor 0.68, increase lookback to 15 for cleaner breakouts and stop_loss_mult to 2.0 to give winning trades more room - recent quick stop-outs suggest stops are too tight

- 2026-04-10 18:08 | AI strategy preferences: Only USD_JPY shows a clear strategy preference with unlabeled strategy significantly outperforming, while other instruments lack sufficient data or show poor performance across all tested strategies.
  - USD_JPY: unlabeled — Strong performance with 41% win rate, positive avg PnL (+4.54), and profit factor of 1.46 over 17 trades
  - EUR_JPY: None — Both strategies show poor performance with breakout having 0% win rate and unlabeled having only 11.8% win rate

- 2026-04-10 18:07 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout, vwap_bounce, rsi_exhaustion
  - Risk per trade: 3.0% | Max positions: 6
  - Granularity: M5 | Poll every 10s

- 2026-04-10 16:03 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 42

- 2026-04-10 14:00 | Trade closed: Trade #42 on AUD_USD closed with $+2.88.
  - Exit price: 0.7067 | Reason: take_profit
  - P&L: +0.00% of account

- 2026-04-10 13:55 | Trade opened: SELL AUD_USD via BREAKOUT at 0.70698
  - Units: 7467 | Stop loss: 0.70756 | Take profit: 0.70671
  - EMA: 9/15 | Regime: choppy | Confidence: normal
  - Bankroll: virtual | Effective equity: $836.35 | AI: veto

- 2026-04-10 13:55 | Trade closed: Trade #41 on USD_JPY closed with $-0.03.
  - Exit price: 159.303 | Reason: stop_loss
  - P&L: -0.00% of account

- 2026-04-10 13:50 | Trade opened: SELL USD_JPY via BREAKOUT at 159.25
  - Units: 65 | Stop loss: 159.299 | Take profit: 159.203
  - EMA: 9/15 | Regime: choppy | Confidence: normal
  - Bankroll: virtual | Effective equity: $836.38 | AI: veto

- 2026-04-10 13:45 | Learning cycle: Learning adopted slow_ema 50 -> 15.
  - Trades reviewed: 40 | win rate 25.0% | total P&L $-163.62
  - Best candidate score: 1.31 from backtest

- 2026-04-10 13:45 | Trade closed: Trade #40 on XAU_USD closed with $-9.89.
  - Exit price: 4752.54 | Reason: stop_loss
  - P&L: -0.01% of account

- 2026-04-10 13:30 | Trade opened: SELL XAU_USD via BREAKOUT at 4745.43
  - Units: 1 | Stop loss: 4752.303 | Take profit: 4732.195
  - EMA: 9/50 | Regime: choppy | Confidence: normal
  - Bankroll: virtual | Effective equity: $846.27 | AI: veto

- 2026-04-10 13:08 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout
  - Risk per trade: 3.0% | Max positions: 4
  - Granularity: M5 | Poll every 10s

- 2026-04-10 12:44 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 39

- 2026-04-10 12:01 | Trade closed: Trade #38 on EUR_JPY closed with $-18.37.
  - Exit price: 184.13 | Reason: stop_loss
  - P&L: -0.02% of account

- 2026-04-10 12:01 | Trade closed: Trade #39 on USD_JPY closed with $+21.29.
  - Exit price: 159.468 | Reason: signal
  - P&L: +0.02% of account

- 2026-04-10 12:01 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout
  - Risk per trade: 3.0% | Max positions: 4
  - Granularity: M5 | Poll every 10s

- 2026-04-02 16:50 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 2
  - Recent closed trades (30d): 37

- 2026-04-02 15:35 | Trade opened: SELL USD_JPY via BREAKOUT at 159.519
  - Units: 48065 | Stop loss: 159.561 | Take profit: 159.468
  - EMA: 9/50 | Regime: choppy | Confidence: normal

- 2026-04-02 15:35 | Trade opened: SELL EUR_JPY via BREAKOUT at 184.066
  - Units: 32738 | Stop loss: 184.13 | Take profit: 183.993
  - EMA: 9/50 | Regime: choppy | Confidence: normal

- 2026-04-02 13:34 | Learning cycle: Learning adopted slow_ema 15 -> 50.
  - Trades reviewed: 37 | win rate 24.3% | total P&L $-173.72
  - Best candidate score: 1.11 from backtest
  - AI suggestion: 24% win rate suggests stops too tight and signals too aggressive. Widen slow EMA to 21 for trend stability, increase lookback to 20 and volume mult to 1.2 for quality breakouts, raise stop mult to 2.0 for breathing room

- 2026-04-02 13:20 | Trade closed: Trade #37 on USD_JPY closed with $-13.41.
  - Exit price: 159.585 | Reason: stop_loss
  - P&L: -0.01% of account

- 2026-04-02 12:55 | Trade opened: BUY USD_JPY via BREAKOUT at 159.648
  - Units: 24281 | Stop loss: 159.586 | Take profit: 159.771
  - EMA: 9/15 | Regime: choppy | Confidence: normal

- 2026-04-02 12:55 | Trade closed: Trade #35 on USD_JPY closed with $-34.45.
  - Exit price: 159.657 | Reason: stop_loss
  - P&L: -0.03% of account

- 2026-04-02 12:25 | Trade closed: Trade #36 on EUR_JPY closed with $-16.01.
  - Exit price: 184.154 | Reason: signal
  - P&L: -0.02% of account

- 2026-04-02 12:05 | Trade opened: SELL EUR_JPY via BREAKOUT at 184.073
  - Units: 22557 | Stop loss: 184.154 | Take profit: 183.955
  - EMA: 9/15 | Regime: choppy | Confidence: normal

- 2026-04-02 12:05 | Trade opened: SELL USD_JPY via BREAKOUT at 159.564
  - Units: 42271 | Stop loss: 159.657 | Take profit: 159.444
  - EMA: 9/15 | Regime: trending | Confidence: normal

- 2026-04-02 11:43 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout
  - Risk per trade: 3.0% | Max positions: 4
  - Granularity: M5 | Poll every 10s

- 2026-04-02 11:43 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 34

- 2026-04-02 11:40 | Trade closed: Trade #34 on EUR_JPY closed with $-11.93.
  - Exit price: 184.181 | Reason: stop_loss
  - P&L: -0.01% of account

- 2026-04-02 11:10 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout
  - Risk per trade: 3.0% | Max positions: 4
  - Granularity: M5 | Poll every 10s

- 2026-04-02 11:02 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 1
  - Recent closed trades (30d): 33

- 2026-04-02 11:00 | Trade opened: SELL EUR_JPY via BREAKOUT at 184.111
  - Units: 19452 | Stop loss: 184.181 | Take profit: 183.95
  - EMA: 9/15 | Regime: choppy

- 2026-04-02 10:34 | Session start: Bot started in practice mode and is scanning 7 instruments.
  - Strategies: ema, breakout
  - Risk per trade: 3.0% | Max positions: 4
  - Granularity: M5 | Poll every 10s

- 2026-04-02 10:34 | Session stop: Bot session ended cleanly.
  - Open positions in journal: 0
  - Recent closed trades (30d): 33

- 2026-04-02 09:55 | Trade closed: Trade #33 on EUR_JPY closed with $-30.29.
  - Exit price: 184.043 | Reason: stop_loss
  - P&L: -0.03% of account

- 2026-04-02 09:55 | Trade closed: Trade #32 on EUR_JPY closed with $-19.83.
  - Exit price: 184.165 | Reason: signal
  - P&L: -0.02% of account

- 2026-04-02 09:55 | Trade closed: Trade #31 on EUR_JPY closed with $-22.05.
  - Exit price: 184.082 | Reason: signal
  - P&L: -0.02% of account
<!-- AUTO-DIARY:END -->
