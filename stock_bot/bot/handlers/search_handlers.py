"""
/search handler — lets users find tickers by company name.

Flow:
  1. /search Apple              → numbered list of matches
  2. User replies 1/2/3         → asks "Add to watchlist?"
  3. User replies yes           → asks "Entry date? (today or DD/MM/YYYY)"
  4. User replies today / date  → adds to watchlist
  5. User replies no            → ends without adding

  At any step: 'cancel' aborts. 'other' tries a new search (max 2 attempts).
  After 2 failed attempts       → shows Yahoo Finance search link.

State is stored in ctx.user_data["search"] per user.
"""

import logging
import re
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.services.ticker_search import search_tickers
from stock_bot.services import watchlist_service as ws
from stock_bot.bot.handlers._helpers import get_account_id

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
YAHOO_SEARCH = "https://finance.yahoo.com/lookup/"


def _parse_date(value: str) -> date:
    return date(*reversed([int(p) for p in value.split("/")]))


# ── Public entry point ─────────────────────────────────────────────────────────

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /search COMPANY NAME"""
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /search COMPANY NAME\n\n"
            "Examples:\n"
            "  /search Apple\n"
            "  /search Reliance Industries\n"
            "  /search HDFC Bank"
        )
        return

    query = " ".join(ctx.args)
    await _run_search(update, ctx, query, attempt=1)


async def handle_search_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches all non-command text messages and routes them through the
    search state machine. Silently ignored if no search is active.
    """
    state = ctx.user_data.get("search")
    if not state:
        return

    text = (update.message.text or "").strip()
    phase = state.get("phase", "pick")

    if phase == "pick":
        await _handle_pick(update, ctx, state, text)
    elif phase == "confirm":
        await _handle_confirm(update, ctx, state, text)
    elif phase == "date":
        await _handle_date(update, ctx, state, text)


# ── Phase handlers ─────────────────────────────────────────────────────────────

async def _handle_pick(update, ctx, state, text):
    """User is choosing a number from the results list."""
    lower = text.lower()

    if lower == "cancel":
        ctx.user_data.pop("search", None)
        await update.message.reply_text("Search cancelled.")
        return

    if lower in ("other", "0", "none"):
        attempt = state["attempt"] + 1
        if attempt > MAX_ATTEMPTS:
            ctx.user_data.pop("search", None)
            await update.message.reply_text(
                "No match found. Search directly on Yahoo Finance:\n"
                f"{YAHOO_SEARCH}\n\n"
                "Then use: /watch TICKER EXCHANGE"
            )
            return
        state["attempt"] = attempt
        state["awaiting_query"] = True
        await update.message.reply_text(
            f"Try a different spelling or the full company name "
            f"(attempt {attempt}/{MAX_ATTEMPTS}):"
        )
        return

    if state.get("awaiting_query"):
        state["awaiting_query"] = False
        await _run_search(update, ctx, text, attempt=state["attempt"])
        return

    if not re.match(r"^[1-9]$", text):
        return  # not our message, ignore

    idx = int(text) - 1
    results = state.get("results", [])
    if idx >= len(results):
        await update.message.reply_text(
            f"Pick a number between 1 and {len(results)}, or reply 'other'."
        )
        return

    pick = results[idx]
    state["selected"] = pick
    state["phase"]    = "confirm"
    exch = f" — {pick['exchange']}" if pick["exchange"] else ""
    await update.message.reply_text(
        f"You picked: {pick['name']} ({pick['ticker']}){exch}\n\n"
        f"Add to watchlist? Reply yes or no"
    )


async def _handle_confirm(update, ctx, state, text):
    """User said yes or no to adding the stock."""
    lower = text.lower()

    if lower in ("cancel", "no"):
        ctx.user_data.pop("search", None)
        ticker = state["selected"]["ticker"]
        msg = "Cancelled." if lower == "cancel" else f"Ok, {ticker} not added."
        await update.message.reply_text(msg)
        return

    if lower == "yes":
        state["phase"] = "date"
        await update.message.reply_text(
            "Entry date?\n\n"
            "Reply today for the current price, or enter a date:\n"
            "DD/MM/YYYY — e.g. 15/01/2025"
        )
    else:
        await update.message.reply_text("Please reply yes or no.")


async def _handle_date(update, ctx, state, text):
    """User provided an entry date."""
    lower = text.lower()

    if lower == "cancel":
        ctx.user_data.pop("search", None)
        await update.message.reply_text("Cancelled.")
        return

    entry_date = None
    if lower != "today":
        try:
            entry_date = _parse_date(text)
            if entry_date > date.today():
                await update.message.reply_text("❌ Date cannot be in the future. Try again or reply today.")
                return
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Couldn't read that date. Use DD/MM/YYYY (e.g. 15/01/2025) or reply today."
            )
            return

    pick        = state["selected"]
    telegram_id = get_account_id(update)
    ctx.user_data.pop("search", None)
    await _do_watch(update, pick["ticker"], pick["exchange"], pick["name"], telegram_id, entry_date)


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _run_search(update, ctx, query: str, attempt: int) -> None:
    results = search_tickers(query)

    if not results:
        if attempt >= MAX_ATTEMPTS:
            ctx.user_data.pop("search", None)
            await update.message.reply_text(
                f"Couldn't find anything for \"{query}\".\n\n"
                "Search directly on Yahoo Finance:\n"
                f"{YAHOO_SEARCH}\n\n"
                "Then use: /watch TICKER EXCHANGE"
            )
        else:
            ctx.user_data["search"] = {
                "attempt": attempt + 1, "awaiting_query": True, "phase": "pick"
            }
            await update.message.reply_text(
                f"Couldn't find anything for \"{query}\". "
                "Try a different spelling or the full company name:"
            )
        return

    ctx.user_data["search"] = {
        "results":       results,
        "attempt":       attempt,
        "awaiting_query": False,
        "phase":         "pick",
    }

    lines = [f"Results for \"{query}\" — reply with a number:\n"]
    for i, r in enumerate(results, 1):
        exch = f" — {r['exchange']}" if r["exchange"] else ""
        lines.append(f"{i}. {r['name']} ({r['ticker']}){exch}")
    lines.append("\n0. None of these / try again")
    lines.append("cancel — cancel")

    await update.message.reply_text("\n".join(lines))


async def _do_watch(update, ticker, exchange, name, telegram_id, entry_date) -> None:
    if not exchange:
        await update.message.reply_text(
            f"Found {ticker} ({name}) but couldn't detect its exchange.\n"
            f"Add it manually: /watch {ticker} EXCHANGE\n"
            "(Exchange: NASDAQ, NYSE, NSE, BSE)"
        )
        return
    try:
        result   = ws.add_stock(telegram_id, ticker, exchange, entry_date)
        currency = CURRENCY_SYMBOL.get(exchange, "")
        await update.message.reply_text(
            f"✅ Added {ticker} ({name}) to watchlist\n"
            f"Exchange: {exchange}\n"
            f"Entry price: {currency}{result['added_price']:,.2f} ({result['price_label']})"
        )
    except ws.WatchlistError as e:
        await update.message.reply_text(f"❌ {e}")
