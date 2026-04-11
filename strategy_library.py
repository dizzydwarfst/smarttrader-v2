"""
strategy_library.py - Structured strategy cards plus optional reference-doc ingestion.

This module gives the bot a safe knowledge layer:
- Strategy cards are machine-readable JSON files the bot and AI can rely on.
- Reference docs (Markdown, text, PDF) are research inputs for the AI only.
- The live bot should still trade from code and backtests, not raw document text.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from config import config

logger = logging.getLogger("SmartTrader")


class StrategyLibrary:
    """Loads structured strategy cards and optional reference documents."""

    SUPPORTED_REFERENCE_EXTS = {".md", ".txt", ".pdf"}

    def __init__(self, base_path=None, docs_name=None, cards_name=None):
        self.base_path = Path(base_path or Path(__file__).parent)
        self.docs_path = self._resolve_path(docs_name or config.STRATEGY_DOCS_PATH)
        self.cards_path = self._resolve_path(cards_name or config.STRATEGY_CARDS_PATH)
        self.ensure_structure()

    def _resolve_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.base_path / path

    def ensure_structure(self):
        self.docs_path.mkdir(parents=True, exist_ok=True)
        self.cards_path.mkdir(parents=True, exist_ok=True)

        docs_readme = self.docs_path / "README.md"
        if not docs_readme.exists():
            docs_readme.write_text(self._default_docs_readme(), encoding="utf-8")

        for filename, payload in self._default_cards().items():
            card_path = self.cards_path / filename
            if not card_path.exists():
                card_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _default_docs_readme(self):
        return """# Strategy Reference Docs

Drop your research notes here.

Supported file types:
- `.md`
- `.txt`
- `.pdf`

How this folder is used:
- The AI advisor can read these files as reference material.
- These files do not become live trading logic automatically.
- Every new idea should still be converted into a structured strategy card, then backtested and paper traded.

