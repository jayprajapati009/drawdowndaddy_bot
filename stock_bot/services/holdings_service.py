"""
Holdings and lot management.

Cost basis and P&L are always computed from raw lot data at query time.
Sells consume the oldest open BUY lots first (FIFO).
"""

import logging
from typing import Optional

from stock_bot.database.db import get_connection
from stock_bot.database import queries as q
from stock_bot.services.price_fetcher import get_current_price

logger = logging.getLogger(__name__)


class HoldingsError(Exception):
    pass


def buy(
    telegram_id: str,
    ticker: str,
    exchange: str,
    quantity: float,
    price: float,
    notes: Optional[str] = None,
) -> dict:
    """Log a BUY lot. Returns lot details."""
    if quantity <= 0 or price <= 0:
        raise HoldingsError("Quantity and price must be positive.")

    with get_connection() as conn:
        user_id = q.get_user_id(conn, telegram_id)
        if user_id is None:
            raise HoldingsError("User not registered. Send /start first.")
        holding_id = q.get_or_create_holding(conn, user_id, ticker, exchange)
        lot_id = q.add_lot(conn, holding_id, "BUY", quantity, price, notes)

    logger.info("BUY %s × %s @ %s for user %s", quantity, ticker, price, telegram_id)
    return {"ticker": ticker.upper(), "action": "BUY", "quantity": quantity, "price": price}


def sell(
    telegram_id: str,
    ticker: str,
    quantity: float,
    price: float,
    notes: Optional[str] = None,
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
        remaining = quantity
        realised_pnl = 0.0
        consumed = []

        for lot in buy_lots:
            if remaining <= 0:
                break
            lot_qty = lot["quantity"]
            consumed_qty = min(lot_qty, remaining)
            realised_pnl += consumed_qty * (price - lot["price"])
            consumed.append({"lot_id": lot["id"], "qty": consumed_qty, "cost": lot["price"]})
            remaining -= consumed_qty

            if consumed_qty >= lot_qty:
                q.delete_lot(conn, lot["id"])
            else:
                q.update_lot_quantity(conn, lot["id"], lot_qty - consumed_qty)

        # Record the SELL lot for history
        q.add_lot(conn, holding["id"], "SELL", quantity, price, notes)

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
        positions = []
        for h in holdings:
            buy_lots = q.get_open_buy_lots(conn, h["id"])
            total_qty = sum(lot["quantity"] for lot in buy_lots)
            if total_qty == 0:
                continue  # fully sold out
            avg_cost = sum(lot["quantity"] * lot["price"] for lot in buy_lots) / total_qty
            current = get_current_price(h["ticker"])
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
