"""
bot.py — SmartTrader Bot v2.0 (OANDA)

What's new in v2:
- Multi-strategy: EMA Crossover + Breakout (runs both, picks best signal)
- News filter: pauses trading during high-impact economic events
- AI-ready: works with the dashboard and Claude API advisor
- Verified trades: confirms every order with OANDA before logging

Run: python bot.py
Dashboard: python api.py (in a separate terminal)
"""

import argparse
import os
import socket
import subprocess
import sys
import time
import signal as sig_module
import logging
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import schedule
from oandapyV20 import API
from oandapyV20.exceptions import V20Error
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments_ep
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades_ep
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions_ep
from oandapyV20.contrib.requests import (
    MarketOrderRequest,
    TakeProfitDetails,
    StopLossDetails,
)

from config import config
from instruments import get_instrument_info
from strategy import (
    EMAStrategy,
    BreakoutStrategy,
    VWAPBounceStrategy,
    RSIExhaustionStrategy,
    MomentumScalperStrategy,
    StrategyManager,
    Signal,
    MarketRegime,
)
from risk_manager import RiskManager
from trade_journal import TradeJournal
from learning_engine import LearningEngine
from news_filter import NewsFilter
from ai_advisor import AIAdvisor
from ai_decision import AIDecisionEngine
from trading_memory import TradingMemory
from serialization_utils import make_json_safe
from trading_profiles import (
    read_command,
    acknowledge_command,
    get_profile,
    PROFILES,
)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SmartTrader")


