from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from ecotrace.core.exceptions import ConflictError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application.stationary_combustion_api_service import (
    get_stationary_combustion_parameters,
    list_active_stationary_combustion_fuels,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_service import (
    StationaryCombustionFuelCreate,
    StationaryCombustionParameterSetCreate,
    create_fuel,
    create_parameter_set,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamReferenceSource,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionParameterSet,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def _ipcc(db):
    return db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == "IPCC",
        )
    ).scalar_one()


def test_inactive_fuels_not_listed(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="DIESEL",
            name="Diesel inactive list check",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
            status="INACTIVE",
        ),
    )
    fuels = list_active_stationary_combustion_fuels(seeded_db, admin, org.id)
    codes = {f.code for f in fuels}
    assert "NATURAL_GAS" in codes
    assert "DIESEL" not in codes
    archived = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == "NATURAL_GAS"
        )
    ).scalar_one()
    archived.status = "ARCHIVED"
    seeded_db.flush()
    fuels2 = list_active_stationary_combustion_fuels(seeded_db, admin, org.id)
    assert all(f.code != "NATURAL_GAS" for f in fuels2)


def test_ambiguous_parameters_conflict_via_api_service(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="OTHER_FUEL",
            name="Other",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    create_parameter_set(
        seeded_db,
        StationaryCombustionParameterSetCreate(
            fuel_id=fuel.id,
            dataset_code="AMB",
            dataset_version="V1",
            valid_from=date(2020, 1, 1),
            status="ACTIVE",
            net_calorific_value=Decimal("40"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("50000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        ),
    )
    seeded_db.add(
        CbamStationaryCombustionParameterSet(
            fuel_id=fuel.id,
            dataset_code="AMB",
            dataset_version="V2",
            valid_from=date(2021, 1, 1),
            status="ACTIVE",
            net_calorific_value=Decimal("41"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("51000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        )
    )
    seeded_db.flush()
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    with pytest.raises(ConflictError) as exc:
        get_stationary_combustion_parameters(
            seeded_db,
            admin,
            org.id,
            "OTHER_FUEL",
            reference_date=date(2024, 1, 1),
        )
    assert any(d.get("code") == "AMBIGUOUS_PARAMETER_SET" for d in exc.value.details)
