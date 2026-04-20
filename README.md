# Stock Alert & Portfolio Telegram Bot

A Telegram bot for two people to track a shared stock watchlist and personal holdings.  
Runs continuously on a DigitalOcean droplet (or any Linux server).

---

## What it does

- **Watchlist** — track any stock (Indian or US), record your entry price, and set named checkpoints to measure returns from specific dates
- **Alerts** — get notified when a stock's price comes within X% of its 10-week or 40-week EMA
- **Holdings** — log every buy and sell as a separate lot; sell matching uses FIFO (oldest lots first); see unrealised P&L at any time
- **Reports** — weekly summary of watchlist returns and holdings P&L; per-stock deep-dive

Each person in the group has their own independent watchlist and holdings.

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo>
cd telegram_bot
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALERT_CHAT_ID=-1009876543210
DATABASE_URL=sqlite:///stock_bot.db
```

| Variable | How to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Message `@BotFather` on Telegram → `/newbot` |
| `ALERT_CHAT_ID` | Add the bot to your group, visit `api.telegram.org/bot<TOKEN>/getUpdates`, send any message in the group, find `"chat":{"id":...}` |
| `DATABASE_URL` | Leave as default for SQLite; set a `postgresql://...` URL for Postgres |

### 3. Run the bot

```bash
python3 -m stock_bot.main
```

The SQLite database is created automatically on first run.

---

## Running continuously on a server (DigitalOcean)

Create a systemd service so the bot restarts automatically:

```bash
sudo nano /etc/systemd/system/stockbot.service
```

Paste:

```ini
[Unit]
Description=Stock Alert Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/home/jp/jay/telegram_bot
EnvironmentFile=/home/jp/jay/telegram_bot/.env
ExecStart=/usr/bin/python3 -m stock_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable stockbot
sudo systemctl start stockbot
sudo systemctl status stockbot
```

View logs:

```bash
journalctl -u stockbot -f
```

---

## All commands

Send these in your Telegram group (or privately to the bot).

### Getting started

| Command | Description |
|---|---|
| `/start` | Register yourself — **run this first** |
| `/help` | Show all commands with examples |

---

### Watchlist

Track stocks and measure returns from when you added them.

| Command | Example |
|---|---|
| `/add_watchlist TICKER EXCHANGE` | `/add_watchlist RELIANCE.NS NSE` |
| `/remove_watchlist TICKER` | `/remove_watchlist AAPL` |
| `/view_watchlist` | Shows all stocks with live prices and % returns |
| `/set_checkpoint TICKER LABEL` | `/set_checkpoint RELIANCE.NS pre-results` |

**Ticker format:**
- Indian stocks: use Yahoo Finance format — `RELIANCE.NS` (NSE) or `RELIANCE.BO` (BSE)
- US stocks: plain ticker — `AAPL`, `TSLA`, `NVDA`

**Checkpoints** let you mark today's price with a label so you can track returns from that specific date (e.g. before an earnings announcement).

---

### Alerts

Get notified when a stock's price approaches a key moving average.

| Command | Example |
|---|---|
| `/set_alert TICKER INDICATOR THRESHOLD` | `/set_alert RELIANCE.NS EMA_10W 5` |
| `/remove_alert TICKER INDICATOR` | `/remove_alert AAPL EMA_40W` |
| `/view_alerts TICKER` | `/view_alerts RELIANCE.NS` |

**Indicators:**
- `EMA_10W` — 10-week exponential moving average
- `EMA_40W` — 40-week exponential moving average

**Threshold** is a percentage. `/set_alert AAPL EMA_10W 5` fires when AAPL is within 5% of its 10-week EMA.

Alerts fire at most once every 2 hours for the same condition to avoid spam.

---

### Holdings

Log every transaction as a separate lot. Cost basis and P&L are always calculated from raw data.

| Command | Example |
|---|---|
| `/buy TICKER EXCHANGE QTY PRICE [notes]` | `/buy RELIANCE.NS NSE 10 2450` |
| `/sell TICKER QTY PRICE [notes]` | `/sell RELIANCE.NS 5 2600` |
| `/view_holdings` | All open positions with unrealised P&L |
| `/transaction_history TICKER` | `/transaction_history AAPL` |

**Sell logic:** FIFO — the oldest buy lots are consumed first. If you sell more than one lot's worth, it automatically chains across multiple lots and shows you the total realised P&L.

---

### Reports

| Command | Description |
|---|---|
| `/weekly_report` | Watchlist returns + holdings P&L for all your positions |
| `/stock_details TICKER` | Full breakdown for one stock: live price, EMA values, watchlist return, holding P&L |

---

## Supported exchanges

| Exchange | Country | Ticker example |
|---|---|---|
| NSE | India | `RELIANCE.NS` |
| BSE | India | `RELIANCE.BO` |
| NASDAQ | USA | `AAPL` |
| NYSE | USA | `JPM` |

---

## How the indicators are calculated

### Exponential Moving Average (EMA)

An EMA gives more weight to recent prices than older ones — unlike a simple moving average which weights every day equally. This makes it more responsive to recent price moves.

**Formula:**

