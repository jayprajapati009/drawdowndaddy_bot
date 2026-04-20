"""
Database connection management and schema initialisation.

Uses raw sqlite3 so the schema is transparent and easy to migrate to
PostgreSQL by swapping this module for a psycopg2-backed equivalent.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from stock_bot.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Resolve the file path from the sqlite:/// URL (handles both relative and absolute)
_DB_PATH: str = DATABASE_URL.removeprefix("sqlite:///")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT    UNIQUE NOT NULL,
    username    TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    ticker      TEXT    NOT NULL,
    exchange    TEXT    NOT NULL,
    added_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    added_price REAL    NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS watchlist_checkpoints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id        INTEGER NOT NULL REFERENCES watchlist(id),
    label               TEXT    NOT NULL,
    price_at_checkpoint REAL    NOT NULL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_configs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id   INTEGER NOT NULL REFERENCES watchlist(id),
    indicator      TEXT    NOT NULL,
    threshold_pct  REAL    NOT NULL,
    is_active      BOOLEAN DEFAULT TRUE,
    UNIQUE(watchlist_id, indicator)
);

CREATE TABLE IF NOT EXISTS alert_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_config_id  INTEGER NOT NULL REFERENCES alert_configs(id),
    triggered_price  REAL    NOT NULL,
    indicator_value  REAL    NOT NULL,
    triggered_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS holdings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    ticker    TEXT    NOT NULL,
    exchange  TEXT    NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS lots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id    INTEGER NOT NULL REFERENCES holdings(id),
    action        TEXT    NOT NULL CHECK(action IN ('BUY', 'SELL')),
    quantity      REAL    NOT NULL,
    price         REAL    NOT NULL,
    transacted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes         TEXT
);
"""


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call multiple times."""
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info("Database initialised at %s", _DB_PATH)


@contextmanager
def get_connection():
    """Yield a sqlite3 connection with row_factory and foreign keys enabled."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
