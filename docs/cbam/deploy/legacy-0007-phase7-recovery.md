# Legacy local DB recovery — `0007_phase7` stamp mismatch

**Do not run this procedure automatically in deployment.**  
**Never use `alembic stamp` to “fix” a new or production database.**

## When this applies

Only when an **existing local developer database** was previously stamped or migrated under the obsolete revision id `0007_phase7` and Alembic cannot resolve the chain to `0032_cbam_prec_audit`.

## Safe path for new / external-test databases

1. Create an empty PostgreSQL database.  
2. Run `alembic upgrade head` (no stamp).  
3. Confirm `alembic_version.version_num = 0032_cbam_prec_audit`.  
4. Run `python -m ecotrace.db.seed` twice and confirm idempotency.  
5. Confirm **53** `cbam_*` tables exist.

## Manual recovery (legacy local only)

1. Back up the database.  
2. Inspect `alembic_version`.  
3. If the only problem is the obsolete label `0007_phase7` and schema already matches a known good revision (historically `0007_intelligence` in this project), an operator may **manually** update the version row after review — never as part of container entrypoint.  
4. Then run `alembic upgrade head` and re-verify head `0032_cbam_prec_audit`.  
5. If schema is uncertain, prefer recreate-from-empty over stamp-based repair.

## Deployment rule

Container entrypoint must only run `alembic upgrade head` on empty or forward-compatible databases. Stamp-based repairs stay operator-owned and documented here only.
