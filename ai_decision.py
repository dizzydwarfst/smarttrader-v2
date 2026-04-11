"""
ai_decision.py - Runtime AI trade review and sizing guardrails.
"""

from __future__ import annotations

import logging

from config import config

logger = logging.getLogger("SmartTrader")


CONFIDENCE_RANK = {
    "low": 0,
    "normal": 1,
    "high": 2,
}


class AIDecisionEngine:
    """Applies mode logic and safety clamps around AI trade decisions."""

    def __init__(self, advisor):
        self.advisor = advisor
        self.last_entry_decision = None
        self.last_exit_decision = None

    def _base_decision(self, mode=None):
        return {
            "mode": mode or config.AI_MODE,
            "reviewed": False,
            "available": bool(self.advisor and self.advisor.enabled),
            "allow_trade": True,
            "should_execute": True,
            "action": "pass",
            "confidence": "normal",
            "size_mult": 1.0,
            "bankroll_fit": "unknown",
            "risk_flags": [],
            "reason": "AI trade review is disabled.",
        }

    def _base_exit_decision(self, mode=None):
        return {
            "mode": mode or config.AI_MODE,
            "reviewed": False,
            "available": bool(self.advisor and self.advisor.enabled),
            "exit_now": False,
            "should_exit": False,
            "action": "hold",
            "confidence": "normal",
            "risk_flags": [],
            "reason": "AI exit review is disabled.",
        }

    def _sanitize_decision(self, raw_decision, mode):
        decision = self._base_decision(mode=mode)
        decision["reviewed"] = True

        if not isinstance(raw_decision, dict):
            decision["allow_trade"] = mode != "gated"
            decision["should_execute"] = mode != "gated"
            decision["action"] = "pass" if mode != "gated" else "veto"
            decision["reason"] = "AI returned an invalid decision payload."
            return decision

        confidence = str(raw_decision.get("confidence", "normal")).lower()
        if confidence not in CONFIDENCE_RANK:
            confidence = "normal"

        size_mult = raw_decision.get("size_mult", 1.0)
        try:
            size_mult = float(size_mult)
        except (TypeError, ValueError):
            size_mult = 1.0
        size_mult = max(config.AI_MIN_SIZE_MULT, min(size_mult, config.AI_MAX_SIZE_MULT))

        risk_flags = raw_decision.get("risk_flags") or []
        if not isinstance(risk_flags, list):
            risk_flags = [str(risk_flags)]
        risk_flags = [str(item) for item in risk_flags[:6]]

        allow_trade = bool(raw_decision.get("allow_trade", True))
        min_confidence = config.AI_MIN_CONFIDENCE
        if min_confidence not in CONFIDENCE_RANK:
            min_confidence = "normal"
        confidence_ok = CONFIDENCE_RANK[confidence] >= CONFIDENCE_RANK[min_confidence]
        should_execute = allow_trade and confidence_ok

        decision.update({
            "allow_trade": allow_trade,
            "should_execute": should_execute if mode == "gated" else True,
            "confidence": confidence,
            "size_mult": size_mult if allow_trade else 0.0,
            "bankroll_fit": str(raw_decision.get("bankroll_fit", "unknown")).lower(),
            "risk_flags": risk_flags,
            "reason": str(raw_decision.get("reason", "AI reviewed the setup.")),
        })

        if not allow_trade:
            decision["action"] = "veto"
        elif size_mult < 0.95:
            decision["action"] = "reduce"
        elif size_mult > 1.05:
            decision["action"] = "press"
        else:
            decision["action"] = "approve"

        if mode == "gated" and not confidence_ok and allow_trade:
            decision["allow_trade"] = False
            decision["should_execute"] = False
            decision["action"] = "veto"
            decision["reason"] = (
                f"AI confidence {confidence} is below the minimum required level of {min_confidence}."
            )

        return decision

    def _sanitize_exit_decision(self, raw_decision, mode):
        decision = self._base_exit_decision(mode=mode)
        decision["reviewed"] = True

        if not isinstance(raw_decision, dict):
            decision["reason"] = "AI returned an invalid exit decision payload."
            return decision

        confidence = str(raw_decision.get("confidence", "normal")).lower()
        if confidence not in CONFIDENCE_RANK:
            confidence = "normal"

        risk_flags = raw_decision.get("risk_flags") or []
        if not isinstance(risk_flags, list):
            risk_flags = [str(risk_flags)]
        risk_flags = [str(item) for item in risk_flags[:6]]

        exit_now = bool(raw_decision.get("exit_now", False))
        min_confidence = config.AI_MIN_CONFIDENCE
        if min_confidence not in CONFIDENCE_RANK:
            min_confidence = "normal"
        confidence_ok = CONFIDENCE_RANK[confidence] >= CONFIDENCE_RANK[min_confidence]

        decision.update({
            "exit_now": exit_now,
            "should_exit": exit_now and confidence_ok and mode == "gated",
            "confidence": confidence,
            "risk_flags": risk_flags,
            "reason": str(raw_decision.get("reason", "AI reviewed the open trade.")),
        })

        if exit_now and decision["should_exit"]:
            decision["action"] = "exit"
        elif exit_now:
            decision["action"] = "watch_exit"
        else:
            decision["action"] = "hold"

        return decision

    def evaluate_entry(self, instrument, signal_payload, market_snapshot, bankroll_context):
        mode = config.AI_MODE
        base = self._base_decision(mode=mode)

        if mode not in {"shadow", "gated"}:
            self.last_entry_decision = base
            return base

        if not self.advisor or not self.advisor.enabled:
            base["allow_trade"] = mode != "gated"
            base["should_execute"] = mode != "gated"
            base["action"] = "pass" if mode != "gated" else "veto"
            base["reason"] = (
                "AI advisor is unavailable."
                if mode != "gated"
                else "AI gating is enabled but the AI advisor is unavailable."
            )
            self.last_entry_decision = base
            return base

        try:
            raw_decision = self.advisor.evaluate_trade_setup(
                instrument=instrument,
                signal_payload=signal_payload,
                market_snapshot=market_snapshot,
                bankroll_context=bankroll_context,
            )
            decision = self._sanitize_decision(raw_decision, mode)
        except Exception as exc:
            logger.warning(f"AI entry review failed for {instrument}: {exc}")
            decision = self._base_decision(mode=mode)
            decision["reviewed"] = True
            decision["allow_trade"] = mode != "gated"
            decision["should_execute"] = mode != "gated"
            decision["action"] = "pass" if mode != "gated" else "veto"
            decision["reason"] = (
                f"AI entry review failed: {exc}"
                if mode != "gated" else f"AI gating failed: {exc}"
            )

        self.last_entry_decision = decision
        return decision

    def evaluate_exit(self, instrument, open_trade, market_snapshot, bankroll_context):
        mode = config.AI_MODE
        base = self._base_exit_decision(mode=mode)

        if mode not in {"shadow", "gated"}:
            self.last_exit_decision = base
            return base

        if not self.advisor or not self.advisor.enabled:
            base["reason"] = (
                "AI advisor is unavailable."
                if mode != "gated"
                else "AI gating is enabled but the AI advisor is unavailable."
            )
            self.last_exit_decision = base
            return base

        try:
            raw_decision = self.advisor.evaluate_open_trade(
                instrument=instrument,
                open_trade=open_trade,
                market_snapshot=market_snapshot,
                bankroll_context=bankroll_context,
            )
            decision = self._sanitize_exit_decision(raw_decision, mode)
        except Exception as exc:
            logger.warning(f"AI exit review failed for {instrument}: {exc}")
            decision = self._base_exit_decision(mode=mode)
            decision["reviewed"] = True
            decision["reason"] = f"AI exit review failed: {exc}"

        self.last_exit_decision = decision
        return decision
