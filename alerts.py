"""
alerts.py — Telegram push alerts for SmartTrader.

Silent no-op if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set, so it's
safe to call from anywhere. Import and call:

    from alerts import send_alert
    send_alert("Bot started", level="info")
    send_alert("Daily loss limit hit, pausing", level="critical")

Levels just prepend an emoji; message still goes through. Network errors
are swallowed — alerts must never crash the caller.

Set up once:
    1. Talk to @BotFather on Telegram, create a bot, copy the token.
    2. Send a message to your new bot, then visit
         https://api.telegram.org/bot<TOKEN>/getUpdates
       to find your chat_id (it's the "chat":{"id":...} field).
    3. Put both in .env:
         TELEGRAM_BOT_TOKEN=123456:ABC...
         TELEGRAM_CHAT_ID=987654321
"""

from __future__ import annotations

import logging
import os
from typing import Literal

import requests

logger = logging.getLogger("alerts")

Level = Literal["info", "success", "warning", "critical", "trade"]

_EMOJI: dict[str, str] = {
    "info":     "ℹ️",
    "success":  "✅",
    "warning":  "⚠️",
    "critical": "🚨",
    "trade":    "💹",
}

# Tiny in-process dedupe so the same alert doesn't spam when a loop fires it
# every second. Keyed by (level, message), value is last-sent monotonic time.
_recent: dict[tuple[str, str], float] = {}
_DEDUPE_SECONDS = 30.0


def _credentials() -> tuple[str, str] | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return None
    return token, chat_id


def alerts_configured() -> bool:
    """True iff Telegram credentials are present."""
    return _credentials() is not None


def send_alert(message: str, level: Level = "info", *, silent: bool = False) -> bool:
    """Send a Telegram message. Returns True on success, False on failure or no-op.

    ``silent=True`` sends without a notification sound (useful for low-priority).
    """
    import time

    creds = _credentials()
    if creds is None:
        return False

    key = (level, message)
    now = time.monotonic()
    last = _recent.get(key)
    if last is not None and (now - last) < _DEDUPE_SECONDS:
        return False
    _recent[key] = now

    token, chat_id = creds
    emoji = _EMOJI.get(level, "•")
    text = f"{emoji} *SmartTrader* — {message}"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_notification": silent,
            },
            timeout=5,
        )
        if resp.status_code >= 400:
            logger.warning("Telegram alert failed (%s): %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as exc:  # network, DNS, timeout, anything
        logger.warning("Telegram alert error: %s", exc)
        return False


def send_alert_safe(*args, **kwargs) -> None:
    """Fire-and-forget wrapper that can't raise. Use from crash handlers."""
    try:
        send_alert(*args, **kwargs)
    except Exception:
        pass
