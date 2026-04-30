"""
/search handler — lets users find tickers by company name.

Flow:
  1. /search Apple           → shows numbered list of matches
  2. User replies 1/2/3      → adds that ticker to watchlist automatically
  3. User replies "other"    → try again (up to MAX_ATTEMPTS)
  4. After MAX_ATTEMPTS      → shows Yahoo Finance search link

State is stored in ctx.user_data["search"] per user so multiple users
in a group can search independently without interfering.
"""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.services.ticker_search import search_tickers
from stock_bot.services import watchlist_service as ws
from stock_bot.bot.handlers._helpers import get_account_id

logger = logging.getLogger(__name__)

MAX_ATTEMPTS   = 2
YAHOO_SEARCH   = "https://finance.yahoo.com/lookup/"
_DIGIT_RE      = re.compile(r"^\s*([1-9])\s*$")
_OTHER_RE      = re.compile(r"^\s*(other|0|none|cancel)\s*$", re.IGNORECASE)


# ── Public entry point ─────────────────────────────────────────────────────────

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage: /search COMPANY NAME
    Searches Yahoo Finance and lets the user pick a ticker interactively.
    """
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
    MessageHandler that catches digit / 'other' replies to a pending search.
    Silently ignored if the user has no active search.
    """
    state = ctx.user_data.get("search")
    if not state:
        return

    text = (update.message.text or "").strip()

    # ── Cancel ─────────────────────────────────────────────────────────────────
    if _OTHER_RE.match(text) and "cancel" in text.lower():
        ctx.user_data.pop("search", None)
        await update.message.reply_text("Search cancelled.")
        return

    # ── "Other" — try again ────────────────────────────────────────────────────
    if _OTHER_RE.match(text):
        attempt = state["attempt"] + 1
        if attempt > MAX_ATTEMPTS:
            ctx.user_data.pop("search", None)
            await update.message.reply_text(
                "No worries! You can search directly on Yahoo Finance to find the exact ticker:\n"
                f"{YAHOO_SEARCH}\n\n"
                "Once you have the ticker, use:\n"
                "  /watch TICKER EXCHANGE\n"
                "Example: /watch AAPL NASDAQ"
            )
            return
        await update.message.reply_text(
            f"No problem! Try a different spelling or the full company name.\n"
            f"(Attempt {attempt}/{MAX_ATTEMPTS})\n\n"
            "Type your search:"
        )
        state["attempt"] = attempt
        state["awaiting_query"] = True
        return

    # ── New query after "other" ────────────────────────────────────────────────
    if state.get("awaiting_query"):
        state["awaiting_query"] = False
        await _run_search(update, ctx, text, attempt=state["attempt"])
        return

    # ── Number selection ───────────────────────────────────────────────────────
    m = _DIGIT_RE.match(text)
    if not m:
        return

    idx = int(m.group(1)) - 1
    results = state.get("results", [])
    if idx >= len(results):
        await update.message.reply_text(
            f"Please pick a number between 1 and {len(results)}, or reply 'other'."
        )
        return

    pick = results[idx]
    ctx.user_data.pop("search", None)
    await _do_watch(update, ctx, pick["ticker"], pick["exchange"], pick["name"])


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _run_search(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    query: str,
    attempt: int,
) -> None:
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
            ctx.user_data["search"] = {"attempt": attempt + 1, "awaiting_query": True}
            await update.message.reply_text(
                f"Couldn't find anything for \"{query}\". Try a different spelling or the full company name:"
            )
        return

    ctx.user_data["search"] = {
        "results": results,
        "attempt": attempt,
        "awaiting_query": False,
    }

    lines = [f"Search results for \"{query}\" — reply with a number:\n"]
    for i, r in enumerate(results, 1):
        exch = f" — {r['exchange']}" if r["exchange"] else ""
        lines.append(f"{i}. {r['name']} ({r['ticker']}){exch}")
    lines.append(f"\n0. None of these / try again")
    lines.append("cancel — cancel search")

    await update.message.reply_text("\n".join(lines))


async def _do_watch(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    ticker: str,
    exchange: str,
    name: str,
) -> None:
    telegram_id = get_account_id(update)
    if not exchange:
        await update.message.reply_text(
            f"Found {ticker} ({name}) but couldn't detect its exchange automatically.\n"
            f"Add it manually: /watch {ticker} EXCHANGE\n"
            f"(Exchange is one of: NASDAQ, NYSE, NSE, BSE)"
        )
        return
    try:
        result   = ws.add_stock(telegram_id, ticker, exchange)
        currency = CURRENCY_SYMBOL.get(exchange, "")
        await update.message.reply_text(
            f"✅ Added {ticker} ({name}) to watchlist\n"
            f"Exchange: {exchange}\n"
            f"Entry price: {currency}{result['added_price']:,.2f}"
        )
    except ws.WatchlistError as e:
        await update.message.reply_text(f"❌ {e}")
