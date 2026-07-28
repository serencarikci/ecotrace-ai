#!/usr/bin/env bash
set -euo pipefail

HOST="${POSTGRES_HOST:-postgres}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-ecotrace}"
MAX_ATTEMPTS="${WAIT_DB_MAX_ATTEMPTS:-60}"
SLEEP_SECONDS="${WAIT_DB_SLEEP_SECONDS:-2}"

echo "Waiting for PostgreSQL at ${HOST}:${PORT}..."

attempt=1
while (( attempt <= MAX_ATTEMPTS )); do
  if pg_isready -h "${HOST}" -p "${PORT}" -U "${USER}" >/dev/null 2>&1; then
    echo "PostgreSQL is ready."
    exit 0
  fi
  echo "Attempt ${attempt}/${MAX_ATTEMPTS}: not ready yet..."
  sleep "${SLEEP_SECONDS}"
  ((attempt++))
done

echo "ERROR: PostgreSQL did not become ready in time." >&2
exit 1
