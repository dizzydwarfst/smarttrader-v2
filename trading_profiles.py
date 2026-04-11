"""
trading_profiles.py -- Preset trading profiles for runtime switching.

Profiles let you change the bot's behavior on the fly:
  - conservative: slow, safe, fewer trades
  - routine: balanced default
  - aggressive: faster scans, more risk, more positions
  - scalper: ultra-fast M1 candles, max positions, quick in-and-out

Usage:
  POST /api/profile/activate  {"profile": "aggressive"}
  POST /api/settings           {"poll_interval": 10, "max_positions": 5}
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("Profiles")

# ─── Profile definitions ────────────────────────────────────

PROFILES = {
    "conservative": {
        "label": "Conservative",
        "description": "Slow and safe. Fewer trades, wider stops, lower risk.",
        "settings": {
            "POLL_INTERVAL": 60,
            "BAR_GRANULARITY": "H1",
            "RISK_PER_TRADE": 0.01,
            "MAX_POSITIONS": 2,
            "DAILY_LOSS_LIMIT": 0.03,
            "STOP_LOSS_ATR_MULT": 2.0,
            "TAKE_PROFIT_ATR_MULT": 4.0,
            "SPREAD_LIMIT_MULT": 0.8,
            "STRATEGIES": ["ema", "vwap_bounce"],
        },
    },
    "routine": {
        "label": "Routine",
        "description": "Balanced default. Standard risk, M15 candles, steady pace.",
        "settings": {
            "POLL_INTERVAL": 30,
            "BAR_GRANULARITY": "M15",
            "RISK_PER_TRADE": 0.02,
            "MAX_POSITIONS": 3,
            "DAILY_LOSS_LIMIT": 0.05,
            "STOP_LOSS_ATR_MULT": 1.5,
            "TAKE_PROFIT_ATR_MULT": 3.0,
            "SPREAD_LIMIT_MULT": 1.0,
            "STRATEGIES": ["ema", "breakout", "vwap_bounce", "rsi_exhaustion"],
        },
    },
    "aggressive": {
        "label": "Aggressive",
        "description": "More risk, faster scans, more positions. Trades every 5 min candle.",
        "settings": {
            "POLL_INTERVAL": 15,
            "BAR_GRANULARITY": "M5",
            "RISK_PER_TRADE": 0.03,
            "MAX_POSITIONS": 5,
            "DAILY_LOSS_LIMIT": 0.08,
            "STOP_LOSS_ATR_MULT": 1.2,
            "TAKE_PROFIT_ATR_MULT": 2.5,
            "SPREAD_LIMIT_MULT": 1.5,
            "STRATEGIES": ["ema", "breakout", "vwap_bounce", "rsi_exhaustion", "momentum_scalp"],
        },
    },
    "scalper": {
        "label": "Scalper",
        "description": "Ultra-fast M1 candles. Max positions, quick in-and-out trades.",
        "settings": {
            "POLL_INTERVAL": 10,
            "BAR_GRANULARITY": "M1",
            "RISK_PER_TRADE": 0.015,
            "MAX_POSITIONS": 8,
            "DAILY_LOSS_LIMIT": 0.06,
            "STOP_LOSS_ATR_MULT": 1.0,
            "TAKE_PROFIT_ATR_MULT": 1.5,
            "SPREAD_LIMIT_MULT": 2.0,
            "STRATEGIES": ["ema", "momentum_scalp", "breakout"],
        },
    },
}

# ─── Command file for bot <-> API communication ─────────────

COMMAND_FILE = Path(__file__).parent / "runtime_commands.json"


def write_command(command: str, payload: dict | None = None):
    """Write a command for the bot to pick up on its next loop iteration."""
    cmd = {
        "command": command,
        "payload": payload or {},
        "timestamp": datetime.now().isoformat(),
        "acknowledged": False,
    }
    temp = COMMAND_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(cmd, indent=2), encoding="utf-8")
    temp.replace(COMMAND_FILE)
    logger.info(f"Command queued: {command}")
    return cmd


def read_command():
    """Read pending command (returns None if no unacknowledged command)."""
    if not COMMAND_FILE.exists():
        return None
    try:
        data = json.loads(COMMAND_FILE.read_text(encoding="utf-8"))
        if data.get("acknowledged"):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def acknowledge_command():
    """Mark the current command as processed."""
    if not COMMAND_FILE.exists():
        return
    try:
        data = json.loads(COMMAND_FILE.read_text(encoding="utf-8"))
        data["acknowledged"] = True
        data["acknowledged_at"] = datetime.now().isoformat()
        COMMAND_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        pass


def get_profile(name: str) -> dict | None:
    """Get a profile by name."""
    return PROFILES.get(name.lower())


def list_profiles() -> dict:
    """Return all profiles with their descriptions."""
    return {
        name: {"label": p["label"], "description": p["description"]}
        for name, p in PROFILES.items()
    }
