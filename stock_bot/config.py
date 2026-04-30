"""
Application-wide constants shared by all bot instances.
Per-bot values (token, DB path, log path, features) live in configs/bot-N.json.
"""

from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Market hours (local time ranges, inclusive)
# ---------------------------------------------------------------------------
IST = ZoneInfo("Asia/Kolkata")
EST = ZoneInfo("America/New_York")

MARKET_HOURS = {
    "NSE":    {"tz": IST, "open": (9, 15),  "close": (15, 30)},
    "BSE":    {"tz": IST, "open": (9, 15),  "close": (15, 30)},
    "NASDAQ": {"tz": EST, "open": (9, 30),  "close": (16, 0)},
    "NYSE":   {"tz": EST, "open": (9, 30),  "close": (16, 0)},
}

INDIAN_EXCHANGES = {"NSE", "BSE"}
US_EXCHANGES     = {"NASDAQ", "NYSE"}

# ---------------------------------------------------------------------------
# EMA spans (in weeks)
# ---------------------------------------------------------------------------
EMA_SPANS: dict[str, int] = {
    "EMA_10W": 10,
    "EMA_40W": 40,
}

EMA_HISTORY_MULTIPLIER: int = 3   # fetch 3× the longest span for reliable seeding

# ---------------------------------------------------------------------------
# Currency symbols by exchange
# ---------------------------------------------------------------------------
CURRENCY_SYMBOL: dict[str, str] = {
    "NSE":    "₹",
    "BSE":    "₹",
    "NASDAQ": "$",
    "NYSE":   "$",
}
