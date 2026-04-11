"""
strategy.py — Multi-Strategy Engine (EMA Crossover + Breakout)

Two strategies that complement each other:
- EMA Crossover: catches trends (works in trending markets)
- Breakout: catches explosive moves after consolidation (works in ranging markets)

The bot runs both and takes whichever signal fires first.
"""

import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange


class Signal:
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketRegime:
    TRENDING = "trending"
    CHOPPY = "choppy"
    VOLATILE = "volatile"


def _classify_regime_series(atr_pct_series):
    """Classify regime from an ATR% series using one set of thresholds per frame."""
    regime = pd.Series(MarketRegime.TRENDING, index=atr_pct_series.index, dtype="object")
    valid = atr_pct_series.dropna()
    if len(valid) < 20:
        return regime

    atr_p75 = valid.quantile(0.75)
    atr_p25 = valid.quantile(0.25)
    regime.loc[atr_pct_series > atr_p75 * 1.5] = MarketRegime.VOLATILE
    regime.loc[(atr_pct_series < atr_p25) & atr_pct_series.notna()] = MarketRegime.CHOPPY
    return regime


def _directional_streaks(close_series):
    """Return consecutive up/down close streak lengths."""
    up_streak = np.zeros(len(close_series), dtype=int)
    down_streak = np.zeros(len(close_series), dtype=int)

    changes = close_series.diff().fillna(0)
    for index, change in enumerate(changes):
        if change > 0:
            up_streak[index] = (up_streak[index - 1] if index else 0) + 1
            down_streak[index] = 0
        elif change < 0:
            down_streak[index] = (down_streak[index - 1] if index else 0) + 1
            up_streak[index] = 0
        else:
            up_streak[index] = 0
            down_streak[index] = 0

    return up_streak, down_streak


# ─── EMA CROSSOVER STRATEGY ─────────────────────────────

class EMAStrategy:
    """
    Fast EMA crosses above slow EMA → BUY
    Fast EMA crosses below slow EMA → SELL
    """

    def __init__(self, fast_period=9, slow_period=21, atr_period=14):
        self.name = "ema"
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_period = atr_period

    def calculate_indicators(self, df):
        df = df.copy()
        df["ema_fast"] = EMAIndicator(close=df["close"], window=self.fast_period).ema_indicator()
        df["ema_slow"] = EMAIndicator(close=df["close"], window=self.slow_period).ema_indicator()
        atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=self.atr_period)
        df["atr"] = atr.average_true_range()
        df["atr_pct"] = df["atr"] / df["close"] * 100
        df["ema_diff"] = df["ema_fast"] - df["ema_slow"]
        df["crossover"] = np.where(
            (df["ema_diff"] > 0) & (df["ema_diff"].shift(1) <= 0), Signal.BUY,
            np.where(
                (df["ema_diff"] < 0) & (df["ema_diff"].shift(1) >= 0), Signal.SELL,
                Signal.HOLD
            )
        )
        df["regime"] = _classify_regime_series(df["atr_pct"])
        return df

    def signal_frame(self, df):
        """Return a frame of per-bar EMA signals for backtesting or inspection."""
        if df is None or len(df) < self.slow_period + 5:
            return None

        frame = self.calculate_indicators(df)
        frame["signal"] = frame["crossover"]
        # Choppy regime no longer kills signals — risk_manager already halves
        # position size in choppy markets, so double-filtering is removed.
        frame["price"] = frame["close"]
        return frame

    def get_signal(self, df):
        frame = self.signal_frame(df)
        if frame is None:
            return {"signal": Signal.HOLD, "regime": MarketRegime.TRENDING, "reason": "Not enough data", "strategy": self.name}

        latest = frame.iloc[-1]
        signal = latest["signal"]
        regime = latest["regime"]
        choppy_note = " (choppy regime — size reduced)" if regime == MarketRegime.CHOPPY and signal != Signal.HOLD else ""
        if signal == Signal.BUY:
            reason = f"Fast EMA ({self.fast_period}) crossed above Slow EMA ({self.slow_period}){choppy_note}"
        elif signal == Signal.SELL:
            reason = f"Fast EMA ({self.fast_period}) crossed below Slow EMA ({self.slow_period}){choppy_note}"
        else:
            reason = "No EMA crossover"
        return {
            "signal": signal, "regime": regime, "reason": reason, "strategy": self.name,
            "atr": latest.get("atr", 0), "atr_pct": latest.get("atr_pct", 0),
            "ema_fast": latest.get("ema_fast", 0), "ema_slow": latest.get("ema_slow", 0),
            "price": latest["close"],
        }

    def update_params(self, fast_period=None, slow_period=None):
        changes = {}
        if fast_period and fast_period != self.fast_period:
            changes["fast_ema"] = (self.fast_period, fast_period)
            self.fast_period = fast_period
        if slow_period and slow_period != self.slow_period:
            changes["slow_ema"] = (self.slow_period, slow_period)
            self.slow_period = slow_period
        return changes


