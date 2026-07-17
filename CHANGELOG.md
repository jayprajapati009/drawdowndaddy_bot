# Changelog

Most recent changes appear first.

---

## 2026-07-16 — Automatic weekly EMA alerts

- **Default EMA triggers everywhere** — every stock you /watch, /buy, or /sell now automatically gets alerts on the 10, 20, 30, and 40-week EMAs (fires when price comes within 2% of the EMA)
- **Existing stocks covered too** — on startup the bot backfills the default alerts for everything already on your watchlist and in your portfolio
- **New indicators** — EMA_20W and EMA_30W join EMA_10W and EMA_40W; /stock and /alert support all four
- **Your customisations are safe** — thresholds you changed with /alert and alerts you removed with /unalert are never overwritten by the defaults

---

## 2026-05-29 — Transactions command

- **/transactions** — see your last 10 trades across all stocks in one place; use `/transactions 20` for more or `/transactions all` for everything
- **Table format** — transactions display as a clean fixed-width table with columns for date, ticker, type, qty, and price

---

## 2026-05-14 — Price alert actions + restart message

- **Price alerts now have buttons** — when an alert fires, tap Keep watching or Remove alert directly in the message instead of typing commands
- **Restart message fixed** — bot now posts a clean, readable update to the group every time it restarts
- **Prompt log and changelog** — all changes are now tracked in CHANGELOG.md and prompt_log.md on git

---

## 2026-05-11 — Transaction history + bulk import fixes

- **Full buy history preserved** — bought lots no longer disappear after selling; /history now shows every buy, with "(sold)" tag on consumed ones
- **P&L on each sell line** — /history shows realized profit/loss and % next to every sell entry
- **Bulk import fixed** — pasting 35+ commands at once now works reliably; errors are shown per-line in the summary instead of crashing silently
- **Trade dates on /buy and /sell** — add a date to log historical transactions: `/buy AAPL NASDAQ 10 185 15/01/2025`

---

## 2026-05-10 — Search, RSI, returns, TradingView

- **/search** — find any stock by company name instead of needing the ticker; handles typos; tap buttons to select, confirm exchange and date
- **RSI(14)** added to /stock technical indicators with overbought/oversold label
- **Time-weighted return** shown alongside simple return in /stock
- **TradingView chart link** shown at the bottom of /stock
- **/date command** — use `/date DD/MM/YYYY` to enter a past date after /search picks a stock (works in groups with privacy mode)
- **Past date for /mark** — `/mark TICKER LABEL DD/MM/YYYY` saves the historical price as the checkpoint

---

## 2026-04-30 — Multi-bot config system (v2)

- **Two independent bots** from one codebase — each bot has its own `configs/bot-N.json` with its own token, database, logs and feature flags
- **Feature flags** — turn watchlist, alerts, price alerts, holdings or reports on/off per bot
- **services.sh** — deploy, restart, remove and tail logs for all bots with one command
- **Bot 2 (friends group)** — watchlist + alerts only, holdings disabled

---

## 2026-04-28 — Price alerts + search improvements

- **/palert TICKER PRICE** — get notified when a stock crosses your target price; direction auto-detected
- **/palertsall** — see all active price alerts across every ticker
- **/palerts TICKER** — alerts for one stock
- **/stock** now shows added date, price alerts with % distance, and TradingView link

---

## 2026-04-22 — Core bot (v1.0.0)

- **Watchlist** — /watch /unwatch /watchlist /mark with historical entry dates
- **EMA alerts** — alert when price is within X% of 10-week or 40-week EMA
- **Holdings** — /buy /sell (FIFO lot matching) /holdings /history
- **Reports** — /report weekly summary, /stock deep-dive
- **/search** — find tickers by company name
- **Shared group account** — all members in the group share one watchlist and portfolio
- **Smart logs** — daily rotation, gzip compression, 30-day retention
- **Deployed on DigitalOcean** via systemd
