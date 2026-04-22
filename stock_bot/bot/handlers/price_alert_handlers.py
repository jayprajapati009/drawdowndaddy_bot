"""
Handlers for price-level alerts (/palert, /unpalert, /palerts).
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import get_current_price
from stock_bot.bot.handlers._helpers import get_account_id

logger = logging.getLogger(__name__)


async def cmd_set_price_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage: /palert TICKER PRICE
    Automatically sets direction: ABOVE if target > current price, BELOW if lower.
    Example: /palert AAPL 250
    """
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /palert TICKER PRICE\n"
            "Example: /palert AAPL 250\n\n"
            "Fires when the price crosses your target from either direction."
        )
        return

    ticker = args[0].upper()
    try:
        target_price = float(args[1].replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Price must be a number — e.g. /palert AAPL 250")
        return

    telegram_id = get_account_id(update)
    user = update.effective_user
    logger.info("cmd=/palert user=%s(%s) ticker=%s target=%.2f", user.username or "?", user.id, ticker, target_price)

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return

        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(
                f"❌ {ticker} is not on your watchlist. Add it first with /watch."
            )
            return

        # Auto-detect direction from current price
        current = get_current_price(ticker)
        if current is None:
            await update.message.reply_text(f"❌ Could not fetch current price for {ticker}.")
            return

        direction = "ABOVE" if target_price > current else "BELOW"
        q.add_price_alert(conn, item["id"], target_price, direction)

    currency = CURRENCY_SYMBOL.get(item["exchange"], "")
    arrow    = "📈" if direction == "ABOVE" else "📉"
    await update.message.reply_text(
        f"{arrow} Price alert set for {ticker}\n"
        f"Target: {currency}{target_price:,.2f} ({direction})\n"
        f"Current: {currency}{current:,.2f}"
    )


async def cmd_remove_price_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage: /unpalert TICKER PRICE
    Removes the price alert closest to the given target price.
    """
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /unpalert TICKER PRICE\nExample: /unpalert AAPL 250")
        return

    ticker = args[0].upper()
    try:
        target_price = float(args[1].replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Price must be a number.")
        return

    telegram_id = get_account_id(update)

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return

        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(f"❌ {ticker} is not on your watchlist.")
            return

        alerts = q.get_price_alerts(conn, item["id"])
        # Find the alert closest to the given price
        match = min(alerts, key=lambda a: abs(a["target_price"] - target_price), default=None)
        if match is None or abs(match["target_price"] - target_price) > 1:
            await update.message.reply_text(f"❌ No price alert found near {target_price} for {ticker}.")
            return

        q.deactivate_price_alert(conn, match["id"])

    await update.message.reply_text(f"✅ Price alert removed for {ticker} @ {match['target_price']:,.2f}")


async def cmd_view_price_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage: /palerts TICKER | /palerts all
    """
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /palerts TICKER  or  /palerts all")
        return

    telegram_id = get_account_id(update)

    if args[0].lower() == "all":
        with get_connection() as conn:
            all_alerts = q.get_all_active_price_alerts(conn)

        if not all_alerts:
            await update.message.reply_text("No active price alerts. Use /palert to set one.")
            return

        lines = ["🎯 All price alerts\n"]
        current_ticker = None
        for a in sorted(all_alerts, key=lambda x: x["ticker"]):
            if a["ticker"] != current_ticker:
                current_ticker = a["ticker"]
                lines.append(f"{current_ticker}")
            currency = CURRENCY_SYMBOL.get(a["exchange"], "")
            arrow = "📈" if a["direction"] == "ABOVE" else "📉"
            lines.append(f"  {arrow} {currency}{a['target_price']:,.2f} ({a['direction']})")

        await update.message.reply_text("\n".join(lines))
        return

    ticker = args[0].upper()
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return
        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(f"❌ {ticker} is not on your watchlist.")
            return
        alerts = q.get_price_alerts(conn, item["id"])

    if not alerts:
        await update.message.reply_text(f"No price alerts for {ticker}. Use /palert to set one.")
        return

    currency = CURRENCY_SYMBOL.get(item["exchange"], "")
    lines = [f"🎯 Price alerts for {ticker}\n"]
    for a in alerts:
        arrow = "📈" if a["direction"] == "ABOVE" else "📉"
        lines.append(f"{arrow} {currency}{a['target_price']:,.2f} ({a['direction']})")

    await update.message.reply_text("\n".join(lines))
