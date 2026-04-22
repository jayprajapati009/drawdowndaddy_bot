"""
All SQL operations as pure functions.
Every function accepts a connection as its first argument so callers control
transaction boundaries.
"""

import sqlite3
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def upsert_user(conn: sqlite3.Connection, telegram_id: str, username: Optional[str]) -> int:
    """Insert user if not exists; return the user.id."""
    conn.execute(
        "INSERT INTO users(telegram_id, username) VALUES(?,?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username",
        (telegram_id, username),
    )
    row = conn.execute(
        "SELECT id FROM users WHERE telegram_id=?", (telegram_id,)
    ).fetchone()
    return row["id"]


def get_user_id(conn: sqlite3.Connection, telegram_id: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM users WHERE telegram_id=?", (telegram_id,)
    ).fetchone()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def add_to_watchlist(
    conn: sqlite3.Connection,
    user_id: int,
    ticker: str,
    exchange: str,
    added_price: float,
) -> int:
    """Return new watchlist.id or raise if duplicate."""
    cur = conn.execute(
        "INSERT INTO watchlist(user_id, ticker, exchange, added_price) VALUES(?,?,?,?)",
        (user_id, ticker.upper(), exchange.upper(), added_price),
    )
    return cur.lastrowid


def remove_from_watchlist(conn: sqlite3.Connection, user_id: int, ticker: str) -> bool:
    """Return True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM watchlist WHERE user_id=? AND ticker=?",
        (user_id, ticker.upper()),
    )
    return cur.rowcount > 0


def get_watchlist(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at",
        (user_id,),
    ).fetchall()


def get_watchlist_item(
    conn: sqlite3.Connection, user_id: int, ticker: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM watchlist WHERE user_id=? AND ticker=?",
        (user_id, ticker.upper()),
    ).fetchone()


def get_all_watchlist_items(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return every watchlist row across all users (used by alert scheduler)."""
    return conn.execute("SELECT * FROM watchlist").fetchall()


# ---------------------------------------------------------------------------
# Watchlist checkpoints
# ---------------------------------------------------------------------------

def add_checkpoint(
    conn: sqlite3.Connection,
    watchlist_id: int,
    label: str,
    price: float,
) -> int:
    cur = conn.execute(
        "INSERT INTO watchlist_checkpoints(watchlist_id, label, price_at_checkpoint) "
        "VALUES(?,?,?)",
        (watchlist_id, label, price),
    )
    return cur.lastrowid


