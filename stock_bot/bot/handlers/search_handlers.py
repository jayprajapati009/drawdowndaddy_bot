"""
/search handler — lets users find tickers by company name.

Uses inline keyboard buttons so the flow works in groups regardless of
Telegram's privacy mode (plain text replies aren't received in groups
unless privacy mode is disabled).

Flow:
  1. /search Apple          → numbered list with tap-to-select buttons
  2. User taps a result     → "Add to watchlist?" [Yes] [No]
  3. User taps Yes          → "Entry date?" [Today] [Enter date]
  4a. User taps Today       → added at current price
  4b. User taps Enter date  → bot asks for reply with DD/MM/YYYY
  5.  User replies with date → added at historical price
"""

import logging
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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


# ── Keyboards ──────────────────────────────────────────────────────────────────

def _pick_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for i, r in enumerate(results):
        label = f"{i + 1}. {r['name']} ({r['ticker']})"
        if r["exchange"]:
            label += f" — {r['exchange']}"
        rows.append([InlineKeyboardButton(label, callback_data=f"search:pick:{i}")])
    rows.append([
        InlineKeyboardButton("🔄 None of these", callback_data="search:other"),
        InlineKeyboardButton("❌ Cancel",         callback_data="search:cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _confirm_keyboard(ticker: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Yes, add {ticker}", callback_data="search:confirm:yes"),
        InlineKeyboardButton("❌ No",                 callback_data="search:confirm:no"),
    ]])


def _date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Today (current price)", callback_data="search:date:today"),
        InlineKeyboardButton("📆 Enter a past date",     callback_data="search:date:manual"),
    ]])


# ── Entry points ───────────────────────────────────────────────────────────────

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
    await _run_search(update.message.reply_text, ctx, query, attempt=1)


async def handle_search_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """CallbackQueryHandler — handles all inline button presses for the search flow."""
    cq    = update.callback_query
    await cq.answer()
    data  = cq.data
    state = ctx.user_data.get("search")

    # ── Cancel ─────────────────────────────────────────────────────────────────
    if data == "search:cancel":
        ctx.user_data.pop("search", None)
        await cq.edit_message_text("Search cancelled.")
        return

    if state is None:
        await cq.edit_message_text("This search has expired. Use /search to start a new one.")
        return

    # ── None of these / try again ──────────────────────────────────────────────
    if data == "search:other":
        attempt = state["attempt"] + 1
        if attempt > MAX_ATTEMPTS:
            ctx.user_data.pop("search", None)
            await cq.edit_message_text(
                "No match found. Search directly on Yahoo Finance:\n"
                f"{YAHOO_SEARCH}\n\n"
                "Then use: /watch TICKER EXCHANGE"
            )
        else:
            state["attempt"]       = attempt
            state["awaiting_query"] = True
            await cq.edit_message_text(
                f"Try a different spelling or the full name "
                f"(attempt {attempt}/{MAX_ATTEMPTS}).\n\n"
                "Reply to this message with your search:"
            )
        return

    # ── Pick a result ──────────────────────────────────────────────────────────
    if data.startswith("search:pick:"):
        idx     = int(data.split(":")[-1])
        results = state.get("results", [])
        if idx >= len(results):
            await cq.edit_message_text("Invalid selection. Use /search to try again.")
            return
        pick              = results[idx]
        state["selected"] = pick
        state["phase"]    = "confirm"
        exch = f" — {pick['exchange']}" if pick["exchange"] else ""
        await cq.edit_message_text(
            f"You picked: {pick['name']} ({pick['ticker']}){exch}\n\n"
            "Add to watchlist?",
            reply_markup=_confirm_keyboard(pick["ticker"]),
        )
        return

    # ── Confirm yes / no ───────────────────────────────────────────────────────
    if data == "search:confirm:no":
        ticker = state.get("selected", {}).get("ticker", "")
        ctx.user_data.pop("search", None)
        await cq.edit_message_text(f"Ok, {ticker} not added.")
        return

    if data == "search:confirm:yes":
        state["phase"] = "date"
        await cq.edit_message_text("Entry date?", reply_markup=_date_keyboard())
        return

    # ── Date selection ─────────────────────────────────────────────────────────
    if data == "search:date:today":
        pick        = state["selected"]
        telegram_id = get_account_id(update)
        ctx.user_data.pop("search", None)
        await cq.edit_message_text(f"Adding {pick['ticker']} to watchlist…")
        await _do_watch(cq.message.reply_text, pick, telegram_id, entry_date=None)
        return

    if data == "search:date:manual":
        state["phase"] = "date_manual"
        await cq.edit_message_text(
            "Enter the entry date using the command:\n\n"
            "/date DD/MM/YYYY\n\n"
            "Example: /date 15/01/2025"
        )
        return


