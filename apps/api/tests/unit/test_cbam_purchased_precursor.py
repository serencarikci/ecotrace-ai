"""Phase 10A purchased-precursor service behavior (E_PurchPrec).

EU-default tests lazy-seed the 12 532-row catalog on demand; the supplier-data tests
never touch it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tests.cbam_dea_helpers import admin, org, setup_binding
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application import purchased_precursor_service
from ecotrace.modules.cbam.application.precursor_constants import (
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    BALANCE_UNBALANCED,
    CALC_STATUS_CALCULATED,
    CALC_STATUS_INCOMPLETE,
    CALC_STATUS_NOT_CALCULATED,
    CODE_DEFAULT_VALUE_AMBIGUOUS,
    CODE_DEFAULT_VALUE_UNRESOLVED,
    CODE_INCOMPATIBLE_PRECURSOR_UNIT,
    CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED,
    CODE_PRECURSOR_CN_CODE_REQUIRED,
    CODE_PRECURSOR_DISTRIBUTION_INCOMPLETE,
    CODE_PRECURSOR_DISTRIBUTION_UNBALANCED,
    CODE_PRECURSOR_MODE_UNSUPPORTED,
    CODE_PRECURSOR_NAME_REQUIRED,
    CODE_PRECURSOR_QUANTITY_REQUIRED,
    CODE_PRECURSOR_TARGET_PRODUCT_INVALID,
    CODE_SUPPLIER_EMISSIONS_DATA_REQUIRED,
    CODE_SUPPLIER_PROVENANCE_REQUIRED,
    ELECTRICITY_EF_UNIT,
    ELECTRICITY_INTENSITY_UNIT,
    METHODOLOGY_CODE,
    MODE_EU_DEFAULT,
    MODE_SUPPLIER_DATA,
    READINESS_AMBIGUOUS,
    READINESS_EMPTY,
    READINESS_INCOMPLETE,
    READINESS_READY,
    READINESS_UNBALANCED,
    READINESS_UNRESOLVED,
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_NOT_APPLICABLE,
    RESOLUTION_RESOLVED,
    RESOLUTION_UNRESOLVED,
    SPECIFIC_DIRECT_UNIT,
    SPECIFIC_INDIRECT_UNIT,
    WORKBOOK_PRIMARY_SHEET,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.precursor_default_catalog_service import (
    resolve_default_value,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseCreate,
    PrecursorProductUseUpdate,
    PurchasedPrecursorCreate,
    PurchasedPrecursorUpdate,
    PurchasedPrecursorVersionRequest,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamProductProfileVersion,
    CbamPurchasedPrecursor,
    CbamPurchasedPrecursorProductUse,
)
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.suppliers.infrastructure.models import Supplier

# Albania 2523 29 00 (grey Portland cement) is a unique NUMERIC row in the DV catalog.
DEFAULT_COUNTRY = 'Albania'
DEFAULT_CN = '2523 29 00'
DEFAULT_CN_NORMALIZED = '25232900'
DEFAULT_DIRECT = Decimal('0.9')
DEFAULT_INDIRECT = Decimal('0.03')

# Argentina 2523 90 00 carries grey + white cement on a NULL route.
AMBIGUOUS_COUNTRY = 'Argentina'
AMBIGUOUS_CN = '2523 90 00'


def _supplier(db: Session, organization_id: uuid.UUID, *, name: str) -> Supplier:
    row = Supplier(
        organization_id=organization_id,
        code=f'SUP-{uuid.uuid4().hex[:8]}',
        name=name,
        supplier_type='material',
        status='active',
    )
    db.add(row)
    db.flush()
    return row


def _create(db, user, organization, binding, installation, **kwargs):
    payload = {'installation_profile_id': installation.id}
    payload.update(kwargs)
    return purchased_precursor_service.create_purchased_precursor(
        db, user, organization.id, binding.id, PurchasedPrecursorCreate(**payload)
    )


def _update(db, user, organization, binding, precursor, **kwargs):
    return purchased_precursor_service.update_purchased_precursor_draft(
        db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PurchasedPrecursorUpdate(row_version=precursor.row_version, **kwargs),
    )


def _read(db, user, organization, binding, precursor_id):
    return purchased_precursor_service.get_purchased_precursor(
        db, user, organization.id, binding.id, precursor_id
    )


def _setup(db: Session):
    organization = org(db)
    user = admin(db)
    binding, installation = setup_binding(db, user, organization)
    return organization, user, binding, installation


def _supplier_payload(**overrides):
    payload = {
        'name': 'Hot rolled coil',
        'quantity': Decimal('10'),
        'quantity_unit': 't',
        'non_cbam_quantity': Decimal('0'),
        'non_cbam_quantity_unit': 't',
        'specific_direct_embedded_emissions': Decimal('1.5'),
        'electricity_consumption_intensity': Decimal('2'),
        'electricity_emission_factor': Decimal('0.3'),
        'provenance_notes': 'Supplier declaration 2024-11',
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------------------


def test_metadata_exposes_workbook_refs_and_active_dataset(seeded_db) -> None:
    organization, user, _, _ = _setup(seeded_db)
    meta = purchased_precursor_service.get_purchased_precursor_metadata(
        seeded_db, user, organization.id
    )
    assert meta.methodology_code == METHODOLOGY_CODE
    assert meta.workbook_sha256 == WORKBOOK_SHA256
    assert meta.workbook_primary_sheet == WORKBOOK_PRIMARY_SHEET
    assert 'L52=L50*L51' in meta.workbook_formula_refs
    assert sorted(meta.supported_data_source_modes) == [MODE_EU_DEFAULT, MODE_SUPPLIER_DATA]
    assert meta.units['specificDirect'] == SPECIFIC_DIRECT_UNIT
    assert meta.units['electricityIntensity'] == ELECTRICITY_INTENSITY_UNIT
    assert meta.units['electricityEmissionFactor'] == ELECTRICITY_EF_UNIT
    assert meta.default_value_dataset.value_count == 12532
    assert {lst.list_code for lst in meta.controlled_lists} == {
        'CONST_MeasDefaultUnknown',
        'CONST_ElecSource',
        'CONST_DefaultJustification',
    }


# --------------------------------------------------------------------------------------
# Lifecycle and readiness (supplier data)
# --------------------------------------------------------------------------------------


def test_blank_draft_is_empty_with_stable_blocking_codes(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    created = _create(seeded_db, user, organization, binding, installation)
    assert created.data_source_mode == MODE_SUPPLIER_DATA
    assert created.readiness.status == READINESS_EMPTY
    assert created.readiness.blocking_issue_codes == [
        CODE_PRECURSOR_NAME_REQUIRED,
        CODE_PRECURSOR_QUANTITY_REQUIRED,
        CODE_PRECURSOR_DISTRIBUTION_INCOMPLETE,
    ]
    assert created.distribution.balance_status == BALANCE_INCOMPLETE
    assert created.default_source.applicable is False
    assert created.default_source.resolution_status == RESOLUTION_NOT_APPLICABLE
    assert created.calculation.status == CALC_STATUS_INCOMPLETE
    assert created.calculation.total_embedded_emissions is None


def test_unsupported_data_source_mode_is_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(BusinessRuleError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            data_source_mode='UNKNOWN',
        )
    assert CODE_PRECURSOR_MODE_UNSUPPORTED in str(exc.value.details)


def test_supplier_mode_incomplete_emissions_block_readiness(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    created = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        name='Hot rolled coil',
        quantity=Decimal('10'),
        quantity_unit='t',
        non_cbam_quantity=Decimal('10'),
        non_cbam_quantity_unit='t',
    )
    assert created.readiness.status == READINESS_INCOMPLETE
    assert created.readiness.blocking_issue_codes == [CODE_SUPPLIER_EMISSIONS_DATA_REQUIRED]
    assert created.supplier_data.applicable is True
    assert created.supplier_data.specific_indirect_embedded_emissions is None
    assert created.calculation.status == CALC_STATUS_INCOMPLETE

    # Direct value alone still leaves the electricity legs missing.
    partial = _update(
        seeded_db,
        user,
        organization,
        binding,
        created,
        specific_direct_embedded_emissions=Decimal('1.5'),
        provenance_notes='Supplier declaration',
    )
    assert partial.readiness.blocking_issue_codes == [CODE_SUPPLIER_EMISSIONS_DATA_REQUIRED]
    assert partial.calculation.status != CALC_STATUS_CALCULATED


def test_supplier_provenance_required_when_numeric_values_present(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(BusinessRuleError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            specific_direct_embedded_emissions=Decimal('1.5'),
        )
    assert CODE_SUPPLIER_PROVENANCE_REQUIRED in str(exc.value.details)

    # An evidence reference satisfies the same rule.
    ok = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        name='Hot rolled coil',
        specific_direct_embedded_emissions=Decimal('1.5'),
        evidence_reference='DOC-2024-118',
    )
    assert ok.supplier_data.evidence_reference == 'DOC-2024-118'
    assert CODE_SUPPLIER_PROVENANCE_REQUIRED not in ok.readiness.blocking_issue_codes

    # Clearing provenance while numeric values remain is rejected on update too.
    with pytest.raises(BusinessRuleError) as exc:
        _update(
            seeded_db, user, organization, binding, ok, evidence_reference=None
        )
    assert CODE_SUPPLIER_PROVENANCE_REQUIRED in str(exc.value.details)


def test_manual_electricity_factor_derives_specific_indirect(seeded_db) -> None:
    """L52 = L50*L51 is recomputed and persisted on every write."""
    organization, user, binding, installation = _setup(seeded_db)
    created = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        name='Hot rolled coil',
        electricity_consumption_intensity=Decimal('2'),
        electricity_emission_factor=Decimal('0.3'),
        provenance_notes='Supplier declaration',
    )
    assert created.supplier_data.specific_indirect_embedded_emissions == Decimal('0.6')
    assert created.supplier_data.specific_indirect_unit == SPECIFIC_INDIRECT_UNIT
    assert created.supplier_data.electricity_intensity_unit == ELECTRICITY_INTENSITY_UNIT
    assert created.supplier_data.electricity_ef_unit == ELECTRICITY_EF_UNIT

    edited = _update(
        seeded_db,
        user,
        organization,
        binding,
        created,
        electricity_emission_factor=Decimal('0.5'),
    )
    assert edited.supplier_data.specific_indirect_embedded_emissions == Decimal('1.0')

    cleared = _update(
        seeded_db,
        user,
        organization,
        binding,
        edited,
        electricity_emission_factor=None,
    )
    assert cleared.supplier_data.specific_indirect_embedded_emissions is None
    assert cleared.supplier_data.specific_indirect_unit is None


def test_fixed_emission_units_are_enforced(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(ValidationAppError):
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            specific_direct_embedded_emissions=Decimal('1.5'),
            specific_direct_unit='kgCO2e/t',
            provenance_notes='Supplier declaration',
        )


def test_invalid_controlled_list_codes_are_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(ValidationAppError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            specific_direct_source_code='GUESSED',
        )
    assert 'PARAMETER_SOURCE_CODE_INVALID' in str(exc.value.details)

    with pytest.raises(ValidationAppError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            electricity_ef_source_code='D.9.9',
        )
    assert 'ELECTRICITY_SOURCE_CODE_INVALID' in str(exc.value.details)


# --------------------------------------------------------------------------------------
# Suppliers
# --------------------------------------------------------------------------------------


def test_same_material_from_two_suppliers_creates_two_records(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    first_supplier = _supplier(seeded_db, organization.id, name='Mill A')
    second_supplier = _supplier(seeded_db, organization.id, name='Mill B')

    first = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        supplier_id=first_supplier.id,
        **_supplier_payload(specific_direct_embedded_emissions=Decimal('1.5')),
    )
    second = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        supplier_id=second_supplier.id,
        **_supplier_payload(specific_direct_embedded_emissions=Decimal('2.1')),
    )
    assert first.id != second.id
    assert first.supplier_id == first_supplier.id
    assert second.supplier_id == second_supplier.id

    listing = purchased_precursor_service.list_purchased_precursors(
        seeded_db, user, organization.id, binding.id
    )
    assert listing.total_items == 2
    assert {row.supplier_id for row in listing.items} == {
        first_supplier.id,
        second_supplier.id,
    }

    summary = purchased_precursor_service.get_purchased_precursor_binding_summary(
        seeded_db, user, organization.id, binding.id
    )
    assert summary.precursor_count == 2
    assert summary.draft_count == 2


def test_supplier_from_another_organization_is_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    other = Organization(
        name='Other Org', slug=f'other-{uuid.uuid4().hex[:8]}', is_active=True
    )
    seeded_db.add(other)
    seeded_db.flush()
    foreign_supplier = _supplier(seeded_db, other.id, name='Foreign Mill')

    with pytest.raises(NotFoundError):
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            supplier_id=foreign_supplier.id,
        )


# --------------------------------------------------------------------------------------
# Distribution
# --------------------------------------------------------------------------------------


def test_product_distribution_crud_and_balance(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile_a = create_active_ready_profile(seeded_db, user, organization.id)
    profile_b = create_active_ready_profile(
        seeded_db,
        user,
        organization.id,
        product=ensure_org_product(seeded_db, organization.id, code='TGT-B'),
    )
    precursor = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        **_supplier_payload(),
    )

    use_a = purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile_a.id, quantity=Decimal('6')
        ),
    )
    assert use_a.quantity_tonnes == Decimal('6')

    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile_b.id, quantity=Decimal('3')
        ),
    )
    after_create = _read(seeded_db, user, organization, binding, precursor.id)
    assert len(after_create.distribution.product_uses) == 2
    assert after_create.distribution.product_use_tonnes == Decimal('9')
    assert after_create.distribution.remaining_tonnes == Decimal('1')
    assert after_create.distribution.balance_status == BALANCE_UNBALANCED

    # A second row for the same target profile is refused.
    with pytest.raises(BusinessRuleError) as exc:
        purchased_precursor_service.create_precursor_product_use(
            seeded_db,
            user,
            organization.id,
            binding.id,
            precursor.id,
            PrecursorProductUseCreate(
                target_product_profile_version_id=profile_a.id, quantity=Decimal('1')
            ),
        )
    assert 'PRODUCT_USE_DUPLICATE' in str(exc.value.details)

    updated = purchased_precursor_service.update_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        use_a.id,
        PrecursorProductUseUpdate(row_version=use_a.row_version, quantity=Decimal('7')),
    )
    assert updated.quantity == Decimal('7')
    after_update = _read(seeded_db, user, organization, binding, precursor.id)
    assert after_update.distribution.remaining_tonnes == Decimal('0')
    assert after_update.distribution.balance_status == BALANCE_BALANCED

    purchased_precursor_service.delete_precursor_product_use(
        seeded_db, user, organization.id, binding.id, precursor.id, updated.id
    )
    after_delete = _read(seeded_db, user, organization, binding, precursor.id)
    assert len(after_delete.distribution.product_uses) == 1
    assert after_delete.distribution.remaining_tonnes == Decimal('7')


def test_non_cbam_quantity_counts_towards_the_balance(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    precursor = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        **_supplier_payload(non_cbam_quantity=Decimal('4')),
    )
    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile.id, quantity=Decimal('6')
        ),
    )
    view = _read(seeded_db, user, organization, binding, precursor.id)
    assert view.distribution.non_cbam_tonnes == Decimal('4')
    assert view.distribution.distributed_tonnes == Decimal('10')
    assert view.distribution.remaining_tonnes == Decimal('0')
    assert view.distribution.balance_status == BALANCE_BALANCED
    assert view.distribution.formula_ref == 'E_PurchPrec!L39=L25-SUM(L28:L38)'


def test_unbalanced_draft_saves_but_blocks_readiness(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile.id, quantity=Decimal('9.99999999')
        ),
    )
    # The draft persisted even though the balance is off by 1e-8 t.
    stored = seeded_db.get(CbamPurchasedPrecursor, precursor.id)
    assert stored is not None

    readiness = purchased_precursor_service.get_purchased_precursor_readiness(
        seeded_db, user, organization.id, binding.id, precursor.id
    )
    assert readiness.status == READINESS_UNBALANCED
    assert readiness.blocking_issue_codes == [CODE_PRECURSOR_DISTRIBUTION_UNBALANCED]
    assert readiness.remaining_tonnes == Decimal('0.00000001')

    summary = purchased_precursor_service.get_purchased_precursor_binding_summary(
        seeded_db, user, organization.id, binding.id
    )
    assert summary.unbalanced_count == 1
    assert summary.ready_count == 0


def test_exact_balance_supplier_record_is_ready_with_golden_totals(seeded_db) -> None:
    """qty=10 t, L49=1.5, L50=2, L51=0.3 → L52=0.6, T49=15, T52=6, total=21 tCO2e."""
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile.id, quantity=Decimal('10')
        ),
    )
    view = _read(seeded_db, user, organization, binding, precursor.id)
    assert view.distribution.remaining_tonnes == Decimal('0')
    assert view.readiness.status == READINESS_READY
    assert view.readiness.blocking_issue_codes == []

    calc = view.calculation
    assert calc.status == CALC_STATUS_CALCULATED
    assert calc.value_source == MODE_SUPPLIER_DATA
    assert calc.quantity_tonnes == Decimal('10')
    assert calc.specific_direct_embedded_emissions == Decimal('1.5')
    assert calc.specific_indirect_embedded_emissions == Decimal('0.6')
    assert calc.total_direct_embedded_emissions == Decimal('15')
    assert calc.total_indirect_embedded_emissions == Decimal('6')
    assert calc.total_embedded_emissions == Decimal('21')
    assert calc.result_unit == 'tCO2e'
    assert 'not rolled up into product totals' in calc.rollup_note

    summary = purchased_precursor_service.get_purchased_precursor_binding_summary(
        seeded_db, user, organization.id, binding.id
    )
    assert summary.ready_count == 1


def test_cross_org_target_product_is_rejected_and_flagged(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    other = Organization(
        name='Other Org', slug=f'other-{uuid.uuid4().hex[:8]}', is_active=True
    )
    seeded_db.add(other)
    seeded_db.flush()
    foreign_profile = CbamProductProfileVersion(
        organization_id=other.id,
        product_id=ensure_org_product(seeded_db, other.id).id,
        version=1,
        status='active',
        classification_ready=True,
        product_name='Foreign',
        cn_normalized_code='73181595',
        cn_display_code='7318 15 95',
    )
    seeded_db.add(foreign_profile)
    seeded_db.flush()

    with pytest.raises(NotFoundError):
        purchased_precursor_service.create_precursor_product_use(
            seeded_db,
            user,
            organization.id,
            binding.id,
            precursor.id,
            PrecursorProductUseCreate(
                target_product_profile_version_id=foreign_profile.id,
                quantity=Decimal('10'),
            ),
        )

    # A row that points outside the organization keeps readiness blocked on reads.
    seeded_db.add(
        CbamPurchasedPrecursorProductUse(
            precursor_id=precursor.id,
            organization_id=organization.id,
            reporting_period_binding_id=binding.id,
            target_product_profile_version_id=foreign_profile.id,
            quantity=Decimal('10'),
            unit='t',
        )
    )
    seeded_db.flush()
    readiness = purchased_precursor_service.get_purchased_precursor_readiness(
        seeded_db, user, organization.id, binding.id, precursor.id
    )
    assert CODE_PRECURSOR_TARGET_PRODUCT_INVALID in readiness.blocking_issue_codes
    assert CODE_PRECURSOR_TARGET_PRODUCT_INVALID == 'PRECURSOR_TARGET_PRODUCT_INVALID'


# --------------------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------------------


def test_mass_units_are_normalized_to_tonnes(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    precursor = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        **_supplier_payload(
            quantity=Decimal('5000'),
            quantity_unit='kg',
            non_cbam_quantity=Decimal('500000'),
            non_cbam_quantity_unit='kg',
        ),
    )
    assert precursor.distribution.purchased_tonnes == Decimal('5')
    assert precursor.distribution.non_cbam_tonnes == Decimal('500')

    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile.id,
            quantity=Decimal('2500'),
            unit='kg',
        ),
    )
    view = _read(seeded_db, user, organization, binding, precursor.id)
    assert view.distribution.product_uses[0].quantity_tonnes == Decimal('2.5')
    assert view.distribution.product_use_tonnes == Decimal('2.5')
    assert view.calculation.quantity_tonnes == Decimal('5')


def test_incompatible_precursor_unit_is_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(ValidationAppError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            quantity=Decimal('10'),
            quantity_unit='MWh',
        )
    assert CODE_INCOMPATIBLE_PRECURSOR_UNIT in str(exc.value.details)
    assert CODE_INCOMPATIBLE_PRECURSOR_UNIT == 'INCOMPATIBLE_PRECURSOR_UNIT'

    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    with pytest.raises(ValidationAppError) as exc:
        purchased_precursor_service.create_precursor_product_use(
            seeded_db,
            user,
            organization.id,
            binding.id,
            precursor.id,
            PrecursorProductUseCreate(
                target_product_profile_version_id=profile.id,
                quantity=Decimal('1'),
                unit='MWh',
            ),
        )
    assert CODE_INCOMPATIBLE_PRECURSOR_UNIT in str(exc.value.details)


def test_negative_quantity_is_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(ValidationAppError):
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            name='Hot rolled coil',
            quantity=Decimal('-1'),
            quantity_unit='t',
        )


# --------------------------------------------------------------------------------------
# EU default values
# --------------------------------------------------------------------------------------


def test_eu_default_snapshot_on_create_and_update(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    created = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Grey Portland cement',
        cn_code=DEFAULT_CN,
        country_of_origin=DEFAULT_COUNTRY,
        quantity=Decimal('10'),
        quantity_unit='t',
        non_cbam_quantity=Decimal('0'),
        non_cbam_quantity_unit='t',
        default_justification_code='SUPPLIER_DATA_UNAVAILABLE',
    )
    assert created.cn_normalized_code == DEFAULT_CN_NORMALIZED
    source = created.default_source
    assert source.applicable is True
    assert source.from_snapshot is True
    assert source.resolution_status == RESOLUTION_RESOLVED
    assert source.specific_direct_embedded_emissions == DEFAULT_DIRECT
    assert source.specific_indirect_embedded_emissions == DEFAULT_INDIRECT
    assert source.justification_code == 'SUPPLIER_DATA_UNAVAILABLE'
    assert source.snapshot is not None
    assert source.snapshot['value']['cnNormalizedCode'] == DEFAULT_CN_NORMALIZED
    assert created.supplier_data.applicable is False
    assert created.calculation.value_source == 'EU_DEFAULT_SNAPSHOT'
    assert created.calculation.total_direct_embedded_emissions == Decimal('9')
    assert created.calculation.total_indirect_embedded_emissions == Decimal('0.3')
    assert created.calculation.total_embedded_emissions == Decimal('9.3')

    purchased_precursor_service.create_precursor_product_use(
        seeded_db,
        user,
        organization.id,
        binding.id,
        created.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile.id, quantity=Decimal('10')
        ),
    )
    ready = _read(seeded_db, user, organization, binding, created.id)
    assert ready.readiness.status == READINESS_READY

    # Changing the identity re-resolves and re-snapshots.
    moved = _update(
        seeded_db,
        user,
        organization,
        binding,
        ready,
        country_of_origin='Algeria',
    )
    assert moved.default_source.from_snapshot is True
    assert moved.default_source.snapshot is not None
    assert moved.default_source.snapshot['value']['countryName'] == 'Algeria'
    assert moved.default_source.default_value_id != created.default_source.default_value_id


def test_eu_default_unresolved_and_ambiguous_readiness(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    unresolved = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Mystery precursor',
        cn_code='9999 99 99',
        country_of_origin=DEFAULT_COUNTRY,
        quantity=Decimal('10'),
        quantity_unit='t',
        non_cbam_quantity=Decimal('10'),
        non_cbam_quantity_unit='t',
    )
    assert unresolved.default_source.from_snapshot is False
    assert unresolved.default_source.resolution_status == RESOLUTION_UNRESOLVED
    assert unresolved.default_source.issue_code == CODE_DEFAULT_VALUE_UNRESOLVED
    assert unresolved.readiness.status == READINESS_UNRESOLVED
    assert CODE_DEFAULT_VALUE_UNRESOLVED in unresolved.readiness.blocking_issue_codes
    assert unresolved.calculation.status == CALC_STATUS_NOT_CALCULATED

    ambiguous = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Hydraulic cement',
        cn_code=AMBIGUOUS_CN,
        country_of_origin=AMBIGUOUS_COUNTRY,
        quantity=Decimal('10'),
        quantity_unit='t',
        non_cbam_quantity=Decimal('10'),
        non_cbam_quantity_unit='t',
    )
    assert ambiguous.default_source.resolution_status == RESOLUTION_AMBIGUOUS
    assert ambiguous.default_source.issue_code == CODE_DEFAULT_VALUE_AMBIGUOUS
    assert ambiguous.default_source.candidate_count == 2
    assert ambiguous.readiness.status == READINESS_AMBIGUOUS
    assert CODE_DEFAULT_VALUE_AMBIGUOUS in ambiguous.readiness.blocking_issue_codes

    missing_cn = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='No CN',
        country_of_origin=DEFAULT_COUNTRY,
        quantity=Decimal('10'),
        quantity_unit='t',
    )
    assert CODE_PRECURSOR_CN_CODE_REQUIRED in missing_cn.readiness.blocking_issue_codes


def test_mixed_precursor_source_is_rejected(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    with pytest.raises(BusinessRuleError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            data_source_mode=MODE_SUPPLIER_DATA,
            name='Mixed',
            default_justification_code='SUPPLIER_DATA_UNAVAILABLE',
        )
    assert CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED in str(exc.value.details)

    with pytest.raises(BusinessRuleError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            data_source_mode=MODE_EU_DEFAULT,
            name='Mixed',
            cn_code=DEFAULT_CN,
            country_of_origin=DEFAULT_COUNTRY,
            specific_direct_embedded_emissions=Decimal('1.5'),
            provenance_notes='Supplier declaration',
        )
    assert CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED in str(exc.value.details)
    assert CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED == 'MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED'


def test_switching_mode_clears_the_other_sources_fields(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    created = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Grey Portland cement',
        cn_code=DEFAULT_CN,
        country_of_origin=DEFAULT_COUNTRY,
    )
    assert created.default_source.from_snapshot is True

    switched = _update(
        seeded_db,
        user,
        organization,
        binding,
        created,
        data_source_mode=MODE_SUPPLIER_DATA,
        specific_direct_embedded_emissions=Decimal('1.5'),
        provenance_notes='Supplier declaration',
    )
    assert switched.default_source.applicable is False
    assert switched.default_source.snapshot is None
    assert switched.supplier_data.specific_direct_embedded_emissions == Decimal('1.5')

    stored = seeded_db.get(CbamPurchasedPrecursor, created.id)
    assert stored is not None
    assert stored.default_value_id is None
    assert stored.default_snapshot_json is None


def test_default_snapshot_survives_live_catalog_mutation(seeded_db) -> None:
    """Historical records read their own snapshot, never the live catalog row."""
    organization, user, binding, installation = _setup(seeded_db)
    created = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Grey Portland cement',
        cn_code=DEFAULT_CN,
        country_of_origin=DEFAULT_COUNTRY,
        quantity=Decimal('10'),
        quantity_unit='t',
    )
    value_id = created.default_source.default_value_id
    assert value_id is not None
    assert created.default_source.specific_direct_embedded_emissions == DEFAULT_DIRECT

    seeded_db.execute(
        text(
            """