class SmartTraderBot:
    def __init__(self):
        config.validate()

        # OANDA client
        self.api = API(
            access_token=config.OANDA_API_KEY,
            environment=config.oanda_environment,
        )
        self.account_id = config.OANDA_ACCOUNT_ID

        # Core components
        self.journal = TradeJournal()
        self._apply_learned_parameter_overrides()
        self.risk_manager = RiskManager(self.journal)
        self.news_filter = NewsFilter()
        self.memory = TradingMemory(
            soul_name=config.SOUL_PATH,
            skills_name=config.SKILLS_PATH,
        )
        self.ai_advisor = AIAdvisor(self.journal, self.memory)
        self.ai_decision_engine = AIDecisionEngine(self.ai_advisor)
        self.learner = None  # Init after strategies

        # ─── Build strategy manager ──────────────
        strategies = []
        if "ema" in config.STRATEGIES:
            strategies.append(EMAStrategy(
                fast_period=config.FAST_EMA,
                slow_period=config.SLOW_EMA,
            ))
        if "breakout" in config.STRATEGIES:
            strategies.append(BreakoutStrategy(
                lookback=config.BREAKOUT_LOOKBACK,
                atr_threshold=config.BREAKOUT_ATR_THRESHOLD,
                volume_mult=config.BREAKOUT_VOLUME_MULT,
            ))
        if "vwap_bounce" in config.STRATEGIES:
            strategies.append(VWAPBounceStrategy(
                bias_ema_period=config.VWAP_BIAS_EMA,
                volume_lookback=config.VWAP_VOLUME_LOOKBACK,
                volume_mult=config.VWAP_VOLUME_MULT,
                wick_ratio=config.VWAP_WICK_RATIO,
            ))
        if "rsi_exhaustion" in config.STRATEGIES:
            strategies.append(RSIExhaustionStrategy(
                rsi_period=config.RSI_EXHAUSTION_PERIOD,
                overbought=config.RSI_EXHAUSTION_OVERBOUGHT,
                oversold=config.RSI_EXHAUSTION_OVERSOLD,
                streak_min=config.RSI_EXHAUSTION_STREAK_MIN,
            ))
        # Momentum scalper — auto-enabled in practice mode, or set SCALP_ENABLED=true
        scalp_enabled = (
            config.SCALP_ENABLED == "true"
            or (config.SCALP_ENABLED == "auto" and config.is_practice)
        )
        if scalp_enabled or "momentum_scalp" in config.STRATEGIES:
            strategies.append(MomentumScalperStrategy(
                fast_period=config.SCALP_FAST_EMA,
                slow_period=config.SCALP_SLOW_EMA,
                rsi_period=config.SCALP_RSI_PERIOD,
            ))
        self.strategy_manager = StrategyManager(strategies)

        # Learning engine (uses first EMA strategy if available)
        ema_strat = next((s for s in strategies if s.name == "ema"), None)
        breakout_strat = next((s for s in strategies if s.name == "breakout"), None)
        vwap_strat = next((s for s in strategies if s.name == "vwap_bounce"), None)
        rsi_strat = next((s for s in strategies if s.name == "rsi_exhaustion"), None)
        if ema_strat:
            self.learner = LearningEngine(
                self.journal,
                ema_strat,
                breakout_strategy=breakout_strat,
                vwap_strategy=vwap_strat,
                rsi_strategy=rsi_strat,
                ai_advisor=self.ai_advisor,
                memory=self.memory,
            )

        # State
        self.price_data = {}
        self.htf_data = {}
        self.htf_bias = {}
        self.instrument_info = get_instrument_info()
        self.running = False
        self.activity_log = []  # Ring buffer of recent log entries
        self.account_value = 0
        self.balance = 0
        self.unrealized_pnl = 0
        self.last_candle_time = {}
        self.decision_factors = {}
        self.dashboard_process = None
        self.price_cache = {}
        self.price_cache_timestamp = 0.0
        self.last_candle_fetch = {}
        self.last_htf_fetch = {}
        self.api_cooldown_until = 0.0
        self.api_cooldown_reason = ""
        self.pending_ai_exits = {}

    def _apply_learned_parameter_overrides(self):
        """Restore the latest learned parameters from the journal before strategies are built."""
        latest = self.journal.get_latest_param_values()
        if not latest:
            return

        applied = []

        parameter_map = {
            "fast_ema": ("FAST_EMA", int),
            "slow_ema": ("SLOW_EMA", int),
            "stop_loss_atr_mult": ("STOP_LOSS_ATR_MULT", float),
            "breakout_lookback": ("BREAKOUT_LOOKBACK", int),
            "breakout_volume_mult": ("BREAKOUT_VOLUME_MULT", float),
        }

        for param_name, (config_attr, caster) in parameter_map.items():
            entry = latest.get(param_name)
            if not entry:
                continue
            try:
                value = caster(entry["value"])
            except (TypeError, ValueError):
                continue
            setattr(config, config_attr, value)
            applied.append(f"{param_name}={value}")

        if config.is_practice and config.PRACTICE_STYLE == "active":
            config.PRACTICE_FAST_EMA = config.FAST_EMA
            config.PRACTICE_SLOW_EMA = config.SLOW_EMA
            config.PRACTICE_BREAKOUT_LOOKBACK = config.BREAKOUT_LOOKBACK
            config.PRACTICE_BREAKOUT_VOLUME_MULT = config.BREAKOUT_VOLUME_MULT

        if applied:
            logger.info(f"🧠 Restored learned parameters from journal: {', '.join(applied)}")

    # ─── Runtime command processing ────────────

    def _process_runtime_commands(self):
        """Check for and execute pending runtime commands from the API."""
        cmd = read_command()
        if not cmd:
            return

        command = cmd.get("command")
        payload = cmd.get("payload", {})
        logger.info(f"Processing runtime command: {command}")

        try:
            if command == "activate_profile":
                self._apply_profile(payload.get("profile", "routine"))
            elif command == "update_settings":
                self._apply_settings(payload)
                self._paused = False
            elif command == "pause":
                self._paused = True
                logger.info("Bot PAUSED by user command.")
            elif command == "resume":
                self._paused = False
                profile = getattr(self, '_active_profile', 'routine')
                logger.info(f"Bot RESUMED with {profile.upper()} profile.")
                self._log_activity(
                    f"Bot RESUMED — running {profile.upper()} | {config.BAR_GRANULARITY} candles | "
                    f"{config.POLL_INTERVAL}s scan | {config.RISK_PER_TRADE*100:.1f}% risk | "
                    f"max {config.MAX_POSITIONS} positions",
                    level="trade",
                )
            elif command == "close_all":
                self._close_all_positions()
            else:
                logger.warning(f"Unknown command: {command}")
        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}")
        finally:
            acknowledge_command()

    def _apply_profile(self, profile_name: str):
        """Apply a trading profile, updating config and rebuilding strategies."""
        profile = get_profile(profile_name)
        if not profile:
            logger.warning(f"Unknown profile: {profile_name}")
            return

        settings = profile["settings"]
        self._apply_settings(settings)
        self._active_profile = profile_name
        self._paused = False
        logger.info(f"Profile activated: {profile['label']} -- {profile['description']}")
        self.memory.append_diary_entry(
            "Profile switch",
            f"Switched to '{profile['label']}' profile.",
            details=[
                f"Poll: {config.POLL_INTERVAL}s | Candles: {config.BAR_GRANULARITY}",
                f"Risk: {config.RISK_PER_TRADE*100:.1f}% | Max pos: {config.MAX_POSITIONS}",
                f"Strategies: {', '.join(config.STRATEGIES)}",
            ],
        )

    def _apply_settings(self, settings: dict):
        """Apply individual setting overrides and rebuild strategies if needed."""
        needs_rebuild = False
        for key, value in settings.items():
            key_upper = key.upper()
            if hasattr(config, key_upper):
                old = getattr(config, key_upper)
                setattr(config, key_upper, value)
                if old != value:
                    logger.info(f"  Setting {key_upper}: {old} -> {value}")
                if key_upper in ("STRATEGIES", "FAST_EMA", "SLOW_EMA",
                                 "BREAKOUT_LOOKBACK", "BREAKOUT_ATR_THRESHOLD",
                                 "BREAKOUT_VOLUME_MULT", "VWAP_BIAS_EMA",
                                 "SCALP_FAST_EMA", "SCALP_SLOW_EMA",
                                 "RSI_EXHAUSTION_PERIOD", "RSI_EXHAUSTION_OVERBOUGHT",
                                 "RSI_EXHAUSTION_OVERSOLD"):
                    needs_rebuild = True

        if needs_rebuild:
            self._rebuild_strategies()
        # Reset candle cache so new granularity takes effect immediately
        self.last_candle_time.clear()
        self.price_data.clear()
        self.last_candle_fetch.clear()

    def _rebuild_strategies(self):
        """Rebuild strategy manager from current config values."""
        strategies = []
        if "ema" in config.STRATEGIES:
            strategies.append(EMAStrategy(
                fast_period=config.FAST_EMA,
                slow_period=config.SLOW_EMA,
            ))
        if "breakout" in config.STRATEGIES:
            strategies.append(BreakoutStrategy(
                lookback=config.BREAKOUT_LOOKBACK,
                atr_threshold=config.BREAKOUT_ATR_THRESHOLD,
                volume_mult=config.BREAKOUT_VOLUME_MULT,
            ))
        if "vwap_bounce" in config.STRATEGIES:
            strategies.append(VWAPBounceStrategy(
                bias_ema_period=config.VWAP_BIAS_EMA,
                volume_lookback=config.VWAP_VOLUME_LOOKBACK,
                volume_mult=config.VWAP_VOLUME_MULT,
                wick_ratio=config.VWAP_WICK_RATIO,
            ))
        if "rsi_exhaustion" in config.STRATEGIES:
            strategies.append(RSIExhaustionStrategy(
                rsi_period=config.RSI_EXHAUSTION_PERIOD,
                overbought=config.RSI_EXHAUSTION_OVERBOUGHT,
                oversold=config.RSI_EXHAUSTION_OVERSOLD,
                streak_min=config.RSI_EXHAUSTION_STREAK_MIN,
            ))
        scalp_enabled = (
            config.SCALP_ENABLED == "true"
            or (config.SCALP_ENABLED == "auto" and config.is_practice)
        )
        if scalp_enabled or "momentum_scalp" in config.STRATEGIES:
            strategies.append(MomentumScalperStrategy(
                fast_period=config.SCALP_FAST_EMA,
                slow_period=config.SCALP_SLOW_EMA,
                rsi_period=config.SCALP_RSI_PERIOD,
            ))
        self.strategy_manager = StrategyManager(strategies)

        # Reconnect learning engine
        ema_strat = next((s for s in strategies if s.name == "ema"), None)
        breakout_strat = next((s for s in strategies if s.name == "breakout"), None)
        vwap_strat = next((s for s in strategies if s.name == "vwap_bounce"), None)
        rsi_strat = next((s for s in strategies if s.name == "rsi_exhaustion"), None)
        if ema_strat:
            self.learner = LearningEngine(
                self.journal, ema_strat,
                breakout_strategy=breakout_strat,
                vwap_strategy=vwap_strat,
                rsi_strategy=rsi_strat,
                ai_advisor=self.ai_advisor,
                memory=self.memory,
            )
        logger.info(f"Strategies rebuilt: {[s.name for s in strategies]}")

    def _close_all_positions(self):
        """Close all open OANDA positions."""
        try:
            for instrument in config.INSTRUMENTS:
                req = positions_ep.PositionClose(self.account_id, instrument,
                                                  data={"longUnits": "ALL", "shortUnits": "ALL"})
                try:
                    self.api.request(req)
                    logger.info(f"Closed all positions for {instrument}")
                except V20Error:
                    pass  # No position open for this instrument
            logger.info("All positions closed.")
        except Exception as e:
            logger.error(f"Error closing positions: {e}")

    def start(self):
        self._paused = False
        self._active_profile = "routine"
        config.print_summary()

        if not config.is_practice:
            print("\n" + "!" * 60)
            print("  ⚠️  WARNING: LIVE TRADING MODE")
            print("!" * 60)
            response = input("  Type 'YES' to confirm: ")
            if response != "YES":
                config.TRADING_MODE = "practice"

        try:
            logger.info("Connecting to OANDA API...")
            self._update_account_value()
            logger.info("✅ Connected to OANDA!")
        except V20Error as e:
            logger.error(f"❌ Could not connect: {e}")
            sys.exit(1)

        self._load_historical_data()
        self._refresh_price_cache(force=True)
        self._repair_recent_closed_trade_pnl()
        self._ensure_dashboard_running()
        self.memory.refresh_skills_snapshot(
            stats=self.journal.get_trade_stats(days=30),
            recent_trades=self.journal.get_recent_trades(days=30),
            param_history=self.journal.get_param_history(limit=10),
        )
        self.memory.append_diary_entry(
            "Session start",
            f"Bot started in {config.TRADING_MODE} mode and is scanning {len(config.INSTRUMENTS)} instruments.",
            details=[
                f"Strategies: {', '.join(config.STRATEGIES)}",
                f"Risk per trade: {config.RISK_PER_TRADE*100:.1f}% | Max positions: {config.MAX_POSITIONS}",
                f"Granularity: {config.BAR_GRANULARITY} | Poll every {config.POLL_INTERVAL}s",
            ],
        )
        self._write_runtime_status(
            bot_online=True,
            current_activity="Connected to OANDA. Waiting for first market scan.",
            last_scan_at=None,
            news_filter=self.news_filter.get_status(),
            trade_readiness=self._build_trade_readiness({}),
        )

        if config.LEARNING_ENABLED and self.learner:
            logger.info(
                f"🧠 Adaptive learning enabled | min trades: {config.MIN_TRADES_FOR_LEARNING} | "
                f"cooldown: {config.LEARNING_COOLDOWN_MINUTES}m"
            )

        self.running = True
        logger.info(f"🚀 Bot running! Polling every {config.POLL_INTERVAL}s. Ctrl+C to stop.\n")
        self._main_loop()

    def _dashboard_host(self):
        if config.API_HOST in {"0.0.0.0", "::", "localhost"}:
            return "127.0.0.1"
        return config.API_HOST

    def _dashboard_is_available(self):
        try:
            with socket.create_connection((self._dashboard_host(), config.API_PORT), timeout=1):
                return True
        except OSError:
            return False

    def _wait_for_dashboard(self, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.dashboard_process and self.dashboard_process.poll() is not None:
                return False
            if self._dashboard_is_available():
                return True
            time.sleep(0.25)
        return False

    def _ensure_dashboard_running(self):
        if not config.AUTO_START_DASHBOARD:
            logger.info(f"Dashboard auto-start disabled. Start it manually at {config.dashboard_url}")
            return

        if self._dashboard_is_available():
            logger.info(f"Dashboard already running at {config.dashboard_url}")
            return

        api_script = Path(__file__).with_name("api.py")
        child_env = dict(os.environ)
        child_env["TRADING_MODE"] = config.TRADING_MODE

        try:
            self.dashboard_process = subprocess.Popen(
                [sys.executable, str(api_script)],
                cwd=str(api_script.parent),
                env=child_env,
            )
        except Exception as e:
            logger.warning(f"Could not auto-start dashboard: {e}")
            return

        if self._wait_for_dashboard():
            logger.info(f"Dashboard ready at {config.dashboard_url}")
        else:
            logger.warning(
                f"Dashboard process started but {config.dashboard_url} did not respond within 10 seconds."
            )

    def _stop_dashboard(self):
        if not self.dashboard_process or self.dashboard_process.poll() is not None:
            return

        self.dashboard_process.terminate()
        try:
            self.dashboard_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.dashboard_process.kill()
        finally:
            self.dashboard_process = None

    def _status_path(self):
        path = Path(config.BOT_STATUS_PATH)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        return path

    def _bankroll_mode(self):
        return "virtual" if config.use_virtual_bankroll else "broker_nav"

    def _pending_ai_exit_key(self, trade):
        if trade.get("oanda_trade_id"):
            return f"oanda:{trade['oanda_trade_id']}"
        return f"journal:{trade.get('id')}"

    def _remember_pending_ai_exit(self, trade, decision):
        if not hasattr(self, "pending_ai_exits"):
            self.pending_ai_exits = {}
        payload = {
            "exit_reason": "ai_exit",
            "notes": f"AI exit: {decision.get('reason', 'AI requested an early exit.')}",
            "decision": decision,
        }
        if trade.get("id") is not None:
            self.pending_ai_exits[f"journal:{trade['id']}"] = payload
        if trade.get("oanda_trade_id"):
            self.pending_ai_exits[f"oanda:{trade['oanda_trade_id']}"] = payload

    def _get_pending_ai_exit(self, trade):
        store = getattr(self, "pending_ai_exits", {}) or {}
        if trade.get("oanda_trade_id"):
            pending = store.get(f"oanda:{trade['oanda_trade_id']}")
            if pending:
                return pending
        if trade.get("id") is not None:
            return store.get(f"journal:{trade['id']}")
        return None

    def _clear_pending_ai_exit(self, trade):
        store = getattr(self, "pending_ai_exits", None)
        if not store:
            return
        if trade.get("oanda_trade_id"):
            store.pop(f"oanda:{trade['oanda_trade_id']}", None)
        if trade.get("id") is not None:
            store.pop(f"journal:{trade['id']}", None)

    def _effective_trading_equity(self):
        if not config.use_virtual_bankroll:
            return self.account_value or 0

        realized_pnl = 0
        if hasattr(self.journal, "get_total_closed_pnl"):
            realized_pnl = self.journal.get_total_closed_pnl()
        effective_equity = config.VIRTUAL_BANKROLL + realized_pnl + (self.unrealized_pnl or 0)
        return max(config.VIRTUAL_BANKROLL_FLOOR, effective_equity)

    def _build_bankroll_context(self):
        effective_equity = self._effective_trading_equity()
        realized_pnl = 0
        if hasattr(self.journal, "get_total_closed_pnl"):
            realized_pnl = self.journal.get_total_closed_pnl()
        start_equity = config.VIRTUAL_BANKROLL if config.use_virtual_bankroll else (self.account_value or 0)
        open_trades = self.journal.get_open_trades() if hasattr(self.journal, "get_open_trades") else []
        growth_pct = (
            ((effective_equity - start_equity) / start_equity) * 100
            if start_equity else 0
        )

        return {
            "mode": self._bankroll_mode(),
            "broker_nav": self.account_value,
            "effective_trading_equity": effective_equity,
            "starting_equity": start_equity,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "growth_from_start_pct": growth_pct,
            "daily_pnl": self.journal.get_daily_pnl() if hasattr(self.journal, "get_daily_pnl") else 0,
            "open_trades_count": len(open_trades),
            "risk_per_trade": config.effective_risk_per_trade,
            "max_positions": config.MAX_POSITIONS,
            "ai_mode": config.AI_MODE,
        }

    def _build_execution_status(self):
        """Summarize whether the bot has active or recent trades."""
        try:
            open_trades = self.journal.get_open_trades()
            recent_closed = self.journal.get_recent_trades(days=30)

            latest_open = max(
                open_trades,
                key=lambda trade: trade.get("timestamp") or "",
                default=None,
            )
            latest_closed = recent_closed[0] if recent_closed else None
            latest_trade = latest_open or latest_closed

            if latest_open:
                strategy = latest_open.get("strategy_name") or "unlabeled"
                summary = (
                    f"{len(open_trades)} open trade(s). Latest: "
                    f"{latest_open.get('direction')} {latest_open.get('instrument')} via {strategy}."
                )
            elif latest_closed:
                strategy = latest_closed.get("strategy_name") or "unlabeled"
                summary = (
                    "No open trades. Last recorded trade: "
                    f"{latest_closed.get('direction')} {latest_closed.get('instrument')} via {strategy} "
                    f"at {latest_closed.get('timestamp')}."
                )
            else:
                summary = "No trades recorded yet. The bot is scanning and waiting for a valid signal."

            latest_snapshot = None
            if latest_trade:
                latest_snapshot = {
                    "id": latest_trade.get("id"),
                    "timestamp": latest_trade.get("timestamp"),
                    "instrument": latest_trade.get("instrument"),
                    "direction": latest_trade.get("direction"),
                    "status": latest_trade.get("status", "closed" if latest_trade is latest_closed else "open"),
                    "strategy_name": latest_trade.get("strategy_name") or "unlabeled",
                    "ai_action": latest_trade.get("ai_action"),
                    "ai_confidence": latest_trade.get("ai_confidence"),
                    "entry_price": latest_trade.get("entry_price"),
                    "exit_price": latest_trade.get("exit_price"),
                    "pnl": latest_trade.get("pnl"),
                    "oanda_trade_id": latest_trade.get("oanda_trade_id"),
                }

            return {
                "open_trades_count": len(open_trades),
                "recent_closed_count_30d": len(recent_closed),
                "has_open_trade": bool(open_trades),
                "last_trade": latest_snapshot,
                "bankroll_mode": self._bankroll_mode(),
                "effective_trading_equity": self._effective_trading_equity(),
                "ai_mode": config.AI_MODE,
                "summary": summary,
            }
        except Exception as exc:
            logger.warning(f"Could not build execution status: {exc}")
            return {
                "open_trades_count": None,
                "recent_closed_count_30d": None,
                "has_open_trade": False,
                "last_trade": None,
                "bankroll_mode": self._bankroll_mode(),
                "effective_trading_equity": None,
                "ai_mode": config.AI_MODE,
                "summary": "Trade activity unavailable.",
            }

    def _log_activity(self, message, level="info"):
        """Add an entry to the activity log ring buffer."""
        self.activity_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level,
        })
        # Keep last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]

    def _write_runtime_status(self, **extra):
        status = {
            "timestamp": datetime.now().isoformat(),
            "bot_online": self.running,
            "trading_mode": config.TRADING_MODE,
            "account_nav": self.account_value,
            "balance": self.balance,
            "unrealized_pnl": self.unrealized_pnl,
            "bankroll_context": self._build_bankroll_context(),
            "poll_interval": config.POLL_INTERVAL,
            "execution_status": self._build_execution_status(),
            "activity_log": self.activity_log[-50:],
        }
        status.update(extra)

        path = self._status_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(
                make_json_safe(status),
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        temp_path.replace(path)

    def _api_cooldown_active(self):
        return time.time() < self.api_cooldown_until

    def _start_api_cooldown(self, reason):
        self.api_cooldown_reason = reason
        self.api_cooldown_until = time.time() + config.API_ERROR_COOLDOWN_SECONDS

    def _is_transient_api_error(self, error):
        message = str(error).lower()
        transient_markers = [
            "500",
            "502",
            "503",
            "504",
            "bad gateway",
            "gateway",
            "temporarily unavailable",
            "timed out",
            "maintenance",
            "problem on our side",
        ]
        return any(marker in message for marker in transient_markers)

    def _request_with_retry(self, request_factory, label, retries=2):
        last_error = None
        for attempt in range(retries + 1):
            try:
                return self.api.request(request_factory())
            except Exception as e:
                last_error = e
                transient = self._is_transient_api_error(e)
                if transient and attempt < retries:
                    delay = attempt + 1
                    logger.warning(f"{label} failed ({e}). Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                if transient:
                    self._start_api_cooldown(f"{label} failed: {e}")
                break
        if last_error:
            raise last_error
        return None

    def _refresh_price_cache(self, force=False):
        now = time.time()
        if not force and self.price_cache and (now - self.price_cache_timestamp) < config.PRICE_CACHE_TTL_SECONDS:
            return self.price_cache

        instruments = ",".join(config.INSTRUMENTS)
        try:
            response = self._request_with_retry(
                lambda: pricing.PricingInfo(self.account_id, params={"instruments": instruments}),
                "Price refresh",
            )
            prices = response.get("prices", []) if response else []
            refreshed = {}
            for item in prices:
                instrument = item.get("instrument")
                bids = item.get("bids") or []
                asks = item.get("asks") or []
                if not instrument or not bids or not asks:
                    continue
                bid = float(bids[0]["price"])
                ask = float(asks[0]["price"])
                refreshed[instrument] = {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}

            if refreshed:
                self.price_cache = refreshed
                self.price_cache_timestamp = now
        except Exception as e:
            logger.warning(f"Price refresh failed: {e}")

        return self.price_cache

    def _main_loop(self):
        while self.running:
            try:
                # Check for runtime commands (profile switch, settings change, etc.)
                self._process_runtime_commands()

                # If paused, just write status and sleep
                if getattr(self, '_paused', False):
                    self._write_runtime_status(
                        bot_online=True,
                        current_activity="PAUSED by user. Waiting for resume command.",
                        last_scan_at=datetime.now().isoformat(),
                        news_filter=self.news_filter.get_status(),
                        active_profile=getattr(self, '_active_profile', 'routine'),
                    )
                    time.sleep(2)
                    continue

                schedule.run_pending()
                if self._api_cooldown_active():
                    wait_seconds = max(1, int(round(self.api_cooldown_until - time.time())))
                    logger.warning(
                        f"OANDA cooldown active for {wait_seconds}s: {self.api_cooldown_reason or 'temporary upstream issue'}"
                    )
                    wait_reasons = {
                        instrument: self._summarize_wait_reason(snapshot)
                        for instrument, snapshot in self.decision_factors.items()
                    }
                    self._write_runtime_status(
                        bot_online=True,
                        current_activity=f"OANDA cooldown active. Retrying in {wait_seconds}s.",
                        last_scan_at=datetime.now().isoformat(),
                        news_filter=self.news_filter.get_status(),
                        decision_factors=self.decision_factors,
                        wait_reasons=wait_reasons,
                        trade_readiness=self._build_trade_readiness(self.decision_factors),
                    )
                    time.sleep(min(wait_seconds, config.POLL_INTERVAL))
                    continue
                scan_started = datetime.now().isoformat()
                logger.info("Checking markets...")
                self._log_activity("Scanning all instruments...")
                news_ok, news_reason = self.news_filter.can_trade()
                risk_ok, risk_reason = self.risk_manager.can_trade(self._effective_trading_equity())
                loop_factors = {}
                self._refresh_price_cache()
                self._write_runtime_status(
                    bot_online=True,
                    current_activity="Checking markets...",
                    last_scan_at=scan_started,
                    news_filter=self.news_filter.get_status(),
                )

                for instrument in config.INSTRUMENTS:
                    df = self._fetch_candles(instrument)
                    if df is None or len(df) < 30:
                        loop_factors[instrument] = self._annotate_trade_readiness({
                            "instrument": instrument,
                            "state": "no_data",
                            "reason": "Not enough candle data yet",
                            "news_ok": news_ok,
                            "news_reason": news_reason,
                            "risk_ok": risk_ok,
                            "risk_reason": risk_reason,
                        })
                        continue

                    self.price_data[instrument] = df

                    latest_time = str(df.iloc[-1]["date"])
                    spread_factor = self._get_spread_factor(instrument)
                    if latest_time == self.last_candle_time.get(instrument):
                        loop_factors[instrument] = self._annotate_trade_readiness({
                            "instrument": instrument,
                            "state": "waiting_new_candle",
                            "reason": f"Waiting for next completed {config.BAR_GRANULARITY} candle",
                            "latest_candle_time": latest_time,
                            "news_ok": news_ok,
                            "news_reason": news_reason,
                            "risk_ok": risk_ok,
                            "risk_reason": risk_reason,
                            "spread_ok": spread_factor["ok"],
                            "spread_reason": spread_factor["reason"],
                            "spread_pips": spread_factor.get("spread_pips"),
                            "spread_limit_pips": spread_factor.get("max_spread_pips"),
                            "quote": {
                                "bid": spread_factor.get("bid"),
                                "ask": spread_factor.get("ask"),
                                "mid": spread_factor.get("mid"),
                            },
                        })
                        continue
                    self.last_candle_time[instrument] = latest_time

                    # Get signal from strategy manager
                    result = self.strategy_manager.get_signal(df)
                    signal = result["signal"]
                    final_reason = result.get("reason", "No signal")
                    snapshot = {
                        "instrument": instrument,
                        "state": "evaluated",
                        "latest_candle_time": latest_time,
                        "final_signal": signal,
                        "final_reason": final_reason,
                        "confidence": result.get("confidence", "normal"),
                        "news_ok": news_ok,
                        "news_reason": news_reason,
                        "risk_ok": risk_ok,
                        "risk_reason": risk_reason,
                        "spread_ok": spread_factor["ok"],
                        "spread_reason": spread_factor["reason"],
                        "spread_pips": spread_factor.get("spread_pips"),
                        "spread_limit_pips": spread_factor.get("max_spread_pips"),
                        "quote": {
                            "bid": spread_factor.get("bid"),
                            "ask": spread_factor.get("ask"),
                            "mid": spread_factor.get("mid"),
                        },
                        "strategy_factors": self._build_strategy_factors(result),
                    }

                    # ─── Multi-timeframe bias ────────────────
                    htf_bias = self._get_htf_bias(instrument)
                    snapshot["htf_bias"] = htf_bias
                    if signal != Signal.HOLD and htf_bias != "neutral":
                        aligned = (
                            (signal == Signal.BUY and htf_bias == "bullish")
                            or (signal == Signal.SELL and htf_bias == "bearish")
                        )
                        if aligned and result.get("confidence") == "normal":
                            result["confidence"] = "strong"
                            result["reason"] += f" | HTF ({config.HTF_GRANULARITY}) confirms {htf_bias}"
                        elif not aligned:
                            result["reason"] += f" | HTF ({config.HTF_GRANULARITY}) is {htf_bias} (counter-trend)"

                    if signal == Signal.HOLD:
                        self._log_activity(f"{instrument}: No signal (HOLD)")
                    else:
                        confidence = result.get("confidence", "normal")
                        logger.info(
                            f"📊 {instrument} | {result['strategy'].upper()} | "
                            f"Signal: {signal} | Confidence: {confidence} | "
                            f"{result['reason']}"
                        )
                        self._log_activity(
                            f"{instrument}: {signal} via {result['strategy'].upper()} [{confidence}] — {result['reason']}",
                            level="signal",
                        )

                    if signal != Signal.HOLD:
                        self._write_runtime_status(
                            bot_online=True,
                            current_activity=f"{instrument}: {signal} via {result['strategy'].upper()}",
                            last_scan_at=scan_started,
                            last_signal={
                                "instrument": instrument,
                                "signal": signal,
                                "strategy": result["strategy"],
                                "reason": result["reason"],
                                "timestamp": datetime.now().isoformat(),
                            },
                            news_filter=self.news_filter.get_status(),
                        )

                    # Check exits
                    exit_review = self._check_oanda_trades(instrument, snapshot)
                    if exit_review.get("closed_by_ai"):
                        snapshot["state"] = "managing_position"
                        snapshot["reason"] = f"AI exit requested: {exit_review['ai_exit'].get('reason')}"
                        loop_factors[instrument] = self._annotate_trade_readiness(snapshot)
                        continue

                    # Execute if signal and news is clear
                    if signal in (Signal.BUY, Signal.SELL):
                        if not news_ok:
                            snapshot["state"] = "blocked"
                            snapshot["reason"] = news_reason
                            loop_factors[instrument] = self._annotate_trade_readiness(snapshot)
                            logger.info(f"  📰 Trade blocked: {news_reason}")
                            self._log_activity(f"{instrument}: BLOCKED — {news_reason}", level="blocked")
                            continue
                        if not risk_ok:
                            logger.info(f"  Blocked: {risk_reason}")
                            snapshot["state"] = "blocked"
                            snapshot["reason"] = risk_reason
                            loop_factors[instrument] = self._annotate_trade_readiness(snapshot)
                            self._log_activity(f"{instrument}: BLOCKED — {risk_reason}", level="blocked")
                            continue
                        if not spread_factor["ok"]:
                            logger.info(f"  Blocked: {spread_factor['reason']}")
                            snapshot["state"] = "blocked"
                            snapshot["reason"] = spread_factor["reason"]
                            loop_factors[instrument] = self._annotate_trade_readiness(snapshot)
                            self._log_activity(f"{instrument}: BLOCKED — {spread_factor['reason']}", level="blocked")
                            continue
                        ai_decision = self._review_entry_with_ai(instrument, result, snapshot)
                        snapshot["ai_decision"] = ai_decision
                        snapshot["ai_summary"] = ai_decision.get("reason")
                        result["ai_decision"] = ai_decision
                        result["trading_equity"] = ai_decision.get("effective_trading_equity")
                        if ai_decision.get("reviewed"):
                            logger.info(
                                f"  AI[{ai_decision.get('mode', 'off').upper()}] "
                                f"{ai_decision.get('action', 'pass').upper()} "
                                f"{instrument} | size x{ai_decision.get('size_mult', 1.0):.2f} | "
                                f"{ai_decision.get('reason')}"
                            )
                        if not ai_decision.get("should_execute", True):
                            snapshot["state"] = "blocked"
                            snapshot["reason"] = f"AI veto: {ai_decision.get('reason')}"
                            loop_factors[instrument] = self._annotate_trade_readiness(snapshot)
                            continue
                        execution = self._execute_signal(instrument, result)
                        if execution["submitted"]:
                            snapshot["state"] = "submitted"
                            self._log_activity(f"{instrument}: TRADE OPENED — {signal} | {execution['reason']}", level="trade")
                        else:
                            snapshot["state"] = "blocked"
                            self._log_activity(f"{instrument}: Trade rejected — {execution['reason']}", level="blocked")
                        snapshot["reason"] = execution["reason"]

                    if signal == Signal.HOLD:
                        snapshot["state"] = "waiting_signal"
                        snapshot["reason"] = final_reason

                    loop_factors[instrument] = self._annotate_trade_readiness(snapshot)

                # Periodic updates
                now = datetime.now()
                if now.minute == 0 and now.second < config.POLL_INTERVAL:
                    self._update_account_value()
                    if now.hour == 0:
                        self.risk_manager.reset_daily_limit()

                if config.LEARNING_ENABLED and self.learner and self.learner.should_run():
                    self._run_learning()

                self.decision_factors = loop_factors
                wait_reasons = {
                    instrument: self._summarize_wait_reason(snapshot)
                    for instrument, snapshot in self.decision_factors.items()
                }

                self._write_runtime_status(
                    bot_online=True,
                    current_activity=f"Watching markets. Next scan in {config.POLL_INTERVAL}s.",
                    last_scan_at=scan_started,
                    news_filter=self.news_filter.get_status(),
                    decision_factors=self.decision_factors,
                    wait_reasons=wait_reasons,
                    trade_readiness=self._build_trade_readiness(self.decision_factors),
                    active_profile=getattr(self, '_active_profile', 'routine'),
                    paused=getattr(self, '_paused', False),
                )

                time.sleep(config.POLL_INTERVAL)

            except KeyboardInterrupt:
                self.stop()
                break
            except V20Error as e:
                logger.error(f"OANDA API error: {e}")
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                time.sleep(10)

    # ─── Data ────────────────────────────────────

    def _fetch_candles(self, instrument):
        now = time.time()
        cached = self.price_data.get(instrument)
        if cached is not None:
            last_fetch = self.last_candle_fetch.get(instrument, 0.0)
            if (now - last_fetch) < config.CANDLE_REFRESH_MIN_SECONDS:
                return cached

        try:
            params = {
                "granularity": config.BAR_GRANULARITY,
                "count": config.HISTORY_COUNT,
                "price": "M",
            }
            response = self._request_with_retry(
                lambda: instruments_ep.InstrumentsCandles(instrument=instrument, params=params),
                f"Candle fetch for {instrument}",
            )
            candles = response.get("candles", [])
            if not candles:
                return cached
            rows = []
            for c in candles:
                if c["complete"]:
                    mid = c["mid"]
                    rows.append({
                        "date": c["time"],
                        "open": float(mid["o"]),
                        "high": float(mid["h"]),
                        "low": float(mid["l"]),
                        "close": float(mid["c"]),
                        "volume": int(c["volume"]),
                    })
            if rows:
                self.last_candle_fetch[instrument] = now
                return pd.DataFrame(rows)
            return cached
        except Exception as e:
            logger.error(f"Candle fetch failed for {instrument}: {e}")
            return cached

    def _fetch_htf_candles(self, instrument):
        """Fetch higher-timeframe candles for trend confirmation."""
        if not config.HTF_ENABLED:
            return None
        now = time.time()
        cached = self.htf_data.get(instrument)
        last_fetch = self.last_htf_fetch.get(instrument, 0.0)
        if cached is not None and (now - last_fetch) < 300:
            return cached
        try:
            params = {
                "granularity": config.HTF_GRANULARITY,
                "count": 100,
                "price": "M",
            }
            response = self._request_with_retry(
                lambda: instruments_ep.InstrumentsCandles(instrument=instrument, params=params),
                f"HTF candle fetch for {instrument}",
            )
            candles = response.get("candles", [])
            rows = []
            for c in candles:
                if c["complete"]:
                    mid = c["mid"]
                    rows.append({
                        "date": c["time"],
                        "open": float(mid["o"]),
                        "high": float(mid["h"]),
                        "low": float(mid["l"]),
                        "close": float(mid["c"]),
                        "volume": int(c["volume"]),
                    })
            if rows:
                self.last_htf_fetch[instrument] = now
                df = pd.DataFrame(rows)
                self.htf_data[instrument] = df
                return df
            return cached
        except Exception:
            return cached

    def _get_htf_bias(self, instrument):
        """Return 'bullish', 'bearish', or 'neutral' based on HTF EMA trend."""
        if not config.HTF_ENABLED:
            return "neutral"
        df = self._fetch_htf_candles(instrument)
        if df is None or len(df) < config.HTF_EMA_PERIOD + 2:
            return "neutral"
        from ta.trend import EMAIndicator as _EMA
        ema = _EMA(close=df["close"], window=config.HTF_EMA_PERIOD).ema_indicator()
        latest_close = df["close"].iloc[-1]
        latest_ema = ema.iloc[-1]
        if pd.isna(latest_ema):
            return "neutral"
        if latest_close > latest_ema * 1.001:
            return "bullish"
        elif latest_close < latest_ema * 0.999:
            return "bearish"
        return "neutral"

    def _update_account_value(self):
        try:
            response = self._request_with_retry(
                lambda: accounts.AccountSummary(self.account_id),
                "Account summary",
                retries=1,
            )
            account = response.get("account", {})
            self.account_value = float(account.get("NAV", 0))
            self.balance = float(account.get("balance", 0))
            self.unrealized_pnl = float(account.get("unrealizedPL", 0))
            logger.info(
                f"  💰 Balance: ${self.balance:,.2f} | NAV: ${self.account_value:,.2f} | "
                f"Unrealized: ${self.unrealized_pnl:+,.2f}"
            )
        except Exception as e:
            logger.warning(f"  Could not get account: {e}")
            if self.account_value == 0:
                self.account_value = 100000

    def _get_current_price(self, instrument):
        cache = self._refresh_price_cache()
        if instrument in cache:
            return cache[instrument]

        try:
            response = self._request_with_retry(
                lambda: pricing.PricingInfo(self.account_id, params={"instruments": instrument}),
                f"Price fetch for {instrument}",
                retries=1,
            )
            prices = response.get("prices", []) if response else []
            if prices:
                bid = float(prices[0]["bids"][0]["price"])
                ask = float(prices[0]["asks"][0]["price"])
                quote = {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}
                self.price_cache[instrument] = quote
                self.price_cache_timestamp = time.time()
                return quote
        except Exception as e:
            logger.error(f"Price fetch failed for {instrument}: {e}")
        return self.price_cache.get(instrument)

    def _get_spread_factor(self, instrument):
        quote = self._get_current_price(instrument)
        info = self.instrument_info.get(instrument, {})
        pip_size = info.get("pip_size", 1)
        max_spread_pips = info.get("max_spread_pips")
        if max_spread_pips is not None:
            max_spread_pips *= config.SPREAD_LIMIT_MULT

        if not quote:
            return {
                "ok": not config.SPREAD_FILTER_ENABLED,
                "reason": "Current quote unavailable",
                "spread": None,
                "spread_pips": None,
                "max_spread_pips": max_spread_pips,
            }

        spread = quote["ask"] - quote["bid"]
        spread_pips = spread / pip_size if pip_size else None
        ok = (
            not config.SPREAD_FILTER_ENABLED
            or spread_pips is None
            or max_spread_pips is None
            or spread_pips <= max_spread_pips
        )
        reason = "OK" if ok else f"Spread too wide ({spread_pips:.1f} > {max_spread_pips:.1f} pips)"

        return {
            "ok": ok,
            "reason": reason,
            "spread": spread,
            "spread_pips": spread_pips,
            "max_spread_pips": max_spread_pips,
            "bid": quote["bid"],
            "ask": quote["ask"],
            "mid": quote["mid"],
        }

    def _review_entry_with_ai(self, instrument, signal_data, snapshot):
        if signal_data.get("signal") not in (Signal.BUY, Signal.SELL):
            return {
                "mode": config.AI_MODE,
                "reviewed": False,
                "available": self.ai_advisor.enabled,
                "allow_trade": True,
                "should_execute": True,
                "action": "pass",
                "confidence": "normal",
                "size_mult": 1.0,
                "bankroll_fit": "unknown",
                "risk_flags": [],
                "reason": "No actionable trade signal to review.",
            }

        bankroll_context = self._build_bankroll_context()
        decision = self.ai_decision_engine.evaluate_entry(
            instrument=instrument,
            signal_payload=signal_data,
            market_snapshot=snapshot,
            bankroll_context=bankroll_context,
        )
        decision["effective_trading_equity"] = bankroll_context["effective_trading_equity"]
        decision["bankroll_mode"] = bankroll_context["mode"]
        return decision

    def _review_open_trade_with_ai(self, instrument, trade, snapshot, current_price):
        if not current_price:
            return {
                "mode": config.AI_MODE,
                "reviewed": False,
                "available": self.ai_advisor.enabled,
                "exit_now": False,
                "should_exit": False,
                "action": "hold",
                "confidence": "normal",
                "risk_flags": [],
                "reason": "Current price unavailable for open-trade review.",
            }

        estimated_pnl = self._estimate_pnl_usd(
            instrument,
            trade["direction"],
            trade["entry_price"],
            current_price,
            trade["quantity"],
        )
        trading_equity = self._effective_trading_equity()
        unrealized_pct = (
            (estimated_pnl / trading_equity) * 100
            if estimated_pnl is not None and trading_equity else 0
        )
        hold_mins = 0
        timestamp = trade.get("timestamp")
        if timestamp:
            try:
                hold_mins = int((datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() / 60)
            except ValueError:
                hold_mins = 0

        open_trade = {
            "id": trade.get("id"),
            "oanda_trade_id": trade.get("oanda_trade_id"),
            "direction": trade.get("direction"),
            "entry_price": trade.get("entry_price"),
            "current_price": current_price,
            "quantity": trade.get("quantity"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit"),
            "strategy_name": trade.get("strategy_name"),
            "strategy_confidence": trade.get("strategy_confidence"),
            "market_regime": trade.get("market_regime"),
            "estimated_unrealized_pnl": estimated_pnl,
            "estimated_unrealized_pct": unrealized_pct,
            "hold_mins": hold_mins,
        }

        bankroll_context = self._build_bankroll_context()
        market_snapshot = dict(snapshot or {})
        market_snapshot["current_price"] = current_price
        market_snapshot["open_trade"] = open_trade
        decision = self.ai_decision_engine.evaluate_exit(
            instrument=instrument,
            open_trade=open_trade,
            market_snapshot=market_snapshot,
            bankroll_context=bankroll_context,
        )
        decision["effective_trading_equity"] = bankroll_context["effective_trading_equity"]
        decision["bankroll_mode"] = bankroll_context["mode"]
        return decision

    def _build_strategy_factors(self, result):
        factors = []
        for entry in result.get("all_results", []):
            factors.append({
                "strategy": entry.get("strategy"),
                "signal": entry.get("signal"),
                "reason": entry.get("reason"),
                "regime": entry.get("regime"),
            })
        if not factors:
            factors.append({
                "strategy": result.get("strategy", "none"),
                "signal": result.get("signal", Signal.HOLD),
                "reason": result.get("reason", "No signal"),
                "regime": result.get("regime", MarketRegime.TRENDING),
            })
        return factors

    def _annotate_trade_readiness(self, snapshot):
        blockers = []
        state = snapshot.get("state")

        if state == "no_data":
            blockers.append(snapshot.get("reason", "Waiting for market data"))
        if not snapshot.get("news_ok", True):
            blockers.append(snapshot.get("news_reason", "Blocked by news filter"))
        if not snapshot.get("risk_ok", True):
            blockers.append(snapshot.get("risk_reason", "Blocked by risk manager"))
        if not snapshot.get("spread_ok", True):
            blockers.append(snapshot.get("spread_reason", "Spread too wide"))

        signal = snapshot.get("final_signal")
        armed = state not in {"no_data", "submitted"} and not blockers
        ready_now = signal in (Signal.BUY, Signal.SELL) and not blockers and state not in {"submitted"}

        if state == "submitted":
            readiness_status = "submitted"
            readiness_summary = snapshot.get(
                "reason",
                "Trade signal passed all checks and was submitted to OANDA.",
            )
        elif ready_now:
            readiness_status = "ready_now"
            readiness_summary = "All trade gates are open. The bot can submit this signal now."
        elif armed:
            readiness_status = "armed"
            if state == "waiting_new_candle":
                readiness_summary = f"Armed and waiting for the next completed {config.BAR_GRANULARITY} candle."
            else:
                readiness_summary = (
                    "Armed and ready. If the next completed candle produces a valid BUY or SELL signal, "
                    "the bot will submit it automatically."
                )
        elif state == "no_data":
            readiness_status = "warming_up"
            readiness_summary = snapshot.get("reason", "Waiting for enough market data to evaluate.")
        else:
            readiness_status = "blocked"
            readiness_summary = blockers[0] if blockers else snapshot.get("reason", "Trading is blocked right now.")

        snapshot["trade_blockers"] = blockers
        snapshot["armed_for_next_signal"] = armed
        snapshot["ready_to_submit_now"] = ready_now
        snapshot["trade_readiness_status"] = readiness_status
        snapshot["trade_readiness_summary"] = readiness_summary
        return snapshot

    def _build_trade_readiness(self, decision_factors):
        if self._api_cooldown_active():
            wait_seconds = max(1, int(round(self.api_cooldown_until - time.time())))
            return {
                "status": "cooldown",
                "summary": f"OANDA cooldown active for {wait_seconds}s. The bot will resume trading checks automatically.",
                "armed_instruments": [],
                "blocked_instruments": [],
                "warming_up_instruments": [],
                "submitted_instruments": [],
                "waiting_on_candle": [],
                "scanned_instruments": list(decision_factors),
            }

        if not decision_factors:
            return {
                "status": "starting",
                "summary": "Waiting for the first full market scan.",
                "armed_instruments": [],
                "blocked_instruments": [],
                "warming_up_instruments": [],
                "submitted_instruments": [],
                "waiting_on_candle": [],
                "scanned_instruments": [],
            }

        armed = []
        blocked = []
        warming_up = []
        submitted = []
        waiting_on_candle = []

        for instrument, snapshot in decision_factors.items():
            status = snapshot.get("trade_readiness_status")
            entry = {
                "instrument": instrument,
                "reason": snapshot.get("trade_readiness_summary") or snapshot.get("reason", "No status yet"),
            }
            if status == "armed":
                armed.append(entry)
            elif status == "blocked":
                blocked.append(entry)
            elif status == "warming_up":
                warming_up.append(entry)
            elif status == "submitted":
                submitted.append(entry)

            if snapshot.get("state") == "waiting_new_candle":
                waiting_on_candle.append(instrument)

        total = len(decision_factors)
        if submitted:
            status = "submitted"
            summary = (
                f"Trade submitted on {len(submitted)} instrument(s). "
                "The bot will continue monitoring for exits and the next setups."
            )
        elif armed:
            status = "armed"
            summary = (
                f"Armed on {len(armed)}/{total} instrument(s). "
                "If a valid BUY or SELL signal appears on a completed candle, the bot will place the trade automatically."
            )
        elif warming_up and len(warming_up) == total:
            status = "warming_up"
            summary = "Still warming up. The bot needs enough fresh candle data before it can trade."
        elif blocked and len(blocked) == total:
            status = "blocked"
            summary = "All scanned instruments are blocked right now by a trade gate such as news, spread, or risk limits."
        else:
            status = "mixed"
            summary = "Some instruments are blocked while others are still being evaluated or waiting for the next candle."

        return {
            "status": status,
            "summary": summary,
            "armed_instruments": armed,
            "blocked_instruments": blocked,
            "warming_up_instruments": warming_up,
            "submitted_instruments": submitted,
            "waiting_on_candle": waiting_on_candle,
            "scanned_instruments": list(decision_factors),
        }

    def _summarize_wait_reason(self, snapshot):
        readiness_summary = snapshot.get("trade_readiness_summary")
        if readiness_summary and snapshot.get("trade_readiness_status") in {"armed", "warming_up", "submitted"}:
            return readiness_summary
        if snapshot.get("state") == "waiting_new_candle":
            return snapshot["reason"]
        if not snapshot.get("news_ok", True):
            return snapshot.get("news_reason", "Blocked by news filter")
        if not snapshot.get("risk_ok", True):
            return snapshot.get("risk_reason", "Blocked by risk manager")
        if not snapshot.get("spread_ok", True):
            return snapshot.get("spread_reason", "Spread too wide")
        if snapshot.get("final_signal") == Signal.HOLD:
            return snapshot.get("final_reason", "No trading signal yet")
        return snapshot.get("final_reason", "Ready to trade")

    def _infer_exit_reason(self, trade, exit_price):
        if trade["direction"] == "BUY":
            if trade["stop_loss"] and exit_price <= trade["stop_loss"]:
                return "stop_loss"
            if trade["take_profit"] and exit_price >= trade["take_profit"]:
                return "take_profit"
        else:
            if trade["stop_loss"] and exit_price >= trade["stop_loss"]:
                return "stop_loss"
            if trade["take_profit"] and exit_price <= trade["take_profit"]:
                return "take_profit"
        return "signal"

    def _quote_currency_to_usd_rate(self, quote_currency, exit_price=None, instrument=None):
        if quote_currency == "USD":
            return 1.0

        if instrument and instrument.startswith("USD_") and exit_price:
            return 1.0 / exit_price

        direct_pair = f"{quote_currency}_USD"
        inverse_pair = f"USD_{quote_currency}"

        direct_quote = self._get_current_price(direct_pair)
        if direct_quote:
            return direct_quote["mid"]

        inverse_quote = self._get_current_price(inverse_pair)
        if inverse_quote and inverse_quote["mid"]:
            return 1.0 / inverse_quote["mid"]

        return None

    def _estimate_pnl_usd(self, instrument, direction, entry_price, exit_price, quantity):
        if "_" not in instrument:
            return (exit_price - entry_price) * quantity if direction == "BUY" else (entry_price - exit_price) * quantity

        _, quote_currency = instrument.split("_", 1)
        price_diff = (exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)
        pnl_in_quote = price_diff * quantity
        usd_rate = self._quote_currency_to_usd_rate(
            quote_currency,
            exit_price=exit_price,
            instrument=instrument,
        )
        if usd_rate is None:
            return None
        return pnl_in_quote * usd_rate

    def _repair_recent_closed_trade_pnl(self, days=14):
        repaired = 0
        for trade in self.journal.get_recent_trades(days=days):
            if not trade.get("exit_price"):
                continue
            corrected_pnl = self._estimate_pnl_usd(
                trade["instrument"],
                trade["direction"],
                trade["entry_price"],
                trade["exit_price"],
                trade["quantity"],
            )
            if corrected_pnl is None:
                continue

            stored_pnl = trade.get("pnl") or 0
            if abs(corrected_pnl - stored_pnl) < 0.01:
                continue

            pnl_pct = corrected_pnl / self.account_value * 100 if self.account_value else 0
            note = (trade.get("notes") or "").strip()
            repair_note = "P&L repaired using quote-currency conversion."
            if repair_note not in note:
                note = f"{note} | {repair_note}".strip(" |")

            self.journal.revise_closed_trade(
                trade["id"],
                trade["exit_price"],
                corrected_pnl,
                pnl_pct,
                exit_reason=trade.get("exit_reason"),
                notes=note,
            )
            repaired += 1

        if repaired:
            logger.info(f"Repaired P&L values for {repaired} recent closed trade(s).")

    # ─── Execution ───────────────────────────────

    def _execute_signal(self, instrument, signal_data):
        direction = signal_data["signal"]

        # ─── Reverse mode: flip every signal before execution ──────
        # When REVERSE_MODE is on, a BUY becomes a SELL and vice versa.
        # This runs after the strategy has decided but before anything
        # is sent to the broker, journal, or logs — so the rest of the
        # pipeline is completely unaware the flip happened.
        if config.REVERSE_MODE and direction in (Signal.BUY, Signal.SELL):
            original = direction
            direction = Signal.SELL if direction == Signal.BUY else Signal.BUY
            logger.info(f"  🔄 REVERSE MODE: flipped {original} -> {direction} on {instrument}")
            self._log_activity(
                f"REVERSE: flipped {original} -> {direction} on {instrument}",
                level="signal",
            )

        price = signal_data["price"]
        atr = signal_data.get("atr", 0)
        regime = signal_data.get("regime", MarketRegime.TRENDING)
        strategy_name = signal_data.get("strategy", "unknown")
        strategy_confidence = signal_data.get("confidence", "normal")
        strategy_details = signal_data.get("all_results", [])
        ai_decision = signal_data.get("ai_decision") or {}
        trading_equity = signal_data.get("trading_equity") or self._effective_trading_equity()
        bankroll_mode = self._bankroll_mode()

        can_trade, reason = self.risk_manager.can_trade(trading_equity)
        if not can_trade:
            logger.info(f"  🛑 Blocked: {reason}")
            return {"submitted": False, "reason": reason}

        existing = self._get_oanda_positions(instrument)
        is_scale_in = False
        if existing:
            existing_dir = "BUY" if existing["long"]["units"] != "0" else "SELL"
            if existing_dir == direction:
                # Scale-in: add to existing position if allowed
                open_trades = self.journal.get_open_trades(instrument)
                scale_in_count = len(open_trades)
                if config.SCALE_IN_ENABLED and scale_in_count < config.SCALE_IN_MAX_ADDS + 1:
                    is_scale_in = True
                    logger.info(f"  📈 Scale-in #{scale_in_count + 1} on {instrument} {direction}")
                else:
                    return {
                        "submitted": False,
                        "reason": f"Existing {direction} position on {instrument} (max scale-ins reached)",
                    }
            else:
                self._close_oanda_position(instrument)

        stop_loss = self.risk_manager.calculate_stop_loss(price, direction, atr, regime)
        take_profit = self.risk_manager.calculate_take_profit(price, direction, atr)
        info = self.instrument_info.get(instrument, {})
        size_mult = ai_decision.get("size_mult") or 1.0
        if is_scale_in:
            size_mult *= config.SCALE_IN_SIZE_FRACTION
        size_mult *= self.risk_manager.get_time_of_day_multiplier()
        position_size = self.risk_manager.calculate_position_size(
            trading_equity,
            price,
            stop_loss,
            regime,
            size_mult=size_mult,
            min_units=info.get("min_units", 1),
        )

        if position_size <= 0:
            return {"submitted": False, "reason": "Position size resolved to 0 units"}

        risk_amount = abs(price - stop_loss) * position_size
        risk_pct = (risk_amount / trading_equity) if trading_equity else 0

        units = position_size if direction == Signal.BUY else -position_size
        precision = info.get("precision", 5)

        # Get EMA values for journal logging
        ema_strat = next((s for s in self.strategy_manager.strategies if s.name == "ema"), None)
        fast_ema = ema_strat.fast_period if ema_strat else 0
        slow_ema = ema_strat.slow_period if ema_strat else 0

        try:
            order_data = MarketOrderRequest(
                instrument=instrument,
                units=units,
                stopLossOnFill=StopLossDetails(price=round(stop_loss, precision)).data,
                takeProfitOnFill=TakeProfitDetails(price=round(take_profit, precision)).data,
            )
            r = orders.OrderCreate(self.account_id, data=order_data.data)
            response = self.api.request(r)

            fill = response.get("orderFillTransaction")
            if not fill:
                logger.warning("  ⚠️  No fill confirmation")
                return {"submitted": False, "reason": "OANDA did not return a fill confirmation"}

            fill_price = float(fill.get("price", price))
            fill_units = abs(int(float(fill.get("units", units))))
            trade_id = fill.get("tradeOpened", {}).get("tradeID", "?")

            logger.info(f"  📤 FILLED [{strategy_name.upper()}]: {direction} {fill_units} {instrument} @ {fill_price}")
            logger.info(f"     Trade #{trade_id} | SL: {round(stop_loss, precision)} | TP: {round(take_profit, precision)}")

            r2 = accounts.AccountSummary(self.account_id)
            resp2 = self.api.request(r2)
            nav = float(resp2.get("account", {}).get("NAV", 0))
            margin = float(resp2.get("account", {}).get("marginUsed", 0))
            logger.info(f"     NAV: ${nav:,.2f} | Margin: ${margin:,.2f}")

            journal_warning = None
            try:
                journal_trade_id = self.journal.open_trade(
                    instrument=instrument,
                    direction=direction,
                    oanda_trade_id=trade_id,
                    entry_price=fill_price,
                    quantity=fill_units,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    fast_ema=fast_ema,
                    slow_ema=slow_ema,
                    atr_at_entry=atr,
                    market_regime=regime,
                    bankroll_mode=bankroll_mode,
                    equity_reference=trading_equity,
                    broker_nav=self.account_value,
                    risk_pct_at_entry=risk_pct,
                    strategy_name=strategy_name,
                    strategy_confidence=strategy_confidence,
                    strategy_details=strategy_details,
                    ai_mode=ai_decision.get("mode", config.AI_MODE),
                    ai_action=ai_decision.get("action"),
                    ai_confidence=ai_decision.get("confidence"),
                    ai_size_mult=ai_decision.get("size_mult"),
                    ai_reason=ai_decision.get("reason"),
                    ai_payload=ai_decision,
                )
                logger.info(f"     Journal trade #{journal_trade_id} recorded locally.")
            except Exception as journal_error:
                journal_warning = (
                    f"OANDA fill succeeded, but local trade journaling failed: {journal_error}"
                )
                logger.error(
                    "%s | OANDA trade %s %s %s",
                    journal_warning,
                    trade_id,
                    direction,
                    instrument,
                    exc_info=True,
                )

            try:
                self.memory.append_diary_entry(
                    "Trade opened",
                    f"{direction} {instrument} via {strategy_name.upper()} at {fill_price}",
                    details=[
                        f"Units: {fill_units} | Stop loss: {round(stop_loss, precision)} | Take profit: {round(take_profit, precision)}",
                        f"EMA: {fast_ema}/{slow_ema} | Regime: {regime} | Confidence: {strategy_confidence}",
                        f"Bankroll: {bankroll_mode} | Effective equity: ${trading_equity:,.2f} | AI: {ai_decision.get('action', 'pass')}",
                    ],
                )
            except Exception as memory_error:
                logger.warning(f"Could not append memory diary entry for trade {trade_id}: {memory_error}")

            reason = f"Trade #{trade_id} was filled on OANDA at {fill_price}"
            if journal_warning:
                reason = f"{reason}. Warning: {journal_warning}"
            return {
                "submitted": True,
                "reason": reason,
                "trade_id": trade_id,
                "journal_synced": journal_warning is None,
            }

        except V20Error as e:
            logger.error(f"  ❌ Order rejected: {e}")
            return {"submitted": False, "reason": f"Order rejected by OANDA: {e}"}
        except Exception as e:
            logger.error(f"  ❌ Order error: {e}", exc_info=True)
            return {"submitted": False, "reason": f"Order error: {e}"}

    # ─── Trade Monitoring ────────────────────────

    def _check_oanda_trades(self, instrument, snapshot=None):
        journal_trades = self.journal.get_open_trades(instrument)
        if not journal_trades:
            return {"closed_by_ai": False}
        try:
            r = trades_ep.OpenTrades(self.account_id)
            response = self.api.request(r)
            oanda_instruments = [t["instrument"] for t in response.get("trades", [])]
            for trade in journal_trades:
                if instrument not in oanda_instruments:
                    verified = self._verify_closed_trade(instrument, trade)
                    if verified:
                        self.journal.close_trade(
                            trade["id"], verified["exit_price"],
                            verified["pnl"], verified["pnl_pct"], verified["reason"],
                            notes=verified.get("notes", ""),
                        )
                        self._clear_pending_ai_exit(trade)
                        self.memory.append_diary_entry(
                            "Trade closed",
                            f"Trade #{trade['id']} on {instrument} closed with ${verified['pnl']:+.2f}.",
                            details=[
                                f"Exit price: {verified['exit_price']} | Reason: {verified['reason']}",
                                f"P&L: {verified['pnl_pct']:+.2f}% of account",
                            ],
                        )
                        self.memory.refresh_skills_snapshot(
                            stats=self.journal.get_trade_stats(days=30),
                            recent_trades=self.journal.get_recent_trades(days=30),
                            param_history=self.journal.get_param_history(limit=10),
                        )
                        # Continuous AI learning — review every closed trade
                        try:
                            closed_trade_data = dict(trade)
                            closed_trade_data["exit_price"] = verified["exit_price"]
                            closed_trade_data["pnl"] = verified["pnl"]
                            closed_trade_data["exit_reason"] = verified["reason"]
                            review = self.ai_advisor.post_trade_review(closed_trade_data)
                            if review and review.get("lesson"):
                                logger.info(f"  🧠 AI lesson: {review['lesson']}")
                                self.memory.append_diary_entry(
                                    "Post-trade AI lesson",
                                    review["lesson"],
                                    details=[
                                        f"Category: {review.get('category', 'general')}",
                                        f"Trade: {trade.get('direction')} {instrument} | P&L: ${verified['pnl']:+.2f}",
                                    ],
                                )
                        except Exception as review_err:
                            logger.debug(f"Post-trade review skipped: {review_err}")
                    else:
                        pending_ai_exit = self._get_pending_ai_exit(trade)
                        self.journal.close_trade(
                            trade["id"],
                            0,
                            0,
                            0,
                            pending_ai_exit.get("exit_reason", "unverified") if pending_ai_exit else "unverified",
                            notes=pending_ai_exit.get("notes", "") if pending_ai_exit else "",
                        )
                        self._clear_pending_ai_exit(trade)
                    continue

                quote = self._get_current_price(instrument)
                current_price = quote["mid"] if quote else None

                # ─── Trailing stop-loss update ───────────
                if current_price and trade.get("atr_at_entry"):
                    new_stop = self.risk_manager.calculate_trailing_stop(
                        trade, current_price, trade["atr_at_entry"]
                    )
                    if new_stop is not None:
                        self._update_oanda_stop_loss(trade, new_stop, instrument)

                exit_decision = self._review_open_trade_with_ai(instrument, trade, snapshot or {}, current_price)
                if snapshot is not None:
                    snapshot["ai_exit_decision"] = exit_decision
                if exit_decision.get("reviewed") and exit_decision.get("action") != "hold":
                    logger.info(
                        f"  AI[{exit_decision.get('mode', 'off').upper()}] "
                        f"{exit_decision.get('action', 'hold').upper()} "
                        f"{instrument} | {exit_decision.get('reason')}"
                    )
                if exit_decision.get("should_exit"):
                    self._remember_pending_ai_exit(trade, exit_decision)
                    self._close_oanda_position(instrument)
                    try:
                        self.memory.append_diary_entry(
                            "AI exit requested",
                            f"{instrument} trade flagged for exit by AI.",
                            details=[
                                f"Trade #{trade.get('id')} | OANDA #{trade.get('oanda_trade_id')}",
                                exit_decision.get("reason", "AI requested an early exit."),
                            ],
                        )
                    except Exception as memory_error:
                        logger.warning(f"Could not append AI exit diary entry for {instrument}: {memory_error}")
                    return {"closed_by_ai": True, "ai_exit": exit_decision}
        except V20Error as e:
            logger.error(f"Trade check error: {e}")
        return {"closed_by_ai": False}

    def _verify_closed_trade(self, instrument, trade):
        try:
            pending_ai_exit = self._get_pending_ai_exit(trade)
            oanda_trade_id = trade.get("oanda_trade_id")
            if oanda_trade_id:
                try:
                    response = self.api.request(trades_ep.TradeDetails(self.account_id, tradeID=oanda_trade_id))
                    oanda_trade = response.get("trade", {})
                    if oanda_trade:
                        exit_price = float(
                            oanda_trade.get("averageClosePrice")
                            or oanda_trade.get("price")
                            or trade["entry_price"]
                        )
                        pnl = float(oanda_trade.get("realizedPL", 0)) + float(oanda_trade.get("financing", 0))
                        pnl_pct = pnl / self.account_value * 100 if self.account_value else 0
                        reason = (
                            pending_ai_exit.get("exit_reason")
                            if pending_ai_exit else self._infer_exit_reason(trade, exit_price)
                        )
                        logger.info(
                            f"  🔍 Verified from OANDA: #{trade['id']} / {oanda_trade_id} exit @ {exit_price}, "
                            f"P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)"
                        )
                        return {
                            "exit_price": exit_price,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "reason": reason,
                            "notes": pending_ai_exit.get("notes", "") if pending_ai_exit else "",
                        }
                except Exception as detail_error:
                    logger.warning(f"  Could not fetch closed trade {oanda_trade_id} from OANDA: {detail_error}")

            price_data = self._get_current_price(instrument)
            if not price_data:
                return None
            exit_price = price_data["mid"]
            pnl = self._estimate_pnl_usd(
                instrument,
                trade["direction"],
                trade["entry_price"],
                exit_price,
                trade["quantity"],
            )
            if pnl is None:
                return None
            reason = (
                pending_ai_exit.get("exit_reason")
                if pending_ai_exit else self._infer_exit_reason(trade, exit_price)
            )
            pnl_pct = pnl / self.account_value * 100 if self.account_value else 0
            logger.info(
                f"  🔍 Verified by estimate: #{trade['id']} exit @ {exit_price}, "
                f"P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)"
            )
            return {
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": reason,
                "notes": pending_ai_exit.get("notes", "") if pending_ai_exit else "",
            }
        except Exception as e:
            logger.error(f"  Verify error: {e}")
            return None

    def _update_oanda_stop_loss(self, trade, new_stop, instrument):
        """Move the stop-loss on OANDA and update the local journal."""
        oanda_trade_id = trade.get("oanda_trade_id")
        if not oanda_trade_id:
            return
        info = self.instrument_info.get(instrument, {})
        precision = info.get("precision", 5)
        try:
            data = {"stopLoss": {"price": str(round(new_stop, precision))}}
            r = trades_ep.TradeCRCDO(self.account_id, tradeID=oanda_trade_id, data=data)
            self.api.request(r)
            old_stop = trade["stop_loss"]
            trade["stop_loss"] = new_stop
            self.journal.update_stop_loss(trade["id"], new_stop)
            logger.info(
                f"  📈 Trailing stop moved on {instrument}: "
                f"{round(old_stop, precision)} → {round(new_stop, precision)}"
            )
        except Exception as e:
            logger.warning(f"  Could not update trailing stop for {instrument}: {e}")

    # ─── Position Management ─────────────────────

    def _get_oanda_positions(self, instrument):
        try:
            r = accounts.AccountDetails(self.account_id)
            response = self.api.request(r)
            for pos in response.get("account", {}).get("positions", []):
                if pos["instrument"] == instrument:
                    if int(pos["long"]["units"]) != 0 or int(pos["short"]["units"]) != 0:
                        return pos
        except Exception as e:
            logger.warning(f"Could not inspect OANDA positions for {instrument}: {e}")
        return None

    def _close_oanda_position(self, instrument):
        try:
            try:
                r = positions_ep.PositionClose(self.account_id, instrument=instrument, data={"longUnits": "ALL"})
                self.api.request(r)
                logger.info(f"  🔄 Closed long {instrument}")
            except V20Error as e:
                logger.debug(f"No long {instrument} position to close: {e}")
            try:
                r = positions_ep.PositionClose(self.account_id, instrument=instrument, data={"shortUnits": "ALL"})
                self.api.request(r)
                logger.info(f"  🔄 Closed short {instrument}")
            except V20Error as e:
                logger.debug(f"No short {instrument} position to close: {e}")
        except Exception as e:
            logger.error(f"  Close error: {e}")

    # ─── Helpers ─────────────────────────────────

    def _load_historical_data(self):
        logger.info("📥 Loading historical data...")
        for instrument in config.INSTRUMENTS:
            df = self._fetch_candles(instrument)
            if df is not None and len(df) > 0:
                self.price_data[instrument] = df
                logger.info(f"  ✅ {instrument}: {len(df)} candles")
            else:
                logger.warning(f"  ⚠️  {instrument}: No data")

    def _run_learning(self):
        if not self.price_data or not self.learner:
            return
        changes = self.learner.run_learning_cycle(self.price_data)
        if changes:
            logger.info(f"  🧠 Learning: {len(changes)} change(s)")

    def stop(self):
        print(f"\n{'='*50}")
        print(f"  🛑 Shutting down SmartTrader Bot v2.0...")
        print(f"{'='*50}")
        self.running = False
        self._write_runtime_status(
            bot_online=False,
            current_activity="Bot stopped.",
            last_scan_at=datetime.now().isoformat(),
            news_filter=self.news_filter.get_status(),
        )
        self.memory.append_diary_entry(
            "Session stop",
            "Bot session ended cleanly.",
            details=[
                f"Open positions in journal: {len(self.journal.get_open_trades())}",
                f"Recent closed trades (30d): {self.journal.get_trade_stats(days=30)['total']}",
            ],
        )
        self._stop_dashboard()
        self.journal.print_performance_report()
        if self.learner:
            summary = self.learner.get_learning_summary()
            print(f"  🧠 Fast EMA: {summary['current_fast_ema']} | Slow EMA: {summary['current_slow_ema']}")
            print(f"     Win Rate: {summary['current_win_rate']:.1%} | Changes: {summary['total_param_changes']}")
        print(f"\n  👋 Data saved to {config.DB_PATH}. Run again: python bot.py\n")

def parse_args():
    parser = argparse.ArgumentParser(description="Run SmartTrader Bot v2.0")
    parser.add_argument(
        "--dashboard",
        dest="dashboard",
        action="store_true",
        help="Start the dashboard API alongside the bot.",
    )
    parser.add_argument(
        "--no-dashboard",
        dest="dashboard",
        action="store_false",
        help="Run the bot without auto-starting the dashboard API.",
    )
    parser.set_defaults(dashboard=None)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.dashboard is not None:
        config.AUTO_START_DASHBOARD = args.dashboard
    print(r"""
    ╔═══════════════════════════════════════╗
    ║   🐟 SmartTrader Bot v2.0             ║
    ║   Multi-Strategy · News Filter · AI   ║
    ║   Gold · Silver · USD/JPY             ║
    ╚═══════════════════════════════════════╝
    """)
    bot = SmartTraderBot()
    def handler(sig, frame):
        bot.stop()
        sys.exit(0)
    sig_module.signal(sig_module.SIGINT, handler)
    bot.start()


if __name__ == "__main__":
    main()
