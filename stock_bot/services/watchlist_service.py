"""
Watchlist business logic.
"""

import logging
from datetime import date
from typing import Optional

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import get_current_price, get_price_on_date, get_prices_batch

logger = logging.getLogger(__name__)


class WatchlistError(Exception):
    pass


def add_stock(
    telegram_id: str,
    ticker: str,
    exchange: str,
    entry_date: Optional[date] = None,
) -> dict:
    """
    Add *ticker* to the user's watchlist.

    If *entry_date* is provided, fetches the historical close for that date
    (falling back to the nearest prior trading day if the market was closed).
    Otherwise uses the current live price.

    Returns a dict with the added stock's details including the resolved date.
    Raises WatchlistError if already on watchlist or price cannot be fetched.
    """
    if entry_date is not None:
        price = get_price_on_date(ticker, entry_date)
        price_label = f"close on {entry_date.strftime('%d %b %Y')}"
    else:
        price = get_current_price(ticker)
        price_label = "current price"

    if price is None:
        hint = f"on {entry_date}" if entry_date else ""
        raise WatchlistError(
            f"Could not fetch price for {ticker} {hint}. "
            "Check the ticker symbol is correct and the date is a past trading day."
        )

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise WatchlistError("User not registered. Send /start first.")

        existing = q.get_watchlist_item(conn, user_id, ticker)
        if existing:
            raise WatchlistError(f"{ticker.upper()} is already on your watchlist.")

        q.add_to_watchlist(conn, user_id, ticker, exchange, price)

    logger.info("Added %s to watchlist for user %s at %s (%.2f)", ticker, telegram_id, price_label, price)
    return {
        "ticker": ticker.upper(),
        "exchange": exchange.upper(),
        "added_price": price,
        "price_label": price_label,
    }


def remove_stock(telegram_id: str, ticker: str) -> None:
    """Remove *ticker* from the user's watchlist. Raises WatchlistError if not found."""
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise WatchlistError("User not registered.")
        removed = q.remove_from_watchlist(conn, user_id, ticker)
        if not removed:
            raise WatchlistError(f"{ticker.upper()} was not on your watchlist.")


def get_watchlist_with_prices(telegram_id: str) -> list[dict]:
    """
    Return the full watchlist with live prices and return percentages.
    Each entry: ticker, exchange, added_price, current_price, pct_return, checkpoints.
    """
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            return []
        items = q.get_watchlist(conn, user_id)
        checkpoints_by_id = {row["id"]: q.get_checkpoints(conn, row["id"]) for row in items}

    # Fetch all prices in parallel outside the DB connection
    prices = get_prices_batch([row["ticker"] for row in items])

    result = []
    for row in items:
        current = prices.get(row["ticker"])
        pct = None
        if current and row["added_price"]:
            pct = ((current - row["added_price"]) / row["added_price"]) * 100

        cp_data = []
        for cp in checkpoints_by_id.get(row["id"], []):
            cp_pct = None
            if current and cp["price_at_checkpoint"]:
                cp_pct = ((current - cp["price_at_checkpoint"]) / cp["price_at_checkpoint"]) * 100
            cp_data.append({
                "label": cp["label"],
                "price": cp["price_at_checkpoint"],
                "pct_return": cp_pct,
                "created_at": cp["created_at"],
            })

        result.append({
            "ticker": row["ticker"],
            "exchange": row["exchange"],
            "added_price": row["added_price"],
            "added_at": row["added_at"],
            "current_price": current,
            "pct_return": pct,
            "watchlist_id": row["id"],
            "checkpoints": cp_data,
        })
    return result


def set_checkpoint(
    telegram_id: str,
    ticker: str,
    label: str,
    entry_date: Optional[date] = None,
) -> dict:
    """Mark the price of *ticker* as a named checkpoint.
    Uses historical close if *entry_date* is given, otherwise current price."""
    if entry_date is not None:
        price = get_price_on_date(ticker, entry_date)
        price_label = f"close on {entry_date.strftime('%d %b %Y')}"
    else:
        price = get_current_price(ticker)
        price_label = "current price"

    if price is None:
        raise WatchlistError(f"Could not fetch price for {ticker}.")

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise WatchlistError("User not registered.")
        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            raise WatchlistError(f"{ticker.upper()} is not on your watchlist.")
        q.add_checkpoint(conn, item["id"], label, price)

    return {"ticker": ticker.upper(), "label": label, "price": price, "price_label": price_label}
