"""CBAM Phase 10A: purchased precursors + EU default-value catalog.

Revision ID: 0026_cbam_purchased_precursor
Revises: 0025_cbam_production_process
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0026_cbam_purchased_precursor'
down_revision: str | None = '0025_cbam_production_process'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_precursor_default_datasets (
    id UUID NOT NULL,
    dataset_code VARCHAR(64) NOT NULL,
    dataset_version VARCHAR(64) NOT NULL,
    content_checksum VARCHAR(64) NOT NULL,
    source_workbook_name VARCHAR(512) NOT NULL,
    source_workbook_sha256 VARCHAR(64) NOT NULL,
    source_template_version VARCHAR(32) NOT NULL,
    regulation_reference VARCHAR(512),
    valid_from DATE NOT NULL,
    valid_until DATE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    value_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_precursor_default_datasets PRIMARY KEY (id),
    CONSTRAINT uq_cbam_precursor_dv_dataset_code_version
        UNIQUE (dataset_code, dataset_version),
    CONSTRAINT ck_cbam_precursor_dv_dataset_status
        CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')),
    CONSTRAINT ck_cbam_precursor_dv_dataset_dates
        CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CONSTRAINT ck_cbam_precursor_dv_dataset_value_count
        CHECK (value_count >= 0)
);

CREATE INDEX ix_cbam_precursor_dv_datasets_status
    ON cbam_precursor_default_datasets (status);

CREATE TABLE cbam_precursor_default_values (
    id UUID NOT NULL,
    dataset_id UUID NOT NULL,
    country_name VARCHAR(255) NOT NULL,
    source_sheet VARCHAR(128) NOT NULL,
    source_row INTEGER NOT NULL,
    is_other_countries_group BOOLEAN NOT NULL DEFAULT FALSE,
    cn_normalized_code VARCHAR(32) NOT NULL,
    cn_display_code VARCHAR(64),
    goods_category VARCHAR(128),
    goods_description VARCHAR(512),
    production_route VARCHAR(64),
    direct_value NUMERIC(24, 8),
    direct_value_status VARCHAR(32) NOT NULL,
    indirect_value NUMERIC(24, 8),
    indirect_value_status VARCHAR(32) NOT NULL,
    total_value NUMERIC(24, 8),
    total_value_status VARCHAR(32) NOT NULL,
    direct_unit VARCHAR(32),
    indirect_unit VARCHAR(32),
    total_unit VARCHAR(32),
    unit_note TEXT,
    marked_up_totals_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    original_keys_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lookup_key VARCHAR(512) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_precursor_default_values PRIMARY KEY (id),
    CONSTRAINT fk_cbam_precursor_dv_values_dataset
        FOREIGN KEY (dataset_id) REFERENCES cbam_precursor_default_datasets(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_cbam_precursor_dv_values_dataset_source
        UNIQUE (dataset_id, source_sheet, source_row),
    CONSTRAINT ck_cbam_precursor_dv_source_row CHECK (source_row >= 1)
);

CREATE INDEX ix_cbam_precursor_dv_values_dataset ON cbam_precursor_default_values (dataset_id);
CREATE INDEX ix_cbam_precursor_dv_values_lookup ON cbam_precursor_default_values (dataset_id, lookup_key);
CREATE INDEX ix_cbam_precursor_dv_values_country_cn
    ON cbam_precursor_default_values (dataset_id, country_name, cn_normalized_code);

CREATE TABLE cbam_purchased_precursors (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    installation_profile_id UUID NOT NULL,
    purchased_input_record_id UUID,
    supplier_id UUID,
    name VARCHAR(255),
    identifier VARCHAR(128),
    aggregated_goods_category VARCHAR(128),
    cn_normalized_code VARCHAR(32),
    cn_display_code VARCHAR(64),
    country_of_origin VARCHAR(255),
    production_route VARCHAR(64),
    data_source_mode VARCHAR(32) NOT NULL,
    quantity NUMERIC(24, 8),
    quantity_unit VARCHAR(32),
    non_cbam_quantity NUMERIC(24, 8),
    non_cbam_quantity_unit VARCHAR(32),
    specific_direct_embedded_emissions NUMERIC(24, 8),
    specific_direct_unit VARCHAR(32),
    specific_direct_source_code VARCHAR(64),
    electricity_consumption_intensity NUMERIC(24, 8),
    electricity_intensity_unit VARCHAR(32),
    electricity_intensity_source_code VARCHAR(64),
    electricity_emission_factor NUMERIC(24, 8),
    electricity_ef_unit VARCHAR(32),
    electricity_ef_source_code VARCHAR(64),
    specific_indirect_embedded_emissions NUMERIC(24, 8),
    specific_indirect_unit VARCHAR(32),
    default_justification_code VARCHAR(128),
    provenance_notes TEXT,
    evidence_reference TEXT,
    default_dataset_id UUID,
    default_value_id UUID,
    default_snapshot_json JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_purchased_precursors PRIMARY KEY (id),
    CONSTRAINT fk_cbam_purch_prec_org FOREIGN KEY (organization_id)
        REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_purch_prec_binding FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_installation FOREIGN KEY (installation_profile_id)
        REFERENCES cbam_installation_profiles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_purchased_input FOREIGN KEY (purchased_input_record_id)
        REFERENCES cbam_purchased_input_records(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_supplier FOREIGN KEY (supplier_id)
        REFERENCES suppliers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_default_dataset FOREIGN KEY (default_dataset_id)
        REFERENCES cbam_precursor_default_datasets(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_default_value FOREIGN KEY (default_value_id)
        REFERENCES cbam_precursor_default_values(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_created_by FOREIGN KEY (created_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_purch_prec_updated_by FOREIGN KEY (updated_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_purch_prec_status CHECK (status IN ('draft', 'archived')),
    CONSTRAINT ck_cbam_purch_prec_mode
        CHECK (data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT')),
    CONSTRAINT ck_cbam_purch_prec_row_version CHECK (row_version >= 1),
    CONSTRAINT ck_cbam_purch_prec_qty_nonneg CHECK (quantity IS NULL OR quantity >= 0),
    CONSTRAINT ck_cbam_purch_prec_non_cbam_nonneg
        CHECK (non_cbam_quantity IS NULL OR non_cbam_quantity >= 0)
);

CREATE INDEX ix_cbam_purch_prec_org ON cbam_purchased_precursors (organization_id);
CREATE INDEX ix_cbam_purch_prec_org_binding
    ON cbam_purchased_precursors (organization_id, reporting_period_binding_id);
CREATE INDEX ix_cbam_purch_prec_status ON cbam_purchased_precursors (status);
CREATE INDEX ix_cbam_purch_prec_supplier ON cbam_purchased_precursors (supplier_id);
CREATE INDEX ix_cbam_purch_prec_cn ON cbam_purchased_precursors (cn_normalized_code);

CREATE TABLE cbam_purchased_precursor_product_uses (
    id UUID NOT NULL,
    precursor_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    target_product_profile_version_id UUID NOT NULL,
    quantity NUMERIC(24, 8) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_purchased_precursor_product_uses PRIMARY KEY (id),
    CONSTRAINT fk_cbam_purch_prec_use_precursor FOREIGN KEY (precursor_id)
        REFERENCES cbam_purchased_precursors(id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_purch_prec_use_org FOREIGN KEY (organization_id)
        REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_purch_prec_use_binding FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_use_target FOREIGN KEY (target_product_profile_version_id)
        REFERENCES cbam_product_profile_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_purch_prec_use_created_by FOREIGN KEY (created_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_cbam_purch_prec_use_updated_by FOREIGN KEY (updated_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_cbam_purch_prec_use_target
        UNIQUE (precursor_id, target_product_profile_version_id),
    CONSTRAINT ck_cbam_purch_prec_use_qty_nonneg CHECK (quantity >= 0),
    CONSTRAINT ck_cbam_purch_prec_use_row_version CHECK (row_version >= 1)
);

CREATE INDEX ix_cbam_purch_prec_use_precursor
    ON cbam_purchased_precursor_product_uses (precursor_id);
CREATE INDEX ix_cbam_purch_prec_use_target
    ON cbam_purchased_precursor_product_uses (target_product_profile_version_id);
"""
    )


def downgrade() -> None:
    op.execute(
        """
DROP TABLE IF EXISTS cbam_purchased_precursor_product_uses;
DROP TABLE IF EXISTS cbam_purchased_precursors;
DROP TABLE IF EXISTS cbam_precursor_default_values;
DROP TABLE IF EXISTS cbam_precursor_default_datasets;
"""
    )
