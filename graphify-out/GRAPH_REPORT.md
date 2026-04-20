# Graph Report - /home/jp/jay/telegram_bot  (2026-04-20)

## Corpus Check
- 20 files · ~5,299 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 140 nodes · 212 edges · 16 communities detected
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 81 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 17 edges
2. `get_user_id()` - 12 edges
3. `sell()` - 11 edges
4. `get_watchlist_with_prices()` - 10 edges
5. `get_positions()` - 10 edges
6. `add_stock()` - 9 edges
7. `set_checkpoint()` - 9 edges
8. `buy()` - 8 edges
9. `get_current_price()` - 8 edges
10. `remove_stock()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `_scheduled_alert_job()` --calls--> `run_alert_check()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/main.py → /home/jp/jay/telegram_bot/stock_bot/services/alert_service.py
- `add_stock()` --calls--> `get_current_price()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/services/watchlist_service.py → /home/jp/jay/telegram_bot/stock_bot/services/price_fetcher.py
- `add_stock()` --calls--> `get_connection()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/services/watchlist_service.py → /home/jp/jay/telegram_bot/stock_bot/database/db.py
- `add_stock()` --calls--> `get_watchlist_item()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/services/watchlist_service.py → /home/jp/jay/telegram_bot/stock_bot/database/queries.py
- `add_stock()` --calls--> `add_to_watchlist()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/services/watchlist_service.py → /home/jp/jay/telegram_bot/stock_bot/database/queries.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.1
Nodes (22): cmd_buy(), cmd_sell(), cmd_transaction_history(), Telegram command handlers for holdings and transaction management., Usage: /transaction_history TICKER, Usage: /buy TICKER EXCHANGE QUANTITY PRICE [notes], Usage: /sell TICKER QUANTITY PRICE [notes], buy() (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (19): Exception, HoldingsError, add_checkpoint(), get_user_id(), cmd_add_watchlist(), cmd_remove_watchlist(), cmd_set_checkpoint(), Telegram command handlers for watchlist operations. (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (20): fmt_pct(), Format a percentage value for display, e.g. '+12.34%' or 'N/A'., cmd_view_holdings(), Usage: /view_holdings, get_positions(), Return all current open positions with quantity, average cost, current     price, get_current_price(), Fetch the most recent closing price for *ticker*. (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.15
Nodes (14): _check_one_alert(), Alert checking and notification dispatch.  Called by APScheduler on a configurab, Main entry point called by the scheduler.     *chat_id* is the Telegram chat tha, run_alert_check(), add_to_watchlist(), get_all_active_alert_configs(), get_all_watchlist_items(), get_recent_alert_log() (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (10): _connect(), get_connection(), init_db(), Database connection management and schema initialisation.  Uses raw sqlite3 so t, Create all tables if they don't exist. Safe to call multiple times., Yield a sqlite3 connection with row_factory and foreign keys enabled., main(), Maps Telegram commands to their handler functions. (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.2
Nodes (11): cmd_remove_alert(), cmd_set_alert(), cmd_view_alerts(), Telegram command handlers for alert configuration., Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT     Example: /set_alert RELIANC, Usage: /remove_alert TICKER INDICATOR, Usage: /view_alerts TICKER, deactivate_alert() (+3 more)

### Community 6 - "Community 6"
Cohesion: 0.24
Nodes (9): clear_cache(), _fetch_weekly_closes(), get_all_emas(), get_ema(), yfinance wrapper with EMA calculation.  All data is fetched as weekly OHLCV; clo, Call at the start of each scheduler tick to flush stale data., Return the most recent value of *indicator* (e.g. 'EMA_10W') for *ticker*.     R, Return a dict of all configured EMA values for *ticker*. (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.29
Nodes (5): cmd_start(), /start and /help handlers., Register the user and show a welcome message., Insert user if not exists; return the user.id., upsert_user()

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (5): _any_market_open(), Entry point.  Starts the Telegram bot (via Application.run_polling) and wires up, Return True if at least one tracked market is currently open., Wrapper so APScheduler can call the async alert check., _scheduled_alert_job()

### Community 9 - "Community 9"
Cohesion: 0.5
Nodes (3): Shared utilities for all handlers., Decorator: ensure the calling user exists in the DB before running the handler., require_registered()

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (1): Central configuration for the stock alert bot. All secrets come from environment

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (0): 

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **55 isolated node(s):** `Entry point.  Starts the Telegram bot (via Application.run_polling) and wires up`, `Return True if at least one tracked market is currently open.`, `Wrapper so APScheduler can call the async alert check.`, `Central configuration for the stock alert bot. All secrets come from environment`, `Watchlist business logic.` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 10`** (2 nodes): `Central configuration for the stock alert bot. All secrets come from environment`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.367) - this node is a cross-community bridge._
- **Why does `run_alert_check()` connect `Community 3` to `Community 8`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `get_positions()` connect `Community 2` to `Community 0`, `Community 1`, `Community 4`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `get_connection()` (e.g. with `add_stock()` and `remove_stock()`) actually correct?**
  _`get_connection()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `get_user_id()` (e.g. with `add_stock()` and `remove_stock()`) actually correct?**
  _`get_user_id()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `sell()` (e.g. with `get_connection()` and `get_user_id()`) actually correct?**
  _`sell()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `get_watchlist_with_prices()` (e.g. with `get_connection()` and `get_user_id()`) actually correct?**
  _`get_watchlist_with_prices()` has 8 INFERRED edges - model-reasoned connections that need verification._