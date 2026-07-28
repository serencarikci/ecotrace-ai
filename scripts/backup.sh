#!/usr/bin/env bash

set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST required}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
: "${POSTGRES_USER:?POSTGRES_USER required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}"
: "${BACKUP_ROOT:=${BACKUP_STORAGE_PATH:-./backups}}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_ROOT}/${TIMESTAMP}"
mkdir -p "${DEST}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "Backing up PostgreSQL to ${DEST}/postgres.dump.gz"
pg_dump -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" -Fc | gzip -c > "${DEST}/postgres.dump.gz"

backup_dir() {
  local src="$1"
  local name="$2"
  if [ -d "${src}" ]; then
    echo "Backing up ${name} from ${src}"
    tar -czf "${DEST}/${name}.tar.gz" -C "${src}" .
  else
    echo "Skip missing ${name}: ${src}"
  fi
}

backup_dir "${ATTACHMENT_STORAGE_PATH:-/data/attachments}" "attachments"
backup_dir "${KNOWLEDGE_STORAGE_PATH:-/data/knowledge}" "knowledge"
backup_dir "${REPORT_STORAGE_PATH:-/data/reports}" "reports"

(
  cd "${DEST}"
  shasum -a 256 ./* > SHA256SUMS
)

echo "Backup complete: ${DEST}"
echo "Checksums written to ${DEST}/SHA256SUMS"