```
EMA_today = Price_today × k + EMA_yesterday × (1 − k)

where:  k = 2 / (span + 1)
```

For a 10-week EMA: `k = 2 / (10 + 1) = 0.1818`  
For a 40-week EMA: `k = 2 / (40 + 1) = 0.0476`

A smaller `k` means the 40W EMA reacts slowly — it's a long-term trend line. The 10W EMA is more sensitive.

**How the bot calculates it:**

```python
df["Close"].ewm(span=10, adjust=False).mean()  # 10-week EMA
df["Close"].ewm(span=40, adjust=False).mean()  # 40-week EMA
```

- Fetches 2 years of **weekly** closing prices via yfinance
- Runs the EMA over that series; the last value is the current EMA
- `adjust=False` means it uses the recursive formula above, not a weighted correction — matches what most charting tools (TradingView, Zerodha) show

**Why weekly candles?**

Weekly EMAs smooth out daily noise. The 10-week EMA (~50-day) and 40-week EMA (~200-day) are the standard long-term trend indicators used by retail investors. Using weekly data means one new candle per week, so the EMA moves gradually.

---

### Alert distance calculation

When checking an alert, the bot computes how far the current price is from the EMA as a percentage of the EMA:

```
distance_pct = |current_price − EMA| / EMA × 100
```

**Example:**  
RELIANCE.NS current price = ₹2,450  
10-week EMA = ₹2,380  

```
distance_pct = |2450 − 2380| / 2380 × 100 = 2.94%
```

If you set `/set_alert RELIANCE.NS EMA_10W 5`, the alert fires because 2.94% < 5%.  
If you set it to 2%, it would not fire (2.94% > 2%).

---

## How lot tracking and FIFO selling works

Every buy is stored as a separate row in the `lots` table. Nothing is ever pre-aggregated. The average cost and P&L are always computed live from raw lots.

### Example: building a position

```
/buy AAPL NASDAQ 10 150.00   → Lot A: 10 shares @ $150
/buy AAPL NASDAQ 5  180.00   → Lot B:  5 shares @ $180
/buy AAPL NASDAQ 8  160.00   → Lot C:  8 shares @ $160
```

At this point `/view_holdings` shows:

```
Total quantity  : 23 shares
Average cost    : (10×150 + 5×180 + 8×160) / 23 = $161.30
```

---

### Example: selling with FIFO

FIFO = First In, First Out. When you sell, the **oldest** lots are consumed first regardless of which lot has the best or worst cost.

```
/sell AAPL 12 200.00
```

The bot works through lots oldest-first:

| Step | Lot | Available | Consumed | Remaining sell qty |
|------|-----|-----------|----------|--------------------|
| 1    | A   | 10 @ $150 | 10       | 2 left to sell     |
| 2    | B   | 5  @ $180 | 2        | 0 — done           |

Realised P&L:

```
(10 × (200 − 150)) + (2 × (200 − 180))
= 500 + 40
= $540 profit
```

Lot B is partially consumed — 3 shares remain at $180.  
Lot C is untouched.

Remaining open position after the sell:

```
Lot B (remainder): 3 shares @ $180
Lot C:             8 shares @ $160

New average cost: (3×180 + 8×160) / 11 = $165.45
```

---

### Example: selling at a loss

```
/sell AAPL 3 140.00
```

Consumes the remaining 3 shares of Lot B (oldest):

```
Realised P&L = 3 × (140 − 180) = −$120 (loss)
```

---

### Why FIFO?

- It is the standard accounting method for retail investors in most countries (including India under SEBI rules)
- It is deterministic — the same sell always produces the same result regardless of when you run the report
- It matches how most brokers (Zerodha, Groww, Fidelity) calculate your realised gains for tax purposes

---

### What happens to sell lots in the database?

Sells are also stored as rows in the `lots` table (with `action = 'SELL'`) for a complete audit trail. The `/transaction_history` command shows every buy and sell in chronological order. The open position calculation only looks at BUY rows that have not been fully consumed.

---

## How alerts are scheduled

- **During market hours** (any market open): checks every 30 minutes
- **Outside market hours**: checks every 60 minutes
- Market hours checked: NSE/BSE 9:15–15:30 IST, NASDAQ/NYSE 9:30–16:00 EST, Mon–Fri only

---

## Project structure

```
stock_bot/
├── main.py                        # Entry point
├── config.py                      # All config and constants
├── database/
│   ├── db.py                      # Connection and schema init
│   └── queries.py                 # All SQL as typed functions
├── services/
│   ├── price_fetcher.py           # yfinance wrapper + EMA calculations
│   ├── watchlist_service.py       # Watchlist business logic
│   ├── holdings_service.py        # Holdings and FIFO sell logic
│   └── alert_service.py           # Alert checking and notifications
└── bot/
    ├── router.py                  # Command → handler mapping
    └── handlers/
        ├── general_handlers.py    # /start, /help
        ├── watchlist_handlers.py  # Watchlist commands
        ├── alert_handlers.py      # Alert commands
        ├── holdings_handlers.py   # Holdings commands
        └── report_handlers.py     # Report commands
```
