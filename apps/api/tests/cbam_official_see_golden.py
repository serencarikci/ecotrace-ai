"""DB-backed golden scenario for Official SEE export Phase 12A acceptance.

Uses production services only (same patterns as cbam_pee/dea/iea/profile helpers).
CN codes ``73181595`` / ``73181699`` exist in both EcoTrace catalog and workbook
Parameters_CNCodes (avoid 73181589 which yields Communication #N/A).
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
from ecotrace.modules.cbam.application import (
    product_embedded_emissions_service as pee,
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
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    METHODOLOGY_CODE_V2,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
    create_product_profile,
    publish_product_profile,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ProductionProcessCreate,
    ProductUseCreate,
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
from tests.cbam_profile_helpers import ensure_org_product

# CN codes present in BOTH EcoTrace catalog and workbook Parameters_CNCodes.
CN_SCREWS = '73181595'
CN_NUTS = '73181699'

PERIOD_START = date(2024, 7, 1)
PERIOD_END = date(2024, 8, 31)

# Two months: (activity_day, NG Sm3, elec kWh, D tonnes, E tonnes, prod_A, prod_B)
MONTHS = [
    (date(2024, 7, 15), Decimal('188'), Decimal('176034.53'), Decimal('100'), Decimal('50'), Decimal('30'), Decimal('20')),
    (date(2024, 8, 15), Decimal('183'), Decimal('180962.85'), Decimal('80'), Decimal('40'), Decimal('25'), Decimal('15')),
]

# Process A (screws): produced 55 = marketed 50 + internal use to B 5
PROCESS_A_PRODUCED = Decimal('55')
PROCESS_A_MARKETED = Decimal('50')
PROCESS_A_TO_B = Decimal('5')

# Process B (nuts): produced 35, all marketed
PROCESS_B_PRODUCED = Decimal('35')
PROCESS_B_MARKETED = Decimal('35')

PRECURSOR_PURCHASED = Decimal('4')
PRECURSOR_USE_ON_B = Decimal('3')
PRECURSOR_NON_CBAM = Decimal('1')
PRECURSOR_SPECIFIC_DIRECT = Decimal('0.5')
PRECURSOR_ELEC_INTENSITY = Decimal('0.2')
PRECURSOR_ELEC_EF = Decimal('0.5')


@dataclass(slots=True)
class OfficialSeeGoldenScenario:
    user: User
    organization: Organization
    binding: object
    installation: object
    profile_a_id: uuid.UUID
    profile_b_id: uuid.UUID
    process_a_id: uuid.UUID
    process_b_id: uuid.UUID
    precursor_id: uuid.UUID
    pee_result_id: uuid.UUID
    methodology_code: str


def _publish_steel_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    code: str,
    name: str,
    cn_code: str,
    reducing_agent: str,
) -> uuid.UUID:
    product = ensure_org_product(db, organization_id, code=code)
    draft = create_product_profile(
        db,
        user,
        organization_id,
        ProductProfileCreate(
            product_id=product.id,
            product_name=name,
            cn_code=cn_code,
            reducing_agent=reducing_agent,
            steel_mill_identification_number=f'TR-{code}',
            percent_mn=Decimal('40'),
            percent_cr=Decimal('20'),
            percent_ni=Decimal('10'),
            percent_other_alloys=Decimal('10'),
            percent_other_materials=Decimal('20'),
        ),
    )
    published = publish_product_profile(
        db,
        user,
        organization_id,
        draft.id,
        ProductProfileVersionRequest(row_version=draft.row_version),
    )
    return published.id


def seed_official_see_golden(
    db: Session,
    user: User | None = None,
    organization: Organization | None = None,
) -> OfficialSeeGoldenScenario:
    """Seed a 2-product V2 chain and execute PEE V2 (current snapshot retained)."""
    user = user or admin(db)
    organization = organization or org(db)
    binding, installation = setup_binding(
        db, user, organization, start=PERIOD_START, end=PERIOD_END
    )

    profile_a = _publish_steel_profile(
        db,
        user,
        organization.id,
        code=f'SEE-A-{uuid.uuid4().hex[:6]}',
        name='EcoTrace Screws',
        cn_code=CN_SCREWS,
        reducing_agent='Natural gas',
    )
    profile_b = _publish_steel_profile(
        db,
        user,
        organization.id,
        code=f'SEE-B-{uuid.uuid4().hex[:6]}',
        name='EcoTrace Nuts',
        cn_code=CN_NUTS,
        reducing_agent='Coal or coke',
    )

    for day, ng_qty, kwh, d_tonnes, e_tonnes, qty_a, qty_b in MONTHS:
        activity = create_ng_activity(
            db, user, organization, binding, installation, qty=ng_qty, day=day
        )
        run_sc(db, user, organization, binding, activity, day=day)

        electricity = activity_record_service.create_activity_record(
            db,
            user,
            organization.id,
            binding.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type='ELECTRICITY',
                activity_date=day,
                quantity=kwh,
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
            ),
        )

        monthly_production_basis_service.create_monthly_production_basis(
            db,
            user,
            organization.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(day.year, day.month, 1),
                total_production_quantity=d_tonnes,
                cbam_quantity=e_tonnes,
                quantity_unit='t',
            ),
        )
        for profile_id, qty in ((profile_a, qty_a), (profile_b, qty_b)):
            production_record_service.create_production_record(
                db,
                user,
                organization.id,
                binding.id,
                ProductionRecordCreate(
                    installation_profile_id=installation.id,
                    product_profile_version_id=profile_id,
                    quantity=qty,
                    unit='t',
                    production_date=day,
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

    process_a = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name='EcoTrace Process Screws',
            product_profile_version_id=profile_a,
            produced_quantity=PROCESS_A_PRODUCED,
            produced_quantity_unit='t',
            marketed_quantity=PROCESS_A_MARKETED,
            marketed_quantity_unit='t',
            non_cbam_quantity=Decimal('0'),
            non_cbam_quantity_unit='t',
            has_measurable_heat=True,
            heat_imported_quantity=Decimal('0.1'),
            heat_imported_unit='TJ',
            heat_exported_quantity=Decimal('0'),
            heat_exported_unit='TJ',
            heat_imported_ef=Decimal('56.1'),
            heat_exported_ef=Decimal('56.1'),
            heat_ef_unit='tCO2/TJ',
            has_waste_gas=True,
            waste_gas_imported_quantity=Decimal('0.05'),
            waste_gas_imported_unit='TJ',
            waste_gas_exported_quantity=Decimal('0'),
            waste_gas_exported_unit='TJ',
            has_exported_electricity=True,
            exported_electricity_quantity=Decimal('1'),
            exported_electricity_unit='MWh',
            exported_electricity_emission_factor=Decimal('0.4'),
            exported_electricity_ef_unit='tCO2/MWh',
            exported_electricity_provenance='metered process export T72',
        ),
    )
    production_process_service.create_product_use(
        db,
        user,
        organization.id,
        binding.id,
        process_a.id,
        ProductUseCreate(
            target_product_profile_version_id=profile_b,
            quantity=PROCESS_A_TO_B,
            unit='t',
        ),
    )

    process_b = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name='EcoTrace Process Nuts',
            product_profile_version_id=profile_b,
            produced_quantity=PROCESS_B_PRODUCED,
            produced_quantity_unit='t',
            marketed_quantity=PROCESS_B_MARKETED,
            marketed_quantity_unit='t',
            non_cbam_quantity=Decimal('0'),
            non_cbam_quantity_unit='t',
            has_measurable_heat=False,
            has_waste_gas=False,
        ),
    )

    precursor = purchased_precursor_service.create_purchased_precursor(
        db,
        user,
        organization.id,
        binding.id,
        PurchasedPrecursorCreate(
            installation_profile_id=installation.id,
            data_source_mode='SUPPLIER_DATA',
            name='Golden SEE precursor',
            quantity=PRECURSOR_PURCHASED,
            quantity_unit='t',
            non_cbam_quantity=PRECURSOR_NON_CBAM,
            non_cbam_quantity_unit='t',
            specific_direct_embedded_emissions=PRECURSOR_SPECIFIC_DIRECT,
            electricity_consumption_intensity=PRECURSOR_ELEC_INTENSITY,
            electricity_emission_factor=PRECURSOR_ELEC_EF,
            provenance_notes='Supplier declaration SEE golden',
            country_of_origin='Albania',
            aggregated_goods_category='Iron or steel products',
        ),
    )
    purchased_precursor_service.create_precursor_product_use(
        db,
        user,
        organization.id,
        binding.id,
        precursor.id,
        PrecursorProductUseCreate(
            target_product_profile_version_id=profile_b,
            quantity=PRECURSOR_USE_ON_B,
            unit='t',
        ),
    )

    db.commit()

    execution = pee.execute_product_embedded_emissions(
        db,
        user,
        organization.id,
        binding.id,
        pee.ProductEmbeddedEmissionsExecuteRequest(
            client_request_id=uuid.uuid4(),
            methodology_code=METHODOLOGY_CODE_V2,
        ),
    )
    assert execution.status == 'COMPLETED', execution
    db.commit()

    return OfficialSeeGoldenScenario(
        user=user,
        organization=organization,
        binding=binding,
        installation=installation,
        profile_a_id=profile_a,
        profile_b_id=profile_b,
        process_a_id=process_a.id,
        process_b_id=process_b.id,
        precursor_id=precursor.id,
        pee_result_id=execution.result_id,
        methodology_code=METHODOLOGY_CODE_V2,
    )
