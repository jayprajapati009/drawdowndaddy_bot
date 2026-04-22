#!/usr/bin/env bash
# Usage:
#   ./db.sh backup          — save a timestamped snapshot
#   ./db.sh restore         — list available backups
#   ./db.sh restore FILE    — restore from a specific backup file

DB="stock_bot.db"
BACKUP_DIR="db_backups"
mkdir -p "$BACKUP_DIR"

case "${1:-}" in
  backup)
    DEST="$BACKUP_DIR/stock_bot_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB" "$DEST"
    echo "Backed up to $DEST"
    ;;
  restore)
    if [ -n "${2:-}" ]; then
      cp "$2" "$DB"
      echo "Restored from $2"
    else
      echo "Available backups:"
      ls -lh "$BACKUP_DIR"/*.db 2>/dev/null | awk '{print $NF, $5, $6, $7}' || echo "  (none)"
      echo ""
      echo "Run:  ./db.sh restore db_backups/FILENAME.db"
    fi
    ;;
  *)
    echo "Usage: ./db.sh backup | restore [FILE]"
    ;;
esac
