#!/bin/bash
# Pull latest code, update dependencies, restart the bot service.
set -e

REPO_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$REPO_DIR"

echo "=== Deploying English Bot ==="

echo "[1/3] Pulling latest changes..."
git pull origin main

echo "[2/3] Installing/updating dependencies..."
pip3 install -r requirements.txt

echo "[3/3] Restarting service..."
sudo systemctl restart english_bot
sudo systemctl status english_bot --no-pager

echo "=== Deploy complete ==="
