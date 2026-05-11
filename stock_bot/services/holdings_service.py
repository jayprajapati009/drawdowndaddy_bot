"""
Holdings and lot management.

Cost basis and P&L are always computed from raw lot data at query time.
Sells consume the oldest open BUY lots first (FIFO).
"""

import logging
from typing import Optional

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import get_current_price, get_prices_batch

logger = logging.getLogger(__name__)


class HoldingsError(Exception):
    """Raised for invalid or impossible holdings operations."""


def buy(
    telegram_id: str,
    ticker: str,
    exchange: str,
    quantity: float,
    price: float,
    notes: Optional[str] = None,
    trade_date: Optional[str] = None,
) -> dict:
    """Log a BUY lot. Returns lot details. trade_date is ISO format YYYY-MM-DD."""
    if quantity <= 0 or price <= 0:
        raise HoldingsError("Quantity and price must be positive.")

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise HoldingsError("User not registered. Send /start first.")
        holding_id = q.get_or_create_holding(conn, user_id, ticker, exchange)
        q.add_lot(conn, holding_id, "BUY", quantity, price, notes, transacted_at=trade_date)

    logger.info("BUY %s × %s @ %s on %s", quantity, ticker, price, trade_date or "today")
    return {"ticker": ticker.upper(), "action": "BUY", "quantity": quantity, "price": price}


def sell(
    telegram_id: str,
    ticker: str,
    quantity: float,
    price: float,
    notes: Optional[str] = None,
    trade_date: Optional[str] = None,
) -> dict:
    """
    Log a SELL using FIFO lot matching.
    Returns realised P&L and a breakdown of which lots were consumed.
    """
    if quantity <= 0 or price <= 0:
        raise HoldingsError("Quantity and price must be positive.")

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise HoldingsError("User not registered.")

        holding = q.get_holding(conn, user_id, ticker)
        if holding is None:
            raise HoldingsError(f"No holding found for {ticker.upper()}.")

        buy_lots = q.get_open_buy_lots(conn, holding["id"])
        total_held = sum(lot["quantity"] for lot in buy_lots)
        if quantity > total_held:
            raise HoldingsError(
                f"Cannot sell {quantity} — you only hold {total_held} units of {ticker.upper()}."
            )

        # FIFO matching
        remaining    = quantity
        realised_pnl = 0.0
        total_cost   = 0.0
        consumed     = []

        for lot in buy_lots:
            if remaining <= 0:
                break
            lot_qty      = lot["quantity"]
            consumed_qty = min(lot_qty, remaining)
            realised_pnl += consumed_qty * (price - lot["price"])
            total_cost   += consumed_qty * lot["price"]
            consumed.append({"lot_id": lot["id"], "qty": consumed_qty, "cost": lot["price"]})
            remaining -= consumed_qty

            if consumed_qty >= lot_qty:
                q.delete_lot(conn, lot["id"])
            else:
                q.update_lot_quantity(conn, lot["id"], lot_qty - consumed_qty)

        avg_cost = total_cost / quantity if quantity else 0.0
        q.add_lot(conn, holding["id"], "SELL", quantity, price, notes,
                  cost_basis=avg_cost, transacted_at=trade_date)

    logger.info("SELL %s × %s @ %s, realised P&L = %.2f for user %s",
                quantity, ticker, price, realised_pnl, telegram_id)
    return {
        "ticker": ticker.upper(),
        "action": "SELL",
        "quantity": quantity,
        "price": price,
        "realised_pnl": realised_pnl,
        "lots_consumed": consumed,
    }


def get_positions(telegram_id: str) -> list[dict]:
    """
    Return all current open positions with quantity, average cost, current
    price, and unrealised P&L.
    """
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            return []
        holdings = q.get_holdings(conn, user_id)
        lots_by_holding = {h["id"]: q.get_open_buy_lots(conn, h["id"]) for h in holdings}

    # Build open positions first, then batch-fetch prices in parallel
    open_positions = []
    for h in holdings:
        buy_lots = lots_by_holding[h["id"]]
        total_qty = sum(lot["quantity"] for lot in buy_lots)
        if total_qty == 0:
            continue
        avg_cost = sum(lot["quantity"] * lot["price"] for lot in buy_lots) / total_qty
        open_positions.append((h, total_qty, avg_cost))

    prices = get_prices_batch([h["ticker"] for h, _, _ in open_positions])

    positions = []
    for h, total_qty, avg_cost in open_positions:
        current = prices.get(h["ticker"])
        unrealised = (current - avg_cost) * total_qty if current else None
        positions.append({
            "ticker": h["ticker"],
            "exchange": h["exchange"],
            "quantity": total_qty,
            "avg_cost": avg_cost,
            "current_price": current,
            "unrealised_pnl": unrealised,
        })
    return positions


def get_stock_returns(telegram_id: str, ticker: str) -> Optional[dict]:
    """
    Returns simple and time-weighted returns for *ticker*.

    SELL lots store cost_basis (avg buy cost) so we can reconstruct
    full history even after FIFO matching deletes consumed buy lots.
    """
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            return None
        holding = q.get_holding(conn, user_id, ticker)
        if holding is None:
            return None
        lots = q.get_lots(conn, holding["id"])

    current   = get_current_price(ticker)
    buy_lots  = [l for l in lots if l["action"] == "BUY"]
    sell_lots = [l for l in lots if l["action"] == "SELL"]

    # Total invested = remaining open buys + cost basis of all sells
    open_invested = sum(l["quantity"] * l["price"] for l in buy_lots)
    sold_invested = sum(l["quantity"] * (l["cost_basis"] or 0) for l in sell_lots)
    total_invested = open_invested + sold_invested

    # Realized P&L from SELL lots (cost_basis populated since this fix)
    realized = sum(
        l["quantity"] * (l["price"] - l["cost_basis"])
        for l in sell_lots if l["cost_basis"] is not None
    )

    # Unrealized P&L on open position
    open_qty  = sum(l["quantity"] for l in buy_lots)
    open_cost = open_invested
    unrealized = (current - open_cost / open_qty) * open_qty if (current and open_qty > 0) else None

    # Simple total return
    total_pnl        = realized + (unrealized or 0.0)
    total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else None

    # Time-weighted return — chain-link each lot's individual return
    # Sells: (sell_price / avg_cost) - 1 per lot
    # Open buys: (current / buy_price) - 1 per lot
    twr_product = 1.0
    has_twr     = False
    for lot in sell_lots:
        if lot["cost_basis"] and lot["cost_basis"] > 0:
            twr_product *= lot["price"] / lot["cost_basis"]
            has_twr = True
    for lot in buy_lots:
        if current and lot["price"] > 0:
            twr_product *= current / lot["price"]
            has_twr = True
    twr_pct = (twr_product - 1) * 100 if has_twr else None

    return {
        "total_invested":   total_invested,
        "realized_pnl":     realized,
        "unrealized_pnl":   unrealized,
        "open_qty":         open_qty,
        "total_return_pct": total_return_pct,
        "twr_pct":          twr_pct,
    }


def get_transaction_history(telegram_id: str, ticker: str) -> list[dict]:
    """Return all lots (BUY and SELL) for *ticker*, oldest first."""
    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            return []
        holding = q.get_holding(conn, user_id, ticker)
        if holding is None:
            return []
        lots = q.get_lots(conn, holding["id"])
        return [
            {
                "action": lot["action"],
                "quantity": lot["quantity"],
                "price": lot["price"],
                "transacted_at": lot["transacted_at"],
                "notes": lot["notes"],
            }
            for lot in lots
        ]