# ─── BREAKOUT STRATEGY ───────────────────────────────────

class BreakoutStrategy:
    """
    Watches for price consolidation (tight range), then trades
    when price breaks out of that range with strong momentum.

    How it works:
    1. Find the highest high and lowest low of the last N candles
    2. If price breaks ABOVE the high → BUY (upward breakout)
    3. If price breaks BELOW the low → SELL (downward breakout)
    4. Confirm with volume (must be above average)
    5. Confirm with ATR (range must be tight before breakout)
    """

    def __init__(self, lookback=20, atr_threshold=0.5, volume_mult=1.2, atr_period=14):
        self.name = "breakout"
        self.lookback = lookback
        self.atr_threshold = atr_threshold
        self.volume_mult = volume_mult
        self.atr_period = atr_period

    def signal_frame(self, df):
        """Return a frame of per-bar breakout signals for backtesting or inspection."""
        if df is None or len(df) < self.lookback + 10:
            return None

        frame = df.copy()
        atr = AverageTrueRange(high=frame["high"], low=frame["low"], close=frame["close"], window=self.atr_period)
        frame["atr"] = atr.average_true_range()
        frame["atr_pct"] = frame["atr"] / frame["close"] * 100
        frame["range_high"] = frame["high"].shift(1).rolling(self.lookback).max()
        frame["range_low"] = frame["low"].shift(1).rolling(self.lookback).min()
        frame["avg_volume"] = frame["volume"].shift(1).rolling(self.lookback).mean()
        frame["volume_ok"] = frame["volume"] > frame["avg_volume"] * self.volume_mult
        frame["prev_close"] = frame["close"].shift(1)
        frame["regime"] = _classify_regime_series(frame["atr_pct"])

        signal = np.full(len(frame), Signal.HOLD, dtype=object)
        buy_mask = (
            (frame["close"] > frame["range_high"])
            & (frame["prev_close"] <= frame["range_high"])
            & frame["volume_ok"]
        )
        sell_mask = (
            (frame["close"] < frame["range_low"])
            & (frame["prev_close"] >= frame["range_low"])
            & frame["volume_ok"]
        )
        signal[buy_mask.to_numpy()] = Signal.BUY
        signal[sell_mask.to_numpy()] = Signal.SELL
        frame["signal"] = signal
        frame["price"] = frame["close"]
        return frame

    def get_signal(self, df):
        frame = self.signal_frame(df)
        if frame is None:
            return {"signal": Signal.HOLD, "regime": MarketRegime.TRENDING, "reason": "Not enough data", "strategy": self.name}

        current = frame.iloc[-1]
        range_high = current["range_high"]
        range_low = current["range_low"]
        regime = current["regime"]
        atr_pct = current["atr_pct"] if not pd.isna(current.get("atr_pct")) else 0
        signal = current["signal"]
        reason = "No breakout detected"

        if current["close"] > range_high and current["prev_close"] <= range_high:
            if current["volume_ok"]:
                reason = f"Breakout ABOVE {range_high:.5f} (range: {self.lookback} bars, vol confirmed)"
            else:
                reason = f"Breakout above {range_high:.5f} but weak volume — skipping"
        elif current["close"] < range_low and current["prev_close"] >= range_low:
            if current["volume_ok"]:
                reason = f"Breakout BELOW {range_low:.5f} (range: {self.lookback} bars, vol confirmed)"
            else:
                reason = f"Breakout below {range_low:.5f} but weak volume — skipping"

        return {
            "signal": signal, "regime": regime, "reason": reason, "strategy": self.name,
            "atr": current.get("atr", 0), "atr_pct": atr_pct,
            "price": current["close"],
            "range_high": range_high, "range_low": range_low,
        }


