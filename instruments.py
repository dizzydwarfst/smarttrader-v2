"""
instruments.py — OANDA instrument definitions

OANDA uses underscore-separated instrument names:
  Gold  = XAU_USD
  Silver = XAG_USD
  Dollar/Yen = USD_JPY

No special "contract" objects needed like IBKR — just string names.
"""


def get_instruments():
    """Returns a list of OANDA instrument names we trade."""
    return [
        "XAU_USD",
        "XAG_USD",
        "USD_JPY",
        "EUR_USD",
        "GBP_USD",
        "AUD_USD",
        "EUR_JPY",
    ]


def get_instrument_info():
    """
    Returns metadata about each instrument for risk calculations.

    pip_size = smallest meaningful price move
    min_units = minimum trade size in OANDA units
    display_name = human-readable name
    """
    return {
        "XAU_USD": {
            "display_name": "Gold",
            "pip_size": 0.01,        # Gold moves in $0.01 increments
            "min_units": 1,          # 1 unit = 1 oz of gold
            "precision": 3,          # Price decimal places
            "atr_period": 14,
            "max_spread_pips": 180,
        },
        "XAG_USD": {
            "display_name": "Silver",
            "pip_size": 0.001,       # Silver moves in $0.001 increments
            "min_units": 1,          # 1 unit = 1 oz of silver
            "precision": 4,
            "atr_period": 14,
            "max_spread_pips": 40,
        },
        "USD_JPY": {
            "display_name": "USD/JPY",
            "pip_size": 0.01,        # JPY pairs use 2 decimal pips
            "min_units": 1,          # 1 unit = 1 USD
            "precision": 3,
            "atr_period": 14,
            "max_spread_pips": 3,
        },
        "EUR_USD": {
            "display_name": "EUR/USD",
            "pip_size": 0.0001,      # Major FX pairs use 4 decimal pips
            "min_units": 1,
            "precision": 5,
            "atr_period": 14,
            "max_spread_pips": 2.5,
        },
        "GBP_USD": {
            "display_name": "GBP/USD",
            "pip_size": 0.0001,
            "min_units": 1,
            "precision": 5,
            "atr_period": 14,
            "max_spread_pips": 3.5,
        },
        "AUD_USD": {
            "display_name": "AUD/USD",
            "pip_size": 0.0001,
            "min_units": 1,
            "precision": 5,
            "atr_period": 14,
            "max_spread_pips": 2.5,
        },
        "EUR_JPY": {
            "display_name": "EUR/JPY",
            "pip_size": 0.01,
            "min_units": 1,
            "precision": 3,
            "atr_period": 14,
            "max_spread_pips": 4.5,
        },
    }
