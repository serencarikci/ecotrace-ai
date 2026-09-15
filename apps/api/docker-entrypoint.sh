#!/usr/bin/env bash
set -euo pipefail

ATTACH_PATH="${ATTACHMENT_STORAGE_PATH:-/data/attachments}"
KNOWLEDGE_PATH="${KNOWLEDGE_STORAGE_PATH:-/data/knowledge}"
REPORT_PATH="${REPORT_STORAGE_PATH:-/data/reports}"
BACKUP_PATH="${BACKUP_STORAGE_PATH:-/data/backups}"
LO_TMP="${LIBREOFFICE_TMP_ROOT:-/tmp/ecotrace-lo}"

ensure_storage() {
  mkdir -p "${ATTACH_PATH}" "${ATTACH_PATH}/imports" \
    "${KNOWLEDGE_PATH}" "${REPORT_PATH}" "${BACKUP_PATH}" "${LO_TMP}"
  chown -R ecotrace:ecotrace "${ATTACH_PATH}" "${KNOWLEDGE_PATH}" \
    "${REPORT_PATH}" "${BACKUP_PATH}" "${LO_TMP}" 2>/dev/null || true
  chmod -R u+rwX,g+rX,o-rwx "${ATTACH_PATH}" "${KNOWLEDGE_PATH}" \
    "${REPORT_PATH}" "${BACKUP_PATH}" "${LO_TMP}" 2>/dev/null || true
}

if [ "$(id -u)" -eq 0 ]; then
  ensure_storage
  exec setpriv --reuid=ecotrace --regid=ecotrace --init-groups -- "$0" "$@"
fi

export TMPDIR="${LO_TMP}"
export HOME="${HOME:-/home/ecotrace}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
mkdir -p "${XDG_CACHE_HOME}/dconf" "${XDG_CONFIG_HOME}" "${HOME}/.local/share" 2>/dev/null || true
export LIBREOFFICE_SOFFICE_PATH="${LIBREOFFICE_SOFFICE_PATH:-/usr/bin/soffice}"
export OFFICIAL_SEE_TEMPLATE_PATH="${OFFICIAL_SEE_TEMPLATE_PATH:-/app/official-see/template.xlsx}"

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
  echo "Running migrations (alembic upgrade head)..."
  alembic upgrade head
fi

# Production / external staging must never silently seed demo accounts.
# Default remains true for local development images only.
APP_ENV_VALUE="${APP_ENV:-development}"
RUN_SEED_VALUE="${RUN_SEED:-true}"
if [ "${APP_ENV_VALUE}" = "production" ] && [ "${RUN_SEED_VALUE}" = "true" ]; then
  echo "RUN_SEED=true is forbidden when APP_ENV=production (fail closed)." >&2
  exit 1
fi

if [ "${RUN_SEED_VALUE}" = "true" ]; then
  echo "Running seed..."
  python -m ecotrace.db.seed
fi

echo "Starting process: $*"
exec "$@"
