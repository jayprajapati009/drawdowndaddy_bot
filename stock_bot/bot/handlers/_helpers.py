"""
Shared utilities for all handlers.
"""

from functools import wraps
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q


def fmt_pct(value: Optional[float]) -> str:
    """Format a percentage value for display, e.g. '+12.34%' or 'N/A'."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def require_registered(handler):
    """Decorator: ensure the calling user exists in the DB before running the handler."""
    @wraps(handler)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        with get_connection() as conn:
            user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            await update.message.reply_text("Please run /start first to register.")
            return
        return await handler(update, ctx)
    return wrapper
