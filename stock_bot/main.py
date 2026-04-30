"""
Entry point.

Usage:
    python -m stock_bot.main --config configs/bot-1.json
"""

import argparse
import logging
import sys
from datetime import datetime

# --- Load .env then config, before anything else ---
from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Path to bot JSON config file")
args = parser.parse_args()

from stock_bot.bot_config import BotConfig
cfg = BotConfig.load(args.config)

# --- Configure log path and DB path before any module imports them ---
from stock_bot import log_manager
log_manager.configure(cfg.logs)

from stock_bot.logger import setup_logging
setup_logging()

from stock_bot.database.db import configure as configure_db
configure_db(cfg.database)

# --- Now safe to import everything else ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import Application

from stock_bot.config import MARKET_HOURS
from stock_bot.database.db import init_db
from stock_bot.bot.router import register_handlers
from stock_bot.services.alert_service import run_alert_check

logger = logging.getLogger(__name__)

# Commands shown in Telegram autocomplete, with their descriptions.
# Only enabled features appear here.
_COMMAND_DESCRIPTIONS = {
    "start":      "Register yourself — run this first",
    "help":       "Show all commands with examples",
    "watch":      "Track a stock — TICKER EXCHANGE [DD/MM/YYYY]",
    "unwatch":    "Stop tracking a stock — TICKER",
    "watchlist":  "All tracked stocks with live prices & returns",
    "mark":       "Save today's price as a reference — TICKER LABEL",
    "alert":      "Add EMA alert — TICKER EMA_10W|EMA_40W THRESHOLD%",
    "unalert":    "Remove an EMA alert — TICKER EMA_10W|EMA_40W",
    "alerts":     "List active EMA alerts for a stock — TICKER",
    "palert":     "Set price alert — TICKER PRICE",
    "unpalert":   "Remove price alert — TICKER PRICE",
    "palerts":    "List price alerts for a stock — TICKER",
    "palertsall": "List all active price alerts",
    "buy":        "Log a buy — TICKER EXCHANGE QTY PRICE [note]",
    "sell":       "Log a sell (FIFO) — TICKER QTY PRICE [note]",
    "holdings":   "Open positions with avg cost & P&L",
    "history":    "Full buy/sell log for a stock — TICKER",
    "report":     "Weekly watchlist + holdings summary",
    "stock":      "Deep-dive on one stock — TICKER",
}


def _any_market_open() -> bool:
    now_utc = datetime.utcnow()
    for exchange, info in MARKET_HOURS.items():
        local_now = datetime.now(tz=info["tz"])
        open_h, open_m   = info["open"]
        close_h, close_m = info["close"]
        open_min  = open_h * 60 + open_m
        close_min = close_h * 60 + close_m
        cur_min   = local_now.hour * 60 + local_now.minute
        if local_now.weekday() < 5 and open_min <= cur_min <= close_min:
            return True
    return False


def main() -> None:
    logger.info("=" * 60)
    logger.info("  BOT STARTING UP  —  %s", cfg.bot_name)
    logger.info("  Config: %s", args.config)
    logger.info("=" * 60)

    init_db()

    app = Application.builder().token(cfg.telegram_token).build()
    command_map = register_handlers(app, cfg.features)

    scheduler = AsyncIOScheduler()

    async def alert_job():
        interval = (
            cfg.settings.check_interval_market_hours
            if _any_market_open()
            else cfg.settings.check_interval_off_hours
        )
        await run_alert_check(app.bot, cfg.alert_chat_id, cfg.settings.alert_cooldown_hours)
        job = scheduler.get_job("alert_check")
        if job:
            job.reschedule(trigger="interval", seconds=interval)

    scheduler.add_job(
        alert_job,
        trigger="interval",
        seconds=cfg.settings.check_interval_off_hours,
        id="alert_check",
        name="Alert check",
    )

    async def on_startup(application: Application) -> None:
        scheduler.start()
        logger.info("Scheduler started")
        bot_commands = [
            BotCommand(cmd, _COMMAND_DESCRIPTIONS[cmd])
            for cmd in command_map
            if cmd in _COMMAND_DESCRIPTIONS
        ]
        for scope in (BotCommandScopeAllPrivateChats(), BotCommandScopeAllGroupChats()):
            await application.bot.set_my_commands(bot_commands, scope=scope)
        logger.info("Registered %d bot commands for autocomplete", len(bot_commands))

    async def on_shutdown(application: Application) -> None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    app.post_init     = on_startup
    app.post_shutdown = on_shutdown

    logger.info("Bot starting…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
