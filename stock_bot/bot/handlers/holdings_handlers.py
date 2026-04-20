"""
Telegram command handlers for holdings and transaction management.
"""

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.services import holdings_service as hs
from stock_bot.bot.handlers._helpers import fmt_pct


async def cmd_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /buy TICKER EXCHANGE QUANTITY PRICE [notes]"""
    args = ctx.args
    if len(args) < 4:
        await update.message.reply_text(
            "Usage: /buy TICKER EXCHANGE QUANTITY PRICE [notes]\n"
            "Example: /buy RELIANCE.NS NSE 10 2450"
        )
        return

    ticker, exchange = args[0].upper(), args[1].upper()
    try:
        quantity = float(args[2])
        price = float(args[3])
    except ValueError:
        await update.message.reply_text("Quantity and price must be numbers.")
        return
    notes = " ".join(args[4:]) or None
    telegram_id = str(update.effective_user.id)

    try:
        result = hs.buy(telegram_id, ticker, exchange, quantity, price, notes)
        currency = CURRENCY_SYMBOL.get(exchange, "")
        await update.message.reply_text(
            f"✅ *BUY logged*\n"
            f"{result['ticker']} ({exchange})\n"
            f"Qty: {result['quantity']} @ {currency}{result['price']:,.2f}\n"
            f"Total: {currency}{result['quantity'] * result['price']:,.2f}",
            parse_mode="Markdown",
        )
    except hs.HoldingsError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_sell(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /sell TICKER QUANTITY PRICE [notes]"""
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /sell TICKER QUANTITY PRICE [notes]\n"
            "Example: /sell RELIANCE.NS 5 2600"
        )
        return

    ticker = args[0].upper()
    try:
        quantity = float(args[1])
        price = float(args[2])
    except ValueError:
        await update.message.reply_text("Quantity and price must be numbers.")
        return
    notes = " ".join(args[3:]) or None
    telegram_id = str(update.effective_user.id)

    try:
        result = hs.sell(telegram_id, ticker, quantity, price, notes)
        pnl = result["realised_pnl"]
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        await update.message.reply_text(
            f"✅ *SELL logged*\n"
            f"{result['ticker']}\n"
            f"Qty: {result['quantity']} @ {price:,.2f}\n"
            f"{pnl_emoji} Realised P&L: {'+' if pnl >= 0 else ''}{pnl:,.2f}",
            parse_mode="Markdown",
        )
    except hs.HoldingsError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_view_holdings(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /view_holdings"""
    telegram_id = str(update.effective_user.id)
    positions = hs.get_positions(telegram_id)

    if not positions:
        await update.message.reply_text("You have no open positions. Use /buy to log a transaction.")
        return

    lines = ["💼 *Your Holdings*\n"]
    total_unrealised = 0.0
    for pos in positions:
        currency = CURRENCY_SYMBOL.get(pos["exchange"], "")
        price_str = f"{currency}{pos['current_price']:,.2f}" if pos["current_price"] else "N/A"
        pnl = pos["unrealised_pnl"]
        pnl_str = f"{'+'if pnl >= 0 else ''}{currency}{pnl:,.2f}" if pnl is not None else "N/A"
        if pnl is not None:
            total_unrealised += pnl

        pct = None
        if pos["current_price"] and pos["avg_cost"]:
            pct = ((pos["current_price"] - pos["avg_cost"]) / pos["avg_cost"]) * 100

        lines.append(
            f"*{pos['ticker']}* ({pos['exchange']})\n"
            f"  Qty: {pos['quantity']} | Avg: {currency}{pos['avg_cost']:,.2f} | Now: {price_str}\n"
            f"  Unrealised P&L: {pnl_str} ({fmt_pct(pct)})"
        )
        lines.append("")

    lines.append(f"Total Unrealised P&L: {'+'if total_unrealised >= 0 else ''}{total_unrealised:,.2f}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_transaction_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /transaction_history TICKER"""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /transaction_history TICKER")
        return

    ticker = args[0].upper()
    telegram_id = str(update.effective_user.id)
    lots = hs.get_transaction_history(telegram_id, ticker)

    if not lots:
        await update.message.reply_text(f"No transaction history found for {ticker}.")
        return

    lines = [f"📜 *Transaction history: {ticker}*\n"]
    for lot in lots:
        action_emoji = "🟢" if lot["action"] == "BUY" else "🔴"
        date_str = str(lot["transacted_at"])[:10]
        note_str = f" — {lot['notes']}" if lot["notes"] else ""
        lines.append(
            f"{action_emoji} {lot['action']} {lot['quantity']} @ {lot['price']:,.2f} on {date_str}{note_str}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
