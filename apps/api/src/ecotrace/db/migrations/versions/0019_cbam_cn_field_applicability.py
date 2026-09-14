"""Persist authoritative per-CN fieldApplicability for Phase 6A+.

Revision ID: 0019_cbam_cn_field_applicability
Revises: 0018_cbam_cn_product_profile
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from importlib import resources
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision: str = '0019_cbam_cn_field_applicability'
down_revision: str | None = '0018_cbam_cn_product_profile'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_PACKAGE = 'ecotrace.modules.cbam.data'
SEED_FILENAME = 'cbam_see_v2_1_cn_catalog.json'
EMPTY_APPLICABILITY = {
    'reducingAgent': False,
    'steelMillIdentificationNumber': False,
    'percentMn': False,
    'percentCr': False,
    'percentNi': False,
    'percentOtherAlloys': False,
    'percentOtherMaterials': False,
}


def _load_seed() -> dict:
    try:
        root = resources.files(SEED_PACKAGE)
        raw = (root / SEED_FILENAME).read_text(encoding='utf-8')
    except (FileNotFoundError, TypeError, AttributeError, ModuleNotFoundError):
        # versions → migrations → db → ecotrace
        ecotrace_root = Path(__file__).resolve().parents[3]
        path = ecotrace_root / 'modules' / 'cbam' / 'data' / SEED_FILENAME
        raw = path.read_text(encoding='utf-8')
    return json.loads(raw)


def _normalize_fa(raw: object) -> dict[str, bool]:
    source = raw if isinstance(raw, dict) else {}
    return {key: bool(source.get(key, False)) for key in EMPTY_APPLICABILITY}


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_cn_codes
    ADD COLUMN IF NOT EXISTS field_applicability JSONB NOT NULL DEFAULT '{}'::jsonb
"""
    )

    seed = _load_seed()
    dataset_meta = seed['dataset']
    expected_checksum = dataset_meta['contentChecksum']
    by_normalized = {
        row['normalizedCode']: _normalize_fa(row.get('fieldApplicability'))
        for row in seed['cnCodes']
    }

    conn = op.get_bind()
    datasets = conn.execute(
        text(
            """
SELECT id, dataset_code, dataset_version, content_checksum
FROM cbam_cn_code_datasets
WHERE dataset_code = :code AND dataset_version = :version
"""
        ),
        {
            'code': dataset_meta['datasetCode'],
            'version': dataset_meta['datasetVersion'],
        },
    ).mappings().all()

    for dataset in datasets:
        codes = conn.execute(
            text(
                """
SELECT id, normalized_code
FROM cbam_cn_codes
WHERE dataset_id = :dataset_id
"""
            ),
            {'dataset_id': dataset['id']},
        ).mappings().all()
        for code in codes:
            fa = by_normalized.get(code['normalized_code'], EMPTY_APPLICABILITY)
            conn.execute(
                text(
                    """
UPDATE cbam_cn_codes
SET field_applicability = CAST(:fa AS jsonb),
    updated_at = now()
WHERE id = :id
"""
                ),
                {'fa': json.dumps(fa, separators=(',', ':')), 'id': code['id']},
            )
        # Align stored checksum with enriched seed (same dataset identity; additive metadata).
        conn.execute(
            text(
                """
UPDATE cbam_cn_code_datasets
SET content_checksum = :checksum,
    updated_at = now()
WHERE id = :id
"""
            ),
            {'checksum': expected_checksum, 'id': dataset['id']},
        )


def downgrade() -> None:
    op.execute('ALTER TABLE cbam_cn_codes DROP COLUMN IF EXISTS field_applicability')
