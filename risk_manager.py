"""
risk_manager.py — Position Sizing & Risk Management

This is the most important module in the bot. Bad risk management
will lose money even with a winning strategy. Good risk management
keeps you in the game even with a losing streak.

Rules:
1. Never risk more than RISK_PER_TRADE (2%) of account on any single trade
2. Never have more than MAX_POSITIONS (3) open at once
3. Stop trading for the day if daily loss exceeds DAILY_LOSS_LIMIT (5%)
4. Every trade MUST have a stop-loss — no exceptions
5. In volatile markets, tighten stop-losses
6. In choppy markets, halve position size
"""

from config import config
from strategy import MarketRegime


class RiskManager:
    """Manages position sizing, stop-losses, and trading limits."""

    def __init__(self, journal):
        self.journal = journal  # Trade journal for checking open positions
        self.daily_loss_triggered = False

    def can_trade(self, account_value):
        """
        Check if we're allowed to open a new trade right now.
        
        Returns:
            (bool, str) — (allowed, reason if not allowed)
        """
        # ─── Check daily loss limit ──────────────────────
        if config.DAILY_LOSS_LIMIT_ENABLED:
            daily_pnl = self.journal.get_daily_pnl()
            daily_loss_limit = account_value * config.DAILY_LOSS_LIMIT

            if daily_pnl < -daily_loss_limit:
                self.daily_loss_triggered = True
                return False, f"Daily loss limit hit (${daily_pnl:.2f} < -${daily_loss_limit:.2f})"
        else:
            # Training mode: daily loss limit disabled, clear any prior trigger
            self.daily_loss_triggered = False

        # ─── Check max open positions ────────────────────
        if hasattr(self.journal, "get_open_position_count"):
            open_positions = self.journal.get_open_position_count()
        else:
            open_positions = len(self.journal.get_open_trades())
        if open_positions >= config.MAX_POSITIONS:
            return False, f"Max positions reached ({open_positions}/{config.MAX_POSITIONS})"

        return True, "OK"

    def calculate_position_size(
        self,
        account_value,
        entry_price,
        stop_loss_price,
        regime,
        size_mult=1.0,
        risk_per_trade_override=None,
        min_units=1,
    ):
        """
        Calculate how much to trade based on risk parameters.
        
        The key formula:
            position_size = (account * risk_per_trade) / (entry - stop_loss)
        
        This ensures that if we hit our stop-loss, we only lose 
        RISK_PER_TRADE percent of our account.
        
        Args:
            account_value: Total account value in USD
            entry_price: Where we plan to enter
            stop_loss_price: Where our stop-loss will be
            regime: Current market regime (affects sizing)
        
        Returns:
            float: Number of units to trade
        """
        # How much money we're willing to lose on this trade
        risk_pct = (
            float(risk_per_trade_override)
            if risk_per_trade_override is not None else config.effective_risk_per_trade
        )
        risk_amount = account_value * risk_pct

        # Distance from entry to stop-loss (per unit)
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            return 0  # Safety check

        # Base position size
        position_size = risk_amount / risk_per_unit

        # ─── Regime adjustment ───────────────────────────
        if regime == MarketRegime.CHOPPY:
            # Halve position size in choppy markets (more likely to stop out)
            position_size *= 0.5
        elif regime == MarketRegime.VOLATILE:
            # Reduce by 30% in volatile markets
            position_size *= 0.7

        # Round to reasonable lot size
        try:
            size_mult = float(size_mult)
        except (TypeError, ValueError):
            size_mult = 1.0

        position_size *= max(0.0, size_mult)
        position_size = max(min_units, round(position_size))

        return position_size

    def calculate_stop_loss(self, entry_price, direction, atr, regime):
        """
        Calculate stop-loss price based on ATR.
        
        Stop-loss distance = ATR × multiplier
        This means the stop adapts to market volatility:
        - Calm market → tight stop
        - Volatile market → wider stop (so you don't get stopped out by noise)
        
        Args:
            entry_price: Where we're entering
            direction: "BUY" or "SELL"
            atr: Current ATR value
            regime: Market regime (volatile = tighter stops)
        """
        multiplier = config.STOP_LOSS_ATR_MULT

        # In volatile markets, tighten stops to limit damage
        if regime == MarketRegime.VOLATILE:
            multiplier *= 0.8  # 20% tighter

        stop_distance = atr * multiplier

        if direction == "BUY":
            # For longs, stop-loss is below entry
            stop_loss = entry_price - stop_distance
        else:
            # For shorts, stop-loss is above entry
            stop_loss = entry_price + stop_distance

        return round(stop_loss, 5)

    def calculate_take_profit(self, entry_price, direction, atr):
        """
        Calculate take-profit price based on ATR.
        
        We want the take-profit to be further than the stop-loss
        (positive risk:reward ratio). Default is 3:1.5 = 2:1 R:R.
        """
        tp_distance = atr * config.TAKE_PROFIT_ATR_MULT

        if direction == "BUY":
            take_profit = entry_price + tp_distance
        else:
            take_profit = entry_price - tp_distance

        return round(take_profit, 5)

    def check_stop_loss(self, trade, current_price):
        """
        Check if a trade has hit its stop-loss or take-profit.

        Returns:
            exit_reason: "stop_loss", "take_profit", or None
        """
        direction = trade["direction"]
        stop_loss = trade["stop_loss"]
        take_profit = trade["take_profit"]

        if direction == "BUY":
            if current_price <= stop_loss:
                return "stop_loss"
            if take_profit and current_price >= take_profit:
                return "take_profit"
        elif direction == "SELL":
            if current_price >= stop_loss:
                return "stop_loss"
            if take_profit and current_price <= take_profit:
                return "take_profit"

        return None

    def calculate_trailing_stop(self, trade, current_price, atr):
        """
        Calculate a new trailing stop-loss if price has moved enough in profit.

        Trailing stop activates after price moves TRAILING_STOP_ACTIVATION_ATR
        in profit, then trails at TRAILING_STOP_DISTANCE_ATR behind the
        highest (for BUY) or lowest (for SELL) price reached.

        Returns:
            new_stop: float or None if no update needed
        """
        if not config.TRAILING_STOP_ENABLED or not atr or atr == 0:
            return None

        direction = trade["direction"]
        entry_price = trade["entry_price"]
        current_stop = trade["stop_loss"]
        activation_distance = atr * config.TRAILING_STOP_ACTIVATION_ATR
        trail_distance = atr * config.TRAILING_STOP_DISTANCE_ATR

        if direction == "BUY":
            profit_distance = current_price - entry_price
            if profit_distance < activation_distance:
                return None
            new_stop = current_price - trail_distance
            if new_stop > current_stop:
                return round(new_stop, 5)

        elif direction == "SELL":
            profit_distance = entry_price - current_price
            if profit_distance < activation_distance:
                return None
            new_stop = current_price + trail_distance
            if new_stop < current_stop:
                return round(new_stop, 5)

        return None

    def get_time_of_day_multiplier(self):
        """
        Return a size multiplier (0.5-1.25) based on historical hourly performance.

        Good hours (positive avg P&L) get full or boosted size.
        Bad hours (negative avg P&L with 3+ trades) get reduced size.
        Unknown hours get full size.
        """
        from datetime import datetime as _dt
        hourly = self.journal.get_hourly_performance(days=30)
        current_hour = _dt.utcnow().hour
        stats = hourly.get(current_hour)
        if not stats or stats["trades"] < 3:
            return 1.0
        if stats["avg_pnl"] > 0 and stats["win_rate"] > 0.55:
            return 1.1
        if stats["avg_pnl"] < 0 and stats["win_rate"] < 0.4:
            return 0.6
        return 1.0

    def reset_daily_limit(self):
        """Call this at the start of each trading day."""
        self.daily_loss_triggered = False
