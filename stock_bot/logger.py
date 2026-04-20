"""
Logging configuration.

Call setup_logging() once at startup (done in main.py).
All modules use logging.getLogger(__name__) — no other setup needed.

Output:
  - Terminal  : colour-coded by level
  - logs/stockbot.log : daily-rotating, compressed, auto-cleaned
                        (see log_manager.py for full policy)
"""

import logging
from pathlib import Path

from stock_bot.log_manager import LOG_DIR, LOG_FILE, SmartRotatingFileHandler, run_cleanup

_FMT      = "%(asctime)s [%(levelname)-8s] %(name)s (%(filename)s:%(lineno)d) — %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_COLOURS = {
    logging.DEBUG:    "\033[36m",   # cyan
    logging.INFO:     "\033[32m",   # green
    logging.WARNING:  "\033[33m",   # yellow
    logging.ERROR:    "\033[31m",   # red
    logging.CRITICAL: "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColouredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # --- Terminal handler ---
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(_ColouredFormatter(_FMT, datefmt=_DATE_FMT))
    root.addHandler(console)

    # --- Smart file handler (daily rotation + compression + auto-cleanup) ---
    file_handler = SmartRotatingFileHandler(LOG_FILE)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    root.addHandler(file_handler)

    # Silence chatty third-party loggers
    for noisy in ("httpx", "httpcore", "apscheduler.executors", "yfinance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    log = logging.getLogger(__name__)
    log.info("Logging initialised — %s", LOG_FILE.resolve())

    # Run startup cleanup in case the process was down for multiple days
    run_cleanup()
