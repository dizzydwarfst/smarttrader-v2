import json
import unittest
import uuid
from pathlib import Path

import pandas as pd

from serialization_utils import make_json_safe
from strategy import (
    MarketRegime,
    Signal,
    StrategyManager,
    VWAPBounceStrategy,
    RSIExhaustionStrategy,
)
from trade_journal import TradeJournal


class FixedStrategy:
    def __init__(self, name, signal, price=100.0):
        self.name = name
        self.signal = signal
        self.price = price

    def get_signal(self, _df):
        return {
            "signal": self.signal,
            "regime": MarketRegime.TRENDING,
            "reason": f"{self.name} test signal",
            "strategy": self.name,
            "atr": 1.5,
            "price": self.price,
        }


class SerializationTests(unittest.TestCase):
    def test_make_json_safe_handles_circular_and_non_finite_values(self):
        payload = {"score": float("inf")}
        payload["self"] = payload

        safe = make_json_safe(payload)

        self.assertIsNone(safe["score"])
        self.assertEqual(safe["self"], "<circular>")
        json.dumps(safe, allow_nan=False)


class TradeJournalTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(__file__).with_name(f"test_trades_{uuid.uuid4().hex}.db")
        self.journal = TradeJournal(db_path=str(self.db_path))

    def tearDown(self):
        for extra_path in (
            self.db_path,
            self.db_path.with_name(self.db_path.name + "-wal"),
            self.db_path.with_name(self.db_path.name + "-shm"),
        ):
            if extra_path.exists():
                extra_path.unlink()

    def test_strategy_details_round_trip_is_structured_and_safe(self):
        details = {"confidence": "strong", "value": float("inf")}
        details["self"] = details

        trade_id = self.journal.open_trade(
            instrument="EUR_USD",
            direction=Signal.BUY,
            entry_price=1.2345,
            quantity=1000,
            stop_loss=1.23,
            take_profit=1.24,
            fast_ema=9,
            slow_ema=21,
            atr_at_entry=0.002,
            market_regime=MarketRegime.TRENDING,
            strategy_name="ema",
            strategy_confidence="strong",
            strategy_details=details,
        )

        open_trades = self.journal.get_open_trades()
        self.assertEqual(trade_id, open_trades[0]["id"])
        self.assertIsNone(open_trades[0]["strategy_details"]["value"])
        self.assertEqual(open_trades[0]["strategy_details"]["self"], "<circular>")

        self.journal.close_trade(
            trade_id=trade_id,
            exit_price=1.24,
            pnl=5.0,
            pnl_percent=0.01,
            exit_reason="take_profit",
        )

        recent_trades = self.journal.get_recent_trades(days=1)
        self.assertEqual(recent_trades[0]["strategy_name"], "ema")
        self.assertEqual(recent_trades[0]["strategy_details"]["confidence"], "strong")

    def test_strategy_scorecard_ranks_strategies_and_contexts(self):
        samples = [
            ("EUR_USD", "ema", MarketRegime.TRENDING, 12.0),
            ("EUR_USD", "ema", MarketRegime.TRENDING, 8.0),
            ("XAU_USD", "breakout", MarketRegime.VOLATILE, -5.0),
            ("XAU_USD", "breakout", MarketRegime.VOLATILE, 2.0),
        ]

        for index, (instrument, strategy_name, regime, pnl) in enumerate(samples, start=1):
            trade_id = self.journal.open_trade(
                instrument=instrument,
                direction=Signal.BUY,
                entry_price=1.2 + index * 0.001,
                quantity=1000,
                stop_loss=1.1,
                take_profit=1.3,
                fast_ema=9,
                slow_ema=21,
                atr_at_entry=0.002,
                market_regime=regime,
                strategy_name=strategy_name,
                strategy_confidence="normal",
                strategy_details={"sample": index},
            )
            self.journal.close_trade(
                trade_id=trade_id,
                exit_price=1.21 + index * 0.001,
                pnl=pnl,
                pnl_percent=pnl / 1000,
                exit_reason="signal",
            )

        scorecard = self.journal.get_strategy_scorecard(days=1, min_trades=2)

        self.assertEqual(scorecard["leaders"]["overall"]["strategy_name"], "ema")
        self.assertEqual(scorecard["leaders"]["overall"]["trades"], 2)
        self.assertEqual(scorecard["leaders"]["by_instrument"][0]["instrument"], "EUR_USD")
        self.assertEqual(scorecard["leaders"]["by_instrument"][0]["strategy_name"], "ema")
        self.assertEqual(scorecard["leaders"]["by_instrument_regime"][0]["market_regime"], MarketRegime.TRENDING)
        self.assertTrue(any(row["strategy_name"] == "breakout" for row in scorecard["strategies"]))

    def test_open_position_count_uses_unique_instruments(self):
        self.journal.open_trade(
            instrument="EUR_USD",
            direction=Signal.BUY,
            entry_price=1.1,
            quantity=1000,
            stop_loss=1.09,
            take_profit=1.12,
            fast_ema=9,
            slow_ema=21,
            atr_at_entry=0.002,
            market_regime=MarketRegime.TRENDING,
            oanda_trade_id="T-1",
        )
        self.journal.open_trade(
            instrument="EUR_USD",
            direction=Signal.BUY,
            entry_price=1.101,
            quantity=800,
            stop_loss=1.091,
            take_profit=1.121,
            fast_ema=9,
            slow_ema=21,
            atr_at_entry=0.002,
            market_regime=MarketRegime.TRENDING,
            oanda_trade_id="T-2",
        )
        self.journal.open_trade(
            instrument="XAU_USD",
            direction=Signal.SELL,
            entry_price=2400,
            quantity=1,
            stop_loss=2410,
            take_profit=2380,
            fast_ema=9,
            slow_ema=21,
            atr_at_entry=5,
            market_regime=MarketRegime.VOLATILE,
            oanda_trade_id="T-3",
        )

        self.assertEqual(self.journal.get_open_position_count(), 2)


