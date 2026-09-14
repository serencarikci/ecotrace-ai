"""CBAM Phase 10D: product embedded-emissions V2 internal product flows + T72.

Revision ID: 0029_cbam_pee_v2
Revises: 0028_cbam_process_exp_elec

Additive only. Historical V1 result rows are never rewritten: the new columns default to
zero / NULL and the "exported electricity must be zero" CHECK is dropped (not relaxed)
because V2 rows legitimately carry the negative workbook T72 term while every V1 row
already stores 0.

The revision id is abbreviated because alembic_version.version_num is varchar(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029_cbam_pee_v2"
down_revision: str | None = "0028_cbam_process_exp_elec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE cbam_product_embedded_emissions_results
    ADD COLUMN internal_contribution_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE cbam_product_embedded_emissions_results
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_results_counts;
ALTER TABLE cbam_product_embedded_emissions_results
    ADD CONSTRAINT ck_cbam_pee_results_counts CHECK (
        product_count >= 1
        AND precursor_contribution_count >= 0
        AND internal_contribution_count >= 0
    );

ALTER TABLE cbam_product_embedded_emissions_products
    ADD COLUMN has_exported_electricity BOOLEAN,
    ADD COLUMN exported_electricity_mwh NUMERIC(36, 18),
    ADD COLUMN exported_electricity_emission_factor NUMERIC(36, 18),
    ADD COLUMN internal_direct_tco2e_raw NUMERIC(36, 18) NOT NULL DEFAULT 0,
    ADD COLUMN internal_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL DEFAULT 0,
    ADD COLUMN internal_direct_tco2e NUMERIC(24, 8) NOT NULL DEFAULT 0,
    ADD COLUMN internal_indirect_tco2e NUMERIC(24, 8) NOT NULL DEFAULT 0,
    ADD COLUMN internal_contribution_count INTEGER NOT NULL DEFAULT 0;

-- V1 rows are all exactly 0; V2 rows carry T72 = -L71*L72 which is zero or negative.
ALTER TABLE cbam_product_embedded_emissions_products
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_products_exported_electricity_zero;
ALTER TABLE cbam_product_embedded_emissions_products
    ADD CONSTRAINT ck_cbam_pee_products_exported_electricity_nonpos
        CHECK (exported_electricity_direct_tco2e <= 0);

ALTER TABLE cbam_product_embedded_emissions_products
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_products_counts;
ALTER TABLE cbam_product_embedded_emissions_products
    ADD CONSTRAINT ck_cbam_pee_products_counts CHECK (
        precursor_contribution_count >= 0
        AND production_record_count >= 0
        AND internal_contribution_count >= 0
    );

CREATE TABLE cbam_product_embedded_emissions_internal_contributions (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    product_row_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    consumer_product_profile_version_id UUID NOT NULL,
    supplier_product_profile_version_id UUID NOT NULL,
    consumer_process_id UUID NOT NULL,
    supplier_process_id UUID NOT NULL,
    supplier_process_row_version INTEGER NOT NULL,
    product_use_id UUID NOT NULL,
    product_use_row_version INTEGER NOT NULL,
    product_use_quantity NUMERIC(24, 8) NOT NULL,
    product_use_unit VARCHAR(32) NOT NULL,
    quantity_tonnes NUMERIC(36, 18) NOT NULL,
    consumer_denominator_tonnes NUMERIC(36, 18) NOT NULL,
    a_coefficient NUMERIC(36, 18) NOT NULL,
    supplier_specific_direct NUMERIC(36, 18) NOT NULL,
    supplier_specific_indirect NUMERIC(36, 18) NOT NULL,
    contribution_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    contribution_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    contribution_direct_tco2e NUMERIC(24, 8) NOT NULL,
    contribution_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    specific_unit VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_pee_internal_contributions PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pee_internal_result
        FOREIGN KEY (result_id)
        REFERENCES cbam_product_embedded_emissions_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_internal_product_row
        FOREIGN KEY (product_row_id, result_id)
        REFERENCES cbam_product_embedded_emissions_products (id, result_id)
        ON DELETE RESTRICT,
    -- Process and product-use ids are snapshot references: drafts stay editable.
    CONSTRAINT fk_cbam_pee_internal_consumer_profile
        FOREIGN KEY (consumer_product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_internal_supplier_profile
        FOREIGN KEY (supplier_product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_pee_internal_result_use UNIQUE (result_id, product_use_id),
    CONSTRAINT ck_cbam_pee_internal_unit CHECK (result_unit = 'tCO2e'),
    CONSTRAINT ck_cbam_pee_internal_specific_unit CHECK (specific_unit = 'tCO2e/t'),
    CONSTRAINT ck_cbam_pee_internal_qty_nonneg CHECK (quantity_tonnes >= 0),
    CONSTRAINT ck_cbam_pee_internal_denominator_positive
        CHECK (consumer_denominator_tonnes > 0),
    CONSTRAINT ck_cbam_pee_internal_no_self_reference
        CHECK (consumer_product_profile_version_id <> supplier_product_profile_version_id)
);

CREATE INDEX ix_cbam_pee_internal_result
    ON cbam_product_embedded_emissions_internal_contributions (result_id);
CREATE INDEX ix_cbam_pee_internal_product_row
    ON cbam_product_embedded_emissions_internal_contributions (product_row_id);
CREATE INDEX ix_cbam_pee_internal_supplier_profile
    ON cbam_product_embedded_emissions_internal_contributions (
        supplier_product_profile_version_id
    );
CREATE INDEX ix_cbam_pee_internal_product_use
    ON cbam_product_embedded_emissions_internal_contributions (product_use_id);
"""
    )


def downgrade() -> None:
    op.execute(
        """
DROP TABLE IF EXISTS cbam_product_embedded_emissions_internal_contributions;

ALTER TABLE cbam_product_embedded_emissions_products
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_products_counts;
ALTER TABLE cbam_product_embedded_emissions_products
    ADD CONSTRAINT ck_cbam_pee_products_counts CHECK (
        precursor_contribution_count >= 0 AND production_record_count >= 0
    );

ALTER TABLE cbam_product_embedded_emissions_products
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_products_exported_electricity_nonpos;
ALTER TABLE cbam_product_embedded_emissions_products
    ADD CONSTRAINT ck_cbam_pee_products_exported_electricity_zero
        CHECK (exported_electricity_direct_tco2e = 0);

ALTER TABLE cbam_product_embedded_emissions_products
    DROP COLUMN IF EXISTS internal_contribution_count,
    DROP COLUMN IF EXISTS internal_indirect_tco2e,
    DROP COLUMN IF EXISTS internal_direct_tco2e,
    DROP COLUMN IF EXISTS internal_indirect_tco2e_raw,
    DROP COLUMN IF EXISTS internal_direct_tco2e_raw,
    DROP COLUMN IF EXISTS exported_electricity_emission_factor,
    DROP COLUMN IF EXISTS exported_electricity_mwh,
    DROP COLUMN IF EXISTS has_exported_electricity;

ALTER TABLE cbam_product_embedded_emissions_results
    DROP CONSTRAINT IF EXISTS ck_cbam_pee_results_counts;
ALTER TABLE cbam_product_embedded_emissions_results
    ADD CONSTRAINT ck_cbam_pee_results_counts CHECK (
        product_count >= 1 AND precursor_contribution_count >= 0
    );

ALTER TABLE cbam_product_embedded_emissions_results
    DROP COLUMN IF EXISTS internal_contribution_count;
"""
    )
