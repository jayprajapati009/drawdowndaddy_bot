#!/usr/bin/env bash
# services.sh — manage systemd services for each bot config
#
# Usage:
#   ./services.sh deploy    — create or update services for all configs/bot-*.json
#   ./services.sh remove    — stop and remove services with no matching config
#   ./services.sh status    — show status of all bot services
#   ./services.sh restart   — restart all bot services
#   ./services.sh logs N    — tail live logs for bot N  (e.g. ./services.sh logs 1)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_PREFIX="stockbot"

# ── Helpers ────────────────────────────────────────────────────────────────────

_require_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Run as root (or with sudo) to manage systemd services."
        exit 1
    fi
}

_bot_name() {
    python3 -c "import json; print(json.load(open('$1'))['bot_name'])" 2>/dev/null || echo "Bot"
}

_service_name() { echo "${SERVICE_PREFIX}-${1}"; }   # e.g. stockbot-1
_service_file() { echo "/etc/systemd/system/$(_service_name "$1").service"; }

_write_service() {
    local bot_id="$1"
    local config_rel="$2"   # relative path, e.g. configs/bot-1.json
    local bot_name="$3"

    cat > "$(_service_file "$bot_id")" <<EOF
[Unit]
Description=${bot_name} stock alert bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_PYTHON} -m stock_bot.main --config ${config_rel}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
}

_active_bot_ids() {
    # IDs of services currently registered with systemd
    systemctl list-units --type=service --all --plain --no-legend 2>/dev/null \
        | awk '{print $1}' \
        | grep "^${SERVICE_PREFIX}-[0-9]*\.service$" \
        | sed "s/^${SERVICE_PREFIX}-//; s/\.service$//"
}

_config_bot_ids() {
    # IDs derived from configs/bot-N.json files (digits only, excludes *.example.json)
    for f in "$PROJECT_DIR"/configs/bot-*.json; do
        [ -f "$f" ] || continue
        local name; name=$(basename "$f")
        # Skip example files
        [[ "$name" == *.example.json ]] && continue
        echo "$name" | sed 's/^bot-//; s/\.json$//'
    done
}

# ── Commands ───────────────────────────────────────────────────────────────────

cmd_deploy() {
    _require_root
    local deployed=0

    for config_file in "$PROJECT_DIR"/configs/bot-*.json; do
        [ -f "$config_file" ] || { echo "⚠️  No config files found in configs/bot-*.json"; exit 1; }

        local filename; filename=$(basename "$config_file")
        # Skip example files
        [[ "$filename" == *.example.json ]] && continue

        local bot_id="${filename#bot-}"; bot_id="${bot_id%.json}"
        local svc; svc=$(_service_name "$bot_id")
        local bot_name; bot_name=$(_bot_name "$config_file")

        echo "→ $svc  ($bot_name)"
        _write_service "$bot_id" "configs/${filename}" "$bot_name"
        systemctl daemon-reload

        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            systemctl restart "$svc"
            echo "  ✓ Restarted (service already existed)"
        else
            systemctl enable "$svc" --quiet
            systemctl start  "$svc"
            echo "  ✓ Created and started"
        fi
        (( deployed++ )) || true
    done

    echo ""
    echo "✅ $deployed service(s) deployed."
}

cmd_remove() {
    _require_root
    local removed=0

    while IFS= read -r bot_id; do
        [ -n "$bot_id" ] || continue
        local config_file="$PROJECT_DIR/configs/bot-${bot_id}.json"
        local svc; svc=$(_service_name "$bot_id")

        if [ ! -f "$config_file" ]; then
            echo "→ $svc has no matching config — removing..."
            systemctl stop    "$svc" 2>/dev/null || true
            systemctl disable "$svc" --quiet 2>/dev/null || true
            rm -f "$(_service_file "$bot_id")"
            systemctl daemon-reload
            echo "  ✓ Removed"
            (( removed++ )) || true
        fi
    done < <(_active_bot_ids)

    if [ "$removed" -eq 0 ]; then
        echo "Nothing to remove — all active services have a matching config."
    else
        echo ""
        echo "✅ $removed service(s) removed."
    fi
}

cmd_status() {
    local found=0
    while IFS= read -r bot_id; do
        [ -n "$bot_id" ] || continue
        local svc; svc=$(_service_name "$bot_id")
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        systemctl status "$svc" --no-pager -l 2>&1 | head -20
        (( found++ )) || true
    done < <(_active_bot_ids)

    if [ "$found" -eq 0 ]; then
        echo "No bot services found. Run ./services.sh deploy first."
    fi
}

cmd_restart() {
    _require_root
    local restarted=0
    while IFS= read -r bot_id; do
        [ -n "$bot_id" ] || continue
        local svc; svc=$(_service_name "$bot_id")
        systemctl restart "$svc"
        echo "✓ Restarted $svc"
        (( restarted++ )) || true
    done < <(_active_bot_ids)

    if [ "$restarted" -eq 0 ]; then
        echo "No bot services found."
    fi
}

cmd_logs() {
    local bot_id="${1:-}"
    if [ -z "$bot_id" ]; then
        echo "Usage: ./services.sh logs N   (e.g. ./services.sh logs 1)"
        exit 1
    fi
    local svc; svc=$(_service_name "$bot_id")
    echo "Tailing $svc — Ctrl+C to stop"
    journalctl -fu "$svc"
}

cmd_usage() {
    echo "Usage: ./services.sh <command>"
    echo ""
    echo "  deploy    Create or update services for all configs/bot-*.json"
    echo "  remove    Stop and delete services with no matching config"
    echo "  status    Show live status of all bot services"
    echo "  restart   Restart all bot services"
    echo "  logs N    Tail live logs for bot N  (e.g. logs 1)"
}

# ── Entry point ────────────────────────────────────────────────────────────────

case "${1:-}" in
    deploy)  cmd_deploy ;;
    remove)  cmd_remove ;;
    status)  cmd_status ;;
    restart) cmd_restart ;;
    logs)    cmd_logs "${2:-}" ;;
    *)       cmd_usage ;;
esac
