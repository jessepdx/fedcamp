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
    echo "==> Uploading ridb.db (this may take a minute)..."
    $SCP ridb.db "$HOST:~"
    $SSH "$HOST" "mv ~/ridb.db $REMOTE_DIR/"
fi

echo "==> Extracting on server..."
$SSH "$HOST" "cd $REMOTE_DIR && tar xzf ~/fedcamp.tar.gz"

echo "==> Restarting gunicorn..."
$SSH "$HOST" "sudo systemctl restart fedcamp"

echo "==> Done! Checking status..."
$SSH "$HOST" "sudo systemctl status fedcamp --no-pager -l"
