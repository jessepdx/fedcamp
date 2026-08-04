#!/usr/bin/env bash
# Weekly RIDB sync wrapper for cron.
#
# Pulls facilities changed since last_sync_date, re-runs the pipeline, and
# applies the cached coords / seasonal enrichments. Does NOT auto-deploy —
# run `python purge_for_deploy.py && ./deploy.sh --db` manually when ready
# to push fresh data to the live host.
#
# Cron entry (Sundays 04:00 local):
#   0 4 * * 0 /Users/jessewest/Desktop/rv-finder/scripts/run_weekly_sync.sh

set -euo pipefail

PROJECT_DIR="/Users/jessewest/Desktop/rv-finder"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/sync.log"

mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

{
    echo "===== sync started $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    # shellcheck disable=SC1091
    source venv/bin/activate
    python sync.py
    echo "===== sync finished $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    echo
} >> "$LOG_FILE" 2>&1
