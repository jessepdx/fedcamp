#!/usr/bin/env bash
set -euo pipefail

# Deploy FedCamp to Lightsail instance
# https://campdex.com
# Usage: ./deploy.sh [--db]  (pass --db to also upload the app database)

HOST="ubuntu@54.190.143.246"
KEY="$HOME/.ssh/lightsail-fedcamp.pem"
# accept-new pins the host key on first contact and refuses to connect if it
# ever changes, unlike StrictHostKeyChecking=no which trusts whatever answers.
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
SCP="scp -i $KEY -o StrictHostKeyChecking=accept-new"
REMOTE_DIR="/home/ubuntu/fedcamp"
STAMP="$(date +%Y%m%d-%H%M%S)"

WITH_DB=0
[[ "${1:-}" == "--db" ]] && WITH_DB=1

if [[ $WITH_DB -eq 1 ]]; then
    if [[ ! -f ridb_app.db ]]; then
        echo "ERROR: ridb_app.db not found. Run 'python purge_for_deploy.py' first." >&2
        exit 1
    fi
    if command -v sqlite3 > /dev/null; then
        echo "==> Checkpointing WAL and verifying ridb_app.db..."
        sqlite3 ridb_app.db 'PRAGMA wal_checkpoint(TRUNCATE);' > /dev/null
        check="$(sqlite3 ridb_app.db 'PRAGMA integrity_check;')"
        if [[ "$check" != "ok" ]]; then
            echo "ERROR: integrity_check failed on ridb_app.db — not deploying:" >&2
            echo "$check" >&2
            exit 1
        fi
    else
        echo "WARNING: sqlite3 not found locally; skipping integrity check." >&2
    fi
fi

echo "==> Packaging app files..."
tar czf /tmp/fedcamp.tar.gz app.py db.py stats.py templates/ static/

echo "==> Uploading app tarball..."
$SCP /tmp/fedcamp.tar.gz "$HOST:~"

if [[ $WITH_DB -eq 1 ]]; then
    echo "==> Uploading ridb_app.db (this may take a minute)..."
    $SCP ridb_app.db "$HOST:~"
fi

echo "==> Snapshotting current release for rollback..."
$SSH "$HOST" "cd $REMOTE_DIR && tar czf ~/fedcamp-rollback-$STAMP.tar.gz app.py db.py stats.py templates/ static/"

# Stop before swapping. The app opens a SQLite connection per request, and
# replacing ridb.db while the OLD ridb.db-wal/-shm remain in place is a known
# corruption path: SQLite binds the WAL by filename, not to file contents, so
# it can try to recover the old database's frames into the new file. The app
# is read-only against this DB (db.py issues no writes), so discarding the
# WAL loses nothing.
echo "==> Stopping gunicorn..."
$SSH "$HOST" "sudo systemctl stop fedcamp"

if [[ $WITH_DB -eq 1 ]]; then
    echo "==> Swapping database (previous kept as ridb.db.prev)..."
    $SSH "$HOST" "cd $REMOTE_DIR \
        && rm -f ridb.db.prev ridb.db.prev-wal ridb.db.prev-shm \
        && if [ -f ridb.db ]; then mv ridb.db ridb.db.prev; fi \
        && rm -f ridb.db-wal ridb.db-shm \
        && mv ~/ridb_app.db ridb.db"
fi

echo "==> Extracting release..."
$SSH "$HOST" "cd $REMOTE_DIR && tar xzf ~/fedcamp.tar.gz"

echo "==> Starting gunicorn..."
$SSH "$HOST" "sudo systemctl start fedcamp"

# systemctl start succeeds as soon as the master forks — it says nothing about
# whether the workers survived import. Actually ask the app for a page.
echo "==> Health check (origin)..."
if ! $SSH "$HOST" 'for i in $(seq 1 15); do
        if curl -fsS -m 5 -o /dev/null http://127.0.0.1:5000/; then exit 0; fi
        sleep 1
    done
    exit 1'; then
    echo >&2
    echo "DEPLOY FAILED: app did not answer on 127.0.0.1:5000 within 15s." >&2
    echo "--- recent logs ---" >&2
    $SSH "$HOST" "sudo journalctl -u fedcamp -n 30 --no-pager" >&2 || true
    echo >&2
    echo "Roll back the code with:" >&2
    echo "  $SSH $HOST 'cd $REMOTE_DIR && tar xzf ~/fedcamp-rollback-$STAMP.tar.gz && sudo systemctl restart fedcamp'" >&2
    if [[ $WITH_DB -eq 1 ]]; then
        echo "Roll back the database with:" >&2
        echo "  $SSH $HOST 'cd $REMOTE_DIR && mv -f ridb.db.prev ridb.db && rm -f ridb.db-wal ridb.db-shm && sudo systemctl restart fedcamp'" >&2
    fi
    exit 1
fi
echo "    origin OK"

# The origin check alone would not have caught the Caddy failure that took the
# site down for 5 days in Jul 2026 — gunicorn was healthy throughout. Verify
# the site is actually reachable by the public, through Caddy and Cloudflare.
echo "==> Health check (public)..."
public_code=""
public_ok=0
for i in 1 2 3 4 5; do
    public_code="$(curl -sS -o /dev/null -w '%{http_code}' -m 15 https://campdex.com/ || true)"
    if [[ "$public_code" == "200" ]]; then
        public_ok=1
        break
    fi
    sleep 3
done

echo "==> Cleaning up..."
rm -f /tmp/fedcamp.tar.gz
$SSH "$HOST" "rm -f ~/fedcamp.tar.gz"

if [[ $public_ok -ne 1 ]]; then
    echo >&2
    echo "WARNING: deploy succeeded but https://campdex.com/ returned '$public_code', not 200." >&2
    echo "The app is healthy on the origin, so suspect Caddy or Cloudflare:" >&2
    echo "  $SSH $HOST 'sudo systemctl status caddy --no-pager -l'" >&2
    exit 1
fi
echo "    public OK"

echo "==> Done. Rollback snapshot on server: ~/fedcamp-rollback-$STAMP.tar.gz"
