"""
api.py — Dashboard API Server

Run this ALONGSIDE the bot to get a visual dashboard:
    python api.py

Then open http://localhost:8000 in your browser.

Provides REST endpoints for the React dashboard to read:
- Trade history and performance stats
- Open positions
- Bot configuration
- Learning engine status
- AI advisor analysis
- News filter status
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from config import config
from trade_journal import TradeJournal
from ai_advisor import AIAdvisor
from news_filter import NewsFilter
from trading_memory import TradingMemory
from strategy_library import StrategyLibrary
from serialization_utils import make_json_safe
from trading_profiles import (
    write_command,
    list_profiles,
    get_profile,
    PROFILES,
    read_command,
)

logger = logging.getLogger("Dashboard")

app = FastAPI(title="SmartTrader Dashboard API", version="3.0")

# Allow dashboard to call API from browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
journal = TradeJournal()
memory = TradingMemory(
    soul_name=config.SOUL_PATH,
    skills_name=config.SKILLS_PATH,
)
strategy_library = StrategyLibrary()
advisor = AIAdvisor(journal, memory)
news_filter = NewsFilter()


def read_runtime_status():
    status_path = Path(config.BOT_STATUS_PATH)
    if not status_path.is_absolute():
        status_path = Path(__file__).parent / status_path
    if not status_path.exists():
        return {}

    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def sync_runtime_control_settings(runtime: dict | None = None):
    """Mirror runtime-only bot settings into this API subprocess."""
    runtime = read_runtime_status() if runtime is None else runtime

    if "daily_loss_limit_enabled" in runtime:
        config.DAILY_LOSS_LIMIT_ENABLED = bool(runtime["daily_loss_limit_enabled"])
    if "reverse_mode" in runtime:
        config.REVERSE_MODE = bool(runtime["reverse_mode"])
    if "min_trade_pnl" in runtime:
        try:
            config.MIN_TRADE_PNL = float(runtime["min_trade_pnl"])
        except (TypeError, ValueError):
            pass

    return runtime


def _json_safe(payload):
    return make_json_safe(payload)


# ─── Dashboard HTML ──────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML page."""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard file not found. Make sure dashboard.html is in the same folder.</h1>")


# ─── Config & Status ─────────────────────────────────────

@app.get("/api/config")
async def get_config():
    sync_runtime_control_settings()
    return _json_safe(config.to_dict())


@app.get("/api/status")
async def get_status():
    """Overall bot status."""
    runtime = sync_runtime_control_settings()
    stats = journal.get_trade_stats(days=14)
    open_trades = journal.get_open_trades()
    daily_pnl = journal.get_daily_pnl()
    return _json_safe({
        "timestamp": datetime.now().isoformat(),
        "trading_mode": runtime.get("trading_mode", config.TRADING_MODE),
        "bot_online": runtime.get("bot_online", False),
        "current_activity": runtime.get("current_activity", "Waiting for bot to connect..."),
        "last_scan_at": runtime.get("last_scan_at"),
        "account_nav": runtime.get("account_nav"),
        "balance": runtime.get("balance"),
        "unrealized_pnl": runtime.get("unrealized_pnl"),
        "open_positions": len(open_trades),
        "daily_pnl": daily_pnl,
        "total_trades_14d": stats["total"],
        "win_rate_14d": stats["win_rate"],
        "total_pnl_14d": stats["total_pnl"],
        "profit_factor_14d": stats["profit_factor"],
        "bankroll_context": runtime.get("bankroll_context", {}),
        "decision_factors": runtime.get("decision_factors", {}),
        "wait_reasons": runtime.get("wait_reasons", {}),
        "trade_readiness": runtime.get("trade_readiness", {}),
        "execution_status": runtime.get("execution_status", {}),
    })


@app.get("/api/news/status")
async def get_news_status():
    runtime = sync_runtime_control_settings()
    if runtime.get("news_filter"):
        return _json_safe(runtime["news_filter"])
    news_filter.can_trade()
    return _json_safe(news_filter.get_status())


