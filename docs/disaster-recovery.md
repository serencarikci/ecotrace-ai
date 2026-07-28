# Disaster Recovery

1. Restore PostgreSQL logical dump
2. Restore attachment / knowledge / report storage archives
3. Verify checksums
4. Run migrations only if restoring onto a newer schema intentionally
5. Validate `/ready` and system health

PITR requires infrastructure WAL archiving and is not provided by application scripts.
