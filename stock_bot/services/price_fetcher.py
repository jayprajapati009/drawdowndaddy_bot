"""
yfinance wrapper with EMA calculation.

Design principles (learned from prior yfinance instability):
- One ticker at a time — no bulk downloads, no MultiIndex columns
- Validate immediately after every download before touching the data
- Normalise into a single schema (flat columns, sorted date index)
- Retry transient failures; skip and log bad tickers rather than crashing
- Treat yfinance as a best-effort external source, not a clean database
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from stock_bot.config import EMA_HISTORY_MULTIPLIER, EMA_SPANS

_RETRY_ATTEMPTS = 3
_RETRY_DELAY    = 3   # seconds between retries
_BATCH_WORKERS  = 8   # parallel threads for batch price fetches

logger = logging.getLogger(__name__)

# Per-scheduler-tick cache: ticker → validated, normalised weekly DataFrame
_weekly_cache: dict[str, pd.DataFrame] = {}


def clear_cache() -> None:
    """Flush stale data at the start of each scheduler tick."""
    _weekly_cache.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_price(ticker: str) -> Optional[float]:
    """
    Return the most recent closing price for *ticker*.
    Retries up to _RETRY_ATTEMPTS times on empty or failed responses.
    """
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            raw = yf.Ticker(ticker).history(period="5d", interval="1d")
            df = _normalise(raw, ticker)
            if df is not None:
                return float(df["Close"].iloc[-1])
            logger.warning(
                "Empty price data for %s (attempt %d/%d)", ticker, attempt, _RETRY_ATTEMPTS
            )
        except Exception as exc:
            logger.warning(
                "Price fetch error for %s (attempt %d/%d): %s",
                ticker, attempt, _RETRY_ATTEMPTS, exc,
            )
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_DELAY)

    logger.error("Giving up on price for %s after %d attempts", ticker, _RETRY_ATTEMPTS)
    return None


def get_ema(ticker: str, indicator: str) -> Optional[float]:
    """
    Return the most recent weekly EMA value for *indicator* on *ticker*.
    Returns None if the indicator is unknown or data cannot be fetched.
    """
    span = EMA_SPANS.get(indicator.upper())
    if span is None:
        logger.error("Unknown indicator '%s' — valid options: %s", indicator, list(EMA_SPANS))
        return None

    df = _fetch_weekly(ticker)
    if df is None:
        return None

    return float(df["Close"].ewm(span=span, adjust=False).mean().iloc[-1])


def get_prices_batch(tickers: list[str]) -> dict[str, Optional[float]]:
    """Fetch current prices for multiple tickers in parallel."""
    if not tickers:
        return {}
    workers = min(len(tickers), _BATCH_WORKERS)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {ticker: pool.submit(get_current_price, ticker) for ticker in tickers}
        return {ticker: f.result() for ticker, f in futures.items()}


def get_all_emas(ticker: str) -> dict[str, Optional[float]]:
    """Return every configured EMA value for *ticker* in one call."""
    return {ind: get_ema(ticker, ind) for ind in EMA_SPANS}


def get_price_on_date(ticker: str, target_date: date) -> Optional[float]:
    """
    Return the closing price for *ticker* on *target_date*.

    If the market was closed that day (weekend / holiday), returns the close
    from the nearest prior trading day within a 7-day lookback window.
    Returns None if no data is found in that window.
    """
    if target_date > date.today():
        logger.warning("Requested future date %s for %s — not allowed", target_date, ticker)
        return None

    # Fetch a small window: target_date up to +7 days forward so yfinance
    # doesn't return an empty range, then we take the first row on/after target.
    # We actually want the close ON or BEFORE target_date, so fetch a window
    # ending at target_date + 1 (end is exclusive in yfinance).
    start = target_date - timedelta(days=7)   # lookback for non-trading days
    end   = target_date + timedelta(days=1)   # exclusive upper bound

    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            raw = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat(), interval="1d")
            df = _normalise(raw, ticker)
            if df is not None and not df.empty:
                # Normalise dates to plain date objects for comparison
                df["DateOnly"] = pd.to_datetime(df["Date"]).dt.date
                # Find rows on or before target_date, take the most recent
                valid = df[df["DateOnly"] <= target_date]
                if not valid.empty:
                    row = valid.iloc[-1]
                    actual_date = row["DateOnly"]
                    price = float(row["Close"])
                    if actual_date != target_date:
                        logger.info(
                            "%s was not a trading day — using close from %s instead",
                            target_date, actual_date,
                        )
                    return price
            logger.warning(
                "No price data for %s on %s (attempt %d/%d)", ticker, target_date, attempt, _RETRY_ATTEMPTS
            )
        except Exception as exc:
            logger.warning(
                "Historical price fetch error for %s on %s (attempt %d/%d): %s",
                ticker, target_date, attempt, _RETRY_ATTEMPTS, exc,
            )
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_DELAY)

    logger.error("Could not fetch price for %s on %s after %d attempts", ticker, target_date, _RETRY_ATTEMPTS)
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_weekly(ticker: str) -> Optional[pd.DataFrame]:
    """
    Download 2 years of weekly closes for *ticker*, normalise, cache, and return.
    Returns None if data cannot be obtained after all retries.
    """
    if ticker in _weekly_cache:
        return _weekly_cache[ticker]

    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            raw = yf.Ticker(ticker).history(period="2y", interval="1wk")
            df = _normalise(raw, ticker)
            if df is not None:
                _weekly_cache[ticker] = df
                logger.debug("Cached %d weekly rows for %s", len(df), ticker)
                return df
            logger.warning(
                "Empty weekly data for %s (attempt %d/%d)", ticker, attempt, _RETRY_ATTEMPTS
            )
        except Exception as exc:
            logger.warning(
                "Weekly fetch error for %s (attempt %d/%d): %s",
                ticker, attempt, _RETRY_ATTEMPTS, exc,
            )
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_DELAY)

    logger.error("Giving up on weekly data for %s after %d attempts", ticker, _RETRY_ATTEMPTS)
    return None


def _normalise(raw: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    """
    Validate and normalise a raw yfinance DataFrame into a consistent schema:
      - Non-empty
      - Has a 'Close' column (case-insensitive)
      - Index reset to a plain RangeIndex; date in a 'date' column
      - Sorted ascending by date
      - No NaN in Close
      - Close values are positive

    Returns None if validation fails so callers can treat it as missing data.
    """
    # --- guard: empty ---
    if raw is None or raw.empty:
        logger.debug("Normalise: empty DataFrame for %s", ticker)
        return None

    df = raw.copy()

    # --- flatten MultiIndex columns (shouldn't happen for single-ticker, but guard anyway) ---
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(filter(None, map(str, col))).strip() for col in df.columns]
        logger.debug("Flattened MultiIndex columns for %s: %s", ticker, list(df.columns))

    # --- normalise column names to title-case so 'close', 'Close', 'CLOSE' all work ---
    df.columns = [c.strip().title() for c in df.columns]

    # --- guard: Close column must exist ---
    if "Close" not in df.columns:
        logger.warning(
            "Normalise: no 'Close' column for %s — found: %s", ticker, list(df.columns)
        )
        return None

    # --- reset index so Date is a plain column, not the index ---
    df = df.reset_index()

    # --- normalise date column name ---
    date_col = next((c for c in df.columns if c.lower() == "date" or c.lower() == "datetime"), None)
    if date_col is None:
        logger.warning("Normalise: no date column for %s — found: %s", ticker, list(df.columns))
        return None
    if date_col != "Date":
        df = df.rename(columns={date_col: "Date"})

    # --- keep only what we need ---
    df = df[["Date", "Close"]].copy()

    # --- drop bad rows ---
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]

    if df.empty:
        logger.warning("Normalise: no valid Close rows for %s after cleaning", ticker)
        return None

    # --- sort ascending and reset to RangeIndex ---
    df = df.sort_values("Date").reset_index(drop=True)

    return df