@app.get("/api/decision/factors")
async def get_decision_factors():
    runtime = read_runtime_status()
    return _json_safe(runtime.get("decision_factors", {}))


@app.get("/api/memory")
async def get_memory_snapshot():
    return _json_safe(memory.get_snapshot())


@app.get("/api/strategy-library")
async def get_strategy_library_snapshot():
    return _json_safe(strategy_library.get_snapshot())


# ─── Trades ──────────────────────────────────────────────

@app.get("/api/trades/open")
async def get_open_trades():
    return _json_safe(journal.get_open_trades())


@app.get("/api/trades/recent")
async def get_recent_trades(days: int = 14):
    return _json_safe(journal.get_recent_trades(days=days))


@app.get("/api/trades/stats")
async def get_trade_stats(days: int = 14):
    sync_runtime_control_settings()
    return _json_safe(journal.get_trade_stats(days=days))


@app.get("/api/strategies/scorecard")
async def get_strategy_scorecard(days: int = 30, min_trades: int = 3):
    sync_runtime_control_settings()
    return _json_safe(journal.get_strategy_scorecard(days=days, min_trades=min_trades))


# ─── Learning Engine ─────────────────────────────────────

@app.get("/api/learning/history")
async def get_learning_history(limit: int = 20):
    return _json_safe(journal.get_param_history(limit=limit))


# ─── AI Advisor ──────────────────────────────────────────

@app.get("/api/ai/status")
async def get_ai_status():
    sync_runtime_control_settings()
    return _json_safe(advisor.get_status())


@app.get("/api/ai/analyze")
async def analyze_performance(days: int = 7):
    sync_runtime_control_settings()
    return _json_safe(advisor.analyze_performance(days=days))


@app.get("/api/ai/why-waiting")
async def explain_why_waiting(instrument: str | None = None):
    runtime = sync_runtime_control_settings()
    return _json_safe(advisor.explain_waiting(runtime_status=runtime, instrument=instrument))


@app.post("/api/ai/ask")
async def ask_ai(body: dict):
    question = body.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")
    return _json_safe(advisor.ask_question(question))


# ─── Performance Chart Data ──────────────────────────────

@app.get("/api/chart/pnl")
async def get_pnl_chart(days: int = 14):
    """Returns cumulative P&L data for charting."""
    trades = journal.get_recent_trades(days=days)
    trades.reverse()  # Oldest first

    cumulative = 0
    data_points = []
    for t in trades:
        cumulative += (t["pnl"] or 0)
        data_points.append({
            "timestamp": t["timestamp"],
            "pnl": t["pnl"],
            "cumulative_pnl": cumulative,
            "instrument": t["instrument"],
            "direction": t["direction"],
            "exit_reason": t["exit_reason"],
        })
    return _json_safe(data_points)


# ─── Bot Control ────────────────────────────────────────

@app.get("/api/profiles")
async def get_profiles():
    """List all available trading profiles."""
    runtime = read_runtime_status()
    active = runtime.get("active_profile", "routine")
    profiles = {}
    for name, p in PROFILES.items():
        profiles[name] = {
            "label": p["label"],
            "description": p["description"],
            "active": name == active,
            "settings": p["settings"],
        }
    return _json_safe(profiles)


@app.post("/api/profile/activate")
async def activate_profile(body: dict):
    """Switch the bot to a different trading profile."""
    profile_name = body.get("profile", "").lower()
    if profile_name not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {profile_name}. Available: {list(PROFILES.keys())}")
    write_command("activate_profile", {"profile": profile_name})
    return {"status": "ok", "message": f"Profile '{profile_name}' activation queued. Bot will switch on next scan."}