async def cmd_set_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /date DD/MM/YYYY — completes a pending /search date entry."""
    state = ctx.user_data.get("search")
    if not state or state.get("phase") != "date_manual":
        await update.message.reply_text(
            "No pending search. Use /search first, then pick a stock and choose 'Enter a past date'."
        )
        return

    if not ctx.args:
        await update.message.reply_text("Usage: /date DD/MM/YYYY\nExample: /date 15/01/2025")
        return

    try:
        entry_date = _parse_date(ctx.args[0])
        if entry_date > date.today():
            await update.message.reply_text("❌ Date cannot be in the future.")
            return
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid date. Use DD/MM/YYYY — e.g. /date 15/01/2025")
        return

    pick        = state["selected"]
    telegram_id = get_account_id(update)
    ctx.user_data.pop("search", None)
    await _do_watch(update.message.reply_text, pick, telegram_id, entry_date)


async def handle_date_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Catches text replies when the user is in the date_manual or awaiting_query phase.
    Replies to the bot's messages are received even with group privacy mode enabled.
    """
    state = ctx.user_data.get("search")
    if not state:
        return

    text  = (update.message.text or "").strip()
    phase = state.get("phase")

    if phase == "awaiting_query" or state.get("awaiting_query"):
        state["awaiting_query"] = False
        await _run_search(update.message.reply_text, ctx, text, attempt=state["attempt"])
        return

    if phase == "date_manual":
        try:
            entry_date = _parse_date(text)
            if entry_date > date.today():
                await update.message.reply_text(
                    "❌ Date cannot be in the future. Reply again with a past date:"
                )
                return
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Couldn't read that. Use DD/MM/YYYY — e.g. 15/01/2025"
            )
            return
        pick        = state["selected"]
        telegram_id = get_account_id(update)
        ctx.user_data.pop("search", None)
        await _do_watch(update.message.reply_text, pick, telegram_id, entry_date)


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _run_search(reply_fn, ctx: ContextTypes.DEFAULT_TYPE, query: str, attempt: int) -> None:
    results = search_tickers(query)

    if not results:
        if attempt >= MAX_ATTEMPTS:
            ctx.user_data.pop("search", None)
            await reply_fn(
                f"Couldn't find anything for \"{query}\".\n\n"
                "Search directly on Yahoo Finance:\n"
                f"{YAHOO_SEARCH}\n\n"
                "Then use: /watch TICKER EXCHANGE"
            )
        else:
            ctx.user_data["search"] = {
                "attempt": attempt + 1, "awaiting_query": True, "phase": "pick",
            }
            await reply_fn(
                f"Couldn't find \"{query}\". Reply with a different name:"
            )
        return

    ctx.user_data["search"] = {
        "results": results, "attempt": attempt,
        "awaiting_query": False, "phase": "pick",
    }
    await reply_fn(
        f"Results for \"{query}\" — tap to select:",
        reply_markup=_pick_keyboard(results),
    )


async def _do_watch(reply_fn, pick: dict, telegram_id: str, entry_date) -> None:
    ticker   = pick["ticker"]
    exchange = pick["exchange"]
    name     = pick["name"]

    if not exchange:
        await reply_fn(
            f"Found {ticker} ({name}) but couldn't detect its exchange.\n"
            f"Add manually: /watch {ticker} EXCHANGE\n"
            "(Exchange: NASDAQ, NYSE, NSE, BSE)"
        )
        return
    try:
        result   = ws.add_stock(telegram_id, ticker, exchange, entry_date)
        currency = CURRENCY_SYMBOL.get(exchange, "")
        await reply_fn(
            f"✅ Added {ticker} ({name}) to watchlist\n"
            f"Exchange: {exchange}\n"
            f"Entry price: {currency}{result['added_price']:,.2f} ({result['price_label']})"
        )
    except ws.WatchlistError as e:
        await reply_fn(f"❌ {e}")