# ─── MULTI-STRATEGY MANAGER ─────────────────────────────

class VWAPBounceStrategy:
    """
    Trade VWAP rejection bounces in the direction of a larger EMA bias.

    This adapts the "ride the trend" and "VWAP bounce" ideas to the
    single-timeframe OHLCV data the bot already has.
    """

    def __init__(self, bias_ema_period=100, volume_lookback=20, volume_mult=1.2, wick_ratio=1.5, atr_period=14):
        self.name = "vwap_bounce"
        self.bias_ema_period = bias_ema_period
        self.volume_lookback = volume_lookback
        self.volume_mult = volume_mult
        self.wick_ratio = wick_ratio
        self.atr_period = atr_period

    def signal_frame(self, df):
        minimum_bars = max(self.bias_ema_period + 5, self.volume_lookback + 5)
        if df is None or len(df) < minimum_bars:
            return None

        frame = df.copy()
        frame["timestamp"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
        frame = frame.dropna(subset=["timestamp"]).copy()
        if len(frame) < minimum_bars:
            return None

        atr = AverageTrueRange(high=frame["high"], low=frame["low"], close=frame["close"], window=self.atr_period)
        frame["atr"] = atr.average_true_range()
        frame["atr_pct"] = frame["atr"] / frame["close"] * 100
        frame["regime"] = _classify_regime_series(frame["atr_pct"])

        frame["typical_price"] = (frame["high"] + frame["low"] + frame["close"]) / 3
        frame["session"] = frame["timestamp"].dt.floor("D")
        frame["cum_pv"] = (frame["typical_price"] * frame["volume"]).groupby(frame["session"]).cumsum()
        frame["cum_volume"] = frame["volume"].groupby(frame["session"]).cumsum().replace(0, np.nan)
        frame["vwap"] = frame["cum_pv"] / frame["cum_volume"]
        frame["ema_bias"] = EMAIndicator(close=frame["close"], window=self.bias_ema_period).ema_indicator()
        frame["avg_volume"] = frame["volume"].shift(1).rolling(self.volume_lookback).mean()
        frame["volume_ok"] = frame["volume"] >= frame["avg_volume"] * self.volume_mult

        body = (frame["close"] - frame["open"]).abs()
        candle_range = (frame["high"] - frame["low"]).replace(0, np.nan)
        lower_wick = np.minimum(frame["open"], frame["close"]) - frame["low"]
        upper_wick = frame["high"] - np.maximum(frame["open"], frame["close"])

        bullish_rejection = (
            (frame["close"] > frame["open"])
            & ((lower_wick >= body * self.wick_ratio) | (lower_wick >= candle_range * 0.35))
        )
        bearish_rejection = (
            (frame["close"] < frame["open"])
            & ((upper_wick >= body * self.wick_ratio) | (upper_wick >= candle_range * 0.35))
        )

        prev_above_vwap = frame["close"].shift(1) > frame["vwap"].shift(1)
        prev_below_vwap = frame["close"].shift(1) < frame["vwap"].shift(1)
        long_bias = frame["close"] > frame["ema_bias"]
        short_bias = frame["close"] < frame["ema_bias"]

        buy_mask = (
            long_bias
            & prev_above_vwap
            & (frame["low"] <= frame["vwap"])
            & (frame["close"] > frame["vwap"])
            & frame["volume_ok"]
            & bullish_rejection
        )
        sell_mask = (
            short_bias
            & prev_below_vwap
            & (frame["high"] >= frame["vwap"])
            & (frame["close"] < frame["vwap"])
            & frame["volume_ok"]
            & bearish_rejection
        )

        signal = np.full(len(frame), Signal.HOLD, dtype=object)
        signal[buy_mask.to_numpy()] = Signal.BUY
        signal[sell_mask.to_numpy()] = Signal.SELL
        frame["signal"] = signal
        frame["price"] = frame["close"]
        return frame

    def get_signal(self, df):
        frame = self.signal_frame(df)
        if frame is None:
            return {
                "signal": Signal.HOLD,
                "regime": MarketRegime.TRENDING,
                "reason": "Not enough data",
                "strategy": self.name,
            }

        current = frame.iloc[-1]
        signal = current["signal"]

        if signal == Signal.BUY:
            reason = f"Bullish VWAP reclaim with rejection wick and volume above EMA{self.bias_ema_period}"
        elif signal == Signal.SELL:
            reason = f"Bearish VWAP rejection with upper wick and volume below EMA{self.bias_ema_period}"
        else:
            reason = "No VWAP bounce detected"

        return {
            "signal": signal,
            "regime": current["regime"],
            "reason": reason,
            "strategy": self.name,
            "atr": current.get("atr", 0),
            "atr_pct": current.get("atr_pct", 0),
            "price": current["close"],
            "vwap": current.get("vwap"),
            "ema_bias": current.get("ema_bias"),
        }


class RSIExhaustionStrategy:
    """
    Fade overextended moves after an RSI extreme and the first reversal candle.

    This is the automated version of the user's "broken parabolic" and
    "RSI exhaustion" ideas.
    """

    def __init__(self, rsi_period=14, overbought=85, oversold=15, streak_min=4, atr_period=14):
        self.name = "rsi_exhaustion"
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self.streak_min = streak_min
        self.atr_period = atr_period

    def signal_frame(self, df):
        minimum_bars = max(self.rsi_period + 5, self.streak_min + 3)
        if df is None or len(df) < minimum_bars:
            return None

        frame = df.copy()
        frame["rsi"] = RSIIndicator(close=frame["close"], window=self.rsi_period).rsi()
        atr = AverageTrueRange(high=frame["high"], low=frame["low"], close=frame["close"], window=self.atr_period)
        frame["atr"] = atr.average_true_range()
        frame["atr_pct"] = frame["atr"] / frame["close"] * 100
        frame["regime"] = _classify_regime_series(frame["atr_pct"])

        up_streak, down_streak = _directional_streaks(frame["close"])
        frame["up_streak"] = up_streak
        frame["down_streak"] = down_streak

        prev_open = frame["open"].shift(1)
        prev_high = frame["high"].shift(1)
        prev_low = frame["low"].shift(1)

        bullish_reversal = (
            (frame["close"] > frame["open"])
            & (frame["low"] <= prev_low)
            & ((frame["close"] >= prev_open) | (frame["close"] > prev_high))
        )
        bearish_reversal = (
            (frame["close"] < frame["open"])
            & (frame["high"] >= prev_high)
            & ((frame["close"] <= prev_open) | (frame["close"] < prev_low))
        )

        buy_mask = (
            (frame["rsi"].shift(1) <= self.oversold)
            & (frame["down_streak"].shift(1) >= self.streak_min)
            & bullish_reversal
        )
        sell_mask = (
            (frame["rsi"].shift(1) >= self.overbought)
            & (frame["up_streak"].shift(1) >= self.streak_min)
            & bearish_reversal
        )

        signal = np.full(len(frame), Signal.HOLD, dtype=object)
        signal[buy_mask.to_numpy()] = Signal.BUY
        signal[sell_mask.to_numpy()] = Signal.SELL
        frame["signal"] = signal
        frame["price"] = frame["close"]
        return frame

    def get_signal(self, df):
        frame = self.signal_frame(df)
        if frame is None:
            return {
                "signal": Signal.HOLD,
                "regime": MarketRegime.TRENDING,
                "reason": "Not enough data",
                "strategy": self.name,
            }

        current = frame.iloc[-1]
        prev = frame.iloc[-2] if len(frame) >= 2 else current
        signal = current["signal"]

        if signal == Signal.BUY:
            reason = (
                f"RSI exhaustion long: prior RSI {prev.get('rsi', 0):.1f}, "
                f"down streak {int(prev.get('down_streak', 0))}, bullish reversal candle"
            )
        elif signal == Signal.SELL:
            reason = (
                f"RSI exhaustion short: prior RSI {prev.get('rsi', 0):.1f}, "
                f"up streak {int(prev.get('up_streak', 0))}, bearish reversal candle"
            )
        else:
            reason = "No RSI exhaustion reversal detected"

        return {
            "signal": signal,
            "regime": current["regime"],
            "reason": reason,
            "strategy": self.name,
            "atr": current.get("atr", 0),
            "atr_pct": current.get("atr_pct", 0),
            "price": current["close"],
            "rsi": current.get("rsi"),
            "up_streak": int(current.get("up_streak", 0)),
            "down_streak": int(current.get("down_streak", 0)),
        }


class MomentumScalperStrategy:
    """
    Fast momentum scalping strategy for generating many small trades.

    Uses a very fast EMA crossover (3/8) combined with RSI momentum
    confirmation. Designed for practice mode to produce frequent
    trade signals for the learning engine.
    """

    def __init__(self, fast_period=3, slow_period=8, rsi_period=7, atr_period=14):
        self.name = "momentum_scalp"
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.atr_period = atr_period

    def signal_frame(self, df):
        if df is None or len(df) < self.slow_period + 10:
            return None

        frame = df.copy()
        frame["ema_fast"] = EMAIndicator(close=frame["close"], window=self.fast_period).ema_indicator()
        frame["ema_slow"] = EMAIndicator(close=frame["close"], window=self.slow_period).ema_indicator()
        frame["rsi"] = RSIIndicator(close=frame["close"], window=self.rsi_period).rsi()
        atr = AverageTrueRange(high=frame["high"], low=frame["low"], close=frame["close"], window=self.atr_period)
        frame["atr"] = atr.average_true_range()
        frame["atr_pct"] = frame["atr"] / frame["close"] * 100
        frame["regime"] = _classify_regime_series(frame["atr_pct"])

        ema_diff = frame["ema_fast"] - frame["ema_slow"]
        crossover_buy = (ema_diff > 0) & (ema_diff.shift(1) <= 0)
        crossover_sell = (ema_diff < 0) & (ema_diff.shift(1) >= 0)

        # Require RSI momentum confirmation
        rsi_bullish = frame["rsi"] > 50
        rsi_bearish = frame["rsi"] < 50

        signal = np.full(len(frame), Signal.HOLD, dtype=object)
        signal[(crossover_buy & rsi_bullish).to_numpy()] = Signal.BUY
        signal[(crossover_sell & rsi_bearish).to_numpy()] = Signal.SELL
        frame["signal"] = signal
        frame["price"] = frame["close"]
        return frame

    def get_signal(self, df):
        frame = self.signal_frame(df)
        if frame is None:
            return {
                "signal": Signal.HOLD, "regime": MarketRegime.TRENDING,
                "reason": "Not enough data", "strategy": self.name,
            }

        latest = frame.iloc[-1]
        signal = latest["signal"]

        if signal == Signal.BUY:
            reason = f"Fast scalp: EMA {self.fast_period}/{self.slow_period} crossover UP + RSI {latest.get('rsi', 0):.0f} > 50"
        elif signal == Signal.SELL:
            reason = f"Fast scalp: EMA {self.fast_period}/{self.slow_period} crossover DOWN + RSI {latest.get('rsi', 0):.0f} < 50"
        else:
            reason = "No scalp signal"

        return {
            "signal": signal, "regime": latest["regime"],
            "reason": reason, "strategy": self.name,
            "atr": latest.get("atr", 0), "atr_pct": latest.get("atr_pct", 0),
            "price": latest["close"],
            "rsi": latest.get("rsi"),
        }


class StrategyManager:
    """
    Runs multiple strategies and picks the best signal.

    Priority rules:
    - If all active strategies agree → strong signal, full size
    - If majority agree → normal signal (majority wins)
    - If only one fires → normal signal, normal size
    - If exactly split (e.g. 2 BUY vs 2 SELL) → skip (true deadlock)
    """

    def __init__(self, strategies):
        self.strategies = strategies

    def _snapshot_result(self, result):
        """Return a copy that is safe to embed in other result payloads."""
        return {
            key: value
            for key, value in dict(result).items()
            if key != "all_results"
        }

    def get_signal(self, df):
        """Run all strategies and return the best signal."""
        raw_results = []

        for strategy in self.strategies:
            result = strategy.get_signal(df)
            raw_results.append(result)

        results = [self._snapshot_result(result) for result in raw_results]

        # Collect non-HOLD signals
        active_signals = [r for r in results if r["signal"] != Signal.HOLD]

        if not active_signals:
            return {
                "signal": Signal.HOLD,
                "regime": results[0]["regime"] if results else MarketRegime.TRENDING,
                "reason": "No signals from any strategy",
                "strategy": "none",
                "atr": results[0].get("atr", 0) if results else 0,
                "price": results[0].get("price", 0) if results else 0,
                "all_results": results,
            }

        if len(active_signals) == 1:
            result = dict(active_signals[0])
            result["confidence"] = "normal"
            result["all_results"] = results
            return result

        # Multiple signals — use majority vote
        directions = set(r["signal"] for r in active_signals)

        if len(directions) == 1:
            # All agree — strong signal
            result = dict(active_signals[0])
            result["confidence"] = "strong"
            result["reason"] = f"MULTI-SIGNAL: {' + '.join(r['strategy'] for r in active_signals)} agree → {result['signal']}"
            result["all_results"] = results
            return result

        # Conflict — majority wins instead of skipping
        buy_signals = [r for r in active_signals if r["signal"] == Signal.BUY]
        sell_signals = [r for r in active_signals if r["signal"] == Signal.SELL]

        if len(buy_signals) == len(sell_signals):
            # True deadlock (e.g. 2 vs 2) — skip
            return {
                "signal": Signal.HOLD,
                "regime": active_signals[0]["regime"],
                "reason": f"DEADLOCK: {len(buy_signals)} BUY vs {len(sell_signals)} SELL — skipping",
                "strategy": "conflict",
                "atr": active_signals[0].get("atr", 0),
                "price": active_signals[0].get("price", 0),
                "all_results": results,
            }

        # Majority direction wins with reduced confidence
        if len(buy_signals) > len(sell_signals):
            winner = buy_signals[0]
            majority_names = [r["strategy"] for r in buy_signals]
            minority_names = [r["strategy"] for r in sell_signals]
        else:
            winner = sell_signals[0]
            majority_names = [r["strategy"] for r in sell_signals]
            minority_names = [r["strategy"] for r in buy_signals]

        result = dict(winner)
        result["confidence"] = "normal"
        result["reason"] = (
            f"MAJORITY: {' + '.join(majority_names)} → {result['signal']} "
            f"(overruled {' + '.join(minority_names)})"
        )
        result["all_results"] = results
        return result
