#!/usr/bin/env bash

set -euo pipefail

BACKUP_DIR="${1:?Usage: verify-backup.sh /path/to/backup-timestamp}"

if [ ! -d "${BACKUP_DIR}" ]; then
  echo "Backup directory not found: ${BACKUP_DIR}" >&2
  exit 1
fi

if [ ! -f "${BACKUP_DIR}/SHA256SUMS" ]; then
  echo "SHA256SUMS missing" >&2
  exit 1
fi

if [ ! -f "${BACKUP_DIR}/postgres.dump.gz" ]; then
  echo "postgres.dump.gz missing" >&2
  exit 1
fi

(cd "${BACKUP_DIR}" && shasum -a 256 -c SHA256SUMS)
echo "Backup verification OK: ${BACKUP_DIR}"
