"""
Telegram command handlers for watchlist operations.
"""

import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services import watchlist_service as ws
from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.bot.handlers._helpers import require_registered, fmt_pct, get_account_id

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date:
    """Parse dd/mm/yyyy into a date object. Raises ValueError on bad format."""
    return date(*reversed([int(p) for p in value.split("/")]))


async def cmd_add_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage:
      /watch TICKER EXCHANGE            — use today's price
      /watch TICKER EXCHANGE DD/MM/YYYY — use historical close
    """
    user = update.effective_user
    raw_text = update.message.text
    logger.info("cmd=/watch user=%s(%s) raw=%r", user.username or "?", user.id, raw_text)

    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "  /watch TICKER EXCHANGE\n"
            "  /watch TICKER EXCHANGE DD/MM/YYYY\n\n"
            "Examples:\n"
            "  /watch RELIANCE.NS NSE\n"
            "  /watch AAPL NASDAQ 15/01/2025",
        )
        return

    ticker = args[0].upper()

    # Catch the common mistake: /watch TICKER DD/MM/YYYY (exchange forgotten)
    if "/" in args[1]:
        logger.warning("  missing exchange — args[1]=%r looks like a date", args[1])
        await update.message.reply_text(
            "❌ Missing exchange. The format is:\n"
            "  /watch TICKER EXCHANGE DD/MM/YYYY\n\n"
            f"Example: /watch {ticker} NYSE {args[1]}"
        )
        return

    exchange   = args[1].upper()
    entry_date = None

    if len(args) >= 3:
        try:
            entry_date = _parse_date(args[2])
            logger.info("  parsed entry_date=%s", entry_date)
        except (ValueError, IndexError) as exc:
            logger.warning("  date parse failed for %r: %s", args[2], exc)
            await update.message.reply_text(
                "❌ Invalid date format. Use DD/MM/YYYY — e.g. 15/01/2025",
            )
            return
        if entry_date > date.today():
            logger.warning("  rejected: future date %s", entry_date)
            await update.message.reply_text("❌ Entry date cannot be in the future.")
            return
    else:
        logger.info("  no date provided — will use current price")

    telegram_id = get_account_id(update)

    try:
        result   = ws.add_stock(telegram_id, ticker, exchange, entry_date)
        currency = CURRENCY_SYMBOL.get(exchange, "")
        logger.info(
            "  added %s %s entry_date=%s price=%.4f (%s)",
            ticker, exchange, entry_date, result["added_price"], result["price_label"],
        )
        await update.message.reply_text(
            f"✅ Added *{result['ticker']}* ({result['exchange']}) to your watchlist\n"
            f"Entry price: {currency}{result['added_price']:,.2f} _{result['price_label']}_",
            parse_mode="Markdown",
        )
    except ws.WatchlistError as e:
        logger.warning("  WatchlistError: %s", e)
        msg = f"❌ {e}"
        if "Could not fetch price" in str(e):
            msg += f"\n\nDon't know the ticker? Try:\n/search {ticker.lower()}"
        await update.message.reply_text(msg)


async def cmd_remove_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /remove_watchlist TICKER"""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /remove_watchlist TICKER")
        return

    ticker = args[0].upper()
    telegram_id = get_account_id(update)

    try:
        ws.remove_stock(telegram_id, ticker)
        await update.message.reply_text(f"✅ Removed *{ticker}* from your watchlist.", parse_mode="Markdown")
    except ws.WatchlistError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_view_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /view_watchlist"""
    telegram_id = get_account_id(update)
    items = ws.get_watchlist_with_prices(telegram_id)

    if not items:
        await update.message.reply_text("Your watchlist is empty. Use /add_watchlist to add stocks.")
        return

    lines = ["📋 *Your Watchlist*\n"]
    for item in items:
        currency = CURRENCY_SYMBOL.get(item["exchange"], "")
        price_str = f"{currency}{item['current_price']:,.2f}" if item["current_price"] else "N/A"
        pct_str = fmt_pct(item["pct_return"])
        lines.append(f"*{item['ticker']}* ({item['exchange']})")
        lines.append(f"  Added: {currency}{item['added_price']:,.2f} → Now: {price_str} ({pct_str})")

        for cp in item["checkpoints"]:
            cp_pct = fmt_pct(cp["pct_return"])
            lines.append(f"  📍 {cp['label']}: {currency}{cp['price']:,.2f} → {cp_pct}")
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_set_checkpoint(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage:
      /mark TICKER LABEL
      /mark TICKER LABEL DD/MM/YYYY
    """
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "  /mark TICKER LABEL\n"
            "  /mark TICKER LABEL DD/MM/YYYY\n\n"
            "Examples:\n"
            "  /mark AAPL pre-earnings\n"
            "  /mark AAPL budget-day 01/02/2025"
        )
        return

    ticker = args[0].upper()
    entry_date = None

    # If the last arg looks like a date, parse it and exclude from label
    label_parts = args[1:]
    if len(label_parts) >= 2 and "/" in label_parts[-1]:
        try:
            entry_date  = _parse_date(label_parts[-1])
            label_parts = label_parts[:-1]
            if entry_date > date.today():
                await update.message.reply_text("❌ Date cannot be in the future.")
                return
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid date format. Use DD/MM/YYYY — e.g. 01/02/2025")
            return

    label       = " ".join(label_parts)
    telegram_id = get_account_id(update)

    try:
        result = ws.set_checkpoint(telegram_id, ticker, label, entry_date)
        await update.message.reply_text(
            f"📍 Checkpoint set for *{result['ticker']}*\n"
            f"Label: {result['label']}\n"
            f"Price: {result['price']:,.2f} ({result['price_label']})",
            parse_mode="Markdown",
        )
    except ws.WatchlistError as e:
        await update.message.reply_text(f"❌ {e}")
