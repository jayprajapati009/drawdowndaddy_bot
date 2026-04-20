"""
Maps Telegram commands to their handler functions.

Command design: short, no underscores, easy to thumb-type.
"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def _log_all_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """MessageHandler that runs before every command and writes a single audit line."""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text if update.message else ""
    logger.info(
        "COMMAND user=%s(%s) chat=%s(%s) text=%r",
        user.username or "?", user.id,
        chat.title or "private", chat.id,
        text,
    )

from stock_bot.bot.handlers.general_handlers import cmd_start, cmd_help
from stock_bot.bot.handlers.watchlist_handlers import (
    cmd_add_watchlist,
    cmd_remove_watchlist,
    cmd_view_watchlist,
    cmd_set_checkpoint,
)
from stock_bot.bot.handlers.alert_handlers import (
    cmd_set_alert,
    cmd_remove_alert,
    cmd_view_alerts,
)
from stock_bot.bot.handlers.holdings_handlers import (
    cmd_buy,
    cmd_sell,
    cmd_view_holdings,
    cmd_transaction_history,
)
from stock_bot.bot.handlers.report_handlers import (
    cmd_weekly_report,
    cmd_stock_details,
)


def register_handlers(app: Application) -> None:
    """Attach all command handlers to the Application instance."""
    # Audit logger — fires first for every message that starts with /
    app.add_handler(MessageHandler(filters.COMMAND, _log_all_commands), group=-1)

    handlers = [
        # General
        CommandHandler("start",     cmd_start),
        CommandHandler("help",      cmd_help),
        # Watchlist
        CommandHandler("watch",     cmd_add_watchlist),
        CommandHandler("unwatch",   cmd_remove_watchlist),
        CommandHandler("watchlist", cmd_view_watchlist),
        CommandHandler("mark",      cmd_set_checkpoint),
        # Alerts
        CommandHandler("alert",     cmd_set_alert),
        CommandHandler("unalert",   cmd_remove_alert),
        CommandHandler("alerts",    cmd_view_alerts),
        # Holdings
        CommandHandler("buy",       cmd_buy),
        CommandHandler("sell",      cmd_sell),
        CommandHandler("holdings",  cmd_view_holdings),
        CommandHandler("history",   cmd_transaction_history),
        # Reports
        CommandHandler("report",    cmd_weekly_report),
        CommandHandler("stock",     cmd_stock_details),
    ]
    for h in handlers:
        app.add_handler(h)
