"""
Maps Telegram commands to their handler functions.

Command design: short, no underscores, easy to thumb-type.
"""

import logging

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, ApplicationHandlerStop, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

from stock_bot.bot_config import Features

logger = logging.getLogger(__name__)


async def _error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(ctx.error, (NetworkError, TimedOut)):
        logger.warning("Transient Telegram error (will retry): %s", ctx.error)
    else:
        logger.error("Unhandled exception", exc_info=ctx.error)


async def _log_all_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
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
from stock_bot.bot.handlers.search_handlers import cmd_search, handle_search_reply
from stock_bot.bot.handlers.watchlist_handlers import (
    cmd_add_watchlist, cmd_remove_watchlist, cmd_view_watchlist, cmd_set_checkpoint,
)
from stock_bot.bot.handlers.alert_handlers import (
    cmd_set_alert, cmd_remove_alert, cmd_view_alerts,
)
from stock_bot.bot.handlers.holdings_handlers import (
    cmd_buy, cmd_sell, cmd_view_holdings, cmd_transaction_history,
)
from stock_bot.bot.handlers.report_handlers import (
    cmd_weekly_report, cmd_stock_details,
)
from stock_bot.bot.handlers.price_alert_handlers import (
    cmd_set_price_alert, cmd_remove_price_alert, cmd_view_price_alerts, cmd_view_all_price_alerts,
)


def _build_command_map(features: Features) -> dict:
    """Build the active command map based on enabled features."""
    cmds = {
        "start":  cmd_start,
        "help":   cmd_help,
        "search": cmd_search,
    }
    if features.watchlist:
        cmds.update({
            "watch":     cmd_add_watchlist,
            "unwatch":   cmd_remove_watchlist,
            "watchlist": cmd_view_watchlist,
            "mark":      cmd_set_checkpoint,
        })
    if features.alerts:
        cmds.update({
            "alert":   cmd_set_alert,
            "unalert": cmd_remove_alert,
            "alerts":  cmd_view_alerts,
        })
    if features.price_alerts:
        cmds.update({
            "palert":     cmd_set_price_alert,
            "unpalert":   cmd_remove_price_alert,
            "palerts":    cmd_view_price_alerts,
            "palertsall": cmd_view_all_price_alerts,
        })
    if features.holdings:
        cmds.update({
            "buy":      cmd_buy,
            "sell":     cmd_sell,
            "holdings": cmd_view_holdings,
            "history":  cmd_transaction_history,
        })
    if features.reports:
        cmds.update({
            "report": cmd_weekly_report,
            "stock":  cmd_stock_details,
        })
    return cmds


def register_handlers(app: Application, features: Features) -> dict:
    """
    Attach command handlers to the Application based on enabled features.
    Returns the active command map (used by main.py to build BOT_COMMANDS).
    """
    command_map = _build_command_map(features)

    app.add_error_handler(_error_handler)

    async def _dispatch_multi_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text or ""
        cmd_lines = [l.strip() for l in text.splitlines() if l.strip().startswith("/")]
        if len(cmd_lines) <= 1:
            return
        for line in cmd_lines:
            parts   = line.split()
            raw_cmd = parts[0].lstrip("/").split("@")[0].lower()
            ctx.args = parts[1:]
            fn = command_map.get(raw_cmd)
            if fn:
                await fn(update, ctx)
            else:
                await update.message.reply_text(f"Unknown command: /{raw_cmd}")
        raise ApplicationHandlerStop

    app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, _dispatch_multi_command), group=-2)
    app.add_handler(MessageHandler(filters.COMMAND, _log_all_commands), group=-1)

    for cmd, fn in command_map.items():
        app.add_handler(CommandHandler(cmd, fn))

    # Catch digit / "other" / "cancel" replies for the interactive search flow.
    # Silently ignored when the user has no pending search.
    import re as _re
    _reply_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(
        _re.compile(r"^\s*([1-9]|other|none|cancel)\s*$", _re.IGNORECASE)
    )
    app.add_handler(MessageHandler(_reply_filter, handle_search_reply), group=1)

    return command_map
