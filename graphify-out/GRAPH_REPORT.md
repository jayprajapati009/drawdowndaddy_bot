# Graph Report - /home/jp/jay/telegram_bot  (2026-07-16)

## Corpus Check
- 26 files · ~27,988 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 303 nodes · 492 edges · 51 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 192 edges (avg confidence: 0.78)
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
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 27 edges
2. `get_account_id()` - 21 edges
3. `get_user_id()` - 16 edges
4. `cmd_stock_details()` - 15 edges
5. `sell()` - 13 edges
6. `add_stock()` - 12 edges
7. `get_current_price()` - 12 edges
8. `get_watchlist_with_prices()` - 11 edges
9. `get_positions()` - 11 edges
10. `set_checkpoint()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `init_db()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/main.py → /home/jp/jay/telegram_bot/stock_bot/database/db.py
- `main()` --calls--> `backfill_default_ema_alerts()`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/main.py → /home/jp/jay/telegram_bot/stock_bot/services/alert_service.py
- `Maps Telegram commands to their handler functions.` --uses--> `Features`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/bot/router.py → /home/jp/jay/telegram_bot/stock_bot/bot_config.py
- `Build the active command map based on enabled features.` --uses--> `Features`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/bot/router.py → /home/jp/jay/telegram_bot/stock_bot/bot_config.py
- `Proxy for Message that buffers reply_text calls instead of sending them.` --uses--> `Features`  [INFERRED]
  /home/jp/jay/telegram_bot/stock_bot/bot/router.py → /home/jp/jay/telegram_bot/stock_bot/bot_config.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (42): cmd_remove_alert(), cmd_set_alert(), cmd_view_alerts(), Telegram command handlers for alert configuration., Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT     Example: /set_alert RELIANC, Usage: /remove_alert TICKER INDICATOR, Usage: /view_alerts TICKER, _check_one_price_alert() (+34 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (33): cmd_help(), cmd_start(), /start and /help handlers., Register the user and show a welcome message., get_account_id(), cmd_buy(), cmd_sell(), cmd_transaction_history() (+25 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (20): BotConfig, Features, load(), Loads and validates a per-bot JSON config file.  Secret values (token, chat ID), Replace ${VAR_NAME} with the corresponding environment variable., _resolve_env(), Settings, _latest_changelog() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (29): _check_one_ema_alert(), Main entry point called by the scheduler.     *chat_id* is the Telegram chat tha, run_alert_check(), cmd_view_all_price_alerts(), clear_cache(), _fetch_weekly(), get_current_price(), get_ema() (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (28): backfill_default_ema_alerts(), ensure_default_ema_alerts(), ensure_watchlist_defaults(), Alert checking and notification dispatch.  Called by APScheduler on a configurab, Seed the default EMA alert configs for one watchlist row.     Returns the indica, Make sure *ticker* has a watchlist row (alerts are anchored to it) and     the d, One-shot seeding at startup: give every existing watchlist stock and every     p, Exception (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (21): _all_log_files(), _compress_old_files(), configure(), _delete_by_age(), _directory_size(), _enforce_size_limit(), _log_directory_stats(), Smart log file manager.  Rotation:  daily at midnight via TimedRotatingFileHandl (+13 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (18): cmd_search(), cmd_set_date(), _confirm_keyboard(), _date_keyboard(), _do_watch(), handle_date_reply(), handle_search_callback(), _parse_date() (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (17): fmt_pct(), Shared utilities for all handlers., Format a percentage value for display, e.g. '+12.34%' or 'N/A'., Decorator: ensure the shared account exists in the DB before running the handler, require_registered(), get_all_emas(), Return every configured EMA value for *ticker* in one call., cmd_stock_details() (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (13): cmd_remove_price_alert(), cmd_set_price_alert(), cmd_view_price_alerts(), handle_price_alert_callback(), Handlers for price-level alerts (/palert, /unpalert, /palerts)., Usage: /palerts TICKER, Handles inline button responses to price alert notifications.     callback_data:, Usage: /palert TICKER PRICE     Automatically sets direction: ABOVE if target > (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.32
Nodes (6): _connect(), init_db(), _migrate(), Database connection management and schema initialisation.  Uses raw sqlite3 so t, Create all tables if they don't exist. Safe to call multiple times., Apply any schema changes that new code requires on existing DBs.

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (1): Central configuration for the stock alert bot. All secrets come from environment

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): Keep the handler's default YYYY-MM-DD suffix as-is.

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Return True if at least one tracked market is currently open.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Wrapper so APScheduler can call the async alert check.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Add *ticker* to the user's watchlist at the current market price.     Returns a

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Remove *ticker* from the user's watchlist. Raises WatchlistError if not found.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the full watchlist with live prices and return percentages.     Each entr

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Mark the current price of *ticker* as a named checkpoint.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Log a BUY lot. Returns lot details.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Log a SELL using FIFO lot matching.     Returns realised P&L and a breakdown of

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return all current open positions with quantity, average cost, current     price

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return all lots (BUY and SELL) for *ticker*, oldest first.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Call at the start of each scheduler tick to flush stale data.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Fetch the most recent closing price for *ticker*.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the most recent value of *indicator* (e.g. 'EMA_10W') for *ticker*.     R

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return a dict of all configured EMA values for *ticker*.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Main entry point called by the scheduler.     *chat_id* is the Telegram chat tha

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Attach all command handlers to the Application instance.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Format a percentage value for display, e.g. '+12.34%' or 'N/A'.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Decorator: ensure the calling user exists in the DB before running the handler.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Register the user and show a welcome message.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT     Example: /set_alert RELIANC

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Usage: /remove_alert TICKER INDICATOR

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Usage: /view_alerts TICKER

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Usage: /buy TICKER EXCHANGE QUANTITY PRICE [notes]

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Usage: /sell TICKER QUANTITY PRICE [notes]

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Usage: /transaction_history TICKER

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Usage: /add_watchlist TICKER EXCHANGE

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Usage: /remove_watchlist TICKER

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Usage: /view_watchlist

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Usage: /set_checkpoint TICKER LABEL

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Usage: /weekly_report

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Usage: /stock_details TICKER

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Create all tables if they don't exist. Safe to call multiple times.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Yield a sqlite3 connection with row_factory and foreign keys enabled.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Return all BUY lots ordered oldest-first (for FIFO sell matching).

## Knowledge Gaps
- **121 isolated node(s):** `Loads and validates a per-bot JSON config file.  Secret values (token, chat ID)`, `Replace ${VAR_NAME} with the corresponding environment variable.`, `Central configuration for the stock alert bot. All secrets come from environment`, `Smart log file manager.  Rotation:  daily at midnight via TimedRotatingFileHandl`, `Set the log directory and file before setup_logging() is called.` (+116 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 10`** (2 nodes): `Central configuration for the stock alert bot. All secrets come from environment`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `Keep the handler's default YYYY-MM-DD suffix as-is.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Return True if at least one tracked market is currently open.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Wrapper so APScheduler can call the async alert check.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Add *ticker* to the user's watchlist at the current market price.     Returns a`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Remove *ticker* from the user's watchlist. Raises WatchlistError if not found.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the full watchlist with live prices and return percentages.     Each entr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Mark the current price of *ticker* as a named checkpoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Log a BUY lot. Returns lot details.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Log a SELL using FIFO lot matching.     Returns realised P&L and a breakdown of`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return all current open positions with quantity, average cost, current     price`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return all lots (BUY and SELL) for *ticker*, oldest first.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Call at the start of each scheduler tick to flush stale data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Fetch the most recent closing price for *ticker*.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the most recent value of *indicator* (e.g. 'EMA_10W') for *ticker*.     R`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return a dict of all configured EMA values for *ticker*.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Main entry point called by the scheduler.     *chat_id* is the Telegram chat tha`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Attach all command handlers to the Application instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Format a percentage value for display, e.g. '+12.34%' or 'N/A'.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Decorator: ensure the calling user exists in the DB before running the handler.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Register the user and show a welcome message.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Usage: /set_alert TICKER INDICATOR THRESHOLD_PCT     Example: /set_alert RELIANC`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Usage: /remove_alert TICKER INDICATOR`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Usage: /view_alerts TICKER`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Usage: /buy TICKER EXCHANGE QUANTITY PRICE [notes]`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Usage: /sell TICKER QUANTITY PRICE [notes]`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Usage: /transaction_history TICKER`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Usage: /add_watchlist TICKER EXCHANGE`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Usage: /remove_watchlist TICKER`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Usage: /view_watchlist`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Usage: /set_checkpoint TICKER LABEL`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Usage: /weekly_report`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Usage: /stock_details TICKER`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Create all tables if they don't exist. Safe to call multiple times.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Yield a sqlite3 connection with row_factory and foreign keys enabled.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Return all BUY lots ordered oldest-first (for FIFO sell matching).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Why does `_SilentMessage` connect `Community 2` to `Community 1`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `get_account_id()` connect `Community 1` to `Community 0`, `Community 8`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `get_connection()` (e.g. with `add_stock()` and `remove_stock()`) actually correct?**
  _`get_connection()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `get_account_id()` (e.g. with `cmd_start()` and `cmd_set_alert()`) actually correct?**
  _`get_account_id()` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `get_user_id()` (e.g. with `add_stock()` and `remove_stock()`) actually correct?**
  _`get_user_id()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `cmd_stock_details()` (e.g. with `.reply_text()` and `get_account_id()`) actually correct?**
  _`cmd_stock_details()` has 9 INFERRED edges - model-reasoned connections that need verification._