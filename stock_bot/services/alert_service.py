"""
Alert checking and notification dispatch.

Called by APScheduler on a configurable interval.  For each active alert
config the service:
  1. Fetches the current price and relevant EMA value
  2. Checks if the price is within the configured threshold %
  3. Skips if an identical alert was fired within cooldown_hours
  4. Sends a Telegram notification and logs the event
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from stock_bot.config import (
    CURRENCY_SYMBOL,
    DEFAULT_ALERT_INDICATORS,
    DEFAULT_ALERT_THRESHOLD_PCT,
    EMA_SPANS,
)
from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import (
    clear_cache, get_all_emas, get_current_price, get_ema,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default EMA alerts
#
# Every stock on the watchlist or in the portfolio gets the default weekly
# EMA alerts (10/20/30/40W). Seeding never overwrites an existing config,
# so custom thresholds and removed alerts stay as the user left them.
# ---------------------------------------------------------------------------

def ensure_default_ema_alerts(conn: sqlite3.Connection, watchlist_id: int) -> list[str]:
    """Seed the default EMA alert configs for one watchlist row.
    Returns the indicators that were newly created."""
    created = [
        indicator
        for indicator in DEFAULT_ALERT_INDICATORS
        if q.insert_alert_config_if_absent(
            conn, watchlist_id, indicator, DEFAULT_ALERT_THRESHOLD_PCT
        )
    ]
    if created:
        logger.info("Seeded default EMA alerts for watchlist %s: %s", watchlist_id, created)
    return created


def ensure_watchlist_defaults(
    conn: sqlite3.Connection,
    user_id: int,
    ticker: str,
    exchange: str,
    fallback_price: float,
) -> list[str]:
    """
    Make sure *ticker* has a watchlist row (alerts are anchored to it) and
    the default EMA alerts. *fallback_price* is used as added_price only when
    the watchlist row has to be created. Returns newly created indicators.
    """
    item = q.get_watchlist_item(conn, user_id, ticker)
    if item is not None:
        watchlist_id = item["id"]
    else:
        watchlist_id = q.add_to_watchlist(conn, user_id, ticker, exchange, fallback_price)
        logger.info("Auto-added %s to watchlist (portfolio stock) for user %s", ticker, user_id)
    return ensure_default_ema_alerts(conn, watchlist_id)


def backfill_default_ema_alerts() -> None:
    """
    One-shot seeding at startup: give every existing watchlist stock and every
    portfolio stock the default EMA alerts. Idempotent — reruns are no-ops.
    """
    with get_connection() as conn:
        # Portfolio stocks with open positions may not be on the watchlist yet
        for holding in q.get_all_holdings(conn):
            open_lots = q.get_open_buy_lots(conn, holding["id"])
            total_qty = sum(lot["quantity"] for lot in open_lots)
            if total_qty <= 0:
                continue
            avg_cost = sum(lot["quantity"] * lot["price"] for lot in open_lots) / total_qty
            ensure_watchlist_defaults(
                conn, holding["user_id"], holding["ticker"], holding["exchange"], avg_cost
            )

        for row in q.get_all_watchlist_items(conn):
            ensure_default_ema_alerts(conn, row["id"])


async def run_alert_check(bot: Bot, chat_id: str, cooldown_hours: int = 2) -> None:
    """
    Main entry point called by the scheduler.
    *chat_id* is the Telegram chat that receives alert notifications.
    """
    clear_cache()  # flush stale price data at the start of each tick
    logger.info("Running alert check cycle")

    with get_connection() as conn:
        ema_configs   = q.get_all_active_alert_configs(conn)
        price_configs = q.get_all_active_price_alerts(conn)

    for cfg in ema_configs:
        try:
            await _check_one_ema_alert(bot, chat_id, cfg, cooldown_hours)
        except Exception as exc:
            logger.warning("EMA alert check failed for %s / %s: %s", cfg["ticker"], cfg["indicator"], exc)

    for cfg in price_configs:
        try:
            await _check_one_price_alert(bot, chat_id, cfg, cooldown_hours)
        except Exception as exc:
            logger.warning("Price alert check failed for %s @ %s: %s", cfg["ticker"], cfg["target_price"], exc)


# ---------------------------------------------------------------------------
# Morning EMA scan
#
# Runs once per market region before the trading day opens and reports which
# stocks are trading below each weekly EMA.
# ---------------------------------------------------------------------------

def build_morning_scan_message(exchanges: set[str] | None = None) -> str | None:
    """
    Scan every watched stock (optionally restricted to *exchanges*) and build
    a report of which are below each weekly EMA. Returns None when there are
    no stocks to scan. Blocking (yfinance) — callers run it in a thread.
    """
    clear_cache()
    with get_connection() as conn:
        items = q.get_all_watchlist_items(conn)

    stocks = sorted({
        (row["ticker"], row["exchange"])
        for row in items
        if exchanges is None or row["exchange"] in exchanges
    })
    if not stocks:
        return None

    below: dict[str, list[str]] = {ind: [] for ind in EMA_SPANS}
    above_all: list[str] = []
    failed: list[str] = []

    for ticker, _exchange in stocks:
        price = get_current_price(ticker)
        emas  = get_all_emas(ticker)
        if price is None or all(v is None for v in emas.values()):
            failed.append(ticker)
            continue
        is_below_any = False
        for indicator, ema in emas.items():
            if ema is not None and price < ema:
                pct = (price - ema) / ema * 100
                below[indicator].append(f"{ticker} ({pct:.1f}%)")
                is_below_any = True
        if not is_below_any:
            above_all.append(ticker)

    today = datetime.now(tz=timezone.utc).strftime("%d %b %Y")
    lines = [f"🌅 *Morning EMA scan — {today}*", ""]
    for indicator in EMA_SPANS:
        entries = below[indicator]
        lines.append(f"📉 Below *{indicator}*: {', '.join(entries) if entries else '—'}")
    if above_all:
        lines.append("")
        lines.append(f"✅ Above all EMAs: {', '.join(above_all)}")
    if failed:
        lines.append("")
        lines.append(f"⚠️ No data: {', '.join(failed)}")
    return "\n".join(lines)


async def run_morning_scan(
    bot: Bot, chat_id: str, exchanges: set[str] | None = None, region: str = ""
) -> None:
    """Scheduler entry point: build and send the pre-market EMA scan."""
    logger.info("Running morning EMA scan (region=%s)", region or "all")
    message = await asyncio.to_thread(build_morning_scan_message, exchanges)
    if message is None:
        logger.info("Morning scan skipped — no stocks for region %s", region or "all")
        return
    if region:
        message = message.replace("*Morning EMA scan", f"*Morning EMA scan ({region})")
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    logger.info("Morning scan sent (region=%s)", region or "all")


async def _check_one_price_alert(bot: Bot, chat_id: str, cfg, cooldown_hours: int) -> None:
    ticker       = cfg["ticker"]
    exchange     = cfg["exchange"]
    target_price = cfg["target_price"]
    direction    = cfg["direction"]  # ABOVE or BELOW

    current_price = get_current_price(ticker)
    if current_price is None:
        return

    triggered = (
        (direction == "ABOVE" and current_price >= target_price) or
        (direction == "BELOW" and current_price <= target_price)
    )
    if not triggered:
        return

    cooldown_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=cooldown_hours)
    with get_connection() as conn:
        recent = q.get_recent_price_alert_log(conn, cfg["id"], cooldown_cutoff)
        if recent:
            return
        q.log_price_alert(conn, cfg["id"], current_price)

    currency = CURRENCY_SYMBOL.get(exchange, "")
    arrow    = "📈" if direction == "ABOVE" else "📉"
    message  = (
        f"{arrow} PRICE ALERT: {ticker}\n"
        f"Target: {currency}{target_price:,.2f} ({direction})\n"
        f"Current price: {currency}{current_price:,.2f}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("👀 Keep watching", callback_data=f"palert:keep:{cfg['id']}"),
        InlineKeyboardButton("🗑 Remove alert",  callback_data=f"palert:cancel:{cfg['id']}"),
    ]])
    await bot.send_message(chat_id=chat_id, text=message, reply_markup=keyboard)
    logger.info("Price alert sent for %s @ %s (current %.2f)", ticker, target_price, current_price)


async def _check_one_ema_alert(bot: Bot, chat_id: str, cfg, cooldown_hours: int) -> None:
    ticker        = cfg["ticker"]
    indicator     = cfg["indicator"]
    threshold_pct = cfg["threshold_pct"]
    exchange      = cfg["exchange"]

    current_price = get_current_price(ticker)
    if current_price is None:
        return

    ema_value = get_ema(ticker, indicator)
    if ema_value is None:
        return

    # --- cross detection: fire when price flips sides of the EMA, no matter
    # how far it moved between checks. last_side is updated every tick (even
    # when the alert is cooldown-suppressed) so a cross is only reported once.
    side      = "ABOVE" if current_price >= ema_value else "BELOW"
    last_side = cfg["last_side"]
    if side != last_side:
        with get_connection() as conn:
            q.update_alert_last_side(conn, cfg["id"], side)
        if last_side is not None:
            await _send_cross_alert(
                bot, chat_id, cfg, current_price, ema_value, side, cooldown_hours
            )
            return  # cross alert supersedes the proximity alert this tick

    distance_pct = abs((current_price - ema_value) / ema_value) * 100
    if distance_pct > threshold_pct:
        return

    cooldown_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=cooldown_hours)
    with get_connection() as conn:
        recent = q.get_recent_alert_log(conn, cfg["id"], cooldown_cutoff)
        if recent:
            return
        q.log_alert(conn, cfg["id"], current_price, ema_value)

    currency = CURRENCY_SYMBOL.get(exchange, "")
    status   = "Hit / crossed" if distance_pct < 0.1 else f"Approaching ({distance_pct:.1f}% away)"
    message  = (
        f"⚠️ *ALERT: {ticker}*\n"
        f"Current price: {currency}{current_price:,.2f}\n"
        f"{indicator}: {currency}{ema_value:,.2f}\n"
        f"Distance: {distance_pct:.2f}% away\n"
        f"Status: {status}"
    )
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    logger.info("Alert sent for %s / %s (distance %.2f%%)", ticker, indicator, distance_pct)


async def _send_cross_alert(
    bot: Bot,
    chat_id: str,
    cfg,
    current_price: float,
    ema_value: float,
    side: str,
    cooldown_hours: int,
) -> None:
    """Notify that the price crossed the EMA. Shares the config's cooldown so
    a price whipsawing around the EMA doesn't spam one message per tick."""
    cooldown_cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=cooldown_hours)
    with get_connection() as conn:
        recent = q.get_recent_alert_log(conn, cfg["id"], cooldown_cutoff)
        if recent:
            return
        q.log_alert(conn, cfg["id"], current_price, ema_value)

    currency = CURRENCY_SYMBOL.get(cfg["exchange"], "")
    arrow    = "📈" if side == "ABOVE" else "📉"
    verb     = "crossed ABOVE" if side == "ABOVE" else "fell BELOW"
    message  = (
        f"{arrow} *CROSS ALERT: {cfg['ticker']}*\n"
        f"Price {verb} {cfg['indicator']}\n"
        f"Current price: {currency}{current_price:,.2f}\n"
        f"{cfg['indicator']}: {currency}{ema_value:,.2f}"
    )
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    logger.info("Cross alert sent for %s / %s (%s)", cfg["ticker"], cfg["indicator"], side)
