#!/usr/bin/env bash
set -euo pipefail

# Deploy FedCamp to Lightsail instance
# https://fedcamp.cloudromeo.com
# Usage: ./deploy.sh [--db]  (pass --db to also upload ridb.db)

HOST="ubuntu@54.190.143.246"
KEY="$HOME/.ssh/lightsail-fedcamp.pem"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no"
SCP="scp -i $KEY -o StrictHostKeyChecking=no"
REMOTE_DIR="/home/ubuntu/fedcamp"

echo "==> Packaging app files..."
tar czf /tmp/fedcamp.tar.gz app.py db.py stats.py templates/ static/

echo "==> Uploading app tarball..."
$SCP /tmp/fedcamp.tar.gz "$HOST:~"

if [[ "${1:-}" == "--db" ]]; then
    if [[ ! -f ridb_app.db ]]; then
        echo "ERROR: ridb_app.db not found. Run 'python purge_for_deploy.py' first." >&2
        exit 1
    fi
    echo "==> Uploading ridb_app.db (this may take a minute)..."
    $SCP ridb_app.db "$HOST:~"
    # Atomic-ish swap: upload to a side path, then mv into place
    $SSH "$HOST" "mv ~/ridb_app.db $REMOTE_DIR/ridb.db.new && mv $REMOTE_DIR/ridb.db.new $REMOTE_DIR/ridb.db"
fi

echo "==> Extracting on server..."
$SSH "$HOST" "cd $REMOTE_DIR && tar xzf ~/fedcamp.tar.gz"

echo "==> Restarting gunicorn..."
$SSH "$HOST" "sudo systemctl restart fedcamp"

echo "==> Done! Checking status..."
$SSH "$HOST" "sudo systemctl status fedcamp --no-pager -l"
