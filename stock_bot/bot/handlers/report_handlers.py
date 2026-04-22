"""
Report and details command handlers.
"""

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.services import watchlist_service as ws, holdings_service as hs
from stock_bot.services.price_fetcher import get_all_emas, get_current_price
from stock_bot.bot.handlers._helpers import fmt_pct, get_account_id


async def cmd_weekly_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /report"""
    telegram_id = get_account_id(update)
    lines = ["📊 Weekly Report\n"]

    # --- Watchlist section ---
    watchlist = ws.get_watchlist_with_prices(telegram_id)
    if watchlist:
        lines.append("── Watchlist ──")
        for item in watchlist:
            currency = CURRENCY_SYMBOL.get(item["exchange"], "")
            price_str = f"{currency}{item['current_price']:,.2f}" if item["current_price"] else "N/A"
            pct_str = fmt_pct(item["pct_return"])
            lines.append(f"• {item['ticker']}: {price_str} ({pct_str} since added)")
            for cp in item["checkpoints"]:
                lines.append(f"  └ {cp['label']}: {fmt_pct(cp['pct_return'])}")
        lines.append("")

    # --- Holdings section ---
    positions = hs.get_positions(telegram_id)
    if positions:
        lines.append("── Holdings P&L ──")
        total = 0.0
        for pos in positions:
            currency = CURRENCY_SYMBOL.get(pos["exchange"], "")
            pnl = pos["unrealised_pnl"]
            pct = None
            if pos["current_price"] and pos["avg_cost"]:
                pct = ((pos["current_price"] - pos["avg_cost"]) / pos["avg_cost"]) * 100
            pnl_str = (f"{'+'if pnl >= 0 else ''}{currency}{pnl:,.2f}") if pnl is not None else "N/A"
            lines.append(f"• {pos['ticker']}: {pnl_str} ({fmt_pct(pct)})")
            if pnl is not None:
                total += pnl
        lines.append(f"\nNet Unrealised P&L: {'+'if total >= 0 else ''}{total:,.2f}")

    if not watchlist and not positions:
        lines.append("Nothing to report yet. Use /watch or /buy to get started.")

    await update.message.reply_text("\n".join(lines))


async def cmd_stock_details(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /stock TICKER"""
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /stock TICKER")
        return

    ticker = args[0].upper()
    telegram_id = get_account_id(update)
    lines = [f"🔍 {ticker} Details\n"]

    current = get_current_price(ticker)
    price_str = f"{current:,.2f}" if current else "N/A"
    lines.append(f"Current price: {price_str}\n")

    # EMA values
    emas = get_all_emas(ticker)
    lines.append("Technical indicators (weekly EMA)")
    for indicator, value in emas.items():
        if value is not None and current is not None:
            dist = ((current - value) / value) * 100
            lines.append(f"• {indicator}: {value:,.2f} ({fmt_pct(dist)} from price)")
        else:
            lines.append(f"• {indicator}: N/A")
    lines.append("")

    # Watchlist info
    watchlist = ws.get_watchlist_with_prices(telegram_id)
    wl_item = next((i for i in watchlist if i["ticker"] == ticker), None)
    if wl_item:
        currency  = CURRENCY_SYMBOL.get(wl_item["exchange"], "")
        added_date = str(wl_item["added_at"])[:10]
        lines.append(
            f"Watchlist: added {added_date} at {currency}{wl_item['added_price']:,.2f} ({fmt_pct(wl_item['pct_return'])})"
        )
        for cp in wl_item["checkpoints"]:
            lines.append(f"  📍 {cp['label']}: {fmt_pct(cp['pct_return'])}")
        lines.append("")

        # Price alerts for this stock
        from stock_bot.database.db import get_connection
        from stock_bot.database import queries as q
        with get_connection() as conn:
            price_alerts = q.get_price_alerts(conn, wl_item["watchlist_id"])
        if price_alerts:
            lines.append("Price alerts")
            for a in price_alerts:
                arrow = "📈" if a["direction"] == "ABOVE" else "📉"
                dist_str = ""
                if current:
                    dist_pct = ((a["target_price"] - current) / current) * 100
                    sign = "+" if dist_pct >= 0 else ""
                    dist_str = f", {sign}{dist_pct:.1f}% away"
                lines.append(f"  {arrow} {currency}{a['target_price']:,.2f} ({a['direction']}{dist_str})")
            lines.append("")

    # Holdings info
    positions = hs.get_positions(telegram_id)
    pos = next((p for p in positions if p["ticker"] == ticker), None)
    if pos:
        currency = CURRENCY_SYMBOL.get(pos["exchange"], "")
        pct = None
        if pos["current_price"] and pos["avg_cost"]:
            pct = ((pos["current_price"] - pos["avg_cost"]) / pos["avg_cost"]) * 100
        pnl = pos["unrealised_pnl"]
        pnl_str = (f"{'+'if pnl >= 0 else ''}{currency}{pnl:,.2f}") if pnl is not None else "N/A"
        lines.append(
            f"Holdings: {pos['quantity']} units\n"
            f"Avg cost: {currency}{pos['avg_cost']:,.2f} | Unrealised: {pnl_str} ({fmt_pct(pct)})"
        )

    await update.message.reply_text("\n".join(lines))
