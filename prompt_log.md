# Prompt Log

Technical session notes for AI agents resuming this project.
Each entry records what the user asked for and what was changed.

---

## 2026-05-11

### User Requests
- Preserve full buy history in /history (buys disappeared after FIFO matching deleted them)
- Show P&L on each sell line in /history
- Show both simple return and time-weighted return in /stock
- Bulk paste of 35+ commands was crashing silently — fix it
- Add trade date support to /buy and /sell
- After every session, save a prompt log (this file) and a user-friendly CHANGELOG.md
- On bot restart, post latest changelog entry to the group
- Clear and re-seed transaction history from Robinhood PDF (accurate dates)

### Changes Made
- `lots` table: added `consumed BOOLEAN DEFAULT FALSE` column (migration auto-runs at startup)
- `queries.py`: `get_open_buy_lots` filters `consumed=FALSE`; new `mark_lot_consumed()`; `add_lot` accepts `consumed` + `transacted_at`
- `holdings_service.py`: `sell()` marks lots consumed instead of deleting; partial lots split into consumed+remaining; `buy()` and `sell()` accept optional `trade_date` (ISO string)
- `holdings_handlers.py`: `/buy` and `/sell` parse optional `DD/MM/YYYY` date from args at position 4 (buy) or 3 (sell); `_extract_date()` helper
- `report_handlers.py`: `_section_history()` shows "(sold)" on consumed buys, P&L+% on sell lines
- `router.py`: bulk import mode — >5 commands pasted at once uses `_SilentUpdate`/`_SilentMessage` proxy to buffer replies, sends one summary; exception catch widened to `Exception` to prevent silent crashes; `raise ApplicationHandlerStop` preserved
- `main.py`: reads `CHANGELOG.md` latest entry on startup, posts to alert_chat_id
- `CHANGELOG.md`: created, user-friendly feature history
- `prompt_log.md`: this file, created

### Known Issues / Notes
- Existing sell lots logged before 2026-05-11 have no `cost_basis` (column was NULL); TWR and realized P&L only accurate for transactions entered after this date — workaround: clear and re-seed from Robinhood PDF
- `lots_consumed` NameError bug: variable renamed from `consumed` → `lot_consumed` but return dict still referenced old name; fixed in commit f5f774e
- Narrow exception catch `(ValueError, RuntimeError, KeyError)` in bulk dispatcher was silently dropping `NameError` and other exceptions — widened to `Exception`
- PSUBNKBEES (Indian ETF) had wrong ticker; corrected to PSUBNKBEES.NS
- Telegram group privacy mode: plain text messages not received by bot; search flow uses inline keyboards + /date command instead

---

## 2026-05-10

### User Requests
- /search: after picking a stock, ask "add to watchlist?" + entry date (not immediately add)
- /stock: add TradingView chart link
- /stock: add RSI(14) indicator
- /stock: show time-weighted returns and realized/unrealized separately
- /stock: show full buy/sell history
- /palerts all → separate command /palertsall
- Fix /palerts TICKER lookup (was broken after shared account migration)
- Support historical date in /mark

### Changes Made
- `price_fetcher.py`: `get_rsi(ticker, period=14)` using Wilder's smoothing on weekly data
- `holdings_service.py`: `get_stock_returns()` returns realized P&L, unrealized P&L, simple return %, TWR %
- `report_handlers.py`: refactored `cmd_stock_details` into section helpers; added `_section_technicals`, `_section_returns`, `_section_history`, `_tradingview_url`
- `search_handlers.py`: full rewrite with inline keyboards (privacy mode compatible); multi-phase state machine (pick → confirm → date); `/date` command for past date entry
- `queries.py`: `get_price_alerts_by_ticker()` to fix alert lookup after shared account migration
- `watchlist_handlers.py`: `cmd_set_checkpoint` accepts optional `DD/MM/YYYY` date
- `watchlist_service.py`: `set_checkpoint()` accepts optional `entry_date`
- `router.py`: `CallbackQueryHandler` for search flow; reply handler for date input

---

## 2026-04-30

### User Requests
- Run two independent bot instances (different groups, different tokens)
- Per-bot config: token, DB, logs, feature flags in JSON
- Tokens/chat IDs stay in .env, configs go on git using ${VAR} placeholders
- services.sh to manage systemd services
- Shared watchlist across all group members (not per-user)

### Changes Made
- `bot_config.py`: new BotConfig dataclass loading JSON with env var substitution
- `configs/bot-1.json`, `configs/bot-2.json`: committed (no secrets, use ${VAR})
- `configs/schema.json`, `*.example.json`: reference files
- `config.py`: stripped per-bot values (token, DB, intervals); now only app-wide constants
- `db.py`: `configure(path)` sets DB path at startup
- `log_manager.py`: `configure(log_dir)` sets log directory at startup
- `alert_service.py`: `cooldown_hours` passed as parameter instead of global constant
- `router.py`: `register_handlers(app, features)` takes Features object, conditionally registers handlers
- `main.py`: `--config PATH` CLI arg; reads BotConfig; wires everything
- `services.sh`: deploy/remove/status/restart/logs commands for systemd

---

## Architecture Notes (for AI agents)

- **DB**: SQLite with WAL mode. Tables: users, watchlist, watchlist_checkpoints, alert_configs, alert_logs, holdings, lots, price_alerts, price_alert_logs. All per-user data uses `telegram_id = "shared"` (shared account mode).
- **Price fetching**: yfinance, one ticker at a time, 3 retries. Parallel fetching via ThreadPoolExecutor for /holdings and /report. Per-tick cache cleared by alert scheduler.
- **FIFO selling**: buy lots marked `consumed=TRUE` instead of deleted, preserving full history. Partial sells split the lot.
- **Multi-command paste**: `_dispatch_multi_command` in router.py runs at group=-2, detects multiple /cmd lines, bulk mode for >5 commands uses proxy objects to buffer replies.
- **Inline keyboards**: search flow uses CallbackQueryHandler (works with group privacy mode). /date command for typed date entry.
- **Two bots**: bot-1 (Jay + 1 friend, all features), bot-2 (friends group, holdings=false). Each has its own systemd service, DB, and log directory.
- **Deployment**: DigitalOcean droplet, systemd, `services.sh deploy` to create/update services.
