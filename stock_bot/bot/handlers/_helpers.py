"""
Shared utilities for all handlers.
"""

from functools import wraps
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q

# All users in the group share one account so data is pooled.
_SHARED_ACCOUNT_ID = "shared"


def get_account_id(update: Update) -> str:
    return _SHARED_ACCOUNT_ID


def fmt_pct(value: Optional[float]) -> str:
    """Format a percentage value for display, e.g. '+12.34%' or 'N/A'."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def require_registered(handler):
    """Decorator: ensure the shared account exists in the DB before running the handler."""
    @wraps(handler)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        with get_connection() as conn:
            user_id = q.get_user_id(conn, _SHARED_ACCOUNT_ID)
        if user_id is None:
            await update.message.reply_text("Please run /start first to register.")
            return
        return await handler(update, ctx)
    return wrapper
