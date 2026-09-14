"""Phase 10C roll-up service: readiness, execution, snapshots and blocking codes."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from tests.cbam_pee_helpers import (
    ACTIVITY_DAY,
    GOLDEN_PRECURSOR_DIRECT_TCO2E,
    GOLDEN_PRECURSOR_INDIRECT_TCO2E,
    PRECURSOR_SPECIFIC_DIRECT,
    PRECURSOR_SPECIFIC_INDIRECT,
    PRECURSOR_USE_TONNES,
    create_ready_precursor,
    create_ready_process,
    seed_allocations,
    seed_ready_rollup,
)
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError
from ecotrace.modules.cbam.application import (
    product_embedded_emissions_service as pee,
)
from ecotrace.modules.cbam.application import (
    production_process_service,
    production_record_service,
    purchased_precursor_service,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    CODE_NO_ELIGIBLE_PRODUCTS,
    CODE_PRECURSOR_NOT_READY,
    CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT,
    CODE_PROCESS_MISSING_FOR_PRODUCT,
    CODE_PROCESS_NOT_READY,
    CODE_PRODUCT_DENOMINATOR_MISMATCH,
    EXPORTED_ELECTRICITY_NOTE_CODE,
    EXPORTED_ELECTRICITY_NOTE_CODE_V2,
    INTERNAL_PRECURSOR_NOTE_CODE,
    INTERNAL_PRECURSOR_NOTE_CODE_V2,
    METHODOLOGY_CODE,
    METHODOLOGY_CODE_V2,
    RESULT_UNIT_TCO2E,
    SPECIFIC_UNIT_TCO2E_PER_T,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ProductionProcessCreate,
    ProductionProcessUpdate,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseCreate,
    PurchasedPrecursorCreate,
    PurchasedPrecursorUpdate,
)


def _execute(db: Session, scenario: object, *, methodology_code: str = METHODOLOGY_CODE) -> object:
    return pee.execute_product_embedded_emissions(
        db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(
            client_request_id=uuid.uuid4(),
            methodology_code=methodology_code,
        ),
    )


def _readiness(
    db: Session, scenario: object, *, methodology_code: str = METHODOLOGY_CODE
) -> object:
    return pee.get_product_embedded_emissions_readiness(
        db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        methodology_code=methodology_code,
    )


def test_readiness_is_ready_for_a_fully_seeded_binding(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    readiness = _readiness(seeded_db, scenario)

    assert readiness.rollup_ready is True
    assert readiness.status == 'READY'
    assert readiness.blocking_issue_codes == []
    assert readiness.methodology_code == METHODOLOGY_CODE
    assert readiness.eligible_product_count == 1
    assert readiness.blocked_product_count == 0
    assert readiness.precursor_contribution_count == 1
    assert readiness.direct_emissions_allocation_result_id is not None
    assert readiness.indirect_emissions_allocation_result_id is not None
    assert readiness.direct_emissions_allocation_stale is False
    assert readiness.indirect_emissions_allocation_stale is False
    assert readiness.current_result_id is None
    assert readiness.exported_electricity_note_code == EXPORTED_ELECTRICITY_NOTE_CODE
    assert readiness.internal_precursor_note_code == INTERNAL_PRECURSOR_NOTE_CODE

    product = readiness.products[0]
    assert product.product_profile_version_id == scenario.profile_id
    assert product.process_id == scenario.process_id
    assert product.status == 'READY'
    assert product.denominator_tonnes == scenario.denominator_tonnes
    assert product.production_records_tonnes == scenario.denominator_tonnes


def test_execute_persists_totals_specifics_and_identities(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    execution = _execute(seeded_db, scenario)

    assert execution.status == 'COMPLETED'
    assert execution.idempotent_replay is False
    assert execution.product_count == 1
    assert execution.precursor_contribution_count == 1
    assert execution.result_unit == RESULT_UNIT_TCO2E
    assert execution.specific_unit == SPECIFIC_UNIT_TCO2E_PER_T

    detail = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        execution.result_id,
    )
    assert detail.is_current is True
    assert detail.is_stale is False
    assert detail.workbook_sha256 == WORKBOOK_SHA256
    assert len(detail.products) == 1
    assert len(detail.precursor_contributions) == 1

    row = detail.products[0]
    own_direct = Decimal(row['ownDirectTco2eRaw'])
    own_indirect = Decimal(row['ownIndirectTco2eRaw'])
    precursor_direct = Decimal(row['precursorDirectTco2eRaw'])
    precursor_indirect = Decimal(row['precursorIndirectTco2eRaw'])
    total_direct = Decimal(row['totalDirectTco2eRaw'])
    total_indirect = Decimal(row['totalIndirectTco2eRaw'])
    total_embedded = Decimal(row['totalEmbeddedTco2eRaw'])
    denominator = Decimal(row['denominatorTonnes'])

    # own_direct = T54 + T58 + T62 + T72 with heat/waste/export all zero here.
    assert own_direct == Decimal(row['deaDirectTco2'])
    assert Decimal(row['heatAttributedTco2e']) == Decimal('0')
    assert Decimal(row['wasteGasAttributedTco2e']) == Decimal('0')
    assert Decimal(row['exportedElectricityDirectTco2e']) == Decimal('0')
    assert row['exportedElectricityNoteCode'] == EXPORTED_ELECTRICITY_NOTE_CODE
    assert own_indirect == Decimal(row['ieaIndirectTco2e'])

    assert precursor_direct == GOLDEN_PRECURSOR_DIRECT_TCO2E
    assert precursor_indirect == GOLDEN_PRECURSOR_INDIRECT_TCO2E
    assert total_direct == own_direct + precursor_direct
    assert total_indirect == own_indirect + precursor_indirect
    assert total_embedded == total_direct + total_indirect

    assert Decimal(row['specificDirectRaw']) == total_direct / denominator
    assert Decimal(row['specificIndirectRaw']) == total_indirect / denominator
    assert Decimal(row['specificTotalRaw']) == total_embedded / denominator
    assert row['specificUnit'] == SPECIFIC_UNIT_TCO2E_PER_T
    assert row['deaSourceUnit'] == 'tCO2'

    # The denominator is the process produced quantity, never the marketed quantity.
    assert row['components']['denominator']['source'] == 'PROCESS_PRODUCED_QUANTITY'
    assert Decimal(row['processProducedQuantity']) == scenario.denominator_tonnes

    contribution = detail.precursor_contributions[0]
    assert Decimal(contribution['quantityTonnes']) == PRECURSOR_USE_TONNES
    assert Decimal(contribution['specificDirect']) == PRECURSOR_SPECIFIC_DIRECT
    assert Decimal(contribution['specificIndirect']) == PRECURSOR_SPECIFIC_INDIRECT
    assert Decimal(contribution['contributionDirectTco2eRaw']) == GOLDEN_PRECURSOR_DIRECT_TCO2E
    assert (
        Decimal(contribution['contributionIndirectTco2eRaw']) == GOLDEN_PRECURSOR_INDIRECT_TCO2E
    )
    assert contribution['dataSourceMode'] == 'SUPPLIER_DATA'


def test_binding_totals_equal_the_sum_of_product_rows(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    execution = _execute(seeded_db, scenario)
    detail = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        execution.result_id,
    )
    assert detail.total_direct_tco2e_raw == sum(
        Decimal(p['totalDirectTco2eRaw']) for p in detail.products
    )
    assert detail.total_indirect_tco2e_raw == sum(
        Decimal(p['totalIndirectTco2eRaw']) for p in detail.products
    )
    assert (
        detail.total_embedded_tco2e_raw
        == detail.total_direct_tco2e_raw + detail.total_indirect_tco2e_raw
    )


def test_summary_and_listing_expose_the_current_pointer(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    execution = _execute(seeded_db, scenario)

    summary = pee.get_product_embedded_emissions_summary(
        seeded_db, scenario.user, scenario.organization.id, scenario.binding.id
    )
    assert summary.current_result_id == execution.result_id
    assert summary.current_is_stale is False
    assert summary.product_count == 1
    assert summary.total_embedded_tco2e == execution.total_embedded_tco2e
    assert len(summary.totals_by_product) == 1

    listing = pee.list_product_embedded_emissions_results(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        page=1,
        page_size=20,
    )
    assert listing.total_items == 1
    assert listing.items[0].result_id == execution.result_id
    assert listing.items[0].is_current is True
    assert listing.items[0].is_stale is False


def test_summary_is_empty_before_any_execution(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    summary = pee.get_product_embedded_emissions_summary(
        seeded_db, scenario.user, scenario.organization.id, scenario.binding.id
    )
    assert summary.current_result_id is None
    assert summary.product_count is None
    assert summary.totals_by_product == []
    assert summary.result_unit == RESULT_UNIT_TCO2E


def test_unknown_result_id_is_not_found(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    with pytest.raises(NotFoundError):
        pee.get_product_embedded_emissions_result(
            seeded_db,
            scenario.user,
            scenario.organization.id,
            scenario.binding.id,
            uuid.uuid4(),
        )


def test_execution_without_allocations_fails_closed(seeded_db: Session) -> None:
    from tests.cbam_dea_helpers import admin, org, setup_binding

    user = admin(seeded_db)
    organization = org(seeded_db)
    binding, _ = setup_binding(seeded_db, user, organization)
    seeded_db.commit()

    readiness = pee.get_product_embedded_emissions_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.rollup_ready is False
    assert 'DIRECT_EMISSIONS_ALLOCATION_NOT_READY' in readiness.blocking_issue_codes
    assert 'INDIRECT_EMISSIONS_ALLOCATION_NOT_READY' in readiness.blocking_issue_codes
    assert CODE_NO_ELIGIBLE_PRODUCTS in readiness.blocking_issue_codes

    with pytest.raises(BusinessRuleError) as excinfo:
        pee.execute_product_embedded_emissions(
            seeded_db,
            user,
            organization.id,
            binding.id,
            pee.ProductEmbeddedEmissionsExecuteRequest(client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE),
        )
    codes = {d['code'] for d in excinfo.value.details}
    assert CODE_NO_ELIGIBLE_PRODUCTS in codes


def test_two_processes_for_one_product_block_as_ambiguous(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    create_ready_process(
        seeded_db,
        scenario.user,
        scenario.organization,
        scenario.binding,
        scenario.installation,
        scenario.profile_id,
    )
    seeded_db.commit()

    readiness = _readiness(seeded_db, scenario)
    assert readiness.rollup_ready is False
    assert CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT in readiness.blocking_issue_codes
    assert readiness.products[0].process_id is None
    assert readiness.eligible_product_count == 0


def test_precursor_use_without_a_process_blocks(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    other_product = ensure_org_product(
        seeded_db, scenario.organization.id, code=f'PEE-X-{uuid.uuid4().hex[:6]}'
    )
    other_profile = create_active_ready_profile(
        seeded_db, scenario.user, scenario.organization.id, product=other_product
    )
    create_ready_precursor(
        seeded_db,
        scenario.user,
        scenario.organization,
        scenario.binding,
        scenario.installation,
        other_profile.id,
    )
    seeded_db.commit()

    readiness = _readiness(seeded_db, scenario)
    assert readiness.rollup_ready is False
    assert CODE_PROCESS_MISSING_FOR_PRODUCT in readiness.blocking_issue_codes
    blocked = [row for row in readiness.products if row.process_id is None]
    assert blocked and blocked[0].blocking_issue_codes == [CODE_PROCESS_MISSING_FOR_PRODUCT]


def test_unbalanced_precursor_blocks_the_product(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    precursor = purchased_precursor_service.get_purchased_precursor(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
    )
    # Purchased quantity no longer equals non-CBAM + product uses → precursor NOT READY.
    purchased_precursor_service.update_purchased_precursor_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.precursor_id,
        PurchasedPrecursorUpdate(row_version=precursor.row_version, quantity=Decimal('9')),
    )
    seeded_db.commit()

    readiness = _readiness(seeded_db, scenario)
    assert readiness.rollup_ready is False
    assert CODE_PRECURSOR_NOT_READY in readiness.blocking_issue_codes


def test_production_record_sum_mismatch_blocks_the_denominator(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    production_record_service.create_production_record(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        ProductionRecordCreate(
            installation_profile_id=scenario.installation.id,
            product_profile_version_id=scenario.profile_id,
            quantity=Decimal('1'),
            unit='t',
            production_date=ACTIVITY_DAY,
        ),
    )
    seeded_db.commit()

    readiness = _readiness(seeded_db, scenario)
    assert readiness.rollup_ready is False
    assert CODE_PRODUCT_DENOMINATOR_MISMATCH in readiness.blocking_issue_codes


def test_process_without_produced_quantity_is_not_ready(seeded_db: Session) -> None:
    user, organization, binding, installation, profile_id = _fresh_allocations(seeded_db)
    process = production_process_service.create_production_process(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name='Incomplete process',
            product_profile_version_id=profile_id,
        ),
    )
    seeded_db.commit()

    readiness = pee.get_product_embedded_emissions_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.rollup_ready is False
    assert CODE_PROCESS_NOT_READY in readiness.blocking_issue_codes
    assert readiness.products[0].process_id == process.id
    assert readiness.eligible_product_count == 0


def test_product_without_precursors_rolls_up_own_emissions_only(seeded_db: Session) -> None:
    user, organization, binding, installation, profile_id = _fresh_allocations(seeded_db)
    create_ready_process(seeded_db, user, organization, binding, installation, profile_id)
    seeded_db.commit()

    execution = pee.execute_product_embedded_emissions(
        seeded_db,
        user,
        organization.id,
        binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE),
    )
    assert execution.precursor_contribution_count == 0

    detail = pee.get_product_embedded_emissions_result(
        seeded_db, user, organization.id, binding.id, execution.result_id
    )
    row = detail.products[0]
    assert Decimal(row['precursorDirectTco2eRaw']) == Decimal('0')
    assert Decimal(row['precursorIndirectTco2eRaw']) == Decimal('0')
    assert Decimal(row['totalDirectTco2eRaw']) == Decimal(row['ownDirectTco2eRaw'])
    assert Decimal(row['totalIndirectTco2eRaw']) == Decimal(row['ownIndirectTco2eRaw'])
    assert detail.precursor_contributions == []


def test_precursor_use_targeting_another_product_is_excluded(seeded_db: Session) -> None:
    """Only the uses that target the product itself contribute to that product."""
    user, organization, binding, installation, profile_id = _fresh_allocations(seeded_db)
    create_ready_process(seeded_db, user, organization, binding, installation, profile_id)
    other_product = ensure_org_product(
        seeded_db, organization.id, code=f'PEE-O-{uuid.uuid4().hex[:6]}'
    )
    other_profile = create_active_ready_profile(
        seeded_db, user, organization.id, product=other_product
    )
    production_process_service.create_production_process(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name='Other product process',
            product_profile_version_id=other_profile.id,
            produced_quantity=Decimal('4'),
            produced_quantity_unit='t',
            marketed_quantity=Decimal('4'),
            marketed_quantity_unit='t',
            non_cbam_quantity=Decimal('0'),
            non_cbam_quantity_unit='t',
            has_measurable_heat=False,
            has_waste_gas=False,
        ),
    )
    # One purchased precursor split across both products.
    precursor = purchased_precursor_service.create_purchased_precursor(
        seeded_db,
        user,
        organization.id,
        binding.id,
        PurchasedPrecursorCreate(
            installation_profile_id=installation.id,
            data_source_mode='SUPPLIER_DATA',
            name='Shared precursor',
            quantity=Decimal('5'),
            quantity_unit='t',
            non_cbam_quantity=Decimal('0'),
            non_cbam_quantity_unit='t',
            specific_direct_embedded_emissions=Decimal('0.5'),
            electricity_consumption_intensity=Decimal('0.2'),
            electricity_emission_factor=Decimal('0.5'),
            provenance_notes='Supplier declaration',
        ),
    )
    for target, qty in ((profile_id, Decimal('3')), (other_profile.id, Decimal('2'))):
        purchased_precursor_service.create_precursor_product_use(
            seeded_db,
            user,
            organization.id,
            binding.id,
            precursor.id,
            PrecursorProductUseCreate(
                target_product_profile_version_id=target, quantity=qty, unit='t'
            ),
        )
    seeded_db.commit()

    readiness = pee.get_product_embedded_emissions_readiness(
        seeded_db, user, organization.id, binding.id
    )
    # The second product has no DEA/IEA row, so only the first is eligible.
    contributions = {
        row.product_profile_version_id: row.precursor_use_count for row in readiness.products
    }
    assert contributions[profile_id] == 1
    assert contributions[other_profile.id] == 1


def test_exported_electricity_is_never_attributed_to_a_product(seeded_db: Session) -> None:
    """Facility-level export raises an informational code but is never allocated (T72 = 0)."""
    from tests.cbam_dea_helpers import admin, org

    user = admin(seeded_db)
    organization = org(seeded_db)
    binding, installation, profile_id = seed_allocations(
        seeded_db, user, organization, exported_electricity_kwh=Decimal('5000')
    )
    create_ready_process(seeded_db, user, organization, binding, installation, profile_id)
    seeded_db.commit()

    readiness = pee.get_product_embedded_emissions_readiness(
        seeded_db,
        user,
        organization.id,
        binding.id,
        methodology_code=METHODOLOGY_CODE,
    )
    assert readiness.rollup_ready is True
    assert EXPORTED_ELECTRICITY_NOTE_CODE in readiness.informational_codes

    execution = pee.execute_product_embedded_emissions(
        seeded_db,
        user,
        organization.id,
        binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(
            client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE
        ),
    )
    detail = pee.get_product_embedded_emissions_result(
        seeded_db, user, organization.id, binding.id, execution.result_id
    )
    row = detail.products[0]
    assert Decimal(row['exportedElectricityDirectTco2e']) == Decimal('0')
    assert Decimal(row['ownDirectTco2eRaw']) == Decimal(row['deaDirectTco2'])
    # Indirect stays the raw IEA value: exported electricity feeds T72 (direct) only.
    assert Decimal(row['ownIndirectTco2eRaw']) == Decimal(row['ieaIndirectTco2e'])
    assert EXPORTED_ELECTRICITY_NOTE_CODE in detail.informational_codes


def _fresh_allocations(
    db: Session,
) -> tuple[object, object, object, object, uuid.UUID]:
    from tests.cbam_dea_helpers import admin, org

    user = admin(db)
    organization = org(db)
    binding, installation, profile_id = seed_allocations(db, user, organization)
    return user, organization, binding, installation, profile_id


def test_v2_execute_defaults_and_matches_v1_when_no_internal_flows(
    seeded_db: Session,
) -> None:
    scenario = seed_ready_rollup(seeded_db)
    v1 = _execute(seeded_db, scenario, methodology_code=METHODOLOGY_CODE)
    v2 = _execute(seeded_db, scenario, methodology_code=METHODOLOGY_CODE_V2)

    assert v2.methodology_code == METHODOLOGY_CODE_V2
    assert v2.internal_contribution_count == 0
    assert v2.total_direct_tco2e == v1.total_direct_tco2e
    assert v2.total_indirect_tco2e == v1.total_indirect_tco2e
    assert v2.total_embedded_tco2e == v1.total_embedded_tco2e

    detail = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        v2.result_id,
    )
    assert detail.exported_electricity_note_code == EXPORTED_ELECTRICITY_NOTE_CODE_V2
    assert detail.internal_precursor_note_code == INTERNAL_PRECURSOR_NOTE_CODE_V2
    assert 'not modeled' not in detail.exported_electricity_note.lower()
    assert 'not modeled' not in detail.internal_precursor_note.lower()
    row = detail.products[0]
    assert Decimal(row['internalDirectTco2eRaw']) == Decimal('0')
    assert Decimal(row['exportedElectricityDirectTco2e']) == Decimal('0')
    assert detail.internal_contributions == []

    v1_detail = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        v1.result_id,
    )
    assert v1_detail.is_current is True
    assert v1_detail.methodology_code == METHODOLOGY_CODE

    summary = pee.get_product_embedded_emissions_summary(
        seeded_db, scenario.user, scenario.organization.id, scenario.binding.id
    )
    assert summary.methodology_code == METHODOLOGY_CODE_V2
    assert summary.current_result_id == v2.result_id


def test_v2_includes_t72_in_own_direct(seeded_db: Session) -> None:
    scenario = seed_ready_rollup(seeded_db)
    process = production_process_service.get_production_process(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
    )
    production_process_service.update_production_process_draft(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        scenario.process_id,
        ProductionProcessUpdate(
            row_version=process.row_version,
            has_exported_electricity=True,
            exported_electricity_quantity=Decimal('2'),
            exported_electricity_unit='MWh',
            exported_electricity_emission_factor=Decimal('0.5'),
            exported_electricity_ef_unit='tCO2/MWh',
            exported_electricity_provenance='metered export',
        ),
    )
    seeded_db.commit()

    execution = _execute(seeded_db, scenario, methodology_code=METHODOLOGY_CODE_V2)
    detail = pee.get_product_embedded_emissions_result(
        seeded_db,
        scenario.user,
        scenario.organization.id,
        scenario.binding.id,
        execution.result_id,
    )
    row = detail.products[0]
    assert Decimal(row['exportedElectricityDirectTco2e']) == Decimal('-1.0')
    assert Decimal(row['ownDirectTco2eRaw']) == Decimal(row['deaDirectTco2']) + Decimal('-1.0')
