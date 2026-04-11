"""
ai_advisor.py - Claude-powered trading advisor and trade reviewer.
"""

import json
import logging
from datetime import datetime

from config import config
from strategy_library import StrategyLibrary

logger = logging.getLogger("SmartTrader")


class AIAdvisor:
    """Claude-powered trading advisor."""

    def __init__(self, journal, memory=None):
        self.journal = journal
        self.memory = memory
        self.strategy_library = StrategyLibrary()
        self.enabled = config.has_claude
        self.client = None
        self.last_analysis = None
        self.last_analysis_time = None

        if self.enabled:
            try:
                from anthropic import Anthropic

                self.client = Anthropic(api_key=config.CLAUDE_API_KEY)
                logger.info("AI Advisor initialized with Claude API")
            except ImportError:
                logger.warning("anthropic package not installed - AI disabled")
                self.enabled = False
            except Exception as exc:
                logger.warning(f"Could not initialize Claude: {exc}")
                self.enabled = False

    def _instrument_list(self):
        return ", ".join(config.INSTRUMENTS)

    def _knowledge_context(self):
        sections = []
        if self.memory:
            sections.append(self.memory.get_prompt_context(max_chars=3500))
        else:
            sections.append("No trading memory files are loaded.")

        if self.strategy_library:
            sections.append(self.strategy_library.get_prompt_context(max_chars=2500))

        return "\n\n".join(section for section in sections if section)

    def _call_model(self, prompt, max_tokens=400):
        response = self.client.messages.create(
            model=config.AI_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _parse_json_response(self, raw):
        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)

    def analyze_performance(self, days=7):
        """Ask Claude to analyze recent trading performance."""
        if not self.enabled:
            return {
                "analysis": "AI Advisor not configured. Add CLAUDE_API_KEY to .env",
                "enabled": False,
            }

        stats = self.journal.get_trade_stats(days=days)
        recent_trades = self.journal.get_recent_trades(days=days)
        param_changes = self.journal.get_param_history(limit=10)

        trade_summary = []
        for trade in recent_trades[:20]:
            trade_summary.append({
                "instrument": trade["instrument"],
                "direction": trade["direction"],
                "entry": trade["entry_price"],
                "exit": trade["exit_price"],
                "pnl": trade["pnl"],
                "regime": trade["market_regime"],
                "exit_reason": trade["exit_reason"],
                "hold_mins": trade["hold_duration_mins"],
                "strategy_ema": f"{trade['fast_ema']}/{trade['slow_ema']}",
                "strategy_name": trade.get("strategy_name"),
                "strategy_confidence": trade.get("strategy_confidence"),
                "ai_action": trade.get("ai_action"),
                "ai_confidence": trade.get("ai_confidence"),
            })

        prompt = f"""You are an AI trading advisor analyzing a paper trading bot's performance.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as part of your context:

{self._knowledge_context()}

Here are the stats for the last {days} days:
- Total trades: {stats['total']}
- Wins: {stats['wins']}, Losses: {stats['losses']}
- Win rate: {stats['win_rate']:.1%}
- Total P&L: ${stats['total_pnl']:.2f}
- Profit factor: {stats['profit_factor']:.2f}
- Average hold time: {stats['avg_hold_mins']:.0f} minutes
- Largest win: ${stats['largest_win']:.2f}
- Largest loss: ${stats['largest_loss']:.2f}

Recent trades:
{json.dumps(trade_summary, indent=2)}

Parameter changes by learning engine:
{json.dumps(param_changes, indent=2)}

Please provide:
1. A brief performance summary (2-3 sentences)
2. What's working and what's not
3. One specific actionable suggestion to improve
4. A risk warning if you see anything concerning

Keep it concise and practical. The trader is a beginner with a small-account mindset."""

        try:
            analysis = self._call_model(prompt, max_tokens=500)
            self.last_analysis = analysis
            self.last_analysis_time = datetime.now().isoformat()
            logger.info("AI analysis complete")
            return {"analysis": analysis, "enabled": True, "timestamp": self.last_analysis_time}
        except Exception as exc:
            logger.error(f"AI analysis failed: {exc}")
            return {"analysis": f"Analysis failed: {exc}", "enabled": True}

    def get_market_briefing(self, price_data):
        """Ask Claude for a quick market briefing based on current price data."""
        if not self.enabled:
            return {"briefing": "AI not configured", "enabled": False}

        price_context = {}
        for instrument, frame in price_data.items():
            if frame is not None and len(frame) > 0:
                latest = frame.iloc[-1]
                high_20 = frame["high"].tail(20).max()
                low_20 = frame["low"].tail(20).min()
                price_context[instrument] = {
                    "current_price": latest["close"],
                    "20_bar_high": high_20,
                    "20_bar_low": low_20,
                    "range_pct": ((high_20 - low_20) / latest["close"]) * 100,
                }

        prompt = f"""You are a trading advisor. Give a 3-sentence market briefing for these instruments.
Focus on current positioning relative to the recent range, and what to watch for next.

Use the shared trading knowledge below as part of your context:

{self._knowledge_context()}

Current data:
{json.dumps(price_context, indent=2)}

Be concise and actionable. No disclaimers needed because this is paper trading."""

        try:
            briefing = self._call_model(prompt, max_tokens=200)
            return {"briefing": briefing, "enabled": True, "timestamp": datetime.now().isoformat()}
        except Exception as exc:
            return {"briefing": f"Briefing failed: {exc}", "enabled": True}

    def ask_question(self, question, trade_context=None):
        """Ask Claude a free-form question about trading."""
        if not self.enabled:
            return {"answer": "AI not configured. Add CLAUDE_API_KEY to .env", "enabled": False}

        stats = self.journal.get_trade_stats(days=14)
        prompt = f"""You are an AI trading advisor for a paper trading bot.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as part of your context:

{self._knowledge_context()}

Current stats (last 14 days):
- Trades: {stats['total']}, Win rate: {stats['win_rate']:.1%}, P&L: ${stats['total_pnl']:.2f}

The trader asks: {question}

Give a concise, helpful answer. The trader is a beginner."""

        try:
            return {"answer": self._call_model(prompt, max_tokens=300), "enabled": True}
        except Exception as exc:
            return {"answer": f"Error: {exc}", "enabled": True}

    def suggest_learning_adjustments(self, current_config, stats, recent_trades):
        """Ask Claude for conservative parameter suggestions based on recent trades."""
        if not self.enabled or not config.ai_learning_enabled:
            return None

        trade_summary = []
        for trade in recent_trades[:25]:
            trade_summary.append({
                "instrument": trade["instrument"],
                "direction": trade["direction"],
                "pnl": trade["pnl"],
                "exit_reason": trade["exit_reason"],
                "market_regime": trade["market_regime"],
                "hold_mins": trade["hold_duration_mins"],
                "strategy_name": trade.get("strategy_name"),
                "strategy_confidence": trade.get("strategy_confidence"),
                "ai_action": trade.get("ai_action"),
                "ai_confidence": trade.get("ai_confidence"),
            })

        prompt = f"""You are helping a paper trading bot tune itself conservatively.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as part of your context:

{self._knowledge_context()}

Current config:
{json.dumps(current_config, indent=2)}

Recent stats:
{json.dumps(stats, indent=2)}

Recent trades:
{json.dumps(trade_summary, indent=2)}

Suggest at most one small adjustment for each field below.
Return JSON only with this exact schema:
{{
  "fast_ema": integer or null,
  "slow_ema": integer or null,
  "breakout_lookback": integer or null,
  "breakout_volume_mult": number or null,
  "stop_loss_mult": number or null,
  "reason": "short explanation"
}}

Rules:
- Keep EMA values in a sensible intraday range.
- Keep fast_ema lower than slow_ema.
- Keep breakout_lookback in a sensible intraday range.
- Keep breakout_volume_mult between 0.9 and 1.5.
- Keep stop_loss_mult between 1.0 and 3.0.
- Be conservative and prefer null when there is not enough evidence."""

        try:
            suggestion = self._parse_json_response(self._call_model(prompt, max_tokens=300))
            suggestion["source"] = "ai"
            return suggestion
        except Exception as exc:
            logger.warning(f"AI learning suggestion failed: {exc}")
            return None

    def suggest_strategy_preferences(self, scorecard):
        """Ask Claude which strategy to prioritize per instrument based on scorecard data."""
        if not self.enabled or not config.ai_learning_enabled:
            return None

        prompt = f"""You are helping a paper trading bot choose the best strategy per instrument.
The bot trades: {self._instrument_list()}.
Available strategies: ema, breakout, vwap_bounce, rsi_exhaustion.

Here is the performance scorecard:
{json.dumps(scorecard, indent=2, default=str)}

Return JSON only with this schema:
{{
  "preferences": {{
    "INSTRUMENT_NAME": {{
      "preferred": "strategy_name",
      "reason": "short explanation"
    }}
  }},
  "summary": "one sentence overview"
}}

Rules:
- Only include instruments where there is enough data to make a recommendation.
- If no strategy has a clear edge, set preferred to null.
- Base your recommendation on win rate, profit factor, and number of trades."""

        try:
            result = self._parse_json_response(self._call_model(prompt, max_tokens=400))
            return result
        except Exception as exc:
            logger.warning(f"AI strategy preference suggestion failed: {exc}")
            return None

    def evaluate_trade_setup(self, instrument, signal_payload, market_snapshot, bankroll_context):
        """Review a live setup and return a structured entry decision."""
        if not self.enabled:
            return None

        recent_instrument_trades = self.journal.get_recent_trades(days=30, instrument=instrument)[:8]
        recent_summary = []
        for trade in recent_instrument_trades:
            recent_summary.append({
                "timestamp": trade.get("timestamp"),
                "direction": trade.get("direction"),
                "pnl": trade.get("pnl"),
                "exit_reason": trade.get("exit_reason"),
                "strategy_name": trade.get("strategy_name"),
                "ai_action": trade.get("ai_action"),
                "ai_confidence": trade.get("ai_confidence"),
            })

        prompt = f"""You are reviewing a paper-trading setup for a rules-based OANDA bot.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as context.

{self._knowledge_context()}

Instrument:
{instrument}

Candidate signal:
{json.dumps(signal_payload, indent=2)}

Market snapshot:
{json.dumps(market_snapshot, indent=2)}

Bankroll context:
{json.dumps(bankroll_context, indent=2)}

Recent trades on this instrument:
{json.dumps(recent_summary, indent=2)}

You are sizing for a small-account trader. Be conservative.
Return JSON only with this exact schema:
{{
  "allow_trade": true,
  "confidence": "low|normal|high",
  "size_mult": 1.0,
  "bankroll_fit": "poor|reduced|good",
  "risk_flags": ["short strings"],
  "reason": "one concise sentence"
}}

Rules:
- If the setup is weak or expensive relative to the bankroll, set allow_trade to false.
- size_mult must stay between {config.AI_MIN_SIZE_MULT} and {config.AI_MAX_SIZE_MULT}.
- Prefer reducing size over increasing size.
- Only suggest a size above 1.0 if the bankroll context is healthy and the setup quality is unusually strong.
- Do not bypass the rules-based signal. You are only filtering or resizing it."""

        return self._parse_json_response(self._call_model(prompt, max_tokens=260))

    def evaluate_open_trade(self, instrument, open_trade, market_snapshot, bankroll_context):
        """Review an already-open trade and decide whether to keep holding it."""
        if not self.enabled:
            return None

        recent_instrument_trades = self.journal.get_recent_trades(days=30, instrument=instrument)[:8]
        recent_summary = []
        for trade in recent_instrument_trades:
            recent_summary.append({
                "timestamp": trade.get("timestamp"),
                "direction": trade.get("direction"),
                "pnl": trade.get("pnl"),
                "exit_reason": trade.get("exit_reason"),
                "strategy_name": trade.get("strategy_name"),
                "ai_action": trade.get("ai_action"),
                "ai_confidence": trade.get("ai_confidence"),
            })

        prompt = f"""You are reviewing whether to keep or exit an already-open paper trade for a rules-based OANDA bot.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as context.

{self._knowledge_context()}

Instrument:
{instrument}

Open trade:
{json.dumps(open_trade, indent=2)}

Current market snapshot:
{json.dumps(market_snapshot, indent=2)}

Bankroll context:
{json.dumps(bankroll_context, indent=2)}

Recent trades on this instrument:
{json.dumps(recent_summary, indent=2)}

You are protecting a small-account trader. Be conservative.
Return JSON only with this exact schema:
{{
  "exit_now": false,
  "confidence": "low|normal|high",
  "risk_flags": ["short strings"],
  "reason": "one concise sentence"
}}

Rules:
- Only suggest exit_now=true if the open trade is clearly degrading, the market context has materially worsened, or bankroll protection matters.
- Do not suggest reversing or adding to the trade.
- If the trade is still valid and only experiencing normal noise, keep exit_now=false.
- Prefer patience over over-management."""

        return self._parse_json_response(self._call_model(prompt, max_tokens=220))

    def post_trade_review(self, trade):
        """Ask Claude to review a just-closed trade and extract a learning insight."""
        if not self.enabled or not config.ai_learning_enabled:
            return None

        trade_data = {
            "instrument": trade.get("instrument"),
            "direction": trade.get("direction"),
            "entry_price": trade.get("entry_price"),
            "exit_price": trade.get("exit_price"),
            "pnl": trade.get("pnl"),
            "exit_reason": trade.get("exit_reason"),
            "strategy_name": trade.get("strategy_name"),
            "strategy_confidence": trade.get("strategy_confidence"),
            "market_regime": trade.get("market_regime"),
            "hold_duration_mins": trade.get("hold_duration_mins"),
            "ai_action": trade.get("ai_action"),
            "ai_confidence": trade.get("ai_confidence"),
        }

        prompt = f"""You are reviewing a just-closed paper trade. Extract one learning insight.
The bot trades: {self._instrument_list()}.

{self._knowledge_context()}

Closed trade:
{json.dumps(trade_data, indent=2)}

In 1-2 sentences, what is the single most useful lesson from this trade?
Focus on: was the entry timing good? Was the strategy appropriate for the market condition?
Should the bot have sized differently? Was the exit optimal?

Return JSON only:
{{
  "lesson": "the insight in one sentence",
  "category": "entry_timing|strategy_selection|position_sizing|exit_management|market_read",
  "actionable": true
}}"""

        try:
            return self._parse_json_response(self._call_model(prompt, max_tokens=200))
        except Exception as exc:
            logger.warning(f"Post-trade review failed: {exc}")
            return None

    def explain_waiting(self, runtime_status, instrument=None):
        decision_factors = runtime_status.get("decision_factors", {}) or {}
        if instrument:
            decision_factors = (
                {instrument: decision_factors.get(instrument)}
                if decision_factors.get(instrument) else {}
            )

        if not decision_factors:
            message = (
                "The bot is online, but there is not enough decision data yet. "
                "Wait for the next scan or completed candle."
            )
            return {"answer": message, "enabled": self.enabled}

        if not self.enabled:
            return {"answer": self._plain_waiting_explanation(decision_factors), "enabled": False}

        prompt = f"""You are an AI trading assistant explaining why a paper trading bot is waiting.
The bot trades these instruments on OANDA: {self._instrument_list()}.
Use the shared trading knowledge below as part of your context:

{self._knowledge_context()}

Current runtime status:
{json.dumps(runtime_status, indent=2)}

Decision factors:
{json.dumps(decision_factors, indent=2)}

Explain in plain English:
1. Why the bot is not trading right now
2. Which factors are blocking or delaying trades
3. What would need to change for a trade to happen

Keep it concise and practical for a beginner."""

        try:
            return {"answer": self._call_model(prompt, max_tokens=350), "enabled": True}
        except Exception as exc:
            logger.warning(f"Waiting explanation failed: {exc}")
            return {"answer": self._plain_waiting_explanation(decision_factors), "enabled": self.enabled}

    def _plain_waiting_explanation(self, decision_factors):
        lines = []
        for instrument, factors in decision_factors.items():
            if not factors:
                continue
            reason = (
                factors.get("trade_readiness_summary")
                or factors.get("reason")
                or factors.get("final_reason")
                or "No reason available"
            )
            state = factors.get("state", "unknown").replace("_", " ")
            lines.append(f"{instrument}: {state}. {reason}")
        return " ".join(lines) if lines else "The bot is waiting for the next valid setup."

    def get_status(self):
        """For the dashboard."""
        return {
            "enabled": self.enabled,
            "mode": config.AI_MODE,
            "model": config.AI_MODEL,
            "last_analysis": self.last_analysis,
            "last_analysis_time": self.last_analysis_time,
        }
