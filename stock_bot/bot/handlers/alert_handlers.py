"""
Telegram command handlers for alert configuration.
"""

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import EMA_SPANS, CURRENCY_SYMBOL
from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.bot.handlers._helpers import get_account_id


async def cmd_set_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT
    Example: /set_alert RELIANCE.NS EMA_10W 5
    """
    args = ctx.args
    if len(args) < 3:
        indicators = ", ".join(EMA_SPANS.keys())
        await update.message.reply_text(
            f"Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT\n"
            f"Available indicators: {indicators}\n"
            f"Example: /set_alert RELIANCE.NS EMA_10W 5"
        )
        return

    ticker = args[0].upper()
    indicator = args[1].upper()
    try:
        threshold_pct = float(args[2])
    except ValueError:
        await update.message.reply_text("Threshold must be a number (e.g. 5 for 5%).")
        return

    if indicator not in EMA_SPANS:
        await update.message.reply_text(f"Unknown indicator '{indicator}'. Use one of: {', '.join(EMA_SPANS)}")
        return

    telegram_id = get_account_id(update)

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return
        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(f"{ticker} is not on your watchlist. Add it first with /add_watchlist.")
            return
        q.upsert_alert_config(conn, item["id"], indicator, threshold_pct)

    await update.message.reply_text(
        f"✅ Alert set for *{ticker}*\n"
        f"Indicator: {indicator}\n"
        f"Trigger: within {threshold_pct}% of {indicator}",
        parse_mode="Markdown",
    )


async def cmd_remove_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /remove_alert TICKER INDICATOR"""
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /remove_alert TICKER INDICATOR\nExample: /remove_alert AAPL EMA_40W")
        return

    ticker = args[0].upper()
    indicator = args[1].upper()
    telegram_id = get_account_id(update)

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return
        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(f"{ticker} is not on your watchlist.")
            return
        removed = q.deactivate_alert(conn, item["id"], indicator)

    if removed:
        await update.message.reply_text(f"✅ Alert removed for *{ticker}* / {indicator}.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"No active alert found for {ticker} / {indicator}.")


async def cmd_view_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /view_alerts TICKER"""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /view_alerts TICKER")
        return

    ticker = args[0].upper()
    telegram_id = get_account_id(update)

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first.")
            return
        item = q.get_watchlist_item(conn, user_id, ticker)
        if item is None:
            await update.message.reply_text(f"{ticker} is not on your watchlist.")
            return
        alerts = q.get_alert_configs(conn, item["id"])

    if not alerts:
        await update.message.reply_text(f"No active alerts for {ticker}. Use /set_alert to create one.")
        return

    lines = [f"🔔 *Alerts for {ticker}*\n"]
    for a in alerts:
        lines.append(f"• {a['indicator']}: trigger within {a['threshold_pct']}%")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
