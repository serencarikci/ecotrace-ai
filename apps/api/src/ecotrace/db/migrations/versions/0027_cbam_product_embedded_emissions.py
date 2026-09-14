"""CBAM Phase 10C: product embedded-emissions roll-up results + current pointer.

Revision ID: 0027_cbam_pee_rollup
Revises: 0026_cbam_purchased_precursor

The revision id is abbreviated because alembic_version.version_num is varchar(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0027_cbam_pee_rollup"
down_revision: str | None = "0026_cbam_purchased_precursor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE cbam_product_embedded_emissions_results (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    methodology_version VARCHAR(32) NOT NULL,
    workbook_filename VARCHAR(512) NOT NULL,
    workbook_sha256 VARCHAR(64) NOT NULL,
    workbook_formula_refs TEXT NOT NULL,
    client_request_id UUID NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    product_count INTEGER NOT NULL,
    precursor_contribution_count INTEGER NOT NULL,
    total_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_embedded_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_direct_tco2e NUMERIC(24, 8) NOT NULL,
    total_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    total_embedded_tco2e NUMERIC(24, 8) NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    specific_unit VARCHAR(32) NOT NULL,
    dea_source_unit VARCHAR(32) NOT NULL,
    workbook_gas VARCHAR(16) NOT NULL,
    workbook_gwp VARCHAR(16) NOT NULL,
    workbook_gwp_factor VARCHAR(16) NOT NULL,
    dea_result_id UUID,
    iea_result_id UUID,
    informational_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_pee_results PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pee_results_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_pee_results_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_results_dea
        FOREIGN KEY (dea_result_id)
        REFERENCES cbam_direct_emissions_allocation_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_results_iea
        FOREIGN KEY (iea_result_id)
        REFERENCES cbam_indirect_emissions_allocation_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_results_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_cbam_pee_results_status CHECK (status = 'COMPLETED'),
    CONSTRAINT ck_cbam_pee_results_unit CHECK (result_unit = 'tCO2e'),
    CONSTRAINT ck_cbam_pee_results_specific_unit CHECK (specific_unit = 'tCO2e/t'),
    CONSTRAINT ck_cbam_pee_results_dea_unit CHECK (dea_source_unit = 'tCO2'),
    CONSTRAINT ck_cbam_pee_results_counts CHECK (
        product_count >= 1 AND precursor_contribution_count >= 0
    )
);

CREATE UNIQUE INDEX uq_cbam_pee_result_org_binding_client_request
    ON cbam_product_embedded_emissions_results (
        organization_id, reporting_period_binding_id, client_request_id
    );
CREATE UNIQUE INDEX uq_cbam_pee_result_id_org_binding
    ON cbam_product_embedded_emissions_results (
        id, organization_id, reporting_period_binding_id
    );
CREATE INDEX ix_cbam_pee_results_org_binding
    ON cbam_product_embedded_emissions_results (
        organization_id, reporting_period_binding_id
    );
CREATE INDEX ix_cbam_pee_results_created_at
    ON cbam_product_embedded_emissions_results (created_at DESC, id DESC);

CREATE TABLE cbam_product_embedded_emissions_products (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    product_id UUID NOT NULL,
    product_profile_version_id UUID NOT NULL,
    profile_version INTEGER NOT NULL,
    cn_normalized_code VARCHAR(32),
    cn_display_code VARCHAR(64),
    product_name VARCHAR(255),
    process_id UUID NOT NULL,
    process_row_version INTEGER NOT NULL,
    process_produced_quantity NUMERIC(24, 8) NOT NULL,
    process_produced_quantity_unit VARCHAR(32) NOT NULL,
    denominator_tonnes NUMERIC(36, 18) NOT NULL,
    production_record_count INTEGER NOT NULL,
    production_records_tonnes NUMERIC(36, 18),
    production_record_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    dea_result_id UUID NOT NULL,
    dea_product_allocation_id UUID,
    dea_direct_tco2 NUMERIC(36, 18) NOT NULL,
    iea_result_id UUID NOT NULL,
    iea_product_allocation_id UUID,
    iea_indirect_tco2e NUMERIC(36, 18) NOT NULL,
    has_measurable_heat BOOLEAN,
    heat_attributed_tco2e NUMERIC(36, 18) NOT NULL,
    has_waste_gas BOOLEAN,
    waste_gas_attributed_tco2e NUMERIC(36, 18) NOT NULL,
    exported_electricity_direct_tco2e NUMERIC(36, 18) NOT NULL,
    exported_electricity_note_code VARCHAR(128) NOT NULL,
    own_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    own_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    precursor_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    precursor_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    total_embedded_tco2e_raw NUMERIC(36, 18) NOT NULL,
    own_direct_tco2e NUMERIC(24, 8) NOT NULL,
    own_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    precursor_direct_tco2e NUMERIC(24, 8) NOT NULL,
    precursor_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    total_direct_tco2e NUMERIC(24, 8) NOT NULL,
    total_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    total_embedded_tco2e NUMERIC(24, 8) NOT NULL,
    specific_direct_raw NUMERIC(36, 18) NOT NULL,
    specific_indirect_raw NUMERIC(36, 18) NOT NULL,
    specific_total_raw NUMERIC(36, 18) NOT NULL,
    specific_direct NUMERIC(24, 8) NOT NULL,
    specific_indirect NUMERIC(24, 8) NOT NULL,
    specific_total NUMERIC(24, 8) NOT NULL,
    precursor_contribution_count INTEGER NOT NULL,
    result_unit VARCHAR(32) NOT NULL,
    specific_unit VARCHAR(32) NOT NULL,
    dea_source_unit VARCHAR(32) NOT NULL,
    components_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_pee_products PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pee_products_result
        FOREIGN KEY (result_id)
        REFERENCES cbam_product_embedded_emissions_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_products_profile
        FOREIGN KEY (product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    -- process_id is a snapshot reference on purpose: draft processes stay editable and
    -- deletable after a roll-up, so no foreign key is declared against them.
    CONSTRAINT fk_cbam_pee_products_dea
        FOREIGN KEY (dea_result_id)
        REFERENCES cbam_direct_emissions_allocation_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_products_iea
        FOREIGN KEY (iea_result_id)
        REFERENCES cbam_indirect_emissions_allocation_results (id) ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_pee_products_result_profile
        UNIQUE (result_id, product_profile_version_id),
    CONSTRAINT uq_cbam_pee_products_id_result UNIQUE (id, result_id),
    CONSTRAINT ck_cbam_pee_products_unit CHECK (result_unit = 'tCO2e'),
    CONSTRAINT ck_cbam_pee_products_specific_unit CHECK (specific_unit = 'tCO2e/t'),
    CONSTRAINT ck_cbam_pee_products_dea_unit CHECK (dea_source_unit = 'tCO2'),
    CONSTRAINT ck_cbam_pee_products_denominator_positive CHECK (denominator_tonnes > 0),
    CONSTRAINT ck_cbam_pee_products_exported_electricity_zero
        CHECK (exported_electricity_direct_tco2e = 0),
    CONSTRAINT ck_cbam_pee_products_counts CHECK (
        precursor_contribution_count >= 0 AND production_record_count >= 0
    )
);

CREATE INDEX ix_cbam_pee_products_result
    ON cbam_product_embedded_emissions_products (result_id);
CREATE INDEX ix_cbam_pee_products_profile
    ON cbam_product_embedded_emissions_products (product_profile_version_id);
CREATE INDEX ix_cbam_pee_products_process
    ON cbam_product_embedded_emissions_products (process_id);
CREATE INDEX ix_cbam_pee_products_org_binding
    ON cbam_product_embedded_emissions_products (
        organization_id, reporting_period_binding_id
    );

CREATE TABLE cbam_product_embedded_emissions_precursor_contributions (
    id UUID NOT NULL,
    result_id UUID NOT NULL,
    product_row_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    product_profile_version_id UUID NOT NULL,
    precursor_id UUID NOT NULL,
    precursor_row_version INTEGER NOT NULL,
    precursor_name VARCHAR(255),
    precursor_cn_normalized_code VARCHAR(32),
    precursor_cn_display_code VARCHAR(64),
    data_source_mode VARCHAR(32) NOT NULL,
    value_source VARCHAR(64) NOT NULL,
    product_use_id UUID NOT NULL,
    product_use_row_version INTEGER NOT NULL,
    product_use_quantity NUMERIC(24, 8) NOT NULL,
    product_use_unit VARCHAR(32) NOT NULL,
    quantity_tonnes NUMERIC(36, 18) NOT NULL,
    specific_direct NUMERIC(36, 18) NOT NULL,
    specific_indirect NUMERIC(36, 18) NOT NULL,
    contribution_direct_tco2e_raw NUMERIC(36, 18) NOT NULL,
    contribution_indirect_tco2e_raw NUMERIC(36, 18) NOT NULL,
    contribution_direct_tco2e NUMERIC(24, 8) NOT NULL,
    contribution_indirect_tco2e NUMERIC(24, 8) NOT NULL,
    default_dataset_id UUID,
    default_value_id UUID,
    default_snapshot_json JSONB,
    result_unit VARCHAR(32) NOT NULL,
    specific_unit VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_pee_precursor_contributions PRIMARY KEY (id),
    CONSTRAINT fk_cbam_pee_contrib_result
        FOREIGN KEY (result_id)
        REFERENCES cbam_product_embedded_emissions_results (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_contrib_product_row
        FOREIGN KEY (product_row_id, result_id)
        REFERENCES cbam_product_embedded_emissions_products (id, result_id)
        ON DELETE RESTRICT,
    -- precursor_id / product_use_id are snapshot references: purchased precursors and
    -- their product uses remain freely editable and deletable after a roll-up.
    CONSTRAINT fk_cbam_pee_contrib_profile
        FOREIGN KEY (product_profile_version_id)
        REFERENCES cbam_product_profile_versions (id) ON DELETE RESTRICT,
    CONSTRAINT uq_cbam_pee_contrib_result_use UNIQUE (result_id, product_use_id),
    CONSTRAINT ck_cbam_pee_contrib_unit CHECK (result_unit = 'tCO2e'),
    CONSTRAINT ck_cbam_pee_contrib_specific_unit CHECK (specific_unit = 'tCO2e/t'),
    CONSTRAINT ck_cbam_pee_contrib_qty_nonneg CHECK (quantity_tonnes >= 0),
    CONSTRAINT ck_cbam_pee_contrib_mode
        CHECK (data_source_mode IN ('SUPPLIER_DATA', 'EU_DEFAULT'))
);

CREATE INDEX ix_cbam_pee_contrib_result
    ON cbam_product_embedded_emissions_precursor_contributions (result_id);
CREATE INDEX ix_cbam_pee_contrib_product_row
    ON cbam_product_embedded_emissions_precursor_contributions (product_row_id);
CREATE INDEX ix_cbam_pee_contrib_precursor
    ON cbam_product_embedded_emissions_precursor_contributions (precursor_id);
CREATE INDEX ix_cbam_pee_contrib_product_use
    ON cbam_product_embedded_emissions_precursor_contributions (product_use_id);

CREATE TABLE cbam_product_embedded_emissions_current (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    methodology_code VARCHAR(128) NOT NULL,
    current_result_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_cbam_pee_current PRIMARY KEY (id),
    CONSTRAINT uq_cbam_pee_current_org_binding_method UNIQUE (
        organization_id, reporting_period_binding_id, methodology_code
    ),
    CONSTRAINT fk_cbam_pee_current_org
        FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_cbam_pee_current_binding
        FOREIGN KEY (reporting_period_binding_id)
        REFERENCES cbam_reporting_period_bindings (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cbam_pee_current_result_identity FOREIGN KEY (
        current_result_id, organization_id, reporting_period_binding_id
    ) REFERENCES cbam_product_embedded_emissions_results (
        id, organization_id, reporting_period_binding_id
    ) ON DELETE RESTRICT
);

CREATE INDEX ix_cbam_pee_current_result
    ON cbam_product_embedded_emissions_current (current_result_id);
"""
    )


def downgrade() -> None:
    op.execute(
        """
DROP TABLE IF EXISTS cbam_product_embedded_emissions_current;
DROP TABLE IF EXISTS cbam_product_embedded_emissions_precursor_contributions;
DROP TABLE IF EXISTS cbam_product_embedded_emissions_products;
DROP TABLE IF EXISTS cbam_product_embedded_emissions_results;
"""
    )
