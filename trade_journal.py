"""
trade_journal.py — SQLite-based trade logging system

Every trade the bot makes gets recorded here with full details.
This data feeds the learning engine so the bot can improve over time.
Also logs parameter changes so you can see exactly what the bot learned.
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from config import config
from serialization_utils import make_json_safe

logger = logging.getLogger("SmartTrader")


class TradeJournal:
    """Records trades and parameter changes to SQLite."""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        self._create_tables()

    def _get_conn(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            logger.debug("Could not enable WAL mode for %s", self.db_path)
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _decode_json_field(self, raw_value):
        """Parse stored JSON metadata back into Python objects."""
        if raw_value in (None, ""):
            return None
        if isinstance(raw_value, (dict, list)):
            return raw_value

        try:
            return make_json_safe(json.loads(raw_value))
        except (json.JSONDecodeError, TypeError):
            return raw_value

    def _fetch_trade_rows(self, cursor):
        columns = [desc[0] for desc in cursor.description]
        trades = []
        for row in cursor.fetchall():
            trade = dict(zip(columns, row))
            trade["strategy_details"] = self._decode_json_field(
                trade.get("strategy_details")
            )
            trade["ai_payload"] = self._decode_json_field(
                trade.get("ai_payload")
            )
            trades.append(trade)
        return trades

    def _fetch_rows_as_dicts(self, cursor):
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _create_tables(self):
        """Create tables if they don't exist yet."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # ─── Trades table ────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                oanda_trade_id TEXT,
                direction TEXT NOT NULL,        -- 'BUY' or 'SELL'
                entry_price REAL NOT NULL,
                exit_price REAL,                -- NULL while trade is open
                quantity REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                pnl REAL,                       -- profit/loss in USD
                pnl_percent REAL,               -- profit/loss as % of account
                hold_duration_mins INTEGER,     -- how long position was held
                exit_reason TEXT,               -- 'signal', 'stop_loss', 'take_profit', 'manual'
                fast_ema INTEGER,               -- EMA settings used for this trade
                slow_ema INTEGER,
                atr_at_entry REAL,              -- volatility when trade was opened
                market_regime TEXT,             -- 'trending', 'choppy', 'volatile'
                bankroll_mode TEXT,
                equity_reference REAL,
                broker_nav REAL,
                risk_pct_at_entry REAL,
                strategy_name TEXT,
                strategy_confidence TEXT,
                strategy_details TEXT,
                ai_mode TEXT,
                ai_action TEXT,
                ai_confidence TEXT,
                ai_size_mult REAL,
                ai_reason TEXT,
                ai_payload TEXT,
                status TEXT DEFAULT 'open',     -- 'open' or 'closed'
                notes TEXT                      -- any extra info
            )
        """)

        cursor.execute("PRAGMA table_info(trades)")
        trade_columns = {row[1] for row in cursor.fetchall()}
        if "oanda_trade_id" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN oanda_trade_id TEXT")
        if "strategy_name" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN strategy_name TEXT")
        if "strategy_confidence" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN strategy_confidence TEXT")
        if "strategy_details" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN strategy_details TEXT")
        if "bankroll_mode" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN bankroll_mode TEXT")
        if "equity_reference" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN equity_reference REAL")
        if "broker_nav" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN broker_nav REAL")
        if "risk_pct_at_entry" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN risk_pct_at_entry REAL")
        if "ai_mode" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_mode TEXT")
        if "ai_action" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_action TEXT")
        if "ai_confidence" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_confidence TEXT")
        if "ai_size_mult" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_size_mult REAL")
        if "ai_reason" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_reason TEXT")
        if "ai_payload" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_payload TEXT")
        if "closed_at" not in trade_columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN closed_at TEXT")

        # ─── Parameter changes table ─────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS param_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                parameter TEXT NOT NULL,        -- which param changed
                old_value TEXT NOT NULL,
                new_value TEXT NOT NULL,
                reason TEXT,                    -- why it changed
                performance_before REAL,        -- win rate before change
                performance_after REAL          -- expected win rate after
            )
        """)

        # ─── Daily performance summary ───────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_pnl REAL,
                largest_win REAL,
                largest_loss REAL,
                avg_hold_mins REAL,
                market_regime TEXT
            )
        """)

        # ─── Learning state ─────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                tags TEXT,
                rating INTEGER DEFAULT 0,
                mood TEXT,
                lessons TEXT,
                mistakes TEXT,
                screenshot_url TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _normalize_tags(self, tags):
        if isinstance(tags, list):
            return ",".join(str(tag).strip() for tag in tags if str(tag).strip())
        return (tags or "").strip()

    # ─── Trade Recording ─────────────────────────────────

    def open_trade(self, instrument, direction, entry_price, quantity,
                   stop_loss, take_profit, fast_ema, slow_ema,
                   atr_at_entry, market_regime, oanda_trade_id=None,
                   strategy_name=None, strategy_confidence=None, strategy_details=None,
                   bankroll_mode=None, equity_reference=None, broker_nav=None,
                   risk_pct_at_entry=None, ai_mode=None, ai_action=None,
                   ai_confidence=None, ai_size_mult=None, ai_reason=None,
                   ai_payload=None, notes=None):
        """Record a new trade being opened. Returns the trade ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        strategy_details_json = (
            json.dumps(
                make_json_safe(strategy_details),
                ensure_ascii=False,
                allow_nan=False,
            )
            if strategy_details is not None else None
        )
        ai_payload_json = (
            json.dumps(
                make_json_safe(ai_payload),
                ensure_ascii=False,
                allow_nan=False,
            )
            if ai_payload is not None else None
        )

        cursor.execute("""
            INSERT INTO trades (
                timestamp, instrument, oanda_trade_id, direction, entry_price, quantity,
                stop_loss, take_profit, fast_ema, slow_ema,
                atr_at_entry, market_regime, bankroll_mode, equity_reference,
                broker_nav, risk_pct_at_entry, strategy_name, strategy_confidence,
                strategy_details, ai_mode, ai_action, ai_confidence,
                ai_size_mult, ai_reason, ai_payload, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """, (
            datetime.now().isoformat(),
            instrument, oanda_trade_id, direction, entry_price, quantity,
            stop_loss, take_profit, fast_ema, slow_ema,
            atr_at_entry, market_regime, bankroll_mode, equity_reference,
            broker_nav, risk_pct_at_entry, strategy_name, strategy_confidence,
            strategy_details_json, ai_mode, ai_action, ai_confidence,
            ai_size_mult, ai_reason, ai_payload_json, notes,
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(
            "Trade #%s opened: %s %s %s @ %s",
            trade_id,
            direction,
            quantity,
            instrument,
            entry_price,
        )
        return trade_id

    def close_trade(self, trade_id, exit_price, pnl, pnl_percent,
                    exit_reason, notes=""):
        """Record a trade being closed."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Calculate hold duration
        cursor.execute("SELECT timestamp FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        if row:
            entry_time = datetime.fromisoformat(row[0])
            hold_mins = int((datetime.now() - entry_time).total_seconds() / 60)
        else:
            hold_mins = 0

        cursor.execute("""
            UPDATE trades SET
                exit_price = ?,
                pnl = ?,
                pnl_percent = ?,
                hold_duration_mins = ?,
                exit_reason = ?,
                status = 'closed',
                closed_at = ?,
                notes = ?
            WHERE id = ?
        """, (exit_price, pnl, pnl_percent, hold_mins, exit_reason, datetime.now().isoformat(), notes, trade_id))

        conn.commit()
        conn.close()

        emoji = "✅" if pnl >= 0 else "❌"
        logger.info(
            "%s Trade #%s closed: $%+.2f (%+.2f%%) - %s",
            emoji,
            trade_id,
            pnl,
            pnl_percent,
            exit_reason,
        )

    def revise_closed_trade(self, trade_id, exit_price, pnl, pnl_percent, exit_reason=None, notes=None):
        """Adjust P&L for an already closed trade without changing hold duration or status."""
        conn = self._get_conn()
        cursor = conn.cursor()

        updates = [
            "exit_price = ?",
            "pnl = ?",
            "pnl_percent = ?",
        ]
        values = [exit_price, pnl, pnl_percent]

        if exit_reason is not None:
            updates.append("exit_reason = ?")
            values.append(exit_reason)
        if notes is not None:
            updates.append("notes = ?")
            values.append(notes)

        values.append(trade_id)
        cursor.execute(
            f"UPDATE trades SET {', '.join(updates)} WHERE id = ?",
            values,
        )

        conn.commit()
        conn.close()

    def update_stop_loss(self, trade_id, new_stop_loss):
        """Update the stop-loss price on an open trade (e.g. trailing stop)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trades SET stop_loss = ? WHERE id = ? AND status = 'open'",
            (new_stop_loss, trade_id),
        )
        conn.commit()
        conn.close()

    # ─── Querying ────────────────────────────────────────

    def get_open_trades(self, instrument=None):
        """Get all currently open trades, optionally filtered by instrument."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if instrument:
            cursor.execute(
                "SELECT * FROM trades WHERE status = 'open' AND instrument = ?",
                (instrument,)
            )
        else:
            cursor.execute("SELECT * FROM trades WHERE status = 'open'")

        trades = self._fetch_trade_rows(cursor)
        conn.close()
        return trades

    def get_open_position_count(self):
        """Count live positions by instrument rather than raw trade rows."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT instrument) FROM trades WHERE status = 'open'")
        row = cursor.fetchone()
        conn.close()
        return int(row[0] or 0)

    def get_recent_trades(self, days=14, instrument=None):
        """Get closed trades from the last N days."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        if instrument:
            cursor.execute("""
                SELECT * FROM trades
                WHERE status = 'closed'
                  AND COALESCE(closed_at, timestamp) > ?
                  AND instrument = ?
                ORDER BY COALESCE(closed_at, timestamp) DESC
            """, (cutoff, instrument))
        else:
            cursor.execute("""
                SELECT * FROM trades
                WHERE status = 'closed'
                  AND COALESCE(closed_at, timestamp) > ?
                ORDER BY COALESCE(closed_at, timestamp) DESC
            """, (cutoff,))

        trades = self._fetch_trade_rows(cursor)
        conn.close()
        return trades

    def _summarize_trades(self, trades):
        """Calculate performance metrics for a list of closed trades.

        Trades with |pnl| < config.MIN_TRADE_PNL are treated as 'noise' and
        excluded from wins/losses/win-rate/profit-factor calculations. They
        still contribute to total P&L so the books stay honest.
        """
        if not trades:
            return {
                "total": 0,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "noise": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "total_pnl": 0,
                "avg_hold_mins": 0,
                "profit_factor": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "last_trade_at": None,
                "min_trade_pnl": config.MIN_TRADE_PNL,
            }

        min_pnl = config.MIN_TRADE_PNL
        # "Meaningful" trades = |pnl| >= min_pnl. Noise trades are skipped for win/loss.
        meaningful = [t for t in trades if abs(t["pnl"] or 0) >= min_pnl]
        noise_count = len(trades) - len(meaningful)
        wins = [t for t in meaningful if (t["pnl"] or 0) > 0]
        losses = [t for t in meaningful if (t["pnl"] or 0) < 0]
        total_wins = sum(t["pnl"] or 0 for t in wins)
        total_losses = abs(sum(t["pnl"] or 0 for t in losses))

        if total_losses > 0:
            profit_factor = total_wins / total_losses
        elif total_wins > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0

        # Risk-adjusted metrics
        pnl_values = [t["pnl"] or 0 for t in trades]
        avg_pnl = sum(pnl_values) / len(pnl_values)
        if len(pnl_values) > 1:
            import math
            variance = sum((p - avg_pnl) ** 2 for p in pnl_values) / (len(pnl_values) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 0
            sharpe = avg_pnl / std_dev if std_dev > 0 else 0

            downside_values = [p for p in pnl_values if p < 0]
            if downside_values:
                downside_var = sum(p ** 2 for p in downside_values) / len(downside_values)
                downside_std = math.sqrt(downside_var)
                sortino = avg_pnl / downside_std if downside_std > 0 else 0
            else:
                sortino = sharpe
        else:
            sharpe = 0
            sortino = 0

        meaningful_count = len(wins) + len(losses)
        win_rate = (len(wins) / meaningful_count) if meaningful_count > 0 else 0

        return {
            "total": len(trades),
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "noise": noise_count,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "total_pnl": sum(pnl_values),
            "avg_hold_mins": sum(t["hold_duration_mins"] or 0 for t in trades) / len(trades),
            "profit_factor": profit_factor,
            "largest_win": max(pnl_values, default=0),
            "largest_loss": min(pnl_values, default=0),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "last_trade_at": max((t["timestamp"] for t in trades), default=None),
            "min_trade_pnl": min_pnl,
        }

    def get_trade_stats(self, days=14):
        """Calculate performance stats for the learning engine."""
        trades = self.get_recent_trades(days=days)
        return self._summarize_trades(trades)

    def _scorecard_sort_tuple(self, row):
        profit_factor = row["profit_factor"]
        profit_factor_score = 999999.0 if profit_factor == float("inf") else profit_factor
        return (
            1 if row["eligible"] else 0,
            row["total_pnl"],
            profit_factor_score,
            row["win_rate"],
            row["trades"],
            row["avg_pnl"],
        )

    def _build_scorecard_rows(self, trades, group_fields, min_trades):
        grouped = {}
        for trade in trades:
            normalized = dict(trade)
            normalized["strategy_name"] = normalized.get("strategy_name") or "unlabeled"
            normalized["market_regime"] = normalized.get("market_regime") or "unknown"
            key = tuple(normalized.get(field) for field in group_fields)
            grouped.setdefault(key, []).append(normalized)

        rows = []
        for key, grouped_trades in grouped.items():
            summary = self._summarize_trades(grouped_trades)
            row = {field: key[idx] for idx, field in enumerate(group_fields)}
            row.update(summary)
            row["eligible"] = summary["trades"] >= min_trades
            rows.append(row)

        rows.sort(key=self._scorecard_sort_tuple, reverse=True)
        return rows

    def _pick_scorecard_leaders(self, rows, leader_group_fields):
        leaders = {}
        for row in rows:
            group_key = tuple(row.get(field) for field in leader_group_fields)
            current = leaders.get(group_key)
            if current is None or self._scorecard_sort_tuple(row) > self._scorecard_sort_tuple(current):
                leaders[group_key] = row

        ordered = list(leaders.values())
        ordered.sort(key=self._scorecard_sort_tuple, reverse=True)
        return ordered

    def get_strategy_scorecard(self, days=30, min_trades=3):
        """Summarize which strategies are performing best by market context."""
        trades = self.get_recent_trades(days=days)
        strategy_trades = []
        for trade in trades:
            normalized = dict(trade)
            normalized["strategy_name"] = normalized.get("strategy_name") or "unlabeled"
            normalized["market_regime"] = normalized.get("market_regime") or "unknown"
            strategy_trades.append(normalized)

        strategies = self._build_scorecard_rows(strategy_trades, ("strategy_name",), min_trades)
        by_instrument = self._build_scorecard_rows(strategy_trades, ("instrument", "strategy_name"), min_trades)
        by_regime = self._build_scorecard_rows(strategy_trades, ("market_regime", "strategy_name"), min_trades)
        by_instrument_regime = self._build_scorecard_rows(
            strategy_trades,
            ("instrument", "market_regime", "strategy_name"),
            min_trades,
        )

        return {
            "generated_at": datetime.now().isoformat(),
            "window_days": days,
            "min_trades": min_trades,
            "overall": self._summarize_trades(strategy_trades),
            "strategies": strategies,
            "leaders": {
                "overall": strategies[0] if strategies else None,
                "by_instrument": self._pick_scorecard_leaders(by_instrument, ("instrument",)),
                "by_regime": self._pick_scorecard_leaders(by_regime, ("market_regime",)),
                "by_instrument_regime": self._pick_scorecard_leaders(
                    by_instrument_regime,
                    ("instrument", "market_regime"),
                ),
            },
            "breakdowns": {
                "by_instrument": by_instrument,
                "by_regime": by_regime,
                "by_instrument_regime": by_instrument_regime,
            },
        }

    def get_daily_pnl(self):
        """Get today's total P&L (for daily loss limit check)."""
        conn = self._get_conn()
        cursor = conn.cursor()

        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COALESCE(SUM(pnl), 0) FROM trades
            WHERE status = 'closed' AND date(timestamp) = ?
        """, (today,))

        daily_pnl = cursor.fetchone()[0]
        conn.close()
        return daily_pnl

    def get_total_closed_pnl(self):
        """Return cumulative realized P&L across all closed trades."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(pnl), 0) FROM trades
            WHERE status = 'closed'
        """)
        total_pnl = cursor.fetchone()[0]
        conn.close()
        return total_pnl

    def get_hourly_performance(self, days=30):
        """Return win rate and average P&L grouped by hour of day (UTC)."""
        trades = self.get_recent_trades(days=days)
        hourly = {}
        for trade in trades:
            ts = trade.get("timestamp")
            if not ts:
                continue
            try:
                hour = datetime.fromisoformat(ts).hour
            except (ValueError, TypeError):
                continue
            if hour not in hourly:
                hourly[hour] = {"wins": 0, "losses": 0, "total_pnl": 0}
            pnl = trade.get("pnl", 0) or 0
            if pnl > 0:
                hourly[hour]["wins"] += 1
            else:
                hourly[hour]["losses"] += 1
            hourly[hour]["total_pnl"] += pnl

        result = {}
        for hour, data in sorted(hourly.items()):
            total = data["wins"] + data["losses"]
            result[hour] = {
                "trades": total,
                "win_rate": data["wins"] / total if total else 0,
                "avg_pnl": data["total_pnl"] / total if total else 0,
                "total_pnl": data["total_pnl"],
            }
        return result

    def get_journal_notes(self, limit=50, offset=0):
        """Return journal notes joined with trade context."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT jn.*, t.instrument, t.direction, t.pnl, t.strategy_name,
                   t.entry_price, t.exit_price, t.exit_reason, t.market_regime
            FROM journal_notes jn
            LEFT JOIN trades t ON jn.trade_id = t.id
            ORDER BY jn.timestamp DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        notes = self._fetch_rows_as_dicts(cursor)
        cursor.execute("SELECT COUNT(*) FROM journal_notes")
        total = cursor.fetchone()[0]
        conn.close()
        return {"notes": notes, "total": total}

    def get_journal_note(self, note_id):
        """Return one journal note by id with trade context."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT jn.*, t.instrument, t.direction, t.pnl, t.strategy_name,
                   t.entry_price, t.exit_price, t.exit_reason, t.market_regime
            FROM journal_notes jn
            LEFT JOIN trades t ON jn.trade_id = t.id
            WHERE jn.id = ?
        """, (note_id,))
        notes = self._fetch_rows_as_dicts(cursor)
        conn.close()
        return notes[0] if notes else None

    def create_journal_note(self, body):
        """Create a new journal note."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO journal_notes (
                trade_id, timestamp, title, content, tags, rating,
                mood, lessons, mistakes, screenshot_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            body.get("trade_id"),
            datetime.now().isoformat(),
            (body.get("title") or "").strip(),
            body.get("content", ""),
            self._normalize_tags(body.get("tags")),
            int(body.get("rating") or 0),
            body.get("mood", ""),
            body.get("lessons", ""),
            body.get("mistakes", ""),
            body.get("screenshot_url", ""),
        ))
        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return note_id

    def update_journal_note(self, note_id, body):
        """Update an existing journal note. Returns True when updated."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM journal_notes WHERE id = ?", (note_id,))
        if not cursor.fetchone():
            conn.close()
            return False

        cursor.execute("""
            UPDATE journal_notes SET
                trade_id = ?,
                title = ?,
                content = ?,
                tags = ?,
                rating = ?,
                mood = ?,
                lessons = ?,
                mistakes = ?,
                screenshot_url = ?
            WHERE id = ?
        """, (
            body.get("trade_id"),
            (body.get("title") or "").strip(),
            body.get("content", ""),
            self._normalize_tags(body.get("tags")),
            int(body.get("rating") or 0),
            body.get("mood", ""),
            body.get("lessons", ""),
            body.get("mistakes", ""),
            body.get("screenshot_url", ""),
            note_id,
        ))
        conn.commit()
        conn.close()
        return True

    def delete_journal_note(self, note_id):
        """Delete a journal note. Returns True when deleted."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM journal_notes WHERE id = ?", (note_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_journal_tags(self):
        """Return all unique note tags."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT tags FROM journal_notes WHERE tags IS NOT NULL AND tags != ''")
        all_tags = set()
        for (tags_string,) in cursor.fetchall():
            for tag in (tags_string or "").split(","):
                cleaned = tag.strip()
                if cleaned:
                    all_tags.add(cleaned)
        conn.close()
        return sorted(all_tags)

    def get_trades_for_linking(self, days=30):
        """Return recent trades in a lightweight shape for note linking."""
        trades = self.get_recent_trades(days=days)
        return [
            {
                "id": trade.get("id"),
                "instrument": trade.get("instrument"),
                "direction": trade.get("direction"),
                "pnl": trade.get("pnl"),
                "strategy_name": trade.get("strategy_name"),
                "timestamp": trade.get("closed_at") or trade.get("timestamp"),
                "exit_reason": trade.get("exit_reason"),
            }
            for trade in trades
        ]

    # ─── Parameter Change Logging ────────────────────────

    def log_param_change(self, parameter, old_value, new_value, reason,
                         perf_before=None, perf_after=None):
        """Log when the learning engine changes a parameter."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO param_changes
            (timestamp, parameter, old_value, new_value, reason,
             performance_before, performance_after)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            parameter, str(old_value), str(new_value), reason,
            perf_before, perf_after
        ))

        conn.commit()
        conn.close()

        logger.info(
            "Parameter changed: %s %s -> %s (%s)",
            parameter,
            old_value,
            new_value,
            reason,
        )

    def get_param_history(self, parameter=None, limit=20):
        """Get history of parameter changes."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if parameter:
            cursor.execute("""
                SELECT * FROM param_changes
                WHERE parameter = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (parameter, limit))
        else:
            cursor.execute("""
                SELECT * FROM param_changes
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        changes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return changes

    def get_latest_param_values(self):
        """Return the latest learned value for each parameter."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT parameter, new_value, timestamp
            FROM param_changes
            ORDER BY timestamp DESC
        """)

        latest = {}
        for parameter, new_value, timestamp in cursor.fetchall():
            if parameter not in latest:
                latest[parameter] = {
                    "value": new_value,
                    "timestamp": timestamp,
                }

        conn.close()
        return latest

    def get_learning_state(self):
        """Return persisted learning-engine state."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT state_key, state_value FROM learning_state")
        state = {key: value for key, value in cursor.fetchall()}
        conn.close()
        return state

    def set_learning_state(self, last_run=None, last_trade_count=None):
        """Persist learning-engine state so it survives restarts."""
        updates = {}
        if last_run is not None:
            updates["last_run"] = (
                last_run.isoformat() if hasattr(last_run, "isoformat") else str(last_run)
            )
        if last_trade_count is not None:
            updates["last_trade_count"] = str(int(last_trade_count))

        if not updates:
            return

        conn = self._get_conn()
        cursor = conn.cursor()
        updated_at = datetime.now().isoformat()

        for key, value in updates.items():
            cursor.execute("""
                INSERT INTO learning_state (state_key, state_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    state_value = excluded.state_value,
                    updated_at = excluded.updated_at
            """, (key, value, updated_at))

        conn.commit()
        conn.close()

    # ─── Reporting ───────────────────────────────────────

    def print_performance_report(self, days=14):
        """Print a nice performance summary to console."""
        stats = self.get_trade_stats(days=days)

        print(f"\n{'='*50}")
        print(f"  📊 Performance Report (last {days} days)")
        print(f"{'='*50}")
        print(f"  Total trades:    {stats['total']}")
        print(f"  Wins / Losses:   {stats['wins']} / {stats['losses']}")
        print(f"  Win rate:        {stats['win_rate']:.1%}")
        print(f"  Total P&L:       ${stats['total_pnl']:+.2f}")
        print(f"  Avg P&L/trade:   ${stats['avg_pnl']:+.2f}")
        print(f"  Profit factor:   {stats['profit_factor']:.2f}")
        print(f"  Largest win:     ${stats['largest_win']:+.2f}")
        print(f"  Largest loss:    ${stats['largest_loss']:+.2f}")
        print(f"  Avg hold time:   {stats['avg_hold_mins']:.0f} mins")
        print(f"{'='*50}\n")

        return stats
