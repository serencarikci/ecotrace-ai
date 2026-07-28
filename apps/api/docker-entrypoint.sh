#!/usr/bin/env bash
set -euo pipefail

ATTACH_PATH="${ATTACHMENT_STORAGE_PATH:-/data/attachments}"
KNOWLEDGE_PATH="${KNOWLEDGE_STORAGE_PATH:-/data/knowledge}"
REPORT_PATH="${REPORT_STORAGE_PATH:-/data/reports}"
BACKUP_PATH="${BACKUP_STORAGE_PATH:-/data/backups}"

ensure_storage() {
  mkdir -p "${ATTACH_PATH}" "${ATTACH_PATH}/imports" \
    "${KNOWLEDGE_PATH}" "${REPORT_PATH}" "${BACKUP_PATH}"
  chown -R ecotrace:ecotrace "${ATTACH_PATH}" "${KNOWLEDGE_PATH}" \
    "${REPORT_PATH}" "${BACKUP_PATH}" 2>/dev/null || true
}

if [ "$(id -u)" -eq 0 ]; then
  ensure_storage
  exec setpriv --reuid=ecotrace --regid=ecotrace --init-groups -- "$0" "$@"
fi

echo "Waiting for database..."
HOST="${POSTGRES_HOST:-postgres}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-ecotrace}"

for i in $(seq 1 60); do
  if pg_isready -h "${HOST}" -p "${PORT}" -U "${USER}" >/dev/null 2>&1; then
    echo "Database is ready."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "Database did not become ready in time." >&2
    exit 1
  fi
  sleep 2
done

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running migrations..."
  alembic upgrade head
fi

if [ "${RUN_SEED:-true}" = "true" ]; then
  echo "Running seed..."
  python -m ecotrace.db.seed
fi

echo "Starting process: $*"
exec "$@"
