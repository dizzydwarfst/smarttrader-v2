#!/usr/bin/env bash
# Daily backup of SmartTrader stateful files.
# Intended to be run from cron, e.g.:
#   0 3 * * *  /root/smarttrader-v2/scripts/backup.sh >> /root/smarttrader-v2/scripts/backup.log 2>&1
#
# Keeps BACKUP_RETAIN_DAYS of daily snapshots under $BACKUP_DIR.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/smarttrader-backups}"
BACKUP_RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"

STAMP="$(date +%Y-%m-%d)"
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Backing up smarttrader-v2 → $DEST"

# Files worth keeping. Globs are OK — missing files are skipped quietly.
FILES=(
    "trades.db"
    "soul.md"
    "skills.md"
    "ai_review_state.json"
    "bot_status.json"
    "runtime_commands.json"
)

copied=0
for f in "${FILES[@]}"; do
    src="$REPO_DIR/$f"
    if [[ -f "$src" ]]; then
        cp -p "$src" "$DEST/"
        copied=$((copied + 1))
        log "  ✓ $f"
    else
        log "  · $f (missing, skipped)"
    fi
done

# strategy_cards directory too, if present
if [[ -d "$REPO_DIR/strategy_cards" ]]; then
    cp -rp "$REPO_DIR/strategy_cards" "$DEST/"
    log "  ✓ strategy_cards/"
fi

log "Copied $copied file(s). Rotating old backups (> $BACKUP_RETAIN_DAYS days)..."

# Delete backup directories older than N days
find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime +"$BACKUP_RETAIN_DAYS" -print -exec rm -rf {} +

log "Backup complete."
