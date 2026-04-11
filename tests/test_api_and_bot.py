import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import api as dashboard_api
import bot as bot_module
from ai_decision import AIDecisionEngine
from strategy import MarketRegime, Signal


class FakeDashboardJournal:
    def get_open_trades(self):
        return []

    def get_daily_pnl(self):
        return 0.0

    def get_trade_stats(self, days=14):
        return {
            "total": 4,
            "wins": 3,
            "losses": 1,
            "win_rate": 0.75,
            "avg_pnl": 12.5,
            "total_pnl": 50.0,
            "avg_hold_mins": 15.0,
            "profit_factor": float("inf"),
            "largest_win": 25.0,
            "largest_loss": -5.0,
        }

    def get_strategy_scorecard(self, days=30, min_trades=3):
        return {
            "window_days": days,
            "min_trades": min_trades,
            "overall": {"trades": 4, "profit_factor": float("inf")},
            "strategies": [
                {
                    "strategy_name": "ema",
                    "trades": 3,
                    "wins": 3,
                    "losses": 0,
                    "win_rate": 1.0,
                    "avg_pnl": 18.0,
                    "total_pnl": 54.0,
                    "avg_hold_mins": 10.0,
                    "profit_factor": float("inf"),
                    "largest_win": 25.0,
                    "largest_loss": 0.0,
                    "last_trade_at": "2026-04-02T10:00:00",
                    "eligible": True,
                }
            ],
            "leaders": {
                "overall": {
                    "strategy_name": "ema",
                    "trades": 3,
                    "profit_factor": float("inf"),
                    "total_pnl": 54.0,
                    "eligible": True,
                },
                "by_instrument": [],
                "by_regime": [],
                "by_instrument_regime": [],
            },
            "breakdowns": {
                "by_instrument": [],
                "by_regime": [],
                "by_instrument_regime": [],
            },
        }


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(dashboard_api.app)

    def test_trade_stats_endpoint_sanitizes_infinite_profit_factor(self):
        with patch.object(dashboard_api, "journal", FakeDashboardJournal()):
            response = self.client.get("/api/trades/stats?days=14")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["profit_factor"])
        self.assertEqual(payload["wins"], 3)

    def test_strategy_scorecard_endpoint_returns_leader_snapshot(self):
        with patch.object(dashboard_api, "journal", FakeDashboardJournal()):
            response = self.client.get("/api/strategies/scorecard?days=30&min_trades=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["window_days"], 30)
        self.assertEqual(payload["min_trades"], 2)
        self.assertEqual(payload["leaders"]["overall"]["strategy_name"], "ema")
        self.assertIsNone(payload["leaders"]["overall"]["profit_factor"])

    def test_status_endpoint_exposes_execution_status(self):
        runtime = {
            "bot_online": True,
            "trading_mode": "practice",
            "current_activity": "Watching markets.",
            "execution_status": {
                "open_trades_count": 0,
                "has_open_trade": False,
                "summary": "No open trades. Last recorded trade: SELL USD_JPY via breakout.",
            },
        }
        with patch.object(dashboard_api, "journal", FakeDashboardJournal()), patch.object(
            dashboard_api,
            "read_runtime_status",
            return_value=runtime,
        ):
            response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["execution_status"]["open_trades_count"], 0)
        self.assertIn("Last recorded trade", payload["execution_status"]["summary"])


class DummyApiClient:
    def __init__(self):
        self.calls = 0

    def request(self, _request):
        self.calls += 1
        if self.calls == 1:
            return {
                "orderFillTransaction": {
                    "price": "1.23456",
                    "units": "100",
                    "tradeOpened": {"tradeID": "T-123"},
                }
            }
        if self.calls == 2:
            return {
                "account": {
                    "NAV": "100000",
                    "marginUsed": "250",
                }
            }
        raise AssertionError("Unexpected API request count")


class FailingJournal:
    def open_trade(self, **_kwargs):
        raise RuntimeError("sqlite write failed")

    def get_total_closed_pnl(self):
        return 0.0


class DummyMemory:
    def __init__(self):
        self.entries = 0

    def append_diary_entry(self, *_args, **_kwargs):
        self.entries += 1