def get_checkpoints(
    conn: sqlite3.Connection, watchlist_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM watchlist_checkpoints WHERE watchlist_id=? ORDER BY created_at",
        (watchlist_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Alert configs
# ---------------------------------------------------------------------------

def upsert_alert_config(
    conn: sqlite3.Connection,
    watchlist_id: int,
    indicator: str,
    threshold_pct: float,
) -> int:
    conn.execute(
        "INSERT INTO alert_configs(watchlist_id, indicator, threshold_pct) VALUES(?,?,?) "
        "ON CONFLICT(watchlist_id, indicator) "
        "DO UPDATE SET threshold_pct=excluded.threshold_pct, is_active=TRUE",
        (watchlist_id, indicator.upper(), threshold_pct),
    )
    row = conn.execute(
        "SELECT id FROM alert_configs WHERE watchlist_id=? AND indicator=?",
        (watchlist_id, indicator.upper()),
    ).fetchone()
    return row["id"]


def deactivate_alert(
    conn: sqlite3.Connection, watchlist_id: int, indicator: str
) -> bool:
    cur = conn.execute(
        "UPDATE alert_configs SET is_active=FALSE "
        "WHERE watchlist_id=? AND indicator=?",
        (watchlist_id, indicator.upper()),
    )
    return cur.rowcount > 0


def get_alert_configs(
    conn: sqlite3.Connection, watchlist_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM alert_configs WHERE watchlist_id=? AND is_active=TRUE",
        (watchlist_id,),
    ).fetchall()


def get_all_active_alert_configs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT ac.*, w.ticker, w.exchange, w.user_id "
        "FROM alert_configs ac "
        "JOIN watchlist w ON w.id = ac.watchlist_id "
        "WHERE ac.is_active=TRUE"
    ).fetchall()


# ---------------------------------------------------------------------------
# Alert logs
# ---------------------------------------------------------------------------

def log_alert(
    conn: sqlite3.Connection,
    alert_config_id: int,
    triggered_price: float,
    indicator_value: float,
) -> None:
    conn.execute(
        "INSERT INTO alert_logs(alert_config_id, triggered_price, indicator_value) "
        "VALUES(?,?,?)",
        (alert_config_id, triggered_price, indicator_value),
    )


def get_recent_alert_log(
    conn: sqlite3.Connection,
    alert_config_id: int,
    since: datetime,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM alert_logs "
        "WHERE alert_config_id=? AND triggered_at >= ? "
        "ORDER BY triggered_at DESC LIMIT 1",
        (alert_config_id, since),
    ).fetchone()


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

def get_or_create_holding(
    conn: sqlite3.Connection, user_id: int, ticker: str, exchange: str
) -> int:
    conn.execute(
        "INSERT INTO holdings(user_id, ticker, exchange) VALUES(?,?,?) "
        "ON CONFLICT(user_id, ticker) DO NOTHING",
        (user_id, ticker.upper(), exchange.upper()),
    )
    row = conn.execute(
        "SELECT id FROM holdings WHERE user_id=? AND ticker=?",
        (user_id, ticker.upper()),
    ).fetchone()
    return row["id"]


def get_holdings(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM holdings WHERE user_id=? ORDER BY ticker",
        (user_id,),
    ).fetchall()


def get_holding(
    conn: sqlite3.Connection, user_id: int, ticker: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM holdings WHERE user_id=? AND ticker=?",
        (user_id, ticker.upper()),
    ).fetchone()


# ---------------------------------------------------------------------------
# Lots
# ---------------------------------------------------------------------------

def add_lot(
    conn: sqlite3.Connection,
    holding_id: int,
    action: str,
    quantity: float,
    price: float,
    notes: Optional[str] = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO lots(holding_id, action, quantity, price, notes) VALUES(?,?,?,?,?)",
        (holding_id, action.upper(), quantity, price, notes),
    )
    return cur.lastrowid


def get_open_buy_lots(
    conn: sqlite3.Connection, holding_id: int
) -> list[sqlite3.Row]:
    """Return all BUY lots ordered oldest-first (for FIFO sell matching)."""
    return conn.execute(
        "SELECT * FROM lots WHERE holding_id=? AND action='BUY' ORDER BY transacted_at",
        (holding_id,),
    ).fetchall()


def get_lots(conn: sqlite3.Connection, holding_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM lots WHERE holding_id=? ORDER BY transacted_at",
        (holding_id,),
    ).fetchall()


def update_lot_quantity(
    conn: sqlite3.Connection, lot_id: int, new_quantity: float
) -> None:
    conn.execute("UPDATE lots SET quantity=? WHERE id=?", (new_quantity, lot_id))


def delete_lot(conn: sqlite3.Connection, lot_id: int) -> None:
    conn.execute("DELETE FROM lots WHERE id=?", (lot_id,))


# ---------------------------------------------------------------------------
# Price alerts
# ---------------------------------------------------------------------------

def add_price_alert(
    conn: sqlite3.Connection,
    watchlist_id: int,
    target_price: float,
    direction: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO price_alerts(watchlist_id, target_price, direction) VALUES(?,?,?)",
        (watchlist_id, target_price, direction.upper()),
    )
    return cur.lastrowid


def get_price_alerts(
    conn: sqlite3.Connection, watchlist_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM price_alerts WHERE watchlist_id=? AND is_active=TRUE ORDER BY target_price",
        (watchlist_id,),
    ).fetchall()


def get_price_alerts_by_ticker(
    conn: sqlite3.Connection, ticker: str
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT pa.*, w.exchange FROM price_alerts pa "
        "JOIN watchlist w ON w.id = pa.watchlist_id "
        "WHERE w.ticker=? AND pa.is_active=TRUE ORDER BY pa.target_price",
        (ticker.upper(),),
    ).fetchall()


def get_all_active_price_alerts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT pa.*, w.ticker, w.exchange, w.user_id "
        "FROM price_alerts pa "
        "JOIN watchlist w ON w.id = pa.watchlist_id "
        "WHERE pa.is_active=TRUE"
    ).fetchall()


def deactivate_price_alert(conn: sqlite3.Connection, alert_id: int) -> bool:
    cur = conn.execute(
        "UPDATE price_alerts SET is_active=FALSE WHERE id=?", (alert_id,)
    )
    return cur.rowcount > 0


def log_price_alert(
    conn: sqlite3.Connection, price_alert_id: int, triggered_price: float
) -> None:
    conn.execute(
        "INSERT INTO price_alert_logs(price_alert_id, triggered_price) VALUES(?,?)",
        (price_alert_id, triggered_price),
    )


def get_recent_price_alert_log(
    conn: sqlite3.Connection, price_alert_id: int, since: datetime
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM price_alert_logs "
        "WHERE price_alert_id=? AND triggered_at >= ? "
        "ORDER BY triggered_at DESC LIMIT 1",
        (price_alert_id, since),
    ).fetchone()
