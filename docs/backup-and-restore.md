# Backup and Restore

Scripts (credentials via environment only):

- `scripts/backup.sh` — `pg_dump` + attachment/knowledge/report tarballs + SHA-256
- `scripts/verify-backup.sh` — checksum verification
- `scripts/restore.sh` — restore order: PostgreSQL first, then file stores

Point-in-time recovery (PITR) is **not** implemented by these scripts; configure WAL archiving at the infrastructure layer if required.

Never automatically delete approved inventories, calculation snapshots, approved LCA/PCF, published passport versions, approval records, or critical audit records.
