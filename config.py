"""
config.py - Loads settings from the .env file.
"""

import os
import sys

from dotenv import load_dotenv


def _configure_console_output():
    """Prefer UTF-8 console output so Windows terminals do not crash on Unicode logs."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if not stream or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            continue


_configure_console_output()
load_dotenv()


class Config:
    OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
    OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
    TRADING_MODE = os.getenv("TRADING_MODE", "practice")
    OANDA_PRACTICE_URL = "https://api-fxpractice.oanda.com"
    OANDA_LIVE_URL = "https://api-fxtrade.oanda.com"

    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    AI_LEARNING_ENABLED = os.getenv("AI_LEARNING_ENABLED", "true").lower() == "true"
    AI_MODE = os.getenv("AI_MODE", "shadow").lower()
    AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
    AI_MIN_CONFIDENCE = os.getenv("AI_MIN_CONFIDENCE", "normal").lower()
    AI_MIN_SIZE_MULT = float(os.getenv("AI_MIN_SIZE_MULT", 0.25))
    AI_MAX_SIZE_MULT = float(os.getenv("AI_MAX_SIZE_MULT", 1.25))
    AI_MAX_AUTOMATED_REVIEWS_PER_WEEK = int(
        os.getenv("AI_MAX_AUTOMATED_REVIEWS_PER_WEEK", "40" if TRADING_MODE == "practice" else "120")
    )
    AI_ENTRY_REVIEW_COOLDOWN_SECONDS = int(
        os.getenv("AI_ENTRY_REVIEW_COOLDOWN_SECONDS", "900" if TRADING_MODE == "practice" else "300")
    )
    AI_EXIT_REVIEW_COOLDOWN_SECONDS = int(
        os.getenv("AI_EXIT_REVIEW_COOLDOWN_SECONDS", "1800" if TRADING_MODE == "practice" else "600")
    )
    AI_POST_TRADE_REVIEW_ENABLED = os.getenv(
        "AI_POST_TRADE_REVIEW_ENABLED",
        "false" if TRADING_MODE == "practice" else "true",
    ).lower() == "true"
    AI_REVIEW_STATE_PATH = os.getenv("AI_REVIEW_STATE_PATH", "ai_review_state.json")
    MISSING_TP_PROFIT_LOCK_USD = float(
        os.getenv("MISSING_TP_PROFIT_LOCK_USD", "10" if TRADING_MODE == "practice" else "0")
    )

    PRACTICE_STYLE = os.getenv("PRACTICE_STYLE", "standard").lower()
    PRACTICE_BAR_GRANULARITY = os.getenv("PRACTICE_BAR_GRANULARITY", "M5")
    PRACTICE_POLL_INTERVAL = int(os.getenv("PRACTICE_POLL_INTERVAL", 10))
    PRACTICE_FAST_EMA = int(os.getenv("PRACTICE_FAST_EMA", 5))
    PRACTICE_SLOW_EMA = int(os.getenv("PRACTICE_SLOW_EMA", 13))
    PRACTICE_BREAKOUT_LOOKBACK = int(os.getenv("PRACTICE_BREAKOUT_LOOKBACK", 10))
    PRACTICE_BREAKOUT_VOLUME_MULT = float(os.getenv("PRACTICE_BREAKOUT_VOLUME_MULT", 1.0))
    PRACTICE_RISK_PER_TRADE = float(os.getenv("PRACTICE_RISK_PER_TRADE", 0.03))
    PRACTICE_MAX_POSITIONS = int(os.getenv("PRACTICE_MAX_POSITIONS", 2))
    PRACTICE_DAILY_LOSS_LIMIT = float(os.getenv("PRACTICE_DAILY_LOSS_LIMIT", 0.06))
    PRACTICE_SPREAD_LIMIT_MULT = float(os.getenv("PRACTICE_SPREAD_LIMIT_MULT", 2.5))
    USE_VIRTUAL_BANKROLL = os.getenv("USE_VIRTUAL_BANKROLL", "true").lower() == "true"
    VIRTUAL_BANKROLL = float(os.getenv("VIRTUAL_BANKROLL", 1000))
    VIRTUAL_BANKROLL_FLOOR = float(os.getenv("VIRTUAL_BANKROLL_FLOOR", 250))
    VIRTUAL_RISK_PER_TRADE = float(os.getenv("VIRTUAL_RISK_PER_TRADE", 0.005))

    STRATEGIES = [
        value.strip().lower()
        for value in os.getenv("STRATEGIES", "ema,breakout,vwap_bounce,rsi_exhaustion").split(",")
        if value.strip()
    ]

    FAST_EMA = int(os.getenv("FAST_EMA", 9))
    SLOW_EMA = int(os.getenv("SLOW_EMA", 21))

    BREAKOUT_LOOKBACK = int(os.getenv("BREAKOUT_LOOKBACK", 20))
    BREAKOUT_ATR_THRESHOLD = float(os.getenv("BREAKOUT_ATR_THRESHOLD", 0.5))
    BREAKOUT_VOLUME_MULT = float(os.getenv("BREAKOUT_VOLUME_MULT", 1.2))

    VWAP_BIAS_EMA = int(os.getenv("VWAP_BIAS_EMA", 100))
    VWAP_VOLUME_LOOKBACK = int(os.getenv("VWAP_VOLUME_LOOKBACK", 20))
    VWAP_VOLUME_MULT = float(os.getenv("VWAP_VOLUME_MULT", 1.2))
    VWAP_WICK_RATIO = float(os.getenv("VWAP_WICK_RATIO", 1.5))

    SCALP_ENABLED = os.getenv("SCALP_ENABLED", "false").lower()
    SCALP_FAST_EMA = int(os.getenv("SCALP_FAST_EMA", 3))
    SCALP_SLOW_EMA = int(os.getenv("SCALP_SLOW_EMA", 8))
    SCALP_RSI_PERIOD = int(os.getenv("SCALP_RSI_PERIOD", 7))

    RSI_EXHAUSTION_PERIOD = int(os.getenv("RSI_EXHAUSTION_PERIOD", 14))
    RSI_EXHAUSTION_OVERBOUGHT = float(os.getenv("RSI_EXHAUSTION_OVERBOUGHT", 70))
    RSI_EXHAUSTION_OVERSOLD = float(os.getenv("RSI_EXHAUSTION_OVERSOLD", 30))
    RSI_EXHAUSTION_STREAK_MIN = int(os.getenv("RSI_EXHAUSTION_STREAK_MIN", 2))

    BAR_GRANULARITY = os.getenv("BAR_GRANULARITY", "M15")
    HTF_GRANULARITY = os.getenv("HTF_GRANULARITY", "H1")
    HTF_ENABLED = os.getenv("HTF_ENABLED", "true").lower() == "true"
    HTF_EMA_PERIOD = int(os.getenv("HTF_EMA_PERIOD", 21))
    HISTORY_COUNT = int(os.getenv("HISTORY_COUNT", 200))

    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.02))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", 2))
    STOP_LOSS_ATR_MULT = float(os.getenv("STOP_LOSS_ATR_MULT", 1.5))
    TAKE_PROFIT_ATR_MULT = float(os.getenv("TAKE_PROFIT_ATR_MULT", 3.0))
    DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", 0.05))
    DAILY_LOSS_LIMIT_ENABLED = os.getenv("DAILY_LOSS_LIMIT_ENABLED", "true").lower() == "true"
    MIN_TRADE_PNL = float(os.getenv("MIN_TRADE_PNL", 1.0))
    REVERSE_MODE = os.getenv("REVERSE_MODE", "false").lower() == "true"
    SCALE_IN_ENABLED = os.getenv("SCALE_IN_ENABLED", "true").lower() == "true"
    SCALE_IN_MAX_ADDS = int(os.getenv("SCALE_IN_MAX_ADDS", 2))
    SCALE_IN_SIZE_FRACTION = float(os.getenv("SCALE_IN_SIZE_FRACTION", 0.5))

    TRAILING_STOP_ENABLED = os.getenv("TRAILING_STOP_ENABLED", "true").lower() == "true"
    TRAILING_STOP_ACTIVATION_ATR = float(os.getenv("TRAILING_STOP_ACTIVATION_ATR", 0.5))
    TRAILING_STOP_DISTANCE_ATR = float(os.getenv("TRAILING_STOP_DISTANCE_ATR", 0.5))

    SPREAD_FILTER_ENABLED = os.getenv("SPREAD_FILTER_ENABLED", "true").lower() == "true"
    SPREAD_LIMIT_MULT = float(os.getenv("SPREAD_LIMIT_MULT", 1.0))

    NEWS_FILTER_ENABLED = os.getenv("NEWS_FILTER_ENABLED", "true").lower() == "true"
    NEWS_BLACKOUT_BEFORE = int(os.getenv("NEWS_BLACKOUT_BEFORE", 30))
    NEWS_BLACKOUT_AFTER = int(os.getenv("NEWS_BLACKOUT_AFTER", 15))
    NEWS_CALENDAR_SOURCE = os.getenv("NEWS_CALENDAR_SOURCE", "tradingeconomics").lower()
    TRADINGECONOMICS_API_KEY = os.getenv("TRADINGECONOMICS_API_KEY", "guest:guest")

    LEARNING_ENABLED = os.getenv("LEARNING_ENABLED", "true").lower() == "true"
    LEARNING_DAY = os.getenv("LEARNING_DAY", "adaptive")
    MIN_TRADES_FOR_LEARNING = int(os.getenv("MIN_TRADES_FOR_LEARNING", 3))
    LEARNING_LOOKBACK_WEEKS = int(os.getenv("LEARNING_LOOKBACK_WEEKS", 2))
    LEARNING_IMPROVEMENT_THRESHOLD = float(os.getenv("LEARNING_IMPROVEMENT_THRESHOLD", 0.02))
    LEARNING_COOLDOWN_MINUTES = int(os.getenv("LEARNING_COOLDOWN_MINUTES", 30))
    LEARNING_MIN_NEW_TRADES = int(os.getenv("LEARNING_MIN_NEW_TRADES", 1))

    INSTRUMENTS = os.getenv(
        "INSTRUMENTS",
        "XAU_USD,XAG_USD,USD_JPY,EUR_USD,AUD_USD,EUR_JPY",
    ).split(",")

    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
    CANDLE_REFRESH_MIN_SECONDS = int(os.getenv("CANDLE_REFRESH_MIN_SECONDS", 30))
    PRICE_CACHE_TTL_SECONDS = int(os.getenv("PRICE_CACHE_TTL_SECONDS", 8))
    API_ERROR_COOLDOWN_SECONDS = int(os.getenv("API_ERROR_COOLDOWN_SECONDS", 25))

    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", 8000))
    AUTO_START_DASHBOARD = os.getenv("AUTO_START_DASHBOARD", "true").lower() == "true"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DB_PATH = os.getenv("DB_PATH", "trades.db")
    BOT_STATUS_PATH = os.getenv("BOT_STATUS_PATH", "bot_status.json")
    SOUL_PATH = os.getenv("SOUL_PATH", "soul.md")
    SKILLS_PATH = os.getenv("SKILLS_PATH", "skills.md")
    STRATEGY_DOCS_PATH = os.getenv("STRATEGY_DOCS_PATH", "strategy_docs")
    STRATEGY_CARDS_PATH = os.getenv("STRATEGY_CARDS_PATH", "strategy_cards")

    @property
    def oanda_environment(self):
        return self.TRADING_MODE

    @property
    def is_practice(self):
        return self.TRADING_MODE == "practice"

    @property
    def has_claude(self):
        return bool(self.CLAUDE_API_KEY)

    @property
    def ai_learning_enabled(self):
        return self.AI_LEARNING_ENABLED and self.has_claude

    @property
    def ai_trading_enabled(self):
        return self.AI_MODE in {"shadow", "gated"}

    @property
    def use_virtual_bankroll(self):
        return self.is_practice and self.USE_VIRTUAL_BANKROLL

    @property
    def effective_risk_per_trade(self):
        if self.use_virtual_bankroll:
            return self.VIRTUAL_RISK_PER_TRADE
        return self.RISK_PER_TRADE

    @property
    def dashboard_url(self):
        host = self.API_HOST
        if host in {"0.0.0.0", "127.0.0.1"}:
            host = "localhost"
        return f"http://{host}:{self.API_PORT}"

    def apply_runtime_profiles(self):
        if self.is_practice and self.PRACTICE_STYLE == "active":
            self.BAR_GRANULARITY = self.PRACTICE_BAR_GRANULARITY
            self.POLL_INTERVAL = self.PRACTICE_POLL_INTERVAL
            self.FAST_EMA = self.PRACTICE_FAST_EMA
            self.SLOW_EMA = self.PRACTICE_SLOW_EMA
            self.BREAKOUT_LOOKBACK = self.PRACTICE_BREAKOUT_LOOKBACK
            self.BREAKOUT_VOLUME_MULT = self.PRACTICE_BREAKOUT_VOLUME_MULT
            self.RISK_PER_TRADE = self.PRACTICE_RISK_PER_TRADE
            self.MAX_POSITIONS = self.PRACTICE_MAX_POSITIONS
            self.DAILY_LOSS_LIMIT = self.PRACTICE_DAILY_LOSS_LIMIT
            self.SPREAD_LIMIT_MULT = self.PRACTICE_SPREAD_LIMIT_MULT

    def validate(self):
        if not self.OANDA_API_KEY or self.OANDA_API_KEY == "paste-your-api-token-here":
            print("\nOANDA_API_KEY not set. Edit your .env file.")
            sys.exit(1)
        if not self.OANDA_ACCOUNT_ID or "12345678" in self.OANDA_ACCOUNT_ID:
            print("\nOANDA_ACCOUNT_ID not set. Edit your .env file.")
            sys.exit(1)

    def print_summary(self):
        mode_label = "PRACTICE" if self.is_practice else "LIVE"
        print(f"\n{'=' * 60}")
        print("  SmartTrader Bot v2.0 - Configuration")
        print(f"{'=' * 60}")
        print(f"  Mode:          {mode_label}")
        print(f"  Account:       {self.OANDA_ACCOUNT_ID}")
        print(f"  Instruments:   {', '.join(self.INSTRUMENTS)}")
        print(f"  Strategies:    {', '.join(self.STRATEGIES)}")
        if self.is_practice:
            print(f"  Practice:      {self.PRACTICE_STYLE.upper()}")
        if self.use_virtual_bankroll:
            print(f"  Virtual Bank:  ${self.VIRTUAL_BANKROLL:,.2f} floor ${self.VIRTUAL_BANKROLL_FLOOR:,.2f}")
        print(f"  EMA:           {self.FAST_EMA}/{self.SLOW_EMA}")
        print(f"  Breakout:      {self.BREAKOUT_LOOKBACK} bar lookback")
        if "vwap_bounce" in self.STRATEGIES:
            print(f"  VWAP Bounce:   EMA{self.VWAP_BIAS_EMA} bias | vol x{self.VWAP_VOLUME_MULT}")
        if "rsi_exhaustion" in self.STRATEGIES:
            print(
                f"  RSI Exhaust:   {self.RSI_EXHAUSTION_OVERSOLD}/"
                f"{self.RSI_EXHAUSTION_OVERBOUGHT} | streak {self.RSI_EXHAUSTION_STREAK_MIN}"
            )
        print(f"  Granularity:   {self.BAR_GRANULARITY}")
        print(f"  Risk/Trade:    {self.effective_risk_per_trade * 100}%")
        print(f"  Spread Limit:  {self.SPREAD_LIMIT_MULT}x")
        print(f"  News Filter:   {'ON' if self.NEWS_FILTER_ENABLED else 'OFF'}")
        print(f"  Learning:      {'ON' if self.LEARNING_ENABLED else 'OFF'}")
        print(f"  AI Advisor:    {'ON' if self.has_claude else 'OFF (no API key)'}")
        print(f"  AI Learning:   {'ON' if self.ai_learning_enabled else 'OFF'}")
        print(f"  AI Trading:    {self.AI_MODE.upper()}")
        if self.has_claude:
            print(
                "  AI Budget:     "
                f"{self.AI_MAX_AUTOMATED_REVIEWS_PER_WEEK}/week | "
                f"entry {self.AI_ENTRY_REVIEW_COOLDOWN_SECONDS}s | "
                f"exit {self.AI_EXIT_REVIEW_COOLDOWN_SECONDS}s"
            )
        print(f"  Poll Every:    {self.POLL_INTERVAL}s")
        print(f"{'=' * 60}\n")

    def to_dict(self):
        """For the dashboard API."""
        return {
            "trading_mode": self.TRADING_MODE,
            "account_id": self.OANDA_ACCOUNT_ID,
            "instruments": self.INSTRUMENTS,
            "strategies": self.STRATEGIES,
            "fast_ema": self.FAST_EMA,
            "slow_ema": self.SLOW_EMA,
            "breakout_lookback": self.BREAKOUT_LOOKBACK,
            "vwap_bias_ema": self.VWAP_BIAS_EMA,
            "vwap_volume_lookback": self.VWAP_VOLUME_LOOKBACK,
            "vwap_volume_mult": self.VWAP_VOLUME_MULT,
            "vwap_wick_ratio": self.VWAP_WICK_RATIO,
            "rsi_exhaustion_period": self.RSI_EXHAUSTION_PERIOD,
            "rsi_exhaustion_overbought": self.RSI_EXHAUSTION_OVERBOUGHT,
            "rsi_exhaustion_oversold": self.RSI_EXHAUSTION_OVERSOLD,
            "rsi_exhaustion_streak_min": self.RSI_EXHAUSTION_STREAK_MIN,
            "bar_granularity": self.BAR_GRANULARITY,
            "risk_per_trade": self.RISK_PER_TRADE,
            "effective_risk_per_trade": self.effective_risk_per_trade,
            "max_positions": self.MAX_POSITIONS,
            "stop_loss_atr_mult": self.STOP_LOSS_ATR_MULT,
            "take_profit_atr_mult": self.TAKE_PROFIT_ATR_MULT,
            "spread_limit_mult": self.SPREAD_LIMIT_MULT,
            "daily_loss_limit": self.DAILY_LOSS_LIMIT,
            "daily_loss_limit_enabled": self.DAILY_LOSS_LIMIT_ENABLED,
            "min_trade_pnl": self.MIN_TRADE_PNL,
            "reverse_mode": self.REVERSE_MODE,
            "news_filter": self.NEWS_FILTER_ENABLED,
            "learning_enabled": self.LEARNING_ENABLED,
            "has_claude": self.has_claude,
            "ai_learning_enabled": self.ai_learning_enabled,
            "ai_mode": self.AI_MODE,
            "ai_model": self.AI_MODEL,
            "ai_min_confidence": self.AI_MIN_CONFIDENCE,
            "ai_min_size_mult": self.AI_MIN_SIZE_MULT,
            "ai_max_size_mult": self.AI_MAX_SIZE_MULT,
            "ai_max_automated_reviews_per_week": self.AI_MAX_AUTOMATED_REVIEWS_PER_WEEK,
            "ai_entry_review_cooldown_seconds": self.AI_ENTRY_REVIEW_COOLDOWN_SECONDS,
            "ai_exit_review_cooldown_seconds": self.AI_EXIT_REVIEW_COOLDOWN_SECONDS,
            "ai_post_trade_review_enabled": self.AI_POST_TRADE_REVIEW_ENABLED,
            "missing_tp_profit_lock_usd": self.MISSING_TP_PROFIT_LOCK_USD,
            "use_virtual_bankroll": self.use_virtual_bankroll,
            "virtual_bankroll": self.VIRTUAL_BANKROLL,
            "virtual_bankroll_floor": self.VIRTUAL_BANKROLL_FLOOR,
            "virtual_risk_per_trade": self.VIRTUAL_RISK_PER_TRADE,
            "trailing_stop_enabled": self.TRAILING_STOP_ENABLED,
            "trailing_stop_activation_atr": self.TRAILING_STOP_ACTIVATION_ATR,
            "trailing_stop_distance_atr": self.TRAILING_STOP_DISTANCE_ATR,
            "poll_interval": self.POLL_INTERVAL,
            "candle_refresh_min_seconds": self.CANDLE_REFRESH_MIN_SECONDS,
            "price_cache_ttl_seconds": self.PRICE_CACHE_TTL_SECONDS,
            "api_error_cooldown_seconds": self.API_ERROR_COOLDOWN_SECONDS,
            "auto_start_dashboard": self.AUTO_START_DASHBOARD,
            "dashboard_url": self.dashboard_url,
            "soul_path": self.SOUL_PATH,
            "skills_path": self.SKILLS_PATH,
            "strategy_docs_path": self.STRATEGY_DOCS_PATH,
            "strategy_cards_path": self.STRATEGY_CARDS_PATH,
        }


config = Config()
config.apply_runtime_profiles()
