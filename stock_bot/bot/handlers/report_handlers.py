"""
Report and details command handlers.
"""

from telegram import Update
from telegram.ext import ContextTypes

from stock_bot.config import CURRENCY_SYMBOL
from stock_bot.services import watchlist_service as ws, holdings_service as hs
from stock_bot.services.price_fetcher import get_all_emas, get_current_price, get_rsi
from stock_bot.bot.handlers._helpers import fmt_pct, get_account_id
from stock_bot.database.db import get_connection
from stock_bot.database import queries as q


def _tradingview_url(ticker: str, exchange: str) -> str:
    clean = ticker.split(".")[0]
    return f"https://www.tradingview.com/chart/?symbol={exchange or 'NASDAQ'}:{clean}"


def _rsi_label(rsi: float) -> str:
    if rsi >= 70:
        return "overbought"
    if rsi <= 30:
        return "oversold"
    return "neutral"


def _section_technicals(ticker: str, current: float | None) -> list[str]:
    lines = ["Technical indicators (weekly)"]
    for indicator, value in get_all_emas(ticker).items():
        if value is not None and current is not None:
            dist = ((current - value) / value) * 100
            lines.append(f"• {indicator}: {value:,.2f} ({fmt_pct(dist)} from price)")
        else:
            lines.append(f"• {indicator}: N/A")
    rsi = get_rsi(ticker)
    if rsi is not None:
        lines.append(f"• RSI(14): {rsi:.1f} ({_rsi_label(rsi)})")
    else:
        lines.append("• RSI(14): N/A")
    return lines


def _section_watchlist(wl_item: dict, current: float | None, currency: str) -> list[str]:
    added_date = str(wl_item["added_at"])[:10]
    entry      = f"{currency}{wl_item['added_price']:,.2f}"
    lines = [f"Watchlist: added {added_date} at {entry} ({fmt_pct(wl_item['pct_return'])})"]
    for cp in wl_item["checkpoints"]:
        lines.append(f"  📍 {cp['label']}: {fmt_pct(cp['pct_return'])}")
    with get_connection() as conn:
        alerts = q.get_price_alerts(conn, wl_item["watchlist_id"])
    if alerts:
        lines.append("Price alerts")
        for a in alerts:
            arrow = "📈" if a["direction"] == "ABOVE" else "📉"
            dist_str = ""
            if current:
                pct  = ((a["target_price"] - current) / current) * 100
                sign = "+" if pct >= 0 else ""
                dist_str = f", {sign}{pct:.1f}% away"
            lines.append(
                f"  {arrow} {currency}{a['target_price']:,.2f}"
                f" ({a['direction']}{dist_str})"
            )
    return lines


def _signed(val: float, currency: str) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{currency}{val:,.2f}"


def _section_returns(returns: dict, currency: str) -> list[str]:
    lines = ["── Returns ──"]

    r_pnl = returns["realized_pnl"]
    lines.append(f"Realized P&L:     {_signed(r_pnl, currency)}")

    u_pnl = returns["unrealized_pnl"]
    if u_pnl is not None:
        lines.append(f"Unrealized P&L:   {_signed(u_pnl, currency)}")

    lines.append(f"Total invested:   {currency}{returns['total_invested']:,.2f}")

    simple = returns["total_return_pct"]
    if simple is not None:
        lines.append(f"Simple return:    {fmt_pct(simple)}")

    twr = returns["twr_pct"]
    if twr is not None:
        lines.append(f"Time-wt. return:  {fmt_pct(twr)}")

    return lines


def _section_history(history: list[dict], currency: str) -> list[str]:
    lines = ["── Transaction history ──"]
    for lot in history:
        date_str = str(lot["transacted_at"])[:10]
        note     = f"  [{lot['notes']}]" if lot.get("notes") else ""
        qty      = lot["quantity"]
        pr       = lot["price"]

        if lot["action"] == "BUY":
            tag = " (sold)" if lot.get("consumed") else ""
            lines.append(f"🟢 BUY {qty:g} @ {currency}{pr:,.2f} — {date_str}{tag}{note}")
        else:
            cb  = lot.get("cost_basis")
            if cb:
                pnl  = (pr - cb) * qty
                pct  = (pr / cb - 1) * 100
                sign = "+" if pnl >= 0 else ""
                pnl_str = f"  →  {sign}{currency}{pnl:,.2f} ({sign}{pct:.1f}%)"
            else:
                pnl_str = ""
            lines.append(f"🔴 SELL {qty:g} @ {currency}{pr:,.2f} — {date_str}{pnl_str}{note}")
    return lines


# ── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_weekly_report(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /report"""
    telegram_id = get_account_id(update)
    lines = ["📊 Weekly Report\n"]

    watchlist = ws.get_watchlist_with_prices(telegram_id)
    if watchlist:
        lines.append("── Watchlist ──")
        for item in watchlist:
            currency  = CURRENCY_SYMBOL.get(item["exchange"], "")
            price_str = f"{currency}{item['current_price']:,.2f}" if item["current_price"] else "N/A"
            lines.append(
                f"• {item['ticker']}: {price_str} ({fmt_pct(item['pct_return'])} since added)"
            )
            for cp in item["checkpoints"]:
                lines.append(f"  └ {cp['label']}: {fmt_pct(cp['pct_return'])}")
        lines.append("")

    positions = hs.get_positions(telegram_id)
    if positions:
        lines.append("── Holdings P&L ──")
        total = 0.0
        for pos in positions:
            currency = CURRENCY_SYMBOL.get(pos["exchange"], "")
            pnl      = pos["unrealised_pnl"]
            pct      = None
            if pos["current_price"] and pos["avg_cost"]:
                pct = ((pos["current_price"] - pos["avg_cost"]) / pos["avg_cost"]) * 100
            pnl_str = (
                f"{'+'if pnl >= 0 else ''}{currency}{pnl:,.2f}"
            ) if pnl is not None else "N/A"
            lines.append(f"• {pos['ticker']}: {pnl_str} ({fmt_pct(pct)})")
            if pnl is not None:
                total += pnl
        sign = "+" if total >= 0 else ""
        lines.append(f"\nNet Unrealised P&L: {sign}{total:,.2f}")

    if not watchlist and not positions:
        lines.append("Nothing to report yet. Use /watch or /buy to get started.")

    await update.message.reply_text("\n".join(lines))


async def cmd_stock_details(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /stock TICKER"""
    if not ctx.args:
        await update.message.reply_text("Usage: /stock TICKER")
        return

    ticker      = ctx.args[0].upper()
    telegram_id = get_account_id(update)
    current     = get_current_price(ticker)
    price_str   = f"{current:,.2f}" if current else "N/A"

    lines = [f"🔍 {ticker} Details\n", f"Current price: {price_str}\n"]
    lines += _section_technicals(ticker, current)
    lines.append("")

    watchlist = ws.get_watchlist_with_prices(telegram_id)
    wl_item   = next((i for i in watchlist if i["ticker"] == ticker), None)
    exchange  = wl_item["exchange"] if wl_item else ""
    currency  = CURRENCY_SYMBOL.get(exchange, "")

    if wl_item:
        lines += _section_watchlist(wl_item, current, currency)
        lines.append("")

    returns = hs.get_stock_returns(telegram_id, ticker)
    if returns:
        lines += _section_returns(returns, currency)
        lines.append("")

    history = hs.get_transaction_history(telegram_id, ticker)
    if history:
        lines += _section_history(history, currency)
        lines.append("")

    lines.append(f"Chart: {_tradingview_url(ticker, exchange)}")
    await update.message.reply_text("\n".join(lines))
