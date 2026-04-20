"""
Alert checking and notification dispatch.

Called by APScheduler on a configurable interval.  For each active alert
config the service:
  1. Fetches the current price and relevant EMA value
  2. Checks if the price is within the configured threshold %
  3. Skips if an identical alert was fired within ALERT_COOLDOWN_HOURS
  4. Sends a Telegram notification and logs the event
"""

import logging
from datetime import datetime, timedelta, timezone

from telegram import Bot

from stock_bot.config import ALERT_COOLDOWN_HOURS, CURRENCY_SYMBOL
from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import clear_cache, get_current_price, get_ema

logger = logging.getLogger(__name__)


async def run_alert_check(bot: Bot, chat_id: str) -> None:
    """
    Main entry point called by the scheduler.
    *chat_id* is the Telegram chat that receives alert notifications.
    """
    clear_cache()  # flush stale price data at the start of each tick
    logger.info("Running alert check cycle")

    with get_connection() as conn:
        configs = q.get_all_active_alert_configs(conn)

    for cfg in configs:
        try:
            await _check_one_alert(bot, chat_id, cfg)
        except Exception as exc:
            logger.warning(
                "Alert check failed for %s / %s: %s",
                cfg["ticker"], cfg["indicator"], exc
            )


async def _check_one_alert(bot: Bot, chat_id: str, cfg) -> None:
    ticker = cfg["ticker"]
    indicator = cfg["indicator"]
    threshold_pct = cfg["threshold_pct"]
    exchange = cfg["exchange"]

    current_price = get_current_price(ticker)
    if current_price is None:
        return

    ema_value = get_ema(ticker, indicator)
    if ema_value is None:
        return

    # Distance as a percentage of EMA value
    distance_pct = abs((current_price - ema_value) / ema_value) * 100

    if distance_pct > threshold_pct:
        return  # outside alert zone

    # --- Deduplication check ---
    cooldown_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)
    with get_connection() as conn:
        recent = q.get_recent_alert_log(conn, cfg["id"], cooldown_cutoff)
        if recent:
            return  # already alerted within cooldown window

        q.log_alert(conn, cfg["id"], current_price, ema_value)

    # --- Build and send notification ---
    currency = CURRENCY_SYMBOL.get(exchange, "")
    crossed = current_price <= ema_value if current_price < ema_value else current_price >= ema_value
    status = "Hit / crossed" if distance_pct < 0.1 else f"Approaching ({distance_pct:.1f}% away)"

    message = (
        f"⚠️ *ALERT: {ticker}*\n"
        f"Current price: {currency}{current_price:,.2f}\n"
        f"{indicator}: {currency}{ema_value:,.2f}\n"
        f"Distance: {distance_pct:.2f}% away\n"
        f"Status: {status}"
    )

    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    logger.info("Alert sent for %s / %s (distance %.2f%%)", ticker, indicator, distance_pct)