@app.post("/api/settings")
async def update_settings(body: dict):
    """Update individual bot settings at runtime."""
    allowed_keys = {
        "poll_interval", "bar_granularity", "risk_per_trade", "max_positions",
        "daily_loss_limit", "stop_loss_atr_mult", "take_profit_atr_mult",
        "spread_limit_mult", "strategies", "fast_ema", "slow_ema",
        "breakout_lookback", "news_filter_enabled", "learning_enabled",
        "daily_loss_limit_enabled", "min_trade_pnl", "reverse_mode",
    }
    settings = {}
    for key, value in body.items():
        if key.lower() in allowed_keys:
            settings[key.upper()] = value
    if not settings:
        raise HTTPException(status_code=400, detail=f"No valid settings provided. Allowed: {sorted(allowed_keys)}")
    write_command("update_settings", settings)
    return {"status": "ok", "message": f"Settings update queued: {list(settings.keys())}"}


@app.post("/api/bot/pause")
async def pause_bot():
    """Pause the bot (stops scanning, keeps running)."""
    write_command("pause")
    return {"status": "ok", "message": "Pause command queued."}


@app.post("/api/bot/resume")
async def resume_bot():
    """Resume the bot after pausing."""
    write_command("resume")
    return {"status": "ok", "message": "Resume command queued."}


@app.post("/api/bot/close-all")
async def close_all_positions():
    """Close all open positions immediately."""
    write_command("close_all")
    return {"status": "ok", "message": "Close-all command queued."}


@app.post("/api/bot/training-mode")
async def set_training_mode(body: dict):
    """Toggle the daily loss limit off for training, or back on for live-style runs."""
    enabled = bool(body.get("enabled", True))
    # training_mode ON  => daily loss limit DISABLED
    # training_mode OFF => daily loss limit ENABLED
    write_command("update_settings", {"DAILY_LOSS_LIMIT_ENABLED": (not enabled)})
    label = "ON (daily loss limit disabled)" if enabled else "OFF (daily loss limit enabled)"
    return {"status": "ok", "message": f"Training mode {label}"}


@app.post("/api/bot/reverse-mode")
async def set_reverse_mode(body: dict):
    """Toggle reverse mode — flips every BUY/SELL before execution."""
    enabled = bool(body.get("enabled", False))
    write_command("update_settings", {"REVERSE_MODE": enabled})
    return {"status": "ok", "message": f"Reverse mode {'ON' if enabled else 'OFF'}"}


@app.post("/api/bot/min-trade-pnl")
async def set_min_trade_pnl(body: dict):
    """Set the minimum |P&L| for a trade to count as a win or loss."""
    try:
        value = float(body.get("value", 1.0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="value must be a number")
    if value < 0:
        raise HTTPException(status_code=400, detail="value must be >= 0")
    write_command("update_settings", {"MIN_TRADE_PNL": value})
    return {"status": "ok", "message": f"Minimum trade P&L set to ${value:.2f}"}


@app.get("/api/bot/activity-log")
async def get_activity_log():
    """Get recent bot activity log entries."""
    runtime = sync_runtime_control_settings()
    return _json_safe(runtime.get("activity_log", []))


@app.get("/api/bot/control-status")
async def get_control_status():
    """Get current bot control state (profile, paused, etc.)."""
    runtime = sync_runtime_control_settings()
    return _json_safe({
        "active_profile": runtime.get("active_profile", "routine"),
        "paused": runtime.get("paused", False),
        "bot_online": runtime.get("bot_online", False),
        "poll_interval": runtime.get("poll_interval", config.POLL_INTERVAL),
        "current_activity": runtime.get("current_activity", "Unknown"),
        "pending_command": read_command() is not None,
        # Read toggle state from the runtime status file the bot writes,
        # not from this subprocess's own stale config object.
        "daily_loss_limit_enabled": runtime.get(
            "daily_loss_limit_enabled", config.DAILY_LOSS_LIMIT_ENABLED
        ),
        "reverse_mode": runtime.get("reverse_mode", config.REVERSE_MODE),
        "min_trade_pnl": runtime.get("min_trade_pnl", config.MIN_TRADE_PNL),
    })


# ─── Run Server ──────────────────────────────────────────

if __name__ == "__main__":
    print(r"""
    ╔═══════════════════════════════════════╗
    ║   📊 SmartTrader Dashboard v3.0       ║
    ║   Open: http://localhost:8000         ║
    ╚═══════════════════════════════════════╝
    """)
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        access_log=False,
        log_level="warning",
    )
