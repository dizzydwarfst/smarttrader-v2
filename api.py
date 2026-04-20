"""
api.py - SmartTrader dashboard and SPA server.

Run this alongside the bot:
    python api.py

The API serves both the trading bot endpoints and the React frontend build
when it exists. If the frontend build has not been generated yet, it falls
back to the legacy dashboard.html page.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

from ai_advisor import AIAdvisor
from config import config
from news_filter import NewsFilter
from serialization_utils import make_json_safe
from strategy_library import StrategyLibrary
from trade_journal import TradeJournal
from trading_memory import TradingMemory
from trading_profiles import PROFILES, read_command, write_command

RECONCILE_MIN_INTERVAL_SECONDS = 5.0
_last_reconcile_request = 0.0


def _request_reconcile(force: bool = False) -> bool:
    """Queue a reconcile command for the bot's next loop tick.

    Throttled so a burst of dashboard requests doesn't flood the command file.
    Skips queuing if another command is still unacknowledged, to avoid
    overwriting it (write_command replaces the pending command).
    """
    global _last_reconcile_request
    now = time.monotonic()
    if not force and (now - _last_reconcile_request) < RECONCILE_MIN_INTERVAL_SECONDS:
        return False
    if read_command() is not None:
        return False
    _last_reconcile_request = now
    try:
        write_command("reconcile")
        return True
    except Exception as exc:
        logger.debug(f"Could not queue reconcile command: {exc}")
        return False

logger = logging.getLogger("Dashboard")

APP_DIR = Path(__file__).parent
LEGACY_DASHBOARD_PATH = APP_DIR / "dashboard.html"
FRONTEND_BUILD_DIR = APP_DIR / "frontend" / "build"
FRONTEND_INDEX_PATH = FRONTEND_BUILD_DIR / "index.html"

app = FastAPI(title="SmartTrader Dashboard API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        status_path = APP_DIR / status_path
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


def _frontend_build_ready() -> bool:
    return FRONTEND_INDEX_PATH.exists()


def _serve_frontend_entry():
    if _frontend_build_ready():
        return FileResponse(FRONTEND_INDEX_PATH)
    if LEGACY_DASHBOARD_PATH.exists():
        return HTMLResponse(LEGACY_DASHBOARD_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend build not found. Run the frontend build first.</h1>")


def _serve_frontend_path(full_path: str):
    if not _frontend_build_ready():
        return _serve_frontend_entry()

    candidate = (FRONTEND_BUILD_DIR / full_path).resolve()
    build_root = FRONTEND_BUILD_DIR.resolve()

    try:
        candidate.relative_to(build_root)
    except ValueError:
        return _serve_frontend_entry()

    if candidate.is_file():
        return FileResponse(candidate)

    return _serve_frontend_entry()


@app.get("/")
async def serve_dashboard():
    return _serve_frontend_entry()


@app.get("/api/config")
async def get_config():
    sync_runtime_control_settings()
    return _json_safe(config.to_dict())


@app.get("/api/status")
async def get_status():
    runtime = sync_runtime_control_settings()
    stats = journal.get_trade_stats(days=14)
    open_trades = journal.get_open_trades()
    if open_trades and runtime.get("bot_online"):
        _request_reconcile()
    open_positions = (
        journal.get_open_position_count()
        if hasattr(journal, "get_open_position_count")
        else len(open_trades)
    )
    daily_pnl = journal.get_daily_pnl()
    return _json_safe(
        {
            "timestamp": datetime.now().isoformat(),
            "trading_mode": runtime.get("trading_mode", config.TRADING_MODE),
            "bot_online": runtime.get("bot_online", False),
            "current_activity": runtime.get("current_activity", "Waiting for bot to connect..."),
            "last_scan_at": runtime.get("last_scan_at"),
            "account_nav": runtime.get("account_nav"),
            "balance": runtime.get("balance"),
            "unrealized_pnl": runtime.get("unrealized_pnl"),
            "open_positions": open_positions,
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
        }
    )


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


@app.get("/api/trades/open")
async def get_open_trades():
    return _json_safe(journal.get_open_trades())


@app.post("/api/trades/reconcile")
async def reconcile_trades():
    queued = _request_reconcile(force=True)
    return {
        "queued": queued,
        "open_trades": len(journal.get_open_trades()),
    }


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


@app.get("/api/learning/history")
async def get_learning_history(limit: int = 20):
    return _json_safe(journal.get_param_history(limit=limit))


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


@app.get("/api/chart/pnl")
async def get_pnl_chart(days: int = 14):
    trades = journal.get_recent_trades(days=days)
    trades.reverse()

    cumulative = 0
    data_points = []
    for trade in trades:
        cumulative += trade.get("pnl") or 0
        data_points.append(
            {
                "timestamp": trade.get("timestamp"),
                "pnl": trade.get("pnl"),
                "cumulative_pnl": cumulative,
                "instrument": trade.get("instrument"),
                "direction": trade.get("direction"),
                "exit_reason": trade.get("exit_reason"),
            }
        )
    return _json_safe(data_points)


@app.get("/api/profiles")
async def get_profiles():
    runtime = read_runtime_status()
    active = runtime.get("active_profile", "routine")
    profiles = {}
    for name, profile in PROFILES.items():
        profiles[name] = {
            "label": profile["label"],
            "description": profile["description"],
            "active": name == active,
            "settings": profile["settings"],
        }
    return _json_safe(profiles)


@app.post("/api/profile/activate")
async def activate_profile(body: dict):
    profile_name = body.get("profile", "").lower()
    if profile_name not in PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown profile: {profile_name}. Available: {list(PROFILES.keys())}",
        )
    write_command("activate_profile", {"profile": profile_name})
    return {
        "status": "ok",
        "message": f"Profile '{profile_name}' activation queued. Bot will switch on next scan.",
    }


@app.post("/api/settings")
async def update_settings(body: dict):
    allowed_keys = {
        "poll_interval",
        "bar_granularity",
        "risk_per_trade",
        "max_positions",
        "daily_loss_limit",
        "stop_loss_atr_mult",
        "take_profit_atr_mult",
        "spread_limit_mult",
        "strategies",
        "fast_ema",
        "slow_ema",
        "breakout_lookback",
        "news_filter_enabled",
        "learning_enabled",
        "daily_loss_limit_enabled",
        "min_trade_pnl",
        "reverse_mode",
    }
    settings = {}
    for key, value in body.items():
        if key.lower() in allowed_keys:
            settings[key.upper()] = value
    if not settings:
        raise HTTPException(
            status_code=400,
            detail=f"No valid settings provided. Allowed: {sorted(allowed_keys)}",
        )
    write_command("update_settings", settings)
    return {"status": "ok", "message": f"Settings update queued: {list(settings.keys())}"}


@app.post("/api/bot/pause")
async def pause_bot():
    write_command("pause")
    return {"status": "ok", "message": "Pause command queued."}


@app.post("/api/bot/resume")
async def resume_bot():
    write_command("resume")
    return {"status": "ok", "message": "Resume command queued."}


@app.post("/api/bot/close-all")
async def close_all_positions():
    write_command("close_all")
    return {"status": "ok", "message": "Close-all command queued."}


@app.post("/api/bot/training-mode")
async def set_training_mode(body: dict):
    enabled = bool(body.get("enabled", True))
    write_command("update_settings", {"DAILY_LOSS_LIMIT_ENABLED": not enabled})
    label = "ON (daily loss limit disabled)" if enabled else "OFF (daily loss limit enabled)"
    return {"status": "ok", "message": f"Training mode {label}"}


@app.post("/api/bot/reverse-mode")
async def set_reverse_mode(body: dict):
    enabled = bool(body.get("enabled", False))
    write_command("update_settings", {"REVERSE_MODE": enabled})
    return {"status": "ok", "message": f"Reverse mode {'ON' if enabled else 'OFF'}"}


@app.post("/api/bot/min-trade-pnl")
async def set_min_trade_pnl(body: dict):
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
    runtime = sync_runtime_control_settings()
    return _json_safe(runtime.get("activity_log", []))


@app.get("/api/bot/control-status")
async def get_control_status():
    runtime = sync_runtime_control_settings()
    return _json_safe(
        {
            "active_profile": runtime.get("active_profile", "routine"),
            "paused": runtime.get("paused", False),
            "bot_online": runtime.get("bot_online", False),
            "poll_interval": runtime.get("poll_interval", config.POLL_INTERVAL),
            "current_activity": runtime.get("current_activity", "Unknown"),
            "pending_command": read_command() is not None,
            "daily_loss_limit_enabled": runtime.get(
                "daily_loss_limit_enabled", config.DAILY_LOSS_LIMIT_ENABLED
            ),
            "reverse_mode": runtime.get("reverse_mode", config.REVERSE_MODE),
            "min_trade_pnl": runtime.get("min_trade_pnl", config.MIN_TRADE_PNL),
        }
    )


@app.get("/api/analytics/overview")
async def get_analytics_overview():
    sync_runtime_control_settings()
    return _json_safe(
        {
            "total_realized_pnl": journal.get_total_closed_pnl(),
            "stats_7d": journal.get_trade_stats(days=7),
            "stats_14d": journal.get_trade_stats(days=14),
            "stats_30d": journal.get_trade_stats(days=30),
            "stats_90d": journal.get_trade_stats(days=90),
        }
    )


@app.get("/api/analytics/daily-breakdown")
async def get_daily_breakdown(days: int = 30):
    trades = journal.get_recent_trades(days=days)
    daily = {}
    for trade in trades:
        timestamp = trade.get("closed_at") or trade.get("timestamp")
        if not timestamp:
            continue
        try:
            date_key = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        daily.setdefault(
            date_key,
            {"date": date_key, "pnl": 0, "trades": 0, "wins": 0, "losses": 0},
        )
        pnl = trade.get("pnl") or 0
        daily[date_key]["pnl"] += pnl
        daily[date_key]["trades"] += 1
        if pnl > 0:
            daily[date_key]["wins"] += 1
        elif pnl < 0:
            daily[date_key]["losses"] += 1

    result = sorted(daily.values(), key=lambda item: item["date"])
    cumulative = 0
    for entry in result:
        cumulative += entry["pnl"]
        entry["cumulative_pnl"] = cumulative
        entry["win_rate"] = entry["wins"] / entry["trades"] if entry["trades"] else 0
    return _json_safe(result)


@app.get("/api/analytics/hourly-performance")
async def get_hourly_performance(days: int = 30):
    return _json_safe(journal.get_hourly_performance(days=days))


@app.get("/api/analytics/instrument-breakdown")
async def get_instrument_breakdown(days: int = 30):
    trades = journal.get_recent_trades(days=days)
    instruments = {}
    for trade in trades:
        instrument = trade.get("instrument") or "Unknown"
        instruments.setdefault(
            instrument,
            {
                "instrument": instrument,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0,
                "total_hold_mins": 0,
            },
        )
        pnl = trade.get("pnl") or 0
        instruments[instrument]["pnl"] += pnl
        instruments[instrument]["trades"] += 1
        instruments[instrument]["total_hold_mins"] += trade.get("hold_duration_mins") or 0
        if pnl > 0:
            instruments[instrument]["wins"] += 1
        elif pnl < 0:
            instruments[instrument]["losses"] += 1

    result = []
    for instrument_data in instruments.values():
        total = instrument_data["trades"]
        meaningful = instrument_data["wins"] + instrument_data["losses"]
        instrument_data["win_rate"] = meaningful and instrument_data["wins"] / meaningful or 0
        instrument_data["avg_hold_mins"] = total and instrument_data["total_hold_mins"] / total or 0
        instrument_data["avg_pnl"] = total and instrument_data["pnl"] / total or 0
        result.append(instrument_data)

    result.sort(key=lambda item: item["pnl"], reverse=True)
    return _json_safe(result)


@app.get("/api/analytics/strategy-breakdown")
async def get_strategy_breakdown(days: int = 30):
    trades = journal.get_recent_trades(days=days)
    strategies = {}
    for trade in trades:
        strategy_name = trade.get("strategy_name") or "unlabeled"
        strategies.setdefault(
            strategy_name,
            {"strategy": strategy_name, "trades": 0, "wins": 0, "losses": 0, "pnl": 0},
        )
        pnl = trade.get("pnl") or 0
        strategies[strategy_name]["pnl"] += pnl
        strategies[strategy_name]["trades"] += 1
        if pnl > 0:
            strategies[strategy_name]["wins"] += 1
        elif pnl < 0:
            strategies[strategy_name]["losses"] += 1

    result = []
    for strategy_data in strategies.values():
        meaningful = strategy_data["wins"] + strategy_data["losses"]
        strategy_data["win_rate"] = meaningful and strategy_data["wins"] / meaningful or 0
        strategy_data["avg_pnl"] = (
            strategy_data["trades"] and strategy_data["pnl"] / strategy_data["trades"] or 0
        )
        result.append(strategy_data)

    result.sort(key=lambda item: item["pnl"], reverse=True)
    return _json_safe(result)


@app.get("/api/analytics/trade-distribution")
async def get_trade_distribution(days: int = 30):
    trades = journal.get_recent_trades(days=days)
    pnl_ranges = {
        "large_loss": 0,
        "small_loss": 0,
        "breakeven": 0,
        "small_win": 0,
        "large_win": 0,
    }
    direction_counts = {"BUY": 0, "SELL": 0}
    exit_reasons = {}

    for trade in trades:
        pnl = trade.get("pnl") or 0
        direction = trade.get("direction") or "BUY"
        exit_reason = trade.get("exit_reason") or "unknown"

        if pnl <= -5:
            pnl_ranges["large_loss"] += 1
        elif pnl < 0:
            pnl_ranges["small_loss"] += 1
        elif pnl == 0:
            pnl_ranges["breakeven"] += 1
        elif pnl < 5:
            pnl_ranges["small_win"] += 1
        else:
            pnl_ranges["large_win"] += 1

        direction_counts[direction] = direction_counts.get(direction, 0) + 1
        exit_reasons[exit_reason] = exit_reasons.get(exit_reason, 0) + 1

    return _json_safe(
        {
            "pnl_ranges": pnl_ranges,
            "direction_counts": direction_counts,
            "exit_reasons": exit_reasons,
            "total_trades": len(trades),
        }
    )


@app.get("/api/journal/notes")
async def get_journal_notes(limit: int = 50, offset: int = 0):
    return _json_safe(journal.get_journal_notes(limit=limit, offset=offset))


@app.get("/api/journal/notes/{note_id}")
async def get_journal_note(note_id: int):
    note = journal.get_journal_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _json_safe(note)


@app.post("/api/journal/notes", status_code=201)
async def create_journal_note(body: dict):
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    note_id = journal.create_journal_note(body)
    return {"status": "ok", "id": note_id}


@app.put("/api/journal/notes/{note_id}")
async def update_journal_note(note_id: int, body: dict):
    if not journal.update_journal_note(note_id, body):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "ok"}


@app.delete("/api/journal/notes/{note_id}")
async def delete_journal_note(note_id: int):
    if not journal.delete_journal_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "ok"}


@app.get("/api/journal/tags")
async def get_journal_tags():
    return _json_safe(journal.get_journal_tags())


@app.get("/api/journal/trades-for-linking")
async def get_trades_for_linking(days: int = 30):
    return _json_safe(journal.get_trades_for_linking(days=days))


@app.get("/{full_path:path}")
async def serve_frontend_routes(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_frontend_path(full_path)


if __name__ == "__main__":
    print(
        r"""
    SmartTrader Dashboard v3.0
    Open: http://localhost:8000
    """
    )
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        access_log=False,
        log_level="warning",
    )
