#!/usr/bin/env bash

set -euo pipefail

BACKUP_DIR="${1:?Usage: restore.sh /path/to/backup-timestamp}"

: "${POSTGRES_HOST:?POSTGRES_HOST required}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
: "${POSTGRES_USER:?POSTGRES_USER required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

if [ ! -f "${BACKUP_DIR}/postgres.dump.gz" ]; then
  echo "Missing postgres.dump.gz in ${BACKUP_DIR}" >&2
  exit 1
fi

if [ ! -f "${BACKUP_DIR}/SHA256SUMS" ]; then
  echo "Warning: SHA256SUMS missing; proceeding without verification." >&2
else
  (cd "${BACKUP_DIR}" && shasum -a 256 -c SHA256SUMS)
fi

echo "Restoring PostgreSQL (destructive to current database contents)."
gunzip -c "${BACKUP_DIR}/postgres.dump.gz" | pg_restore \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" --clean --if-exists

restore_tar() {
  local archive="$1"
  local dest="$2"
  if [ -f "${archive}" ]; then
    mkdir -p "${dest}"
    tar -xzf "${archive}" -C "${dest}"
    echo "Restored ${archive} -> ${dest}"
  fi
}

restore_tar "${BACKUP_DIR}/attachments.tar.gz" "${ATTACHMENT_STORAGE_PATH:-/data/attachments}"
restore_tar "${BACKUP_DIR}/knowledge.tar.gz" "${KNOWLEDGE_STORAGE_PATH:-/data/knowledge}"
restore_tar "${BACKUP_DIR}/reports.tar.gz" "${REPORT_STORAGE_PATH:-/data/reports}"

echo "Restore finished."
echo "Note: Point-in-time recovery (PITR) is an infrastructure option and is not implemented by these scripts."
