"""
Maps Telegram commands to their handler functions.

Command design: short, no underscores, easy to thumb-type.
"""

import logging

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, ApplicationHandlerStop, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def _error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(ctx.error, (NetworkError, TimedOut)):
        logger.warning("Transient Telegram error (will retry): %s", ctx.error)
    else:
        logger.error("Unhandled exception", exc_info=ctx.error)


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
from stock_bot.bot.handlers.price_alert_handlers import (
    cmd_set_price_alert,
    cmd_remove_price_alert,
    cmd_view_price_alerts,
    cmd_view_all_price_alerts,
)

# Single source of truth: command name → handler function.
# Used for both CommandHandler registration and multi-command dispatch.
COMMAND_MAP = {
    "start":     cmd_start,
    "help":      cmd_help,
    "watch":     cmd_add_watchlist,
    "unwatch":   cmd_remove_watchlist,
    "watchlist": cmd_view_watchlist,
    "mark":      cmd_set_checkpoint,
    "alert":     cmd_set_alert,
    "unalert":   cmd_remove_alert,
    "alerts":    cmd_view_alerts,
    "buy":       cmd_buy,
    "sell":      cmd_sell,
    "holdings":  cmd_view_holdings,
    "history":   cmd_transaction_history,
    "palert":     cmd_set_price_alert,
    "unpalert":   cmd_remove_price_alert,
    "palerts":    cmd_view_price_alerts,
    "palertsall": cmd_view_all_price_alerts,
    "report":    cmd_weekly_report,
    "stock":     cmd_stock_details,
}


async def _dispatch_multi_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fires before CommandHandlers (group -2).
    If the message contains multiple /command lines, routes each one and
    raises ApplicationHandlerStop so normal handlers don't double-fire.
    Single-command messages are left alone.
    """
    text = update.message.text or ""
    cmd_lines = [l.strip() for l in text.splitlines() if l.strip().startswith("/")]

    if len(cmd_lines) <= 1:
        return  # normal single-command flow takes over

    for line in cmd_lines:
        parts = line.split()
        raw_cmd = parts[0].lstrip("/").split("@")[0].lower()
        ctx.args = parts[1:]
        handler_fn = COMMAND_MAP.get(raw_cmd)
        if handler_fn:
            await handler_fn(update, ctx)
        else:
            await update.message.reply_text(f"Unknown command: /{raw_cmd}")

    raise ApplicationHandlerStop


def register_handlers(app: Application) -> None:
    """Attach all command handlers to the Application instance."""
    app.add_error_handler(_error_handler)

    # Multi-command paste dispatcher — must be registered before everything else
    app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, _dispatch_multi_command), group=-2)

    # Audit logger
    app.add_handler(MessageHandler(filters.COMMAND, _log_all_commands), group=-1)

    for cmd, fn in COMMAND_MAP.items():
        app.add_handler(CommandHandler(cmd, fn))
