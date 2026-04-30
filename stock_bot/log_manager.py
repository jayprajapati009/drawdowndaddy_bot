"""
Smart log file manager.

Rotation:  daily at midnight via TimedRotatingFileHandler
Retention: 30 days maximum
Compression: the 2 most recent rotated files stay plain-text;
             everything older is gzip-compressed automatically on rotation
Size guard: if the logs/ directory exceeds SIZE_THRESHOLD_MB the oldest
            files are deleted one-by-one until the directory is under the limit
Cleanup:    runs automatically on every rotation (daily) and on startup
"""

import gzip
import logging
import logging.handlers
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOG_DIR             = Path(__file__).parent.parent / "logs"
LOG_FILE            = LOG_DIR / "stockbot.log"
MAX_AGE_DAYS        = 30          # hard retention ceiling
UNCOMPRESSED_KEEP   = 2           # how many recent rotated files stay plain-text
SIZE_THRESHOLD_MB   = 200         # trigger oldest-file deletion above this total size


def configure(log_dir: str) -> None:
    """Set the log directory and file before setup_logging() is called."""
    global LOG_DIR, LOG_FILE
    LOG_DIR  = Path(log_dir)
    LOG_FILE = LOG_DIR / "stockbot.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Custom rotating handler
# ---------------------------------------------------------------------------

class SmartRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Daily-rotating handler that:
    - names rotated files stockbot.log.YYYY-MM-DD
    - gzips rotated files beyond the most recent UNCOMPRESSED_KEEP
    - runs the full cleanup sweep on every rotation
    """

    def __init__(self, path: Path, uncompressed_keep: int = UNCOMPRESSED_KEEP):
        super().__init__(
            filename=str(path),
            when="midnight",
            interval=1,
            backupCount=MAX_AGE_DAYS,
            encoding="utf-8",
            delay=False,
            utc=False,
        )
        self.uncompressed_keep = uncompressed_keep
        # Use YYYY-MM-DD suffix instead of the default numeric counter
        self.suffix = "%Y-%m-%d"
        self.namer = self._date_namer

    @staticmethod
    def _date_namer(default_name: str) -> str:
        """Keep the handler's default YYYY-MM-DD suffix as-is."""
        return default_name

    def doRollover(self) -> None:
        super().doRollover()
        # Compress and clean up after every rotation
        _compress_old_files(self.uncompressed_keep)
        run_cleanup()


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

def _rotated_log_files() -> list[Path]:
    """
    Return all rotated log files (not the active stockbot.log) sorted
    oldest-first by modification time.
    """
    files = [
        f for f in LOG_DIR.glob("stockbot.log.*")
        if not f.name.endswith(".gz")
    ]
    return sorted(files, key=lambda f: f.stat().st_mtime)


def _all_log_files() -> list[Path]:
    """All log files including .gz, oldest first."""
    return sorted(
        [f for f in LOG_DIR.glob("stockbot.log*") if f.name != "stockbot.log"],
        key=lambda f: f.stat().st_mtime,
    )


def _compress_old_files(uncompressed_keep: int = UNCOMPRESSED_KEEP) -> None:
    """
    Gzip-compress every rotated plain-text log except the most recent
    *uncompressed_keep* files.
    """
    plain = _rotated_log_files()          # oldest first
    to_compress = plain[: max(0, len(plain) - uncompressed_keep)]

    for path in to_compress:
        gz_path = path.with_suffix(path.suffix + ".gz")
        try:
            with open(path, "rb") as src, gzip.open(gz_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            path.unlink()
            logger.debug("Compressed log: %s → %s", path.name, gz_path.name)
        except Exception as exc:
            logger.warning("Could not compress %s: %s", path.name, exc)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def run_cleanup() -> None:
    """
    Enforce both the age limit and the size limit.
    Safe to call at any time; skips the active log file.
    """
    _delete_by_age()
    _enforce_size_limit()
    _log_directory_stats()


def _delete_by_age() -> None:
    cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    for f in _all_log_files():
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                size_mb = f.stat().st_size / 1024 / 1024
                f.unlink()
                logger.info(
                    "Deleted expired log: %s (age >%dd, %.1f MB freed)",
                    f.name, MAX_AGE_DAYS, size_mb,
                )
        except Exception as exc:
            logger.warning("Could not delete %s: %s", f.name, exc)


def _enforce_size_limit() -> None:
    threshold = SIZE_THRESHOLD_MB * 1024 * 1024
    candidates = _all_log_files()   # oldest first — delete these first

    total = _directory_size()
    if total <= threshold:
        return

    logger.warning(
        "Log directory %.1f MB exceeds limit of %d MB — pruning oldest files",
        total / 1024 / 1024, SIZE_THRESHOLD_MB,
    )

    for f in candidates:
        if total <= threshold:
            break
        try:
            size = f.stat().st_size
            f.unlink()
            total -= size
            logger.warning(
                "Size prune: deleted %s (freed %.1f MB, dir now %.1f MB)",
                f.name, size / 1024 / 1024, total / 1024 / 1024,
            )
        except Exception as exc:
            logger.warning("Could not delete %s during size prune: %s", f.name, exc)


def _directory_size() -> int:
    """Total bytes used by all files in LOG_DIR."""
    return sum(f.stat().st_size for f in LOG_DIR.iterdir() if f.is_file())


def _log_directory_stats() -> None:
    all_files = list(LOG_DIR.glob("stockbot.log*"))
    total_mb  = _directory_size() / 1024 / 1024
    compressed   = sum(1 for f in all_files if f.suffix == ".gz")
    uncompressed = sum(1 for f in all_files if f.suffix != ".gz" and f.name != "stockbot.log")
    logger.info(
        "Log directory: %.1f MB total | %d plain rotated | %d compressed | threshold %d MB",
        total_mb, uncompressed, compressed, SIZE_THRESHOLD_MB,
    )
