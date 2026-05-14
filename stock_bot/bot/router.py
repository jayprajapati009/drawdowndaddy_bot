"""
Maps Telegram commands to their handler functions.

Command design: short, no underscores, easy to thumb-type.
"""

import logging

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application, ApplicationHandlerStop, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters,
)
from telegram.ext import ContextTypes

from stock_bot.bot_config import Features

logger = logging.getLogger(__name__)


async def _error_handler(_update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(ctx.error, (NetworkError, TimedOut)):
        logger.warning("Transient Telegram error (will retry): %s", ctx.error)
    else:
        logger.error("Unhandled exception", exc_info=ctx.error)


async def _log_all_commands(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
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
from stock_bot.bot.handlers.search_handlers import (
    cmd_search, cmd_set_date, handle_search_callback, handle_date_reply,
)
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
    cmd_set_price_alert, cmd_remove_price_alert, cmd_view_price_alerts,
    cmd_view_all_price_alerts, handle_price_alert_callback,
)


def _build_command_map(features: Features) -> dict:
    """Build the active command map based on enabled features."""
    cmds = {
        "start":  cmd_start,
        "help":   cmd_help,
        "search": cmd_search,
        "date":   cmd_set_date,
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


_BULK_THRESHOLD = 5   # above this, suppress per-command replies and send one summary


class _SilentMessage:
    """Proxy for Message that buffers reply_text calls instead of sending them."""

    def __init__(self, real_message, buffer: list):
        self._msg    = real_message
        self._buffer = buffer

    async def reply_text(self, text, **_kwargs):  # noqa: ANN001
        lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
        entry = " — ".join(lines[:2]) if len(lines) >= 2 else (lines[0] if lines else "")
        self._buffer.append(entry)

    def __getattr__(self, name: str):  # noqa: ANN001
        return getattr(self._msg, name)


class _SilentUpdate:
    """Proxy for Update that injects _SilentMessage during bulk dispatch."""

    def __init__(self, real_update, buffer: list):
        self._update  = real_update
        self._message = _SilentMessage(real_update.message, buffer)

    @property
    def message(self) -> _SilentMessage:
        return self._message

    def __getattr__(self, name: str):  # noqa: ANN001
        return getattr(self._update, name)


def register_handlers(app: Application, features: Features) -> dict:
    """
    Attach command handlers to the Application based on enabled features.
    Returns the active command map (used by main.py to build BOT_COMMANDS).
    """
    command_map = _build_command_map(features)

    app.add_error_handler(_error_handler)

    async def _run_bulk(update, ctx, cmd_lines):
        """Execute cmd_lines silently and return a formatted summary string."""
        buffer: list[str] = []
        silent = _SilentUpdate(update, buffer)
        ok, errors = 0, []
        for line in cmd_lines:
            parts   = line.split()
            raw_cmd = parts[0].lstrip("/").split("@")[0].lower()
            ctx.args = parts[1:]
            fn = command_map.get(raw_cmd)
            try:
                if fn:
                    await fn(silent, ctx)
                    ok += 1
                else:
                    errors.append(f"❓ Unknown: /{raw_cmd}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Bulk dispatch error on /%s: %s", raw_cmd, exc, exc_info=True)
                errors.append(f"❌ /{raw_cmd}: {exc}")
        header = f"📦 Bulk import: {ok}/{len(cmd_lines)} done\n"
        body   = "\n".join(f"• {e}" for e in buffer) + (
            "\n" + "\n".join(errors) if errors else ""
        )
        return header + body

    async def _dispatch_multi_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text or ""
        cmd_lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("/")]
        if len(cmd_lines) <= 1:
            return

        if len(cmd_lines) > _BULK_THRESHOLD:
            summary = await _run_bulk(update, ctx, cmd_lines)
            for i in range(0, len(summary), 4000):
                await update.message.reply_text(summary[i:i + 4000])
        else:
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

    app.add_handler(
        MessageHandler(filters.TEXT & filters.COMMAND, _dispatch_multi_command), group=-2
    )
    app.add_handler(MessageHandler(filters.COMMAND, _log_all_commands), group=-1)

    for cmd, fn in command_map.items():
        app.add_handler(CommandHandler(cmd, fn))

    # Inline button handlers
    app.add_handler(CallbackQueryHandler(handle_search_callback,       pattern=r"^search:"))
    app.add_handler(CallbackQueryHandler(handle_price_alert_callback,  pattern=r"^palert:"))

    # Reply handler for typed date / new query after "none of these".
    # Only fires for replies to the bot's messages, which are received
    # even when group privacy mode is enabled.
    app.add_handler(
        MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND, handle_date_reply),
        group=1,
    )

    return command_map
