#!/bin/bash
# Clean all data or data for a specific user from the SQLite database.
set -e

ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_FILE="${DB_PATH:-english_bot.db}"
REPO_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
DB_FULL_PATH="${REPO_DIR}/${DB_FILE}"

if [ ! -f "$DB_FULL_PATH" ]; then
  echo "Database file not found: $DB_FULL_PATH"
  exit 1
fi

echo "Database: $DB_FULL_PATH"
echo "WARNING: This will permanently delete data!"
read -p "Clean specific user (enter telegram user_id) or ALL? [ALL]: " choice

if [ -z "$choice" ] || [ "$choice" = "ALL" ]; then
  read -p "Delete ALL words and sessions? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
  fi
  sqlite3 "$DB_FULL_PATH" "DELETE FROM user_sessions; DELETE FROM words;"
  echo "All data cleared."
else
  read -p "Delete data for user_id=${choice}? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
  fi
  sqlite3 "$DB_FULL_PATH" "DELETE FROM user_sessions WHERE user_id = ${choice}; DELETE FROM words WHERE user_id = ${choice};"
  echo "Data for user ${choice} cleared."
fi
