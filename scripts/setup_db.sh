#!/bin/bash
# SQLite database is created automatically on first bot start.
# This script just verifies Python dependencies are installed.
set -e

echo "=== Checking dependencies ==="
pip3 install -r "$(dirname "$0")/../requirements.txt"
echo "All dependencies installed. Run bot.py to start — DB will be created automatically."
