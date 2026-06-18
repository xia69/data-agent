#!/bin/sh
set -eu

MYSQL_HOST="${MYSQL_HOST:-mysql}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-112233}"

mysql_exec() {
  mysql \
    -h"${MYSQL_HOST}" \
    -P"${MYSQL_PORT}" \
    -u"${MYSQL_USER}" \
    -p"${MYSQL_PASSWORD}" \
    --default-character-set=utf8mb4 \
    "$@"
}

for _ in $(seq 1 30); do
  if mysql_exec -e "SELECT 1;" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

mysql_exec -e "SELECT 1;" >/dev/null

meta_ready="$(mysql_exec -Nse "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'meta' AND TABLE_NAME = 'table_info';" 2>/dev/null || true)"
if [ "${meta_ready:-0}" = "0" ]; then
  echo "Initializing meta schema..."
  mysql_exec < /initdb/meta.sql
else
  echo "Meta schema already initialized. Skipping."
fi

dw_rows="$(mysql_exec -Nse "SELECT COUNT(*) FROM dw.dim_region;" 2>/dev/null || true)"
if [ "${dw_rows:-0}" = "0" ]; then
  echo "Initializing dw schema and seed data..."
  mysql_exec < /initdb/dw.sql
else
  echo "DW schema already initialized. Skipping."
fi
