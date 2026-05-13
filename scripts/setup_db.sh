#!/bin/bash
# Run once on a new server to create the database and user.
set -e

ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_NAME="${DB_NAME:-english_bot}"
DB_USER="${DB_USER:-english_bot_user}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"

echo "Creating database '${DB_NAME}' and user '${DB_USER}'..."

sudo mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "Done. Database is ready."