Suggested workflow:
1. Add a PDF, markdown note, or study summary here.
2. Create or update a card in `strategy_cards/`.
3. Review results after backtests and paper trades.
4. Let the AI use both the cards and the docs as context for future suggestions.
"""

    def _default_cards(self):
        return {
            "ema_crossover.json": {
                "name": "ema_crossover",
                "status": "active",
                "family": "trend_following",
                "description": "Trades momentum shifts when the fast EMA crosses the slow EMA.",
                "best_for": ["trending markets", "clean directional moves"],
                "avoid_when": ["choppy markets", "high-impact news"],
                "entry_rules": [
                    "BUY when fast EMA crosses above slow EMA",
                    "SELL when fast EMA crosses below slow EMA",
                    "Skip directional entries when the market regime is choppy",
                ],
                "exit_rules": [
                    "Use ATR-based stop loss",
                    "Use ATR-based take profit",
                    "Allow opposing signal or protective levels to close the trade",
                ],
                "parameters": {
                    "fast_ema": config.FAST_EMA,
                    "slow_ema": config.SLOW_EMA,
                    "stop_loss_atr_mult": config.STOP_LOSS_ATR_MULT,
                    "take_profit_atr_mult": config.TAKE_PROFIT_ATR_MULT,
                },
                "research_notes": [
                    "The learning engine may tune EMA values over time.",
                    "This card should be updated when the tuned EMA baseline changes materially.",
                ],
            },
            "breakout.json": {
                "name": "breakout",
                "status": "active",
                "family": "range_expansion",
                "description": "Trades a break outside the recent consolidation range with volume confirmation.",
                "best_for": ["post-consolidation moves", "range expansion", "session momentum"],
                "avoid_when": ["weak volume", "false-breakout environments", "major news spikes"],
                "entry_rules": [
                    "BUY when price closes above the recent range high and volume confirms",
                    "SELL when price closes below the recent range low and volume confirms",
                ],
                "exit_rules": [
                    "Use ATR-based stop loss",
                    "Use ATR-based take profit",
                    "Skip if breakout direction conflicts with another active strategy",
                ],
                "parameters": {
                    "lookback": config.BREAKOUT_LOOKBACK,
                    "volume_mult": config.BREAKOUT_VOLUME_MULT,
                    "stop_loss_atr_mult": config.STOP_LOSS_ATR_MULT,
                    "take_profit_atr_mult": config.TAKE_PROFIT_ATR_MULT,
                },
                "research_notes": [
                    "This strategy is often strongest after compression and before news volatility.",
                    "Future variants can specialize by session or instrument.",
                ],
            },
            "vwap_bounce.json": {
                "name": "vwap_bounce",
                "status": "testing",
                "family": "trend_continuation",
                "description": "Trades VWAP rejection bounces that align with a broader EMA bias and volume confirmation.",
                "best_for": ["intraday pullbacks", "session trend continuation", "M5 practice mode"],
                "avoid_when": ["flat volume", "session opens with violent whipsaw", "major news spikes"],
                "entry_rules": [
                    "BUY when price is above the bias EMA, dips through VWAP, and closes back above VWAP with a long lower wick",
                    "SELL when price is below the bias EMA, wicks through VWAP, and closes back below VWAP with an upper-wick rejection",
                    "Require current volume to beat the rolling average by the configured multiplier",
                ],
                "exit_rules": [
                    "Use ATR-based stop loss",
                    "Use ATR-based take profit",
                    "Do not average into failed VWAP reclaims",
                ],
                "parameters": {
                    "bias_ema_period": config.VWAP_BIAS_EMA,
                    "volume_lookback": config.VWAP_VOLUME_LOOKBACK,
                    "volume_mult": config.VWAP_VOLUME_MULT,
                    "wick_ratio": config.VWAP_WICK_RATIO,
                },
                "research_notes": [
                    "This is a candle-data adaptation of higher-timeframe trend plus VWAP bounce logic.",
                    "Best tested on practice mode with M5 candles before considering any live usage.",
                ],
            },
            "rsi_exhaustion.json": {
                "name": "rsi_exhaustion",
                "status": "testing",
                "family": "mean_reversion",
                "description": "Fades overextended moves after an RSI extreme and the first clear reversal candle.",
                "best_for": ["panic flushes", "parabolic short-term runs", "intraday overstretch"],
                "avoid_when": ["fresh macro catalysts", "strong trend acceleration", "thin liquidity"],
                "entry_rules": [
                    "BUY after an oversold RSI reading, a multi-bar down streak, and the first bullish reversal candle",
                    "SELL after an overbought RSI reading, a multi-bar up streak, and the first bearish reversal candle",
                    "Treat it as a smaller, faster setup than trend-following signals",
                ],
                "exit_rules": [
                    "Use ATR-based stop loss",
                    "Use ATR-based take profit",
                    "Exit quickly if price fails to mean-revert after entry",
                ],
                "parameters": {
                    "rsi_period": config.RSI_EXHAUSTION_PERIOD,
                    "overbought": config.RSI_EXHAUSTION_OVERBOUGHT,
                    "oversold": config.RSI_EXHAUSTION_OVERSOLD,
                    "streak_min": config.RSI_EXHAUSTION_STREAK_MIN,
                },
                "research_notes": [
                    "This adapts the 'broken parabolic' and RSI exhaustion ideas to assets without order-book or options data.",
                    "It should stay in paper trading until the journal shows a stable edge.",
                ],
            },
        }

    def load_cards(self):
        cards = []
        for path in sorted(self.cards_path.glob("*.json")):
            try:
                card = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(f"  Could not load strategy card {path.name}: {exc}")
                continue
            if not isinstance(card, dict):
                continue
            card.setdefault("name", path.stem)
            card["file_name"] = path.name
            cards.append(card)
        return cards

    def load_reference_documents(self, max_chars=1600):
        docs = []
        for path in sorted(self.docs_path.iterdir()):
            if not path.is_file() or path.suffix.lower() not in self.SUPPORTED_REFERENCE_EXTS:
                continue
            excerpt, status = self._read_reference_excerpt(path, max_chars=max_chars)
            docs.append({
                "name": path.name,
                "path": str(path),
                "type": path.suffix.lower().lstrip("."),
                "status": status,
                "excerpt": excerpt,
            })
        return docs

    def _read_reference_excerpt(self, path, max_chars=1600):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(path))
                    raw_pages = [page.extract_text() or "" for page in reader.pages[:5]]
                    status = "ok"
                except ImportError:
                    import pdfplumber

                    with pdfplumber.open(path) as pdf:
                        raw_pages = [(page.extract_text() or "") for page in pdf.pages[:5]]
                    status = "ok_pdfplumber"

                chunks = []
                remaining = max_chars
                for text in raw_pages:
                    cleaned = self._clean_text(text)
                    if not cleaned:
                        continue
                    chunks.append(cleaned[:remaining])
                    remaining -= len(chunks[-1])
                    if remaining <= 0:
                        break
                return "\n".join(chunks).strip(), status
            except Exception as exc:
                logger.warning(f"  Could not read PDF reference {path.name}: {exc}")
                return "", "pdf_read_failed"

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning(f"  Could not read strategy reference {path.name}: {exc}")
            return "", "read_failed"
        return self._clean_text(text)[:max_chars], "ok"

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", text).strip()

    def get_snapshot(self):
        cards = self.load_cards()
        references = self.load_reference_documents()
        return {
            "cards": cards,
            "references": references,
            "card_count": len(cards),
            "reference_count": len(references),
        }

    def get_prompt_context(self, max_chars=3500):
        cards = self.load_cards()
        references = self.load_reference_documents(max_chars=max(500, max_chars // 3))

        sections = [
            "Strategy library guidance:",
            "- Structured strategy cards are implementation candidates.",
            "- Reference documents are research only and must not bypass backtesting.",
        ]

        if cards:
            sections.append("")
            sections.append("Strategy cards:")
            for card in cards[:8]:
                parameters = card.get("parameters", {})
                best_for = ", ".join(card.get("best_for", [])[:3]) or "not specified"
                avoid_when = ", ".join(card.get("avoid_when", [])[:3]) or "not specified"
                sections.append(
                    f"- {card.get('name', 'unknown')} [{card.get('family', 'general')} | {card.get('status', 'draft')}] "
                    f"best for: {best_for}; avoid: {avoid_when}; parameters: {json.dumps(parameters)}"
                )
        else:
            sections.extend(["", "Strategy cards:", "- No strategy cards loaded yet."])

        if references:
            sections.append("")
            sections.append("Reference docs:")
            for doc in references[:5]:
                summary = doc["excerpt"][:300] + ("..." if len(doc["excerpt"]) > 300 else "")
                sections.append(f"- {doc['name']} ({doc['type']}, {doc['status']}): {summary}")

        context = "\n".join(sections).strip()
        if len(context) <= max_chars:
            return context
        return context[: max_chars - 3] + "..."
