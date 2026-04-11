"""
trading_memory.py - Shared markdown memory for the bot and AI advisor.

This module keeps two human-readable files in sync:
- soul.md: the bot's trading constitution and event diary
- skills.md: the bot's evolving skillbook
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class TradingMemory:
    """Maintains the bot's markdown memory files."""

    DIARY_START = "<!-- AUTO-DIARY:START -->"
    DIARY_END = "<!-- AUTO-DIARY:END -->"
    SKILLS_START = "<!-- AUTO-SKILLS:START -->"
    SKILLS_END = "<!-- AUTO-SKILLS:END -->"

    def __init__(self, base_path=None, soul_name="soul.md", skills_name="skills.md", max_diary_entries=40):
        self.base_path = Path(base_path or Path(__file__).parent)
        self.soul_path = self.base_path / soul_name
        self.skills_path = self.base_path / skills_name
        self.max_diary_entries = max_diary_entries
        self.ensure_files()

    def ensure_files(self):
        """Create memory files if they do not exist yet."""
        if not self.soul_path.exists():
            self.soul_path.write_text(self._default_soul(), encoding="utf-8")
        if not self.skills_path.exists():
            self.skills_path.write_text(self._default_skills(), encoding="utf-8")

    def read_soul(self):
        return self.soul_path.read_text(encoding="utf-8")

    def read_skills(self):
        return self.skills_path.read_text(encoding="utf-8")

    def get_snapshot(self):
        return {
            "soul": self.read_soul(),
            "skills": self.read_skills(),
        }

    def get_prompt_context(self, max_chars=5000):
        """Provide compact context for AI prompts."""
        soul = self.read_soul().strip()
        skills = self.read_skills().strip()
        combined = f"Trading Soul:\n{soul}\n\nTrading Skills:\n{skills}"
        if len(combined) <= max_chars:
            return combined
        return combined[: max_chars - 3] + "..."

    def append_diary_entry(self, title, summary, details=None):
        """Add a new diary entry to soul.md."""
        details = details or []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry_lines = [f"- {timestamp} | {title}: {summary}"]
        for detail in details[:4]:
            entry_lines.append(f"  - {detail}")
        entry = "\n".join(entry_lines)

        current = self._read_block(self.soul_path, self.DIARY_START, self.DIARY_END)
        chunks = [
            chunk.strip()
            for chunk in current.strip().split("\n\n")
            if chunk.strip() and "No diary entries yet." not in chunk
        ]
        chunks.insert(0, entry)
        chunks = chunks[: self.max_diary_entries]
        self._replace_block(
            self.soul_path,
            self.DIARY_START,
            self.DIARY_END,
            "\n\n".join(chunks) if chunks else "- No diary entries yet.",
        )

    def refresh_skills_snapshot(self, stats, recent_trades, param_history):
        """Rewrite the auto-managed skill snapshot in skills.md."""
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        profit_factor = stats["profit_factor"]
        if profit_factor == float("inf"):
            profit_factor_text = "inf"
        else:
            profit_factor_text = f"{profit_factor:.2f}"

        lines = [
            f"- Updated: {updated_at}",
            f"- Trades reviewed: {stats['total']}",
            f"- Scorecard: win rate {stats['win_rate']:.1%} | profit factor {profit_factor_text} | total P&L ${stats['total_pnl']:+.2f}",
        ]

        if not recent_trades:
            lines.append("- Learning stage: observing live market behavior and waiting for the first closed trades.")
            lines.append("- Next focus: execute cleanly, collect enough trades, and protect the account while the skillbook is still young.")
            self._replace_block(self.skills_path, self.SKILLS_START, self.SKILLS_END, "\n".join(lines))
            return

        pnl_by_instrument = defaultdict(float)
        wins_by_instrument = defaultdict(int)
        losses_by_instrument = defaultdict(int)
        pnl_by_regime = defaultdict(float)
        count_by_regime = defaultdict(int)

        for trade in recent_trades:
            instrument = trade.get("instrument", "unknown")
            pnl = trade.get("pnl") or 0
            regime = trade.get("market_regime") or "unknown"
            pnl_by_instrument[instrument] += pnl
            pnl_by_regime[regime] += pnl
            count_by_regime[regime] += 1
            if pnl > 0:
                wins_by_instrument[instrument] += 1
            else:
                losses_by_instrument[instrument] += 1

        best_instrument = max(pnl_by_instrument, key=pnl_by_instrument.get)
        worst_instrument = min(pnl_by_instrument, key=pnl_by_instrument.get)
        best_regime = max(pnl_by_regime, key=pnl_by_regime.get)

        lines.append(
            f"- Strongest market right now: {best_instrument} | wins {wins_by_instrument[best_instrument]} | net ${pnl_by_instrument[best_instrument]:+.2f}"
        )
        lines.append(
            f"- Most comfortable regime: {best_regime} | {count_by_regime[best_regime]} trade(s) | net ${pnl_by_regime[best_regime]:+.2f}"
        )

        if worst_instrument != best_instrument or pnl_by_instrument[worst_instrument] < 0:
            lines.append(
                f"- Needs more practice: {worst_instrument} | losses {losses_by_instrument[worst_instrument]} | net ${pnl_by_instrument[worst_instrument]:+.2f}"
            )

        if param_history:
            latest = param_history[0]
            lines.append(
                f"- Latest adaptation: {latest['parameter']} changed from {latest['old_value']} to {latest['new_value']}."
            )

        next_focus = []
        if stats["win_rate"] < 0.45:
            next_focus.append("Improve entry selectivity and skip lower-quality setups.")
        if profit_factor not in (float("inf"),) and profit_factor < 1.0:
            next_focus.append("Tighten loss control and avoid letting weak trades linger.")
        if stats["avg_hold_mins"] and stats["avg_hold_mins"] < 15:
            next_focus.append("Hold good trades long enough for take-profit logic to work.")
        if not next_focus:
            next_focus.append("Stay consistent with the current plan and gather more evidence before making another change.")

        lines.append(f"- Next focus: {' '.join(next_focus)}")
        self._replace_block(self.skills_path, self.SKILLS_START, self.SKILLS_END, "\n".join(lines))

    def _default_soul(self):
        return f"""# SmartTrader Soul

This file is the trading soul of the bot. It tells both the bot and the AI advisor how to behave, what matters, and what must never be ignored.

## Mission

Trade with discipline first, profit second. Stay alive, stay consistent, and let skill compound over time.

## Trading Constitution

1. Respect price, volatility, spread, and risk before chasing a signal.
2. A trade must have a reason, a stop-loss, and a take-profit.
3. High-impact news can pause execution even when the chart looks good.
4. Learning is allowed, but reckless improvisation is not.
5. Practice mode is where the bot earns the right to become smarter.

## Execution Rules

- Follow the active strategy stack from the codebase.
- Prefer clean setups over forced entries.
- Track what happened after every meaningful event.
- Use the diary below to remember outcomes, mistakes, and lessons.

## Diary

{self.DIARY_START}
- {datetime.now().strftime("%Y-%m-%d %H:%M")} | Soul initialized: The bot started its diary and is ready to learn from real trade outcomes.
{self.DIARY_END}
"""

    def _default_skills(self):
        return f"""# SmartTrader Skills

This file tracks the trading skills the bot is building from scratch. The bot and AI advisor can read it to understand what is strong, what is weak, and what should be improved next.

## Skill Tree

- Market selection
- Trend recognition
- Breakout timing
- Risk control
- Exit discipline
- News awareness
- Self-review and adaptation

## Current Skill Snapshot

{self.SKILLS_START}
- Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- Trades reviewed: 0
- Scorecard: win rate 0.0% | profit factor 0.00 | total P&L $+0.00
- Learning stage: observing live market behavior and waiting for the first closed trades.
- Next focus: execute cleanly, collect enough trades, and protect the account while the skillbook is still young.
{self.SKILLS_END}

## Manual Notes

- You can add your own observations above or below the auto-updated snapshot.
- The bot will only rewrite the auto-managed block.
"""

    def _read_block(self, path, start_marker, end_marker):
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"{re.escape(start_marker)}\n(.*?)\n{re.escape(end_marker)}",
            re.DOTALL,
        )
        match = pattern.search(text)
        return match.group(1) if match else ""

    def _replace_block(self, path, start_marker, end_marker, new_content):
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"({re.escape(start_marker)}\n)(.*?)(\n{re.escape(end_marker)})",
            re.DOTALL,
        )
        updated = pattern.sub(rf"\1{new_content}\3", text, count=1)
        path.write_text(updated, encoding="utf-8")
