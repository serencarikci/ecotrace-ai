"""Phase 6A+ migration round-trip for CN field_applicability."""

from __future__ import annotations

import json

from sqlalchemy import select, text

from ecotrace.modules.cbam.application.cn_catalog_seed import (
    ensure_platform_cn_catalog,
    load_cn_catalog_seed_payload,
)
from ecotrace.modules.cbam.application.field_applicability import (
    empty_field_applicability,
    normalize_field_applicability,
)
from ecotrace.modules.cbam.infrastructure.models import CbamCnCode


def _backfill_like_migration(db) -> str:
    """Mirror 0019 upgrade backfill deterministically on the open test session."""
    payload = load_cn_catalog_seed_payload()
    expected_checksum = payload['dataset']['contentChecksum']
    by_norm = {
        row['normalizedCode']: normalize_field_applicability(row.get('fieldApplicability'))
        for row in payload['cnCodes']
    }
    db.execute(
        text(
            """
ALTER TABLE cbam_cn_codes
    ADD COLUMN IF NOT EXISTS field_applicability JSONB NOT NULL DEFAULT '{}'::jsonb
"""
        )
    )
    rows = list(
        db.execute(
            text(
                """
SELECT c.id, c.normalized_code, d.id AS dataset_id
FROM cbam_cn_codes c
JOIN cbam_cn_code_datasets d ON d.id = c.dataset_id
WHERE d.dataset_code = 'CBAM_SEE_CN_CODES' AND d.dataset_version = 'SEE_V2.1'
"""
            )
        ).mappings()
    )
    for row in rows:
        fa = by_norm.get(row['normalized_code'], empty_field_applicability())
        db.execute(
            text(
                """
UPDATE cbam_cn_codes
SET field_applicability = CAST(:fa AS jsonb), updated_at = now()
WHERE id = :id
"""
            ),
            {'fa': json.dumps(fa, separators=(',', ':')), 'id': row['id']},
        )
    db.execute(
        text(
            """
UPDATE cbam_cn_code_datasets
SET content_checksum = :checksum, updated_at = now()
WHERE dataset_code = 'CBAM_SEE_CN_CODES' AND dataset_version = 'SEE_V2.1'
"""
        ),
        {'checksum': expected_checksum},
    )
    db.flush()
    return expected_checksum


def test_field_applicability_migration_round_trip(seeded_db) -> None:
    """upgrade → downgrade → upgrade keeps deterministic backfill/checksum."""
    ensure_platform_cn_catalog(seeded_db)
    payload = load_cn_catalog_seed_payload()
    by_norm = {
        row['normalizedCode']: row['fieldApplicability'] for row in payload['cnCodes']
    }

    # Simulate pre-6A+ schema.
    seeded_db.execute(text('ALTER TABLE cbam_cn_codes DROP COLUMN IF EXISTS field_applicability'))
    seeded_db.execute(
        text(
            """
UPDATE cbam_cn_code_datasets
SET content_checksum = :old
WHERE dataset_code = 'CBAM_SEE_CN_CODES' AND dataset_version = 'SEE_V2.1'
"""
        ),
        {'old': '0' * 64},
    )
    seeded_db.flush()

    expected_checksum = _backfill_like_migration(seeded_db)
    seeded_db.expire_all()

    rows = list(
        seeded_db.execute(
            text('SELECT normalized_code, field_applicability FROM cbam_cn_codes')
        ).mappings()
    )
    assert len(rows) == 569
    for row in rows:
        assert row['field_applicability'] == by_norm[row['normalized_code']]
    checksum = seeded_db.execute(
        text(
            """
SELECT content_checksum FROM cbam_cn_code_datasets
WHERE dataset_code = 'CBAM_SEE_CN_CODES' AND dataset_version = 'SEE_V2.1'
"""
        )
    ).scalar_one()
    assert checksum == expected_checksum

    # Downgrade
    seeded_db.execute(text('ALTER TABLE cbam_cn_codes DROP COLUMN IF EXISTS field_applicability'))
    seeded_db.flush()
    col = seeded_db.execute(
        text(
            """
SELECT 1 FROM information_schema.columns
WHERE table_name = 'cbam_cn_codes' AND column_name = 'field_applicability'
"""
        )
    ).scalar_one_or_none()
    assert col is None

    # Re-upgrade
    _backfill_like_migration(seeded_db)
    seeded_db.expire_all()
    steel = seeded_db.execute(
        text(
            """
SELECT field_applicability FROM cbam_cn_codes WHERE normalized_code = '73181595'
"""
        )
    ).scalar_one()
    assert steel['reducingAgent'] is True
    cement = seeded_db.execute(
        text(
            """
SELECT field_applicability FROM cbam_cn_codes WHERE normalized_code = '25232900'
"""
        )
    ).scalar_one()
    assert cement['reducingAgent'] is False
    orm_steel = seeded_db.execute(
        select(CbamCnCode).where(CbamCnCode.normalized_code == '73181595')
    ).scalar_one()
    assert orm_steel.field_applicability['percentOtherMaterials'] is True
