"""
Central configuration for the stock alert bot.
All secrets come from environment variables; all tunable constants live here.
"""

import os
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///stock_bot.db")

# ---------------------------------------------------------------------------
# Scheduler intervals (seconds)
# ---------------------------------------------------------------------------
ALERT_CHECK_INTERVAL_MARKET_HOURS: int = 30 * 60   # 30 min
ALERT_CHECK_INTERVAL_OFF_HOURS: int = 60 * 60       # 60 min

# ---------------------------------------------------------------------------
# Market hours (local time ranges, inclusive)
# ---------------------------------------------------------------------------
IST = ZoneInfo("Asia/Kolkata")
EST = ZoneInfo("America/New_York")

MARKET_HOURS = {
    "NSE": {"tz": IST, "open": (9, 15), "close": (15, 30)},
    "BSE": {"tz": IST, "open": (9, 15), "close": (15, 30)},
    "NASDAQ": {"tz": EST, "open": (9, 30), "close": (16, 0)},
    "NYSE": {"tz": EST, "open": (9, 30), "close": (16, 0)},
}

INDIAN_EXCHANGES = {"NSE", "BSE"}
US_EXCHANGES = {"NASDAQ", "NYSE"}

# ---------------------------------------------------------------------------
# Alert deduplication window
# ---------------------------------------------------------------------------
ALERT_COOLDOWN_HOURS: int = 2

# ---------------------------------------------------------------------------
# EMA spans (in weeks)
# ---------------------------------------------------------------------------
EMA_SPANS: dict[str, int] = {
    "EMA_10W": 10,
    "EMA_40W": 40,
}

# How many weeks of history to fetch for reliable EMA seeding
EMA_HISTORY_MULTIPLIER: int = 3   # fetch 3× the span

# ---------------------------------------------------------------------------
# Currency symbols by exchange
# ---------------------------------------------------------------------------
CURRENCY_SYMBOL: dict[str, str] = {
    "NSE": "₹",
    "BSE": "₹",
    "NASDAQ": "$",
    "NYSE": "$",
}