class StrategyManagerTests(unittest.TestCase):
    def test_strategy_manager_results_remain_json_safe(self):
        manager = StrategyManager(
            [
                FixedStrategy("ema", Signal.BUY),
                FixedStrategy("breakout", Signal.HOLD),
            ]
        )

        result = manager.get_signal(None)

        self.assertEqual(result["signal"], Signal.BUY)
        self.assertEqual(result["confidence"], "normal")
        self.assertEqual(len(result["all_results"]), 2)
        json.dumps(make_json_safe(result), allow_nan=False)


class StrategySignalTests(unittest.TestCase):
    def test_vwap_bounce_strategy_detects_bullish_reclaim(self):
        rows = []
        for index in range(119):
            open_price = 100 + index * 0.025
            close_price = open_price + 0.02
            rows.append(
                {
                    "date": f"2026-04-01T{index // 12:02d}:{(index % 12) * 5:02d}:00Z",
                    "open": open_price,
                    "high": close_price + 0.05,
                    "low": open_price - 0.05,
                    "close": close_price,
                    "volume": 100,
                }
            )

        rows.append(
            {
                "date": "2026-04-01T10:00:00Z",
                "open": 102.85,
                "high": 103.25,
                "low": 101.40,
                "close": 103.15,
                "volume": 350,
            }
        )

        frame = pd.DataFrame(rows)
        strategy = VWAPBounceStrategy(bias_ema_period=100, volume_lookback=20, volume_mult=1.2, wick_ratio=1.5)
        result = strategy.get_signal(frame)

        self.assertEqual(result["signal"], Signal.BUY)
        self.assertEqual(result["strategy"], "vwap_bounce")

    def test_rsi_exhaustion_strategy_detects_parabolic_reversal(self):
        rows = []
        for index in range(24):
            open_price = 100 + index * 0.4
            close_price = open_price + 0.3
            rows.append(
                {
                    "date": f"2026-04-02T{index // 12:02d}:{(index % 12) * 5:02d}:00Z",
                    "open": open_price,
                    "high": close_price + 0.1,
                    "low": open_price - 0.05,
                    "close": close_price,
                    "volume": 120,
                }
            )

        rows.append(
            {
                "date": "2026-04-02T02:00:00Z",
                "open": 110.30,
                "high": 110.55,
                "low": 108.80,
                "close": 108.95,
                "volume": 180,
            }
        )

        frame = pd.DataFrame(rows)
        strategy = RSIExhaustionStrategy(rsi_period=14, overbought=80, oversold=20, streak_min=4)
        result = strategy.get_signal(frame)

        self.assertEqual(result["signal"], Signal.SELL)
        self.assertEqual(result["strategy"], "rsi_exhaustion")


if __name__ == "__main__":
    unittest.main()