class BotExecutionTests(unittest.TestCase):
    def test_execute_signal_reports_broker_fill_even_if_journal_write_fails(self):
        bot = bot_module.SmartTraderBot.__new__(bot_module.SmartTraderBot)
        bot.account_id = "practice-account"
        bot.account_value = 100000
        bot.unrealized_pnl = 0.0
        bot.api = DummyApiClient()
        bot.journal = FailingJournal()
        bot.memory = DummyMemory()
        bot.instrument_info = {"EUR_USD": {"precision": 5}}
        bot.strategy_manager = SimpleNamespace(
            strategies=[SimpleNamespace(name="ema", fast_period=9, slow_period=21)]
        )
        bot.risk_manager = SimpleNamespace(
            can_trade=lambda _account_value: (True, "ok"),
            calculate_stop_loss=lambda price, direction, atr, regime: 1.23,
            calculate_take_profit=lambda price, direction, atr: 1.24,
            calculate_position_size=lambda account_value, price, stop_loss, regime, size_mult=1.0, min_units=1: 100,
            get_time_of_day_multiplier=lambda: 1.0,
        )
        bot._get_oanda_positions = lambda instrument: None
        bot._close_oanda_position = lambda instrument: None

        result = bot._execute_signal(
            "EUR_USD",
            {
                "signal": Signal.BUY,
                "price": 1.2345,
                "atr": 0.001,
                "regime": MarketRegime.TRENDING,
                "strategy": "ema",
                "confidence": "strong",
                "all_results": [{"strategy": "ema", "signal": Signal.BUY}],
            },
        )

        self.assertTrue(result["submitted"])
        self.assertFalse(result["journal_synced"])
        self.assertEqual(result["trade_id"], "T-123")
        self.assertIn("local trade journaling failed", result["reason"])
        self.assertEqual(bot.memory.entries, 1)

    def test_effective_trading_equity_uses_virtual_bankroll(self):
        bot = bot_module.SmartTraderBot.__new__(bot_module.SmartTraderBot)
        bot.account_value = 100000
        bot.unrealized_pnl = -20
        bot.journal = SimpleNamespace(get_total_closed_pnl=lambda: 120)

        with patch.object(bot_module.config, "TRADING_MODE", "practice"), patch.object(
            bot_module.config,
            "USE_VIRTUAL_BANKROLL",
            True,
        ), patch.object(bot_module.config, "VIRTUAL_BANKROLL", 1000), patch.object(
            bot_module.config,
            "VIRTUAL_BANKROLL_FLOOR",
            250,
        ):
            equity = bot._effective_trading_equity()

        self.assertEqual(equity, 1100)

    def test_ai_decision_engine_blocks_low_confidence_trade_in_gated_mode(self):
        advisor = SimpleNamespace(
            enabled=True,
            evaluate_trade_setup=lambda **_kwargs: {
                "allow_trade": True,
                "confidence": "low",
                "size_mult": 1.0,
                "bankroll_fit": "good",
                "risk_flags": [],
                "reason": "Too weak for execution.",
            },
        )
        engine = AIDecisionEngine(advisor)

        with patch.object(bot_module.config, "AI_MODE", "gated"), patch.object(
            bot_module.config,
            "AI_MIN_CONFIDENCE",
            "normal",
        ):
            decision = engine.evaluate_entry(
                instrument="EUR_USD",
                signal_payload={"signal": Signal.BUY},
                market_snapshot={"spread_ok": True},
                bankroll_context={"effective_trading_equity": 1000},
            )

        self.assertFalse(decision["should_execute"])
        self.assertEqual(decision["action"], "veto")

    def test_ai_decision_engine_can_request_exit_in_gated_mode(self):
        advisor = SimpleNamespace(
            enabled=True,
            evaluate_open_trade=lambda **_kwargs: {
                "exit_now": True,
                "confidence": "high",
                "risk_flags": ["momentum_broken"],
                "reason": "Momentum has clearly faded.",
            },
        )
        engine = AIDecisionEngine(advisor)

        with patch.object(bot_module.config, "AI_MODE", "gated"), patch.object(
            bot_module.config,
            "AI_MIN_CONFIDENCE",
            "normal",
        ):
            decision = engine.evaluate_exit(
                instrument="EUR_USD",
                open_trade={"direction": Signal.BUY},
                market_snapshot={"spread_ok": True},
                bankroll_context={"effective_trading_equity": 1000},
            )

        self.assertTrue(decision["should_exit"])
        self.assertEqual(decision["action"], "exit")

    def test_verify_closed_trade_uses_pending_ai_exit_reason(self):
        bot = bot_module.SmartTraderBot.__new__(bot_module.SmartTraderBot)
        bot.account_id = "practice-account"
        bot.account_value = 1000
        bot.pending_ai_exits = {
            "oanda:T-123": {
                "exit_reason": "ai_exit",
                "notes": "AI exit: trend structure broke.",
            }
        }
        bot.api = SimpleNamespace(
            request=lambda _request: {
                "trade": {
                    "averageClosePrice": "1.2400",
                    "realizedPL": "6.0",
                    "financing": "0.0",
                }
            }
        )

        verified = bot._verify_closed_trade(
            "EUR_USD",
            {
                "id": 7,
                "oanda_trade_id": "T-123",
                "direction": Signal.BUY,
                "entry_price": 1.2345,
                "quantity": 100,
            },
        )

        self.assertEqual(verified["reason"], "ai_exit")
        self.assertIn("AI exit", verified["notes"])


if __name__ == "__main__":
    unittest.main()
