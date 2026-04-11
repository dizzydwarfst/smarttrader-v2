# 🐟 SmartTrader Bot v2.0

Multi-strategy self-learning trading bot with visual dashboard and AI advisor.

## What's New in v2

- **Multi-Strategy**: EMA Crossover + Breakout running simultaneously
- **News Filter**: Pauses trading during Fed decisions, NFP, CPI releases
- **Visual Dashboard**: Dark-themed web UI with charts, tables, and controls
- **AI Advisor**: Claude analyzes your trades and answers questions (optional)
- **Verified Trades**: Every order confirmed with OANDA before logging
- **Active Practice Mode**: Optional faster paper-trading profile for more signal opportunities
- **Adaptive Learning**: Learning can re-run after enough new trades instead of waiting for one weekly window
- **Broader Watchlist**: Metals plus major FX pairs for more setup opportunities
- **Trading Memory**: `soul.md` and `skills.md` keep the bot's playbook, diary, and evolving skillbook
- **API Cooldown**: Batches price checks, reuses recent candles briefly, and backs off during temporary OANDA 5xx outages

## Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env with your OANDA API key and account ID

# 3. Run the bot
python bot.py

# The dashboard API auto-starts with the bot.
# Open http://localhost:8000 in your browser.
```

To run the bot without the dashboard:

```powershell
python bot.py --no-dashboard
```

To run only the dashboard:

```powershell
python api.py
```

## Practice Faster

If you want more paper-trading reps, set:

```env
PRACTICE_STYLE=active
```

That profile uses a faster intraday setup in practice mode:
- `M5` candles
- `10s` polling
- faster EMA settings
- shorter breakout lookback
- `3%` risk per trade
- up to `4` open positions
- relaxed spread limits via a practice multiplier

Default watchlist:
- `XAU_USD`
- `XAG_USD`
- `USD_JPY`
- `EUR_USD`
- `GBP_USD`
- `AUD_USD`
- `EUR_JPY`

It only applies in `TRADING_MODE=practice`.

If you want to test the new intraday basket derived from your strategy notes, a good starting point is:

```env
TRADING_MODE=practice
PRACTICE_STYLE=active
STRATEGIES=ema,breakout,vwap_bounce,rsi_exhaustion
BAR_GRANULARITY=M5
```

If you want practice trading to behave like a real small account instead of the full OANDA paper balance, use:

```env
USE_VIRTUAL_BANKROLL=true
VIRTUAL_BANKROLL=1000
VIRTUAL_RISK_PER_TRADE=0.005
```

If you want to tune how forgiving the spread filter is in paper trading, use:

```env
PRACTICE_SPREAD_LIMIT_MULT=2.5
```

The normal baseline remains:

```env
SPREAD_LIMIT_MULT=1.0
```

## How the Strategies Work

### EMA Crossover (trend following)
Catches momentum shifts. When the fast EMA crosses above the slow EMA → BUY.
Works best in trending markets. Gets "chopped" in sideways markets.

### Breakout (range trading)
Watches for price consolidation, then trades when price breaks out.
Works best after quiet periods. Catches big moves.

### VWAP Bounce (trend pullback)
Uses a 100 EMA bias plus a VWAP rejection wick and volume confirmation.
This is the candle-data adaptation of "ride the trend" and "VWAP bounce".

### RSI Exhaustion (mean reversion)
Fades overstretched moves after an RSI extreme and the first reversal candle.
This is the automated version of the "broken parabolic" and RSI exhaustion ideas.

### Together
They cover each other's weaknesses. When one struggles, the other thrives.
If both agree on a direction → "strong" signal with higher confidence.
If they conflict → bot skips and waits.

## Notes On Your Strategy List

The bot can now test the parts of your idea set that fit its current data feed:
- Trend bias plus VWAP rejection
- RSI/parabolic exhaustion reversals

The following ideas still need data the current OANDA candle feed does not provide:
- Level 2 / hidden bid logic
- Dark-pool footprints
- Options chain / gamma / max pain signals
- Stock-specific reactions like halts, earnings, and merger spreads

## Dashboard

By default, `python bot.py` also starts the dashboard API.

You can still run `python api.py` by itself and open `http://localhost:8000`.

You'll see:
- Account balance and P&L
- Cumulative P&L chart
- Open positions
- Trade history
- Bot's learning memory
- AI chat (requires Claude API key)

## News Filter

The bot now checks a live economic calendar feed first, then falls back to its built-in recurring-event schedule if that feed is unavailable. The blackout logic covers USD, JPY, EUR, GBP, and AUD events for the expanded FX watchlist.

By default it uses:

```env
NEWS_CALENDAR_SOURCE=tradingeconomics
TRADINGECONOMICS_API_KEY=guest:guest
```

## AI Advisor (Optional)

Add `CLAUDE_API_KEY=your-key` to `.env` to enable:
- Performance analysis in plain English
- Market briefings
- Free-form Q&A about your trades
- AI-assisted learning suggestions that are backtested before adoption

Set `AI_LEARNING_ENABLED=true` to let the learning engine ask Claude for conservative parameter ideas.

## AI Trade Review

The bot now supports bankroll-aware AI trade review on top of the rule-based strategies.

Recommended rollout:

```env
AI_MODE=shadow
```

That logs AI approve/reduce/veto decisions for new entries and AI hold/watch-exit decisions for open trades, but still lets the normal strategy execute.

When you want AI to control which paper trades reach OANDA practice, switch to:

```env
AI_MODE=gated
```

In `gated` mode:
- strategies still generate the setup
- AI can approve, veto, resize, or request an early exit
- hard rules like news, spread, and risk limits still override AI
- approved trades are sent to OANDA practice and recorded with AI metadata in the journal/dashboard

## Trading Memory

Two shared markdown files now live in the project root:
- `soul.md` stores the bot's trading constitution and event diary
- `skills.md` stores the bot's evolving skill snapshot

The bot updates them as trades open and close, and after learning cycles. The AI advisor also reads them as context when explaining, analyzing, and suggesting improvements.

Get a key at: https://console.anthropic.com

## File Structure

```
smarttrader-v2/
├── bot.py              # Main trading bot
├── api.py              # Dashboard API server
├── dashboard.html      # Web dashboard UI
├── strategy.py         # EMA + Breakout strategies
├── news_filter.py      # Economic calendar filter
├── ai_advisor.py       # Claude AI integration
├── risk_manager.py     # Position sizing & stop-losses
├── trade_journal.py    # SQLite trade logging
├── learning_engine.py  # Self-tuning parameters
├── instruments.py      # Metals + major FX instrument definitions
├── config.py           # Configuration loader
├── requirements.txt    # Python dependencies
├── .env.example        # Config template
└── README.md           # This file
```
