"""
/start and /help handlers.
"""

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q

HELP_TEXT = """📈 *Stock Alert & Portfolio Bot*

━━━━━━━━━━━━━━━━━━━━
👤 *Getting started*
━━━━━━━━━━━━━━━━━━━━
/start — register yourself \\(run this first\\)

━━━━━━━━━━━━━━━━━━━━
📋 *Watchlist*
━━━━━━━━━━━━━━━━━━━━
/watch TICKER EXCHANGE \\[DD/MM/YYYY\\]
  → `/watch RELIANCE\\.NS NSE`
  → `/watch AAPL NASDAQ 15/01/2025`

/unwatch TICKER — stop tracking
/watchlist — all stocks with live prices & returns
/mark TICKER LABEL — save today's price as a reference
  → `/mark RELIANCE\\.NS pre\\-results`

━━━━━━━━━━━━━━━━━━━━
🔔 *Alerts*
━━━━━━━━━━━━━━━━━━━━
/alert TICKER INDICATOR THRESHOLD
  → fire when price is within X% of an EMA
  → `/alert RELIANCE\\.NS EMA\\_10W 5`
  → `/alert AAPL EMA\\_40W 3`

/unalert TICKER INDICATOR — disable an alert
/alerts TICKER — list active alerts for a stock

Indicators: *EMA\\_10W* \\(10\\-week\\) · *EMA\\_40W* \\(40\\-week\\)

━━━━━━━━━━━━━━━━━━━━
🎯 *Price Alerts*
━━━━━━━━━━━━━━━━━━━━
/palert TICKER PRICE — fire when price crosses target
  → `/palert AAPL 250`
  → direction auto\\-detected from current price

/unpalert TICKER PRICE — remove a price alert
/palerts TICKER — list active price alerts

━━━━━━━━━━━━━━━━━━━━
💼 *Holdings*
━━━━━━━━━━━━━━━━━━━━
/buy TICKER EXCHANGE QTY PRICE \\[note\\]
  → `/buy RELIANCE\\.NS NSE 10 2450`
  → `/buy AAPL NASDAQ 5 185\\.50 long\\-term`

/sell TICKER QTY PRICE \\[note\\] — FIFO lot matching
  → `/sell RELIANCE\\.NS 5 2600`

/holdings — open positions with avg cost & P&L
/history TICKER — full buy/sell log for one stock

━━━━━━━━━━━━━━━━━━━━
📊 *Reports*
━━━━━━━━━━━━━━━━━━━━
/report — full watchlist \\+ holdings summary
/stock TICKER — price, EMAs, watchlist & holding P&L

━━━━━━━━━━━━━━━━━━━━
🌍 *Exchanges*
━━━━━━━━━━━━━━━━━━━━
NSE · BSE \\(India\\) · NASDAQ · NYSE \\(US\\)

⚠️ Each person's data is separate even in a shared group\\.
"""


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Register the user and show a welcome message."""
    user = update.effective_user
    telegram_id = str(user.id)
    username = user.username

    with get_connection() as conn:
        q.upsert_user(conn, telegram_id, username)

    await update.message.reply_text(
        f"👋 Welcome{', @' + username if username else ''}!\n\n"
        "You're registered. Use /help to see all commands.",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")