UPDATE cbam_precursor_default_values
SET direct_value = 99, indirect_value = 88
WHERE id = :i
"""
        ),
        {'i': value_id},
    )
    seeded_db.expire_all()

    reread = _read(seeded_db, user, organization, binding, created.id)
    assert reread.default_source.specific_direct_embedded_emissions == DEFAULT_DIRECT
    assert reread.default_source.specific_indirect_embedded_emissions == DEFAULT_INDIRECT
    assert reread.calculation.total_embedded_emissions == Decimal('9.3')


def test_explicit_default_value_must_match_the_precursor_identity(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    resolved = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Grey Portland cement',
        cn_code=DEFAULT_CN,
        country_of_origin=DEFAULT_COUNTRY,
    )
    value_id = resolved.default_source.default_value_id
    assert value_id is not None

    with pytest.raises(BusinessRuleError) as exc:
        _create(
            seeded_db,
            user,
            organization,
            binding,
            installation,
            data_source_mode=MODE_EU_DEFAULT,
            name='Wrong identity',
            cn_code='2523 10 00',
            country_of_origin=DEFAULT_COUNTRY,
            default_value_id=value_id,
        )
    assert CODE_DEFAULT_VALUE_UNRESOLVED in str(exc.value.details)


def test_explicit_default_value_settles_an_ambiguous_match(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    ambiguous = _create(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        data_source_mode=MODE_EU_DEFAULT,
        name='Hydraulic cement',
        cn_code=AMBIGUOUS_CN,
        country_of_origin=AMBIGUOUS_COUNTRY,
    )
    assert ambiguous.default_source.resolution_status == RESOLUTION_AMBIGUOUS
    candidates = resolve_default_value(
        seeded_db, country_of_origin=AMBIGUOUS_COUNTRY, cn_code=AMBIGUOUS_CN
    ).candidates
    grey = next(c for c in candidates if c.goods_description == 'Grey hydraulic cements')

    picked = _update(
        seeded_db,
        user,
        organization,
        binding,
        ambiguous,
        default_value_id=grey.id,
    )
    assert picked.default_source.from_snapshot is True
    assert picked.default_source.default_value_id == grey.id
    assert picked.default_source.snapshot is not None
    assert (
        picked.default_source.snapshot['value']['goodsDescription']
        == 'Grey hydraulic cements'
    )


# --------------------------------------------------------------------------------------
# Archiving and isolation
# --------------------------------------------------------------------------------------


def test_archived_precursor_is_read_only(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    profile = create_active_ready_profile(seeded_db, user, organization.id)
    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    archived = purchased_precursor_service.archive_purchased_precursor(
        seeded_db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PurchasedPrecursorVersionRequest(row_version=precursor.row_version),
    )
    assert archived.status == 'archived'
    assert archived.readiness.blocking_issue_codes == ['PRECURSOR_ARCHIVED']

    with pytest.raises(BusinessRuleError):
        _update(seeded_db, user, organization, binding, archived, name='Renamed')
    with pytest.raises(BusinessRuleError):
        purchased_precursor_service.create_precursor_product_use(
            seeded_db,
            user,
            organization.id,
            binding.id,
            precursor.id,
            PrecursorProductUseCreate(
                target_product_profile_version_id=profile.id, quantity=Decimal('1')
            ),
        )

    default_listing = purchased_precursor_service.list_purchased_precursors(
        seeded_db, user, organization.id, binding.id
    )
    assert default_listing.total_items == 0
    with_archived = purchased_precursor_service.list_purchased_precursors(
        seeded_db, user, organization.id, binding.id, include_archived=True
    )
    assert with_archived.total_items == 1


def test_precursor_of_another_organization_is_not_readable(seeded_db) -> None:
    organization, user, binding, installation = _setup(seeded_db)
    precursor = _create(
        seeded_db, user, organization, binding, installation, **_supplier_payload()
    )
    other = Organization(
        name='Other Org', slug=f'other-{uuid.uuid4().hex[:8]}', is_active=True
    )
    seeded_db.add(other)
    seeded_db.flush()

    row = seeded_db.execute(
        select(CbamPurchasedPrecursor).where(CbamPurchasedPrecursor.id == precursor.id)
    ).scalar_one()
    assert row.organization_id == organization.id

    with pytest.raises(NotFoundError):
        _read(seeded_db, user, organization, binding, uuid.uuid4())
