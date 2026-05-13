#!/bin/bash
# Clean all data or data for a specific user.
set -e

ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-english_bot}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"

MYSQL_CMD="mysql -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"

echo "WARNING: This will permanently delete data!"
read -p "Clean specific user (enter telegram user_id) or ALL? [ALL]: " choice

if [ -z "$choice" ] || [ "$choice" = "ALL" ]; then
  read -p "Delete ALL words and sessions? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
  fi
  $MYSQL_CMD <<SQL
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE user_sessions;
TRUNCATE TABLE words;
SET FOREIGN_KEY_CHECKS = 1;
SQL
  echo "All data cleared."
else
  read -p "Delete data for user_id=${choice}? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
  fi
  $MYSQL_CMD <<SQL
DELETE FROM user_sessions WHERE user_id = ${choice};
DELETE FROM words WHERE user_id = ${choice};
SQL
  echo "Data for user ${choice} cleared."
fi
