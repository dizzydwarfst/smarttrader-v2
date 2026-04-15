"""
news_filter.py — Economic News Filter

Prevents the bot from trading during high-impact news events
like Fed rate decisions, NFP reports, and CPI releases.

How it works:
1. Fetches economic calendar data from a free API
2. Checks if any high-impact event is within the blackout window
3. If yes → tells the bot to stop trading until the window passes

This prevents getting destroyed by surprise volatility spikes.
"""

import logging
import requests
from datetime import datetime, timedelta, timezone
from config import config

logger = logging.getLogger("SmartTrader")


# High-impact events that affect our instruments
# XAU_USD and XAG_USD are affected by USD news, Fed, inflation.
# Added FX majors broaden the watch list to EUR, GBP, and AUD events too.
WATCHED_CURRENCIES = {"USD", "JPY", "EUR", "GBP", "AUD"}

# Event keywords that are high-impact
HIGH_IMPACT_KEYWORDS = [
    "interest rate", "fed", "fomc", "nonfarm", "non-farm", "nfp",
    "cpi", "inflation", "gdp", "employment", "unemployment",
    "retail sales", "ppi", "pce", "consumer confidence",
    "bank of japan", "boj", "monetary policy",
    "ecb", "european central bank",
    "boe", "bank of england",
    "rba", "reserve bank of australia",
    "trade balance", "manufacturing pmi",
    "services pmi", "employment change",
]


