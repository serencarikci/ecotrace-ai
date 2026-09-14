"""Shared fixtures for Phase 10C product embedded-emissions roll-up tests.

Builds one binding with a single month, one CBAM product, a current DEA result, a
current IEA result, a READY Conventional process and one READY purchased precursor.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application import (
    activity_record_service,
    direct_emissions_allocation_service,
    indirect_emissions_allocation_service,
    monthly_production_basis_service,
    production_process_service,
    production_record_service,
    purchased_precursor_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    IndirectEmissionsAllocationExecuteRequest,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ProductionProcessCreate,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    PurchasedElectricityExecuteRequest,
    execute_purchased_electricity,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseCreate,
    PurchasedPrecursorCreate,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from tests.cbam_dea_helpers import admin, create_ng_activity, org, run_sc, setup_binding
from tests.cbam_iea_helpers import _manual
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

PERIOD_START = date(2024, 7, 1)
PERIOD_END = date(2024, 7, 31)
ACTIVITY_DAY = date(2024, 7, 15)

# Single-month basis: total production D, CBAM quantity E.
TOTAL_PRODUCTION_TONNES = Decimal('100')
CBAM_PRODUCTION_TONNES = Decimal('10')

# Synthetic golden precursor (see docs/cbam/product-embedded-emissions-workbook.md).
PRECURSOR_PURCHASED_TONNES = Decimal('5')
PRECURSOR_USE_TONNES = Decimal('3')
PRECURSOR_NON_CBAM_TONNES = Decimal('2')
PRECURSOR_SPECIFIC_DIRECT = Decimal('0.5')
PRECURSOR_ELECTRICITY_INTENSITY = Decimal('0.2')
PRECURSOR_ELECTRICITY_EF = Decimal('0.5')
PRECURSOR_SPECIFIC_INDIRECT = (
    PRECURSOR_ELECTRICITY_INTENSITY * PRECURSOR_ELECTRICITY_EF
)  # 0.10

GOLDEN_PRECURSOR_DIRECT_TCO2E = PRECURSOR_USE_TONNES * PRECURSOR_SPECIFIC_DIRECT  # 1.5
GOLDEN_PRECURSOR_INDIRECT_TCO2E = PRECURSOR_USE_TONNES * PRECURSOR_SPECIFIC_INDIRECT  # 0.3


@dataclass(slots=True)
class RollupScenario:
    user: User
    organization: Organization
    binding: object
    installation: object
    profile_id: uuid.UUID
    process_id: uuid.UUID
    precursor_id: uuid.UUID
    product_use_id: uuid.UUID
    denominator_tonnes: Decimal


def seed_allocations(
    db: Session,
    user: User,
    organization: Organization,
    *,
    cbam_tonnes: Decimal = CBAM_PRODUCTION_TONNES,
    exported_electricity_kwh: Decimal | None = None,
) -> tuple[object, object, uuid.UUID]:
    """One month of stationary combustion + purchased electricity with a single product."""
    binding, installation = setup_binding(db, user, organization, start=PERIOD_START, end=PERIOD_END)

    activity = create_ng_activity(
        db, user, organization, binding, installation, qty=Decimal('188'), day=ACTIVITY_DAY
    )
    run_sc(db, user, organization, binding, activity, day=ACTIVITY_DAY)

    electricity = activity_record_service.create_activity_record(
        db,
        user,
        organization.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='ELECTRICITY',
            activity_date=ACTIVITY_DAY,
            quantity=Decimal('176034.53'),
            unit='kWh',
            data_source_type='PRIMARY',
        ),
    )
    execute_purchased_electricity(
        db,
        user,
        organization.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=electricity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual(),
            exported_electricity_quantity=exported_electricity_kwh,
            exported_electricity_unit='kWh' if exported_electricity_kwh is not None else None,
        ),
    )

    monthly_production_basis_service.create_monthly_production_basis(
        db,
        user,
        organization.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=PERIOD_START,
            total_production_quantity=TOTAL_PRODUCTION_TONNES,
            cbam_quantity=cbam_tonnes,
            quantity_unit='t',
        ),
    )

    product = ensure_org_product(db, organization.id, code=f'PEE-{uuid.uuid4().hex[:6]}')
    profile = create_active_ready_profile(db, user, organization.id, product=product)
    production_record_service.create_production_record(
        db,
        user,
        organization.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=cbam_tonnes,
            unit='t',
            production_date=ACTIVITY_DAY,
        ),
    )

    direct_emissions_allocation_service.execute_direct_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    indirect_emissions_allocation_service.execute_indirect_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        IndirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    return binding, installation, profile.id


def create_ready_process(
    db: Session,
    user: User,
    organization: Organization,
    binding: object,
    installation: object,
    profile_id: uuid.UUID,
    *,
    produced_tonnes: Decimal = CBAM_PRODUCTION_TONNES,
) -> uuid.UUID:
    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name='Rollup process',
            product_profile_version_id=profile_id,
            produced_quantity=produced_tonnes,
            produced_quantity_unit='t',
            marketed_quantity=produced_tonnes,
            marketed_quantity_unit='t',
            non_cbam_quantity=Decimal('0'),
            non_cbam_quantity_unit='t',
            has_measurable_heat=False,
            has_waste_gas=False,
        ),
    )
    return process.id


def create_ready_precursor(
    db: Session,
    user: User,
    organization: Organization,
    binding: object,
    installation: object,
    profile_id: uuid.UUID,
    *,
    use_tonnes: Decimal = PRECURSOR_USE_TONNES,
    purchased_tonnes: Decimal = PRECURSOR_PURCHASED_TONNES,
    specific_direct: Decimal = PRECURSOR_SPECIFIC_DIRECT,
    electricity_intensity: Decimal = PRECURSOR_ELECTRICITY_INTENSITY,
    electricity_ef: Decimal = PRECURSOR_ELECTRICITY_EF,
) -> tuple[uuid.UUID, uuid.UUID]:
    precursor = purchased_precursor_service.create_purchased_precursor(
        db,
        user,
        organization.id,
        binding.id,
        PurchasedPrecursorCreate(
            installation_profile_id=installation.id,
            data_source_mode='SUPPLIER_DATA',
            name='Golden precursor',
            quantity=purchased_tonnes,
            quantity_unit='t',
            non_cbam_quantity=purchased_tonnes - use_tonnes,
            non_cbam_quantity_unit='t',
            specific_direct_embedded_emissions=specific_direct,
            electricity_consumption_intensity=electricity_intensity,
            electricity_emission_factor=electricity_ef,
            provenance_notes='Supplier declaration 2024-07',
        ),
    )
    use = purchased_precursor_service.create_precursor_product_use(
        db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile_id,
            quantity=use_tonnes,
            unit='t',
        ),
    )
    return precursor.id, use.id


def seed_ready_rollup(
    db: Session,
    user: User | None = None,
    organization: Organization | None = None,
) -> RollupScenario:
    user = user or admin(db)
    organization = organization or org(db)
    binding, installation, profile_id = seed_allocations(db, user, organization)
    process_id = create_ready_process(
        db, user, organization, binding, installation, profile_id
    )
    precursor_id, use_id = create_ready_precursor(
        db, user, organization, binding, installation, profile_id
    )
    db.commit()
    return RollupScenario(
        user=user,
        organization=organization,
        binding=binding,
        installation=installation,
        profile_id=profile_id,
        process_id=process_id,
        precursor_id=precursor_id,
        product_use_id=use_id,
        denominator_tonnes=CBAM_PRODUCTION_TONNES,
    )
