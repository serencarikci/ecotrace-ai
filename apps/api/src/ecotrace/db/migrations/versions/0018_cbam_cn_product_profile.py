"""CBAM Phase 6A CN-code catalog and product-profile classification fields."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0018_cbam_cn_product_profile'
down_revision: str | None = '0017_cbam_sc_current_result'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_cn_code_datasets (
    id UUID PRIMARY KEY,
    dataset_code VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    content_checksum VARCHAR(64) NOT NULL,
    source_workbook_name VARCHAR(512) NOT NULL,
    source_workbook_sha256 VARCHAR(64) NOT NULL,
    source_template_version VARCHAR(32) NOT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cbam_cn_dataset_code_version UNIQUE (dataset_code, dataset_version),
    CONSTRAINT ck_cbam_cn_dataset_status
        CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')),
    CONSTRAINT ck_cbam_cn_dataset_valid_dates
        CHECK (valid_until IS NULL OR valid_until >= valid_from)
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_code_datasets_status ON cbam_cn_code_datasets (status)'
    )

    op.execute(
        """
CREATE TABLE cbam_cn_codes (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES cbam_cn_code_datasets(id) ON DELETE RESTRICT,
    cn_key VARCHAR(64) NOT NULL,
    normalized_code VARCHAR(32) NOT NULL,
    display_code VARCHAR(64) NOT NULL,
    description_en TEXT NOT NULL,
    cbam_sector VARCHAR(128) NOT NULL,
    numbering_label VARCHAR(128) NULL,
    source_sheet VARCHAR(64) NOT NULL,
    source_row INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cbam_cn_codes_dataset_cn_key UNIQUE (dataset_id, cn_key),
    CONSTRAINT uq_cbam_cn_codes_dataset_normalized UNIQUE (dataset_id, normalized_code),
    CONSTRAINT ck_cbam_cn_codes_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')),
    CONSTRAINT ck_cbam_cn_codes_source_row_positive CHECK (source_row >= 1)
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_codes_dataset_id ON cbam_cn_codes (dataset_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_codes_normalized_code ON cbam_cn_codes (normalized_code)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_codes_cbam_sector ON cbam_cn_codes (cbam_sector)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_codes_status ON cbam_cn_codes (status)'
    )

    op.execute(
        """
CREATE TABLE cbam_cn_controlled_list_values (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES cbam_cn_code_datasets(id) ON DELETE RESTRICT,
    list_code VARCHAR(64) NOT NULL,
    value_code VARCHAR(128) NOT NULL,
    value_label VARCHAR(255) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cbam_cn_list_dataset_code_value
        UNIQUE (dataset_id, list_code, value_code),
    CONSTRAINT ck_cbam_cn_list_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED'))
)
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_list_dataset_id ON cbam_cn_controlled_list_values (dataset_id)'
    )
    op.execute(
        'CREATE INDEX ix_cbam_cn_list_list_code ON cbam_cn_controlled_list_values (list_code)'
    )

    op.execute(
        """
ALTER TABLE cbam_product_profile_versions
    ADD COLUMN product_name VARCHAR(255) NULL,
    ADD COLUMN cn_code_id UUID NULL
        REFERENCES cbam_cn_codes(id) ON DELETE RESTRICT,
    ADD COLUMN cn_normalized_code VARCHAR(32) NULL,
    ADD COLUMN cn_display_code VARCHAR(64) NULL,
    ADD COLUMN cn_description TEXT NULL,
    ADD COLUMN cn_sector VARCHAR(128) NULL,
    ADD COLUMN cn_dataset_code VARCHAR(64) NULL,
    ADD COLUMN cn_dataset_version VARCHAR(64) NULL,
    ADD COLUMN reducing_agent VARCHAR(128) NULL,
    ADD COLUMN steel_mill_identification_number VARCHAR(128) NULL,
    ADD COLUMN percent_mn NUMERIC(18, 8) NULL,
    ADD COLUMN percent_cr NUMERIC(18, 8) NULL,
    ADD COLUMN percent_ni NUMERIC(18, 8) NULL,
    ADD COLUMN percent_other_alloys NUMERIC(18, 8) NULL,
    ADD COLUMN percent_other_materials NUMERIC(18, 8) NULL,
    ADD COLUMN missing_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN validation_issues JSONB NOT NULL DEFAULT '[]'::jsonb
"""
    )
    # At most one active published version per organization + product.
    op.execute(
        """
CREATE UNIQUE INDEX uq_cbam_product_profile_one_active
ON cbam_product_profile_versions (organization_id, product_id)
WHERE status = 'active'
"""
    )
    op.execute(
        'CREATE INDEX ix_cbam_product_profile_cn_code_id '
        'ON cbam_product_profile_versions (cn_code_id)'
    )
    # Existing skeleton rows stay draft/not ready; no guessed CN codes.
    op.execute(
        """
UPDATE cbam_product_profile_versions
SET classification_ready = false,
    missing_requirements = '[
      {"code":"PRODUCT_NAME_REQUIRED","message":"Enter a product name."},
      {"code":"CN_CODE_REQUIRED","message":"Select a valid CN code."}
    ]'::jsonb,
    validation_issues = '[]'::jsonb
WHERE TRUE
"""
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS uq_cbam_product_profile_one_active')
    op.execute('DROP INDEX IF EXISTS ix_cbam_product_profile_cn_code_id')
    op.execute(
        """
ALTER TABLE cbam_product_profile_versions
    DROP COLUMN IF EXISTS product_name,
    DROP COLUMN IF EXISTS cn_code_id,
    DROP COLUMN IF EXISTS cn_normalized_code,
    DROP COLUMN IF EXISTS cn_display_code,
    DROP COLUMN IF EXISTS cn_description,
    DROP COLUMN IF EXISTS cn_sector,
    DROP COLUMN IF EXISTS cn_dataset_code,
    DROP COLUMN IF EXISTS cn_dataset_version,
    DROP COLUMN IF EXISTS reducing_agent,
    DROP COLUMN IF EXISTS steel_mill_identification_number,
    DROP COLUMN IF EXISTS percent_mn,
    DROP COLUMN IF EXISTS percent_cr,
    DROP COLUMN IF EXISTS percent_ni,
    DROP COLUMN IF EXISTS percent_other_alloys,
    DROP COLUMN IF EXISTS percent_other_materials,
    DROP COLUMN IF EXISTS missing_requirements,
    DROP COLUMN IF EXISTS validation_issues
"""
    )
    op.execute('DROP TABLE IF EXISTS cbam_cn_controlled_list_values')
    op.execute('DROP TABLE IF EXISTS cbam_cn_codes')
    op.execute('DROP TABLE IF EXISTS cbam_cn_code_datasets')
