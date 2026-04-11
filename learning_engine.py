"""
learning_engine.py — Self-Tuning & Regime Adaptation

This is the "brain" that makes the bot learn from its mistakes.

How it works:
1. Collects trade history from the journal
2. Tests different parameter combinations against recent data
3. If a better combo is found (>15% improvement), adopts it gradually
4. Logs every change so you can see exactly what and why

What it tunes:
- Fast EMA period (range: 5-15)
- Slow EMA period (range: 15-50)
- Breakout lookback (range: 6-30)
- Breakout volume multiplier (range: 0.9-1.5)
- Stop-loss ATR multiplier (range: 1.0-3.0)

Safety rails:
- Needs minimum 10 trades before any changes
- Max 1 parameter change per learning cycle
- Changes must show >15% improvement to be adopted
- All changes are logged and reversible
"""

import itertools
from datetime import datetime, timedelta
import pandas as pd

from config import config
from trade_journal import TradeJournal
from strategy import EMAStrategy, BreakoutStrategy, VWAPBounceStrategy, RSIExhaustionStrategy, Signal


class LearningEngine:
    """Analyzes trade history and optimizes bot parameters."""

    # ─── Parameter ranges (safety bounds) ────────────────
    FAST_EMA_RANGE = range(5, 16)       # 5 to 15
    SLOW_EMA_RANGE = range(15, 51, 2)   # 15 to 50, step 2
    STOP_LOSS_RANGE = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

    # RSI exhaustion tuning ranges
    RSI_OB_RANGE = [70, 75, 80, 85]
    RSI_OS_RANGE = [15, 20, 25, 30]
    RSI_STREAK_RANGE = [2, 3, 4]

    # VWAP bounce tuning ranges
    VWAP_WICK_RANGE = [1.0, 1.25, 1.5, 2.0]
    VWAP_VOL_RANGE = [0.8, 1.0, 1.2, 1.5]

    def __init__(self, journal: TradeJournal, strategy: EMAStrategy, breakout_strategy=None,
                 vwap_strategy=None, rsi_strategy=None, ai_advisor=None, memory=None):
        self.journal = journal
        self.strategy = strategy
        self.breakout_strategy = breakout_strategy
        self.vwap_strategy = vwap_strategy
        self.rsi_strategy = rsi_strategy
        self.ai_advisor = ai_advisor
        self.memory = memory
        self.last_run = None
        self.last_trade_count = 0
        self.last_ai_suggestion = None
        self._load_state()

    def _load_state(self):
        """Restore learning progress so the bot does not relearn the same batch after a restart."""
        state = self.journal.get_learning_state()

        last_run = state.get("last_run")
        if last_run:
            try:
                self.last_run = datetime.fromisoformat(last_run)
            except ValueError:
                self.last_run = None

        last_trade_count = state.get("last_trade_count")
        if last_trade_count:
            try:
                self.last_trade_count = int(last_trade_count)
            except ValueError:
                self.last_trade_count = 0

        # If the journal already has prior learning history but no persisted state yet,
        # avoid immediately reprocessing the same trade batch after this code upgrade.
        if self.last_trade_count == 0 and self.journal.get_param_history(limit=1):
            stats = self.journal.get_trade_stats(days=config.LEARNING_LOOKBACK_WEEKS * 7)
            self.last_trade_count = stats["total"]

    def _save_state(self):
        self.journal.set_learning_state(
            last_run=self.last_run,
            last_trade_count=self.last_trade_count,
        )

    def should_run(self):
        """Check if it's time to run the learning cycle."""
        if not config.LEARNING_ENABLED:
            return False

        now = datetime.now()
        stats = self.journal.get_trade_stats(days=config.LEARNING_LOOKBACK_WEEKS * 7)

        if stats["total"] < config.MIN_TRADES_FOR_LEARNING:
            return False

        learning_day = config.LEARNING_DAY.lower()
        if learning_day not in {"adaptive", "any"} and now.strftime("%A").lower() != learning_day:
            return False

        if self.last_run and (now - self.last_run) < timedelta(minutes=config.LEARNING_COOLDOWN_MINUTES):
            return False

        if stats["total"] - self.last_trade_count < config.LEARNING_MIN_NEW_TRADES:
            return False

        return True

    def run_learning_cycle(self, price_data: dict):
        """
        Main learning function. Runs adaptively after enough new trades.
        
        Args:
            price_data: dict of instrument_name → DataFrame with OHLCV data
        
        Returns:
            dict of changes made (or empty dict if no changes)
        """
        print(f"\n{'='*50}")
        print(f"  🧠 Learning Engine — Running Analysis")
        print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}")

        self.last_run = datetime.now()

        # ─── Step 1: Check if we have enough data ────────
        stats = self.journal.get_trade_stats(
            days=config.LEARNING_LOOKBACK_WEEKS * 7
        )
        recent_trades = self.journal.get_recent_trades(days=config.LEARNING_LOOKBACK_WEEKS * 7)

        if self.memory:
            self.memory.refresh_skills_snapshot(
                stats=stats,
                recent_trades=recent_trades,
                param_history=self.journal.get_param_history(limit=10),
            )

        if stats["total"] < config.MIN_TRADES_FOR_LEARNING:
            print(f"  ⏳ Only {stats['total']} trades — need {config.MIN_TRADES_FOR_LEARNING} before learning")
            print(f"     Keep paper trading! Learning will kick in soon.")
            if self.memory:
                self.memory.append_diary_entry(
                    "Learning cycle",
                    "Performance review finished with no parameter changes.",
                    details=[
                        f"Trades reviewed: {stats['total']} | win rate {stats['win_rate']:.1%} | total P&L ${stats['total_pnl']:+.2f}",
                    ],
                )
            return {}

        self.last_trade_count = stats["total"]

        # Print current performance
        self.journal.print_performance_report(days=config.LEARNING_LOOKBACK_WEEKS * 7)

        # Print per-instrument strategy scorecard
        scorecard = self.journal.get_strategy_scorecard(
            days=config.LEARNING_LOOKBACK_WEEKS * 7,
            min_trades=2,
        )
        leaders = scorecard.get("leaders", {})
        by_instrument = leaders.get("by_instrument", [])
        if by_instrument:
            print(f"\n  📊 Best strategy per instrument:")
            for entry in by_instrument[:7]:
                print(
                    f"     {entry.get('instrument', '?')}: "
                    f"{entry.get('strategy_name', '?')} "
                    f"({entry.get('trades', 0)} trades, "
                    f"WR {entry.get('win_rate', 0):.0%}, "
                    f"PF {entry.get('profit_factor', 0):.1f})"
                )

        # AI strategy preference analysis
        if self.ai_advisor and config.ai_learning_enabled and by_instrument:
            try:
                prefs = self.ai_advisor.suggest_strategy_preferences(scorecard)
                if prefs:
                    print(f"  🤖 AI strategy preferences: {prefs.get('summary', 'No summary')}")
                    if self.memory:
                        pref_details = []
                        for inst, info in (prefs.get("preferences") or {}).items():
                            pref_details.append(f"{inst}: {info.get('preferred', '?')} — {info.get('reason', '')}")
                        if pref_details:
                            self.memory.append_diary_entry(
                                "AI strategy preferences",
                                prefs.get("summary", "AI analyzed per-instrument strategy performance."),
                                details=pref_details[:7],
                            )
            except Exception as exc:
                logger.warning(f"AI strategy preference failed: {exc}")

        # ─── Step 2: Test parameter combinations ─────────
        best_params = self._optimize_parameters(price_data, stats)

        if not best_params:
            print(f"  ✅ Current parameters are already optimal — no changes needed")
            self._save_state()
            return {}

        # ─── Step 3: Apply changes (one at a time) ───────
        changes = self._apply_changes(best_params, stats)

        if self.last_ai_suggestion:
            print(f"  🤖 AI suggestion: {self.last_ai_suggestion.get('reason', 'No reason provided')}")

        self._update_memory(stats, recent_trades, changes, best_params)
        self._save_state()
        return changes

    def _optimize_parameters(self, price_data, current_stats):
        """
        Test different parameter combinations on recent price data.

        Optimizes EMA, Breakout, RSI Exhaustion, and VWAP Bounce parameters.
        Uses walk-forward backtesting with take-profit simulation.
        """
        current_score = current_stats["profit_factor"]
        if current_score == float("inf"):
            current_score = 5.0  # Cap for comparison

        best_score = current_score
        best_params = None
        combos_tested = 0
        self.last_ai_suggestion = None

        current_breakout_lookback = (
            self.breakout_strategy.lookback if self.breakout_strategy else config.BREAKOUT_LOOKBACK
        )
        current_breakout_volume_mult = (
            self.breakout_strategy.volume_mult if self.breakout_strategy else config.BREAKOUT_VOLUME_MULT
        )

        fast_emas = [5, 7, 9, 12, 15]
        slow_emas = [15, 18, 21, 26, 30, 40, 50]
        stop_losses = [1.0, 1.5, 2.0, 2.5]
        ema_pairs = [(fast, slow) for fast, slow in itertools.product(fast_emas, slow_emas) if fast < slow]
        breakout_lookbacks = []
        breakout_volume_mults = []
        estimated_combos = len(ema_pairs) * len(stop_losses)

        if self.breakout_strategy:
            breakout_lookbacks = sorted({
                8, 10, 14, 20,
                max(6, current_breakout_lookback),
            })
            breakout_volume_mults = sorted({
                0.9, 1.0, 1.1, 1.2, 1.3,
                round(current_breakout_volume_mult, 2),
            })
            estimated_combos += len(breakout_lookbacks) * len(breakout_volume_mults)

        if self.rsi_strategy:
            estimated_combos += len(self.RSI_OB_RANGE) * len(self.RSI_OS_RANGE) * len(self.RSI_STREAK_RANGE)

        if self.vwap_strategy:
            estimated_combos += len(self.VWAP_WICK_RANGE) * len(self.VWAP_VOL_RANGE)

        if self.ai_advisor and config.ai_learning_enabled:
            estimated_combos += 1

        print(f"  🔬 Testing parameter combinations ({estimated_combos} candidates)...")

        # ─── EMA + Stop-loss optimization ────────────────
        for fast, slow in ema_pairs:
            for sl_mult in stop_losses:
                score = self._backtest_params(
                    price_data, fast, slow, sl_mult,
                    breakout_lookback=current_breakout_lookback,
                    breakout_volume_mult=current_breakout_volume_mult,
                )
                combos_tested += 1
                if score > best_score:
                    best_score = score
                    best_params = {
                        "fast_ema": fast, "slow_ema": slow,
                        "stop_loss_mult": sl_mult,
                        "score": score, "source": "backtest",
                    }

        # ─── Breakout optimization ───────────────────────
        if self.breakout_strategy:
            for lookback, volume_mult in itertools.product(breakout_lookbacks, breakout_volume_mults):
                score = self._backtest_params(
                    price_data,
                    self.strategy.fast_period, self.strategy.slow_period,
                    config.STOP_LOSS_ATR_MULT,
                    breakout_lookback=lookback, breakout_volume_mult=volume_mult,
                )
                combos_tested += 1
                if score > best_score:
                    best_score = score
                    best_params = {
                        "fast_ema": self.strategy.fast_period,
                        "slow_ema": self.strategy.slow_period,
                        "stop_loss_mult": config.STOP_LOSS_ATR_MULT,
                        "breakout_lookback": lookback,
                        "breakout_volume_mult": volume_mult,
                        "score": score, "source": "backtest",
                    }

        # ─── RSI Exhaustion optimization ─────────────────
        if self.rsi_strategy:
            for ob, os_val, streak in itertools.product(
                self.RSI_OB_RANGE, self.RSI_OS_RANGE, self.RSI_STREAK_RANGE
            ):
                score = self._backtest_rsi_params(price_data, ob, os_val, streak)
                combos_tested += 1
                if score > best_score:
                    best_score = score
                    best_params = {
                        "fast_ema": self.strategy.fast_period,
                        "slow_ema": self.strategy.slow_period,
                        "stop_loss_mult": config.STOP_LOSS_ATR_MULT,
                        "rsi_overbought": ob,
                        "rsi_oversold": os_val,
                        "rsi_streak_min": streak,
                        "score": score, "source": "backtest_rsi",
                    }

        # ─── VWAP Bounce optimization ────────────────────
        if self.vwap_strategy:
            for wick, vol in itertools.product(self.VWAP_WICK_RANGE, self.VWAP_VOL_RANGE):
                score = self._backtest_vwap_params(price_data, wick, vol)
                combos_tested += 1
                if score > best_score:
                    best_score = score
                    best_params = {
                        "fast_ema": self.strategy.fast_period,
                        "slow_ema": self.strategy.slow_period,
                        "stop_loss_mult": config.STOP_LOSS_ATR_MULT,
                        "vwap_wick_ratio": wick,
                        "vwap_volume_mult": vol,
                        "score": score, "source": "backtest_vwap",
                    }

        # ─── AI candidate ───────────────────────────────
        if self.ai_advisor and config.ai_learning_enabled:
            print("  🤖 Checking one AI candidate...")
        ai_candidate = self._get_ai_candidate(current_stats)
        if ai_candidate:
            ai_score = self._backtest_params(
                price_data,
                ai_candidate["fast_ema"], ai_candidate["slow_ema"],
                ai_candidate["stop_loss_mult"],
                breakout_lookback=ai_candidate.get("breakout_lookback"),
                breakout_volume_mult=ai_candidate.get("breakout_volume_mult"),
            )
            combos_tested += 1
            self.last_ai_suggestion = dict(ai_candidate)
            self.last_ai_suggestion["score"] = ai_score
            if ai_score > best_score:
                best_score = ai_score
                best_params = dict(ai_candidate)
                best_params["score"] = ai_score

        print(f"  📊 Tested {combos_tested} combinations")

        if best_params:
            improvement = (best_score - current_score) / max(current_score, 0.01)

            if improvement >= config.LEARNING_IMPROVEMENT_THRESHOLD:
                # Walk-forward validation: test on out-of-sample data
                oos_data = self._build_oos_data(price_data)
                if oos_data:
                    oos_score = self._backtest_params(
                        oos_data,
                        best_params.get("fast_ema", self.strategy.fast_period),
                        best_params.get("slow_ema", self.strategy.slow_period),
                        best_params.get("stop_loss_mult", config.STOP_LOSS_ATR_MULT),
                        breakout_lookback=best_params.get("breakout_lookback"),
                        breakout_volume_mult=best_params.get("breakout_volume_mult"),
                    )
                    if oos_score < current_score * 0.8:
                        print(
                            f"  ⚠️  Out-of-sample validation failed: "
                            f"OOS score {oos_score:.2f} < 80% of current {current_score:.2f}"
                        )
                        print(f"     Rejecting candidate to avoid overfitting.")
                        return None
                    print(f"  ✅ Out-of-sample validation passed (OOS score: {oos_score:.2f})")

                print(f"  🎯 Found better params! Score: {current_score:.2f} → {best_score:.2f} (+{improvement:.1%})")
                best_params["improvement"] = improvement
                return best_params
            else:
                print(f"  📈 Best found: {best_score:.2f} vs current {current_score:.2f}")
                print(f"     Improvement ({improvement:.1%}) below threshold ({config.LEARNING_IMPROVEMENT_THRESHOLD:.0%})")

        return None

    def _build_oos_data(self, price_data):
        """Split price data: use the last 30% of each instrument as out-of-sample."""
        oos = {}
        for instrument, df in price_data.items():
            if df is None or len(df) < 60:
                continue
            split = int(len(df) * 0.7)
            oos[instrument] = df.iloc[split:].copy().reset_index(drop=True)
        return oos if oos else None

    def _get_ai_candidate(self, current_stats):
        if not self.ai_advisor or not config.ai_learning_enabled:
            return None

        recent_trades = self.journal.get_recent_trades(days=config.LEARNING_LOOKBACK_WEEKS * 7)
        current_config = {
            "fast_ema": self.strategy.fast_period,
            "slow_ema": self.strategy.slow_period,
            "breakout_lookback": (
                self.breakout_strategy.lookback if self.breakout_strategy else config.BREAKOUT_LOOKBACK
            ),
            "breakout_volume_mult": (
                self.breakout_strategy.volume_mult if self.breakout_strategy else config.BREAKOUT_VOLUME_MULT
            ),
            "stop_loss_mult": config.STOP_LOSS_ATR_MULT,
            "bar_granularity": config.BAR_GRANULARITY,
            "practice_style": config.PRACTICE_STYLE,
        }

        suggestion = self.ai_advisor.suggest_learning_adjustments(
            current_config=current_config,
            stats=current_stats,
            recent_trades=recent_trades,
        )
        if not suggestion:
            return None

        fast = suggestion.get("fast_ema") or self.strategy.fast_period
        slow = suggestion.get("slow_ema") or self.strategy.slow_period
        stop_loss = suggestion.get("stop_loss_mult") or config.STOP_LOSS_ATR_MULT
        breakout_lookback = suggestion.get("breakout_lookback")
        breakout_volume_mult = suggestion.get("breakout_volume_mult")

        if fast >= slow:
            return None

        return {
            "fast_ema": max(5, min(int(fast), 15)),
            "slow_ema": max(15, min(int(slow), 50)),
            "stop_loss_mult": max(1.0, min(float(stop_loss), 3.0)),
            "breakout_lookback": (
                max(6, min(int(breakout_lookback), 30))
                if breakout_lookback is not None else (
                    self.breakout_strategy.lookback if self.breakout_strategy else config.BREAKOUT_LOOKBACK
                )
            ),
            "breakout_volume_mult": (
                max(0.9, min(float(breakout_volume_mult), 1.5))
                if breakout_volume_mult is not None else (
                    self.breakout_strategy.volume_mult if self.breakout_strategy else config.BREAKOUT_VOLUME_MULT
                )
            ),
            "reason": suggestion.get("reason", "AI suggested a conservative adjustment"),
            "source": "ai",
        }

    def _backtest_params(self, price_data, fast_ema, slow_ema, stop_loss_mult,
                         breakout_lookback=None, breakout_volume_mult=None,
                         take_profit_mult=None):
        """
        Backtest a parameter set on recent price data with SL and TP simulation.

        Uses high/low prices for realistic SL/TP hit detection instead of
        only checking the close price.

        Returns a "score" (profit factor) for this parameter combo.
        Higher score = better parameters.
        """
        if take_profit_mult is None:
            take_profit_mult = config.TAKE_PROFIT_ATR_MULT

        total_profit = 0
        total_loss = 0
        ema_strategy = EMAStrategy(fast_period=fast_ema, slow_period=slow_ema)
        breakout_strategy = None
        if self.breakout_strategy:
            breakout_strategy = BreakoutStrategy(
                lookback=breakout_lookback or self.breakout_strategy.lookback,
                atr_threshold=self.breakout_strategy.atr_threshold,
                volume_mult=breakout_volume_mult or self.breakout_strategy.volume_mult,
                atr_period=self.breakout_strategy.atr_period,
            )

        for instrument, df in price_data.items():
            if df is None or len(df) < slow_ema + 20:
                continue

            test_df = df.tail(140).copy()
            ema_frame = ema_strategy.signal_frame(test_df)
            if ema_frame is None:
                continue

            ema_signals = ema_frame["signal"].to_numpy()
            prices = ema_frame["price"].to_numpy()
            highs = ema_frame["high"].to_numpy()
            lows = ema_frame["low"].to_numpy()
            atr_values = ema_frame["atr"].to_numpy()

            breakout_signals = None
            if breakout_strategy:
                breakout_frame = breakout_strategy.signal_frame(test_df)
                if breakout_frame is not None:
                    breakout_signals = breakout_frame["signal"].to_numpy()

            # Walk through bars and simulate trades
            position = None  # None, "BUY", or "SELL"
            entry_price = 0
            stop_price = 0
            tp_price = 0

            for i in range(slow_ema + 5, len(test_df)):
                signal = ema_signals[i]
                if breakout_signals is not None:
                    breakout_signal = breakout_signals[i]
                    if signal == Signal.HOLD:
                        signal = breakout_signal
                    elif breakout_signal != Signal.HOLD and breakout_signal != signal:
                        signal = Signal.HOLD

                price = prices[i]
                bar_high = highs[i]
                bar_low = lows[i]
                atr = atr_values[i]

                if pd.isna(atr) or atr == 0:
                    continue

                # Check if current position hit stop-loss or take-profit
                if position == "BUY":
                    if bar_low <= stop_price:
                        pnl = stop_price - entry_price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                        position = None
                    elif bar_high >= tp_price:
                        pnl = tp_price - entry_price
                        total_profit += pnl
                        position = None

                elif position == "SELL":
                    if bar_high >= stop_price:
                        pnl = entry_price - stop_price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                        position = None
                    elif bar_low <= tp_price:
                        pnl = entry_price - tp_price
                        total_profit += pnl
                        position = None

                # Check for new signals
                if signal == Signal.BUY and position != "BUY":
                    if position == "SELL":
                        pnl = entry_price - price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)

                    position = "BUY"
                    entry_price = price
                    stop_price = price - (atr * stop_loss_mult)
                    tp_price = price + (atr * take_profit_mult)

                elif signal == Signal.SELL and position != "SELL":
                    if position == "BUY":
                        pnl = price - entry_price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)

                    position = "SELL"
                    entry_price = price
                    stop_price = price + (atr * stop_loss_mult)
                    tp_price = price - (atr * take_profit_mult)

        # Calculate profit factor (our scoring metric)
        if total_loss == 0:
            return total_profit if total_profit > 0 else 0
        return total_profit / total_loss

    def _backtest_strategy_standalone(self, price_data, strategy):
        """Backtest any strategy that has a signal_frame() method."""
        total_profit = 0
        total_loss = 0
        sl_mult = config.STOP_LOSS_ATR_MULT
        tp_mult = config.TAKE_PROFIT_ATR_MULT

        for instrument, df in price_data.items():
            if df is None or len(df) < 50:
                continue
            test_df = df.tail(140).copy()
            frame = strategy.signal_frame(test_df)
            if frame is None:
                continue

            signals = frame["signal"].to_numpy()
            prices = frame["price"].to_numpy()
            highs = frame["high"].to_numpy()
            lows = frame["low"].to_numpy()
            atr_values = frame["atr"].to_numpy()

            position = None
            entry_price = 0
            stop_price = 0
            tp_price = 0

            for i in range(20, len(test_df)):
                price = prices[i]
                bar_high = highs[i]
                bar_low = lows[i]
                atr = atr_values[i]
                if pd.isna(atr) or atr == 0:
                    continue

                if position == "BUY":
                    if bar_low <= stop_price:
                        pnl = stop_price - entry_price
                        (total_profit if pnl > 0 else total_loss)
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                        position = None
                    elif bar_high >= tp_price:
                        total_profit += tp_price - entry_price
                        position = None
                elif position == "SELL":
                    if bar_high >= stop_price:
                        pnl = entry_price - stop_price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                        position = None
                    elif bar_low <= tp_price:
                        total_profit += entry_price - tp_price
                        position = None

                sig = signals[i]
                if sig == Signal.BUY and position != "BUY":
                    if position == "SELL":
                        pnl = entry_price - price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                    position = "BUY"
                    entry_price = price
                    stop_price = price - atr * sl_mult
                    tp_price = price + atr * tp_mult
                elif sig == Signal.SELL and position != "SELL":
                    if position == "BUY":
                        pnl = price - entry_price
                        if pnl > 0:
                            total_profit += pnl
                        else:
                            total_loss += abs(pnl)
                    position = "SELL"
                    entry_price = price
                    stop_price = price + atr * sl_mult
                    tp_price = price - atr * tp_mult

        if total_loss == 0:
            return total_profit if total_profit > 0 else 0
        return total_profit / total_loss

    def _backtest_rsi_params(self, price_data, overbought, oversold, streak_min):
        """Backtest RSI Exhaustion with specific parameter values."""
        strategy = RSIExhaustionStrategy(
            rsi_period=config.RSI_EXHAUSTION_PERIOD,
            overbought=overbought,
            oversold=oversold,
            streak_min=streak_min,
        )
        return self._backtest_strategy_standalone(price_data, strategy)

    def _backtest_vwap_params(self, price_data, wick_ratio, volume_mult):
        """Backtest VWAP Bounce with specific parameter values."""
        strategy = VWAPBounceStrategy(
            bias_ema_period=config.VWAP_BIAS_EMA,
            volume_lookback=config.VWAP_VOLUME_LOOKBACK,
            volume_mult=volume_mult,
            wick_ratio=wick_ratio,
        )
        return self._backtest_strategy_standalone(price_data, strategy)

    def _apply_changes(self, best_params, current_stats):
        """
        Apply parameter changes one at a time (conservative approach).
        
        Only change the ONE parameter that has the biggest impact.
        This prevents overfitting and makes it easier to track what worked.
        """
        changes = {}

        # Determine which parameter changed the most
        param_diffs = {}

        if best_params["fast_ema"] != self.strategy.fast_period:
            param_diffs["fast_ema"] = abs(
                best_params["fast_ema"] - self.strategy.fast_period
            )

        if best_params["slow_ema"] != self.strategy.slow_period:
            param_diffs["slow_ema"] = abs(
                best_params["slow_ema"] - self.strategy.slow_period
            )

        if best_params.get("stop_loss_mult") and \
           best_params["stop_loss_mult"] != config.STOP_LOSS_ATR_MULT:
            param_diffs["stop_loss_mult"] = abs(
                best_params["stop_loss_mult"] - config.STOP_LOSS_ATR_MULT
            )

        if self.breakout_strategy and best_params.get("breakout_lookback") is not None and \
           best_params["breakout_lookback"] != self.breakout_strategy.lookback:
            param_diffs["breakout_lookback"] = abs(
                best_params["breakout_lookback"] - self.breakout_strategy.lookback
            )

        if self.breakout_strategy and best_params.get("breakout_volume_mult") is not None and \
           best_params["breakout_volume_mult"] != self.breakout_strategy.volume_mult:
            param_diffs["breakout_volume_mult"] = abs(
                best_params["breakout_volume_mult"] - self.breakout_strategy.volume_mult
            )

        # RSI parameters
        if self.rsi_strategy and best_params.get("rsi_overbought") is not None and \
           best_params["rsi_overbought"] != self.rsi_strategy.overbought:
            param_diffs["rsi_overbought"] = abs(
                best_params["rsi_overbought"] - self.rsi_strategy.overbought
            )
        if self.rsi_strategy and best_params.get("rsi_oversold") is not None and \
           best_params["rsi_oversold"] != self.rsi_strategy.oversold:
            param_diffs["rsi_oversold"] = abs(
                best_params["rsi_oversold"] - self.rsi_strategy.oversold
            )
        if self.rsi_strategy and best_params.get("rsi_streak_min") is not None and \
           best_params["rsi_streak_min"] != self.rsi_strategy.streak_min:
            param_diffs["rsi_streak_min"] = abs(
                best_params["rsi_streak_min"] - self.rsi_strategy.streak_min
            )

        # VWAP parameters
        if self.vwap_strategy and best_params.get("vwap_wick_ratio") is not None and \
           best_params["vwap_wick_ratio"] != self.vwap_strategy.wick_ratio:
            param_diffs["vwap_wick_ratio"] = abs(
                best_params["vwap_wick_ratio"] - self.vwap_strategy.wick_ratio
            )
        if self.vwap_strategy and best_params.get("vwap_volume_mult") is not None and \
           best_params["vwap_volume_mult"] != self.vwap_strategy.volume_mult:
            param_diffs["vwap_volume_mult"] = abs(
                best_params["vwap_volume_mult"] - self.vwap_strategy.volume_mult
            )

        if not param_diffs:
            return changes

        # Change the most impactful parameter
        biggest_change = max(param_diffs, key=param_diffs.get)

        if biggest_change == "fast_ema":
            old = self.strategy.fast_period
            new = best_params["fast_ema"]
            self.strategy.fast_period = new
            config.FAST_EMA = new
            if config.is_practice and config.PRACTICE_STYLE == "active":
                config.PRACTICE_FAST_EMA = new
            changes["fast_ema"] = (old, new)

            self.journal.log_param_change(
                "fast_ema", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"],
                best_params["score"]
            )

        elif biggest_change == "slow_ema":
            old = self.strategy.slow_period
            new = best_params["slow_ema"]
            self.strategy.slow_period = new
            config.SLOW_EMA = new
            if config.is_practice and config.PRACTICE_STYLE == "active":
                config.PRACTICE_SLOW_EMA = new
            changes["slow_ema"] = (old, new)

            self.journal.log_param_change(
                "slow_ema", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"],
                best_params["score"]
            )

        elif biggest_change == "stop_loss_mult":
            old = config.STOP_LOSS_ATR_MULT
            new = best_params["stop_loss_mult"]
            config.STOP_LOSS_ATR_MULT = new
            changes["stop_loss_mult"] = (old, new)

            self.journal.log_param_change(
                "stop_loss_atr_mult", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"],
                best_params["score"]
            )

        elif biggest_change == "breakout_lookback":
            old = self.breakout_strategy.lookback
            new = int(best_params["breakout_lookback"])
            self.breakout_strategy.lookback = new
            config.BREAKOUT_LOOKBACK = new
            if config.is_practice and config.PRACTICE_STYLE == "active":
                config.PRACTICE_BREAKOUT_LOOKBACK = new
            changes["breakout_lookback"] = (old, new)

            self.journal.log_param_change(
                "breakout_lookback", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"],
                best_params["score"]
            )

        elif biggest_change == "breakout_volume_mult":
            old = self.breakout_strategy.volume_mult
            new = float(best_params["breakout_volume_mult"])
            self.breakout_strategy.volume_mult = new
            config.BREAKOUT_VOLUME_MULT = new
            if config.is_practice and config.PRACTICE_STYLE == "active":
                config.PRACTICE_BREAKOUT_VOLUME_MULT = new
            changes["breakout_volume_mult"] = (old, new)

            self.journal.log_param_change(
                "breakout_volume_mult", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"],
                best_params["score"]
            )

        elif biggest_change == "rsi_overbought":
            old = self.rsi_strategy.overbought
            new = float(best_params["rsi_overbought"])
            self.rsi_strategy.overbought = new
            config.RSI_EXHAUSTION_OVERBOUGHT = new
            changes["rsi_overbought"] = (old, new)
            self.journal.log_param_change(
                "rsi_overbought", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"], best_params["score"]
            )

        elif biggest_change == "rsi_oversold":
            old = self.rsi_strategy.oversold
            new = float(best_params["rsi_oversold"])
            self.rsi_strategy.oversold = new
            config.RSI_EXHAUSTION_OVERSOLD = new
            changes["rsi_oversold"] = (old, new)
            self.journal.log_param_change(
                "rsi_oversold", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"], best_params["score"]
            )

        elif biggest_change == "rsi_streak_min":
            old = self.rsi_strategy.streak_min
            new = int(best_params["rsi_streak_min"])
            self.rsi_strategy.streak_min = new
            config.RSI_EXHAUSTION_STREAK_MIN = new
            changes["rsi_streak_min"] = (old, new)
            self.journal.log_param_change(
                "rsi_streak_min", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"], best_params["score"]
            )

        elif biggest_change == "vwap_wick_ratio":
            old = self.vwap_strategy.wick_ratio
            new = float(best_params["vwap_wick_ratio"])
            self.vwap_strategy.wick_ratio = new
            config.VWAP_WICK_RATIO = new
            changes["vwap_wick_ratio"] = (old, new)
            self.journal.log_param_change(
                "vwap_wick_ratio", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"], best_params["score"]
            )

        elif biggest_change == "vwap_volume_mult":
            old = self.vwap_strategy.volume_mult
            new = float(best_params["vwap_volume_mult"])
            self.vwap_strategy.volume_mult = new
            config.VWAP_VOLUME_MULT = new
            changes["vwap_volume_mult"] = (old, new)
            self.journal.log_param_change(
                "vwap_volume_mult", old, new,
                f"Optimization found better performance (improvement: {best_params['improvement']:.1%})",
                current_stats["profit_factor"], best_params["score"]
            )

        return changes

    def get_learning_summary(self):
        """Get a summary of what the bot has learned so far."""
        param_history = self.journal.get_param_history(limit=50)
        stats = self.journal.get_trade_stats(days=30)

        summary = {
            "total_param_changes": len(param_history),
            "current_fast_ema": self.strategy.fast_period,
            "current_slow_ema": self.strategy.slow_period,
            "current_stop_loss_mult": config.STOP_LOSS_ATR_MULT,
            "current_breakout_lookback": (
                self.breakout_strategy.lookback if self.breakout_strategy else config.BREAKOUT_LOOKBACK
            ),
            "current_breakout_volume_mult": (
                self.breakout_strategy.volume_mult if self.breakout_strategy else config.BREAKOUT_VOLUME_MULT
            ),
            "current_win_rate": stats["win_rate"],
            "current_profit_factor": stats["profit_factor"],
            "recent_changes": param_history[:5],
            "last_learning_run": self.last_run.isoformat() if self.last_run else "Never",
            "last_ai_suggestion": self.last_ai_suggestion,
        }
        if self.rsi_strategy:
            summary["current_rsi_overbought"] = self.rsi_strategy.overbought
            summary["current_rsi_oversold"] = self.rsi_strategy.oversold
            summary["current_rsi_streak_min"] = self.rsi_strategy.streak_min
        if self.vwap_strategy:
            summary["current_vwap_wick_ratio"] = self.vwap_strategy.wick_ratio
            summary["current_vwap_volume_mult"] = self.vwap_strategy.volume_mult
        return summary

    def _update_memory(self, stats, recent_trades, changes, best_params):
        if not self.memory:
            return

        self.memory.refresh_skills_snapshot(
            stats=stats,
            recent_trades=recent_trades,
            param_history=self.journal.get_param_history(limit=10),
        )

        if changes:
            changed_fields = ", ".join(
                f"{name} {old} -> {new}" for name, (old, new) in changes.items()
            )
            summary = f"Learning adopted {changed_fields}."
        else:
            summary = "Learning reviewed performance and kept the current configuration."

        details = [
            f"Trades reviewed: {stats['total']} | win rate {stats['win_rate']:.1%} | total P&L ${stats['total_pnl']:+.2f}",
        ]
        if best_params:
            details.append(
                f"Best candidate score: {best_params.get('score', 0):.2f} from {best_params.get('source', 'backtest')}"
            )
        if self.last_ai_suggestion:
            details.append(f"AI suggestion: {self.last_ai_suggestion.get('reason', 'No reason provided')}")

        self.memory.append_diary_entry(
            "Learning cycle",
            summary,
            details=details,
        )