class NewsFilter:
    """Checks economic calendar and blocks trading during high-impact events."""

    def __init__(self):
        self.blackout_before = config.NEWS_BLACKOUT_BEFORE  # minutes
        self.blackout_after = config.NEWS_BLACKOUT_AFTER    # minutes
        self.cached_events = []
        self.last_fetch = None
        self.fetch_interval = timedelta(hours=1)  # Re-fetch every hour
        self.is_blocked = False
        self.block_reason = ""
        self.advisory_reason = ""
        self.last_source = "fallback"

    def can_trade(self):
        """
        Check if trading is allowed right now.
        Returns (bool, str) — (allowed, reason if blocked)
        """
        if not config.NEWS_FILTER_ENABLED:
            self.is_blocked = False
            self.block_reason = ""
            self.advisory_reason = ""
            return True, "News filter disabled"

        # Refresh calendar if needed
        self._refresh_calendar()
        training_bypass_active = config.is_practice and not config.DAILY_LOSS_LIMIT_ENABLED

        now = datetime.utcnow()

        for event in self.cached_events:
            event_time = event.get("time")
            if not event_time:
                continue

            blackout_start = event_time - timedelta(minutes=self.blackout_before)
            blackout_end = event_time + timedelta(minutes=self.blackout_after)

            if blackout_start <= now <= blackout_end:
                blackout_reason = f"📰 News blackout: {event['title']} at {event_time.strftime('%H:%M UTC')}"
                if training_bypass_active:
                    self.is_blocked = False
                    self.block_reason = ""
                    advisory_reason = (
                        "🎓 Training mode (practice): ignoring news blackout for "
                        f"{event['title']} at {event_time.strftime('%H:%M UTC')}"
                    )
                    if advisory_reason != self.advisory_reason:
                        logger.info(advisory_reason)
                    self.advisory_reason = advisory_reason
                    return True, advisory_reason

                self.is_blocked = True
                self.block_reason = blackout_reason
                self.advisory_reason = ""
                logger.warning(self.block_reason)
                return False, self.block_reason

        self.is_blocked = False
        self.block_reason = ""
        self.advisory_reason = ""
        return True, "No upcoming high-impact news"

    def _refresh_calendar(self):
        """Fetch economic calendar data if cache is stale."""
        now = datetime.utcnow()

        if self.last_fetch and (now - self.last_fetch) < self.fetch_interval:
            return  # Cache is fresh

        try:
            self.cached_events = self._fetch_calendar()
            self.last_fetch = now
            if self.cached_events:
                logger.info(f"  📰 Loaded {len(self.cached_events)} upcoming high-impact events")
        except Exception as e:
            logger.warning(f"  📰 Could not fetch news calendar: {e}")
            # Keep old cache if fetch fails

    def _fetch_calendar(self):
        """
        Fetch economic calendar from free API.
        Falls back to a static schedule of known recurring events.
        """
        events = []
        self.last_source = "fallback"

        if config.NEWS_CALENDAR_SOURCE == "tradingeconomics":
            try:
                events.extend(self._fetch_tradingeconomics_calendar())
                if events:
                    self.last_source = "tradingeconomics"
            except Exception as e:
                logger.warning(f"  📰 TradingEconomics fetch failed: {e}")

        # Try fetching from a free economic calendar API
        try:
            # Using nager.at for public holidays as a basic filter
            # For production, you'd use ForexFactory, Investing.com API, or similar
            today = datetime.utcnow().strftime("%Y-%m-%d")
            url = f"https://date.nager.at/api/v3/publicholidays/{datetime.utcnow().year}/US"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                holidays = response.json()
                for h in holidays:
                    holiday_date = datetime.strptime(h["date"], "%Y-%m-%d")
                    if holiday_date.date() == datetime.utcnow().date():
                        events.append({
                            "title": f"US Holiday: {h['name']} (low liquidity)",
                            "time": holiday_date.replace(hour=13, minute=0),
                            "currency": "USD",
                            "impact": "high",
                        })
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.debug(f"Holiday calendar fetch failed: {exc}")

        # Add known recurring high-impact events
        events.extend(self._get_recurring_events())

        # Filter to today and tomorrow only
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=24)
        events = [e for e in events if e.get("time") and now - timedelta(hours=1) <= e["time"] <= cutoff]

        unique_events = {}
        for event in events:
            event_time = event.get("time")
            if not event_time:
                continue
            unique_key = (
                event.get("title", ""),
                event_time.isoformat(),
                event.get("currency", ""),
            )
            unique_events.setdefault(unique_key, event)

        return sorted(unique_events.values(), key=lambda item: item["time"])

    def _fetch_tradingeconomics_calendar(self):
        response = requests.get(
            "https://api.tradingeconomics.com/calendar",
            params={"c": config.TRADINGECONOMICS_API_KEY},
            headers={"Accept": "application/json"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        now = datetime.utcnow()
        cutoff = now + timedelta(hours=24)
        events = []

        for item in payload:
            event_time = self._parse_te_datetime(item.get("Date"))
            if not event_time:
                continue
            if not (now - timedelta(hours=1) <= event_time <= cutoff):
                continue

            currency = (item.get("Currency") or "").upper()
            country = (item.get("Country") or "").lower()
            if not currency:
                if "united states" in country:
                    currency = "USD"
                elif "japan" in country:
                    currency = "JPY"
                elif "euro" in country:
                    currency = "EUR"
                elif "united kingdom" in country or country == "uk":
                    currency = "GBP"
                elif "australia" in country:
                    currency = "AUD"

            title = item.get("Event") or item.get("Category") or "Economic event"
            importance = self._parse_importance(item.get("Importance"))

            if currency not in WATCHED_CURRENCIES:
                continue
            if importance < 2 and not self._is_high_impact_title(title):
                continue

            events.append({
                "title": title,
                "time": event_time,
                "currency": currency,
                "impact": "high" if importance >= 2 else "medium",
                "source": "TradingEconomics",
            })

        return events

    def _parse_te_datetime(self, value):
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(str(value), fmt)
                except ValueError:
                    continue
        return None

    def _parse_importance(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _is_high_impact_title(self, title):
        lowered = (title or "").lower()
        return any(keyword in lowered for keyword in HIGH_IMPACT_KEYWORDS)

    def _get_recurring_events(self):
        """
        Generate known recurring economic events.
        These are approximate times — real implementation would use a proper calendar API.
        """
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        events = []

        weekday = now.weekday()  # 0=Monday

        # FOMC — usually 8 meetings per year, Wed at 18:00 UTC
        # We'll add a Wednesday check as a conservative approach
        if weekday == 2:  # Wednesday
            events.append({
                "title": "Possible FOMC Decision Day",
                "time": today.replace(hour=18, minute=0),
                "currency": "USD",
                "impact": "high",
            })

        # NFP — First Friday of each month at 12:30 UTC
        if weekday == 4 and now.day <= 7:
            events.append({
                "title": "Non-Farm Payrolls (NFP)",
                "time": today.replace(hour=12, minute=30),
                "currency": "USD",
                "impact": "high",
            })

        # CPI — Usually around 12th-15th of month at 12:30 UTC
        if 12 <= now.day <= 15 and weekday < 5:
            events.append({
                "title": "Possible CPI Release",
                "time": today.replace(hour=12, minute=30),
                "currency": "USD",
                "impact": "high",
            })

        # BoJ — Usually meets 8 times per year
        # Approximate: around the 18th-20th of certain months
        if 18 <= now.day <= 20 and weekday < 5:
            events.append({
                "title": "Possible BoJ Decision",
                "time": today.replace(hour=3, minute=0),
                "currency": "JPY",
                "impact": "high",
            })

        if weekday == 1 and now.day <= 7:
            events.append({
                "title": "Possible RBA Decision",
                "time": today.replace(hour=3, minute=30),
                "currency": "AUD",
                "impact": "high",
            })

        if weekday == 3 and now.day <= 7:
            events.append({
                "title": "Possible ECB Decision",
                "time": today.replace(hour=12, minute=15),
                "currency": "EUR",
                "impact": "high",
            })
            events.append({
                "title": "Possible BoE Decision",
                "time": today.replace(hour=12, minute=0),
                "currency": "GBP",
                "impact": "high",
            })

        return events

    def get_status(self):
        """For the dashboard API."""
        return {
            "enabled": config.NEWS_FILTER_ENABLED,
            "is_blocked": self.is_blocked,
            "block_reason": self.block_reason,
            "advisory_reason": self.advisory_reason,
            "training_bypass_active": config.is_practice and not config.DAILY_LOSS_LIMIT_ENABLED,
            "upcoming_events": [
                {
                    "title": e["title"],
                    "time": e["time"].isoformat() if e.get("time") else None,
                    "currency": e.get("currency", ""),
                    "impact": e.get("impact", ""),
                }
                for e in self.cached_events[:5]
            ],
            "blackout_before_mins": self.blackout_before,
            "blackout_after_mins": self.blackout_after,
            "source": self.last_source,
        }
