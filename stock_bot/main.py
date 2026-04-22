"""
Entry point.

Starts the Telegram bot (via Application.run_polling) and wires up the
APScheduler job that runs alert checks in the background.
"""

import logging
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from stock_bot.logger import setup_logging
setup_logging()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from stock_bot.config import (
    ALERT_CHECK_INTERVAL_MARKET_HOURS,
    ALERT_CHECK_INTERVAL_OFF_HOURS,
    MARKET_HOURS,
    TELEGRAM_TOKEN,
)
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from stock_bot.database.db import init_db
from stock_bot.bot.router import register_handlers
from stock_bot.services.alert_service import run_alert_check

# Short, no-underscore commands shown in Telegram's autocomplete
BOT_COMMANDS = [
    BotCommand("start",     "Register yourself — run this first"),
    BotCommand("help",      "Show all commands with examples"),
    BotCommand("watch",     "Track a stock — TICKER EXCHANGE [DD/MM/YYYY]"),
    BotCommand("unwatch",   "Stop tracking a stock — TICKER"),
    BotCommand("watchlist", "All tracked stocks with live prices & returns"),
    BotCommand("mark",      "Save today's price as a reference — TICKER LABEL"),
    BotCommand("alert",     "Add EMA alert — TICKER EMA_10W|EMA_40W THRESHOLD%"),
    BotCommand("unalert",   "Remove an alert — TICKER EMA_10W|EMA_40W"),
    BotCommand("alerts",    "List active alerts for a stock — TICKER"),
    BotCommand("buy",       "Log a buy — TICKER EXCHANGE QTY PRICE [note]"),
    BotCommand("sell",      "Log a sell (FIFO) — TICKER QTY PRICE [note]"),
    BotCommand("holdings",  "Open positions with avg cost & P&L"),
    BotCommand("history",   "Full buy/sell log for a stock — TICKER"),
    BotCommand("palert",     "Set price alert — TICKER PRICE"),
    BotCommand("unpalert",   "Remove price alert — TICKER PRICE"),
    BotCommand("palerts",    "List price alerts for a stock — TICKER"),
    BotCommand("palertsall", "List all active price alerts"),
    BotCommand("report",    "Weekly watchlist + holdings summary"),
    BotCommand("stock",     "Deep-dive on one stock — TICKER"),
]

logger = logging.getLogger(__name__)

# The Telegram chat that receives alert notifications.
# Set ALERT_CHAT_ID to a group chat ID or your personal chat ID.
ALERT_CHAT_ID: str = os.environ["ALERT_CHAT_ID"]


def _any_market_open() -> bool:
    """Return True if at least one tracked market is currently open."""
    now_utc = datetime.utcnow()
    for exchange, info in MARKET_HOURS.items():
        local_now = datetime.now(tz=info["tz"])
        open_h, open_m = info["open"]
        close_h, close_m = info["close"]
        open_minutes = open_h * 60 + open_m
        close_minutes = close_h * 60 + close_m
        current_minutes = local_now.hour * 60 + local_now.minute
        # Only Mon–Fri
        if local_now.weekday() < 5 and open_minutes <= current_minutes <= close_minutes:
            return True
    return False


async def _scheduled_alert_job(bot, chat_id: str) -> None:
    """Wrapper so APScheduler can call the async alert check."""
    await run_alert_check(bot, chat_id)


def main() -> None:
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)

    scheduler = AsyncIOScheduler()

    async def alert_job():
        interval = (
            ALERT_CHECK_INTERVAL_MARKET_HOURS
            if _any_market_open()
            else ALERT_CHECK_INTERVAL_OFF_HOURS
        )
        await run_alert_check(app.bot, ALERT_CHAT_ID)
        # Reschedule dynamically based on market state
        job = scheduler.get_job("alert_check")
        if job:
            job.reschedule(trigger="interval", seconds=interval)

    # Start with off-hours interval; alert_job reschedules itself each tick
    scheduler.add_job(
        alert_job,
        trigger="interval",
        seconds=ALERT_CHECK_INTERVAL_OFF_HOURS,
        id="alert_check",
        name="Alert check",
    )

    async def on_startup(application: Application) -> None:
        scheduler.start()
        logger.info("Scheduler started")
        # Register commands for both private chats and group chats explicitly
        # so Telegram shows the autocomplete menu in both contexts.
        for scope in (BotCommandScopeAllPrivateChats(), BotCommandScopeAllGroupChats()):
            await application.bot.set_my_commands(BOT_COMMANDS, scope=scope)
        logger.info("Registered %d bot commands for autocomplete", len(BOT_COMMANDS))

    async def on_shutdown(application: Application) -> None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    logger.info("Bot starting…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
