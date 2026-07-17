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
    "EMA_20W": 20,
    "EMA_30W": 30,
    "EMA_40W": 40,
}

EMA_HISTORY_MULTIPLIER: int = 3   # fetch 3× the longest span for reliable seeding

# Every stock on the watchlist or in the portfolio automatically gets these
# EMA alerts (fired when price is within the threshold % of the EMA).
DEFAULT_ALERT_INDICATORS: tuple[str, ...] = ("EMA_10W", "EMA_20W", "EMA_30W", "EMA_40W")
DEFAULT_ALERT_THRESHOLD_PCT: float = 2.0

# Pre-market morning scan: local (hour, minute) per market region, weekdays.
# NSE/BSE open 9:15 IST; NASDAQ/NYSE open 9:30 ET.
MORNING_SCAN_LOCAL_TIME: tuple[int, int] = (8, 30)

# ---------------------------------------------------------------------------
# Currency symbols by exchange
# ---------------------------------------------------------------------------
CURRENCY_SYMBOL: dict[str, str] = {
    "NSE":    "₹",
    "BSE":    "₹",
    "NASDAQ": "$",
    "NYSE":   "$",
}
