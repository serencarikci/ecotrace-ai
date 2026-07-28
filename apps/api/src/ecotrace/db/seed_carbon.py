from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.carbon_constants import (
    ENGINE_VERSION,
    GWP_DATASET_AR5_DEMO,
    METHODOLOGY_VERSION,
)
from ecotrace.core.logging import get_logger
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.carbon_accounting.application.calculation_math import compute_emission_result
from ecotrace.modules.carbon_accounting.application.matching_service import match_emission_factor
from ecotrace.modules.carbon_inventory.infrastructure.models import (
    CarbonCalculationItem,
    CarbonCalculationRun,
    CarbonInventory,
)
from ecotrace.modules.emission_factors.infrastructure.models import (
    EmissionFactor,
    EmissionFactorSource,
    GwpValue,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reference_data.application.unit_conversion import convert_between, get_unit
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

logger = get_logger(__name__)

DEMO_DISCLAIMER = (
    "DEMO/REFERENCE DATA ONLY — not authoritative and not suitable for "
    "regulatory reporting, certification, or legal compliance claims."
)

SOURCES = [
    {
        "code": "DEMO_GRID",
        "name": "EcoTrace Demo National Grid Factors",
        "publisher": "EcoTrace Demo",
        "geographic_coverage": "TR, GLOBAL",
        "methodology": "Illustrative location-based electricity factors for demos.",
    },
    {
        "code": "DEMO_FUEL",
        "name": "EcoTrace Demo Fuel Factors",
        "publisher": "EcoTrace Demo",
        "geographic_coverage": "GLOBAL",
        "methodology": "Illustrative stationary/mobile fuel combustion factors.",
    },
    {
        "code": "DEMO_WASTE",
        "name": "EcoTrace Demo Waste Factors",
        "publisher": "EcoTrace Demo",
        "geographic_coverage": "GLOBAL",
        "methodology": "Illustrative waste treatment emission factors.",
    },
    {
        "code": "DEMO_TRANSPORT",
        "name": "EcoTrace Demo Transport Factors",
        "publisher": "EcoTrace Demo",
        "geographic_coverage": "GLOBAL",
        "methodology": "Illustrative freight, travel, and commuting factors.",
    },
]


GWP_ROWS = [
    ("CO2", "1"),
    ("CH4", "28"),
    ("N2O", "265"),
    ("SF6", "23500"),
    ("NF3", "16100"),
]


def _upsert_source(db: Session, payload: dict[str, str]) -> EmissionFactorSource:
    row = db.execute(
        select(EmissionFactorSource).where(EmissionFactorSource.code == payload["code"])
    ).scalar_one_or_none()
    if row is None:
        row = EmissionFactorSource(
            code=payload["code"],
            name=payload["name"],
            publisher=payload["publisher"],
            description=DEMO_DISCLAIMER,
            methodology=payload["methodology"],
            geographic_coverage=payload["geographic_coverage"],
            license_name="Demo / internal reference — not a licensed dataset",
            release_version="demo-1.0",
            published_at=date(2024, 1, 1),
            valid_from=date(2020, 1, 1),
            valid_to=date(2030, 12, 31),
            is_active=True,
            is_demo=True,
        )
        db.add(row)
        db.flush()
        logger.info("seed.factor_source_created", code=row.code)
    else:
        row.name = payload["name"]
        row.description = DEMO_DISCLAIMER
        row.is_demo = True
        row.is_active = True
    return row


def _upsert_factor(
    db: Session,
    *,
    source: EmissionFactorSource,
    activity_types: dict[str, ActivityType],
    code: str,
    name: str,
    activity_type_code: str,
    scope: str,
    category: str,
    unit_code: str,
    factor_value: str | None,
    geography_code: str = "GLOBAL",
    version: int = 1,
    status: str = "active",
    co2_factor: str | None = None,
    ch4_factor: str | None = None,
    n2o_factor: str | None = None,
    biogenic_co2_factor: str | None = None,
    fuel_type: str | None = None,
    transportation_mode: str | None = None,
    technology_code: str | None = None,
    valid_from: date = date(2020, 1, 1),
    valid_to: date = date(2030, 12, 31),
    supersedes: EmissionFactor | None = None,
) -> EmissionFactor:
    activity_type = activity_types[activity_type_code]
    row = db.execute(
        select(EmissionFactor).where(EmissionFactor.code == code, EmissionFactor.version == version)
    ).scalar_one_or_none()
    fields = {
        "source_id": source.id,
        "name": name,
        "description": DEMO_DISCLAIMER,
        "activity_type_id": activity_type.id,
        "scope": scope,
        "category": category,
        "geography_code": geography_code,
        "unit_code": unit_code,
        "factor_value": Decimal(factor_value) if factor_value is not None else None,
        "co2_factor": Decimal(co2_factor) if co2_factor is not None else None,
        "ch4_factor": Decimal(ch4_factor) if ch4_factor is not None else None,
        "n2o_factor": Decimal(n2o_factor) if n2o_factor is not None else None,
        "biogenic_co2_factor": Decimal(biogenic_co2_factor)
        if biogenic_co2_factor is not None
        else None,
        "fuel_type": fuel_type,
        "transportation_mode": transportation_mode,
        "technology_code": technology_code,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "status": status,
        "is_active": status == "active",
        "is_demo": True,
        "supersedes_factor_id": supersedes.id if supersedes else None,
        "metadata_json": {"disclaimer": DEMO_DISCLAIMER, "demo": True},
    }
    if row is None:
        row = EmissionFactor(code=code, version=version, **fields)
        db.add(row)
        db.flush()
        logger.info("seed.factor_created", code=code, version=version, status=status)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    return row


def seed_gwp(db: Session) -> None:
    for gas, value in GWP_ROWS:
        existing = db.execute(
            select(GwpValue).where(
                GwpValue.assessment_report_code == GWP_DATASET_AR5_DEMO,
                GwpValue.gas_code == gas,
                GwpValue.effective_from == date(2014, 1, 1),
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                GwpValue(
                    assessment_report_code=GWP_DATASET_AR5_DEMO,
                    gas_code=gas,
                    gwp_value=Decimal(value),
                    effective_from=date(2014, 1, 1),
                    effective_to=None,
                    source_reference=(
                        "EcoTrace AR5-demo reference dataset (illustrative values "
                        "inspired by commonly cited AR5 100-year GWPs; not an "
                        "official IPCC distribution)."
                    ),
                    is_active=True,
                )
            )
            db.flush()
            logger.info("seed.gwp_created", gas=gas)
        else:
            existing.gwp_value = Decimal(value)
            existing.is_active = True


def seed_factors(db: Session) -> dict[str, EmissionFactor]:
    sources = {s["code"]: _upsert_source(db, s) for s in SOURCES}
    activity_types = {a.code: a for a in db.execute(select(ActivityType)).scalars().all()}
    factors: dict[str, EmissionFactor] = {}

    v1 = _upsert_factor(
        db,
        source=sources["DEMO_GRID"],
        activity_types=activity_types,
        code="EF-ELEC-TR-DEMO",
        name="Demo TR grid electricity (v1 superseded)",
        activity_type_code="purchased_electricity",
        scope="scope_2",
        category="purchased_electricity",
        unit_code="kWh",
        factor_value="0.460",
        geography_code="TR",
        version=1,
        status="superseded",
        valid_to=date(2023, 12, 31),
    )
    factors["EF-ELEC-TR-DEMO-v1"] = v1
    factors["EF-ELEC-TR-DEMO"] = _upsert_factor(
        db,
        source=sources["DEMO_GRID"],
        activity_types=activity_types,
        code="EF-ELEC-TR-DEMO",
        name="Demo TR grid electricity (location-based)",
        activity_type_code="purchased_electricity",
        scope="scope_2",
        category="purchased_electricity",
        unit_code="kWh",
        factor_value="0.442",
        geography_code="TR",
        version=2,
        status="active",
        supersedes=v1,
    )
    factors["EF-ELEC-GLOBAL-DEMO"] = _upsert_factor(
        db,
        source=sources["DEMO_GRID"],
        activity_types=activity_types,
        code="EF-ELEC-GLOBAL-DEMO",
        name="Demo global electricity average",
        activity_type_code="purchased_electricity",
        scope="scope_2",
        category="purchased_electricity",
        unit_code="kWh",
        factor_value="0.475",
        geography_code="GLOBAL",
    )

    fuel_specs = [
        (
            "EF-NG-DEMO",
            "Demo natural gas",
            "natural_gas_consumption",
            "m3",
            "2.02",
            "natural_gas",
            "scope_1",
            "stationary_combustion",
        ),
        (
            "EF-DIESEL-DEMO",
            "Demo diesel",
            "diesel_consumption",
            "L",
            "2.68",
            "diesel",
            "scope_1",
            "stationary_combustion",
        ),
        (
            "EF-GASOLINE-DEMO",
            "Demo gasoline",
            "gasoline_consumption",
            "L",
            "2.31",
            "gasoline",
            "scope_1",
            "mobile_combustion",
        ),
        (
            "EF-LPG-DEMO",
            "Demo LPG",
            "lpg_consumption",
            "kg",
            "2.98",
            "lpg",
            "scope_1",
            "stationary_combustion",
        ),
    ]
    for code, name, at, unit, value, fuel, scope, cat in fuel_specs:
        factors[code] = _upsert_factor(
            db,
            source=sources["DEMO_FUEL"],
            activity_types=activity_types,
            code=code,
            name=name,
            activity_type_code=at,
            scope=scope,
            category=cat,
            unit_code=unit,
            factor_value=value,
            fuel_type=fuel,
            co2_factor="2.0" if code == "EF-NG-DEMO" else None,
            ch4_factor="0.0001" if code == "EF-NG-DEMO" else None,
            n2o_factor="0.00002" if code == "EF-NG-DEMO" else None,
            biogenic_co2_factor="0.05" if code == "EF-NG-DEMO" else None,
        )

    waste_specs = [
        ("EF-WASTE-HAZ-DEMO", "Demo hazardous waste", "hazardous_waste", "1.2"),
        ("EF-WASTE-NH-DEMO", "Demo non-hazardous waste", "non_hazardous_waste", "0.45"),
        ("EF-WASTE-REC-DEMO", "Demo recycled waste", "recycled_waste", "0.05"),
    ]
    for code, name, at, value in waste_specs:
        factors[code] = _upsert_factor(
            db,
            source=sources["DEMO_WASTE"],
            activity_types=activity_types,
            code=code,
            name=name,
            activity_type_code=at,
            scope="scope_3",
            category="waste_generated_in_operations",
            unit_code="kg",
            factor_value=value,
        )

    transport_specs = [
        ("EF-ROAD-FREIGHT-DEMO", "Demo road freight", "road_freight", "tonne_km", "0.12", "road"),
        ("EF-AIR-TRAVEL-DEMO", "Demo air travel", "air_travel", "km", "0.15", "air"),
        ("EF-COMMUTE-DEMO", "Demo employee commuting", "employee_commuting", "km", "0.17", "road"),
    ]
    for code, name, at, unit, value, mode in transport_specs:
        factors[code] = _upsert_factor(
            db,
            source=sources["DEMO_TRANSPORT"],
            activity_types=activity_types,
            code=code,
            name=name,
            activity_type_code=at,
            scope="scope_3",
            category=(
                "upstream_transportation"
                if at == "road_freight"
                else "business_travel"
                if at == "air_travel"
                else "employee_commuting"
            ),
            unit_code=unit,
            factor_value=value,
            transportation_mode=mode,
        )
    return factors


def seed_demo_inventory(
    db: Session,
    org: Organization,
    actor: User,
    factors: dict[str, EmissionFactor],
) -> None:
    period = db.execute(
        select(ReportingPeriod).where(
            ReportingPeriod.organization_id == org.id,
            ReportingPeriod.code == "2024-Q1",
        )
    ).scalar_one_or_none()
    if period is None:
        logger.warning("seed.carbon_inventory_skipped", reason="period_2024-Q1_missing")
        return

    from ecotrace.modules.facilities.infrastructure.models import Facility
    from ecotrace.modules.reference_data.application.unit_conversion import normalize_quantity

    activity_types = {a.code: a for a in db.execute(select(ActivityType)).scalars().all()}
    facility = db.execute(
        select(Facility).where(Facility.organization_id == org.id, Facility.code == "IZM-PROD")
    ).scalar_one_or_none()
    extra_samples = [
        ("seed:purchased_electricity:approved", "purchased_electricity", Decimal("10000"), "kWh"),
        ("seed:natural_gas_consumption:approved", "natural_gas_consumption", Decimal("500"), "m3"),
        ("seed:road_freight:approved", "road_freight", Decimal("1200"), "tonne_km"),
    ]
    for marker, type_code, qty, unit in extra_samples:
        existing = db.execute(
            select(ActivityRecord).where(
                ActivityRecord.organization_id == org.id,
                ActivityRecord.source_reference == marker,
            )
        ).scalar_one_or_none()
        if existing is None and type_code in activity_types and facility is not None:
            at = activity_types[type_code]
            normalized, normalized_unit = normalize_quantity(
                db, quantity=qty, unit_code=unit, activity_type=at
            )
            db.add(
                ActivityRecord(
                    organization_id=org.id,
                    facility_id=facility.id,
                    activity_type_id=at.id,
                    reporting_period_id=period.id,
                    activity_date=date(2024, 2, 10),
                    quantity=qty,
                    unit_code=unit,
                    normalized_quantity=normalized,
                    normalized_unit_code=normalized_unit,
                    status="approved",
                    source_reference=marker,
                    description="Seed approved activity",
                    created_by_user_id=actor.id,
                    updated_by_user_id=actor.id,
                    approved_by_user_id=actor.id,
                    approved_at=datetime.now(UTC),
                    row_version=1,
                    is_archived=False,
                )
            )
            db.flush()
            logger.info("seed.carbon_activity_created", marker=marker)

    inventory = db.execute(
        select(CarbonInventory).where(
            CarbonInventory.organization_id == org.id,
            CarbonInventory.name == "Demo Carbon Inventory 2024-01",
        )
    ).scalar_one_or_none()
    if inventory is None:
        inventory = CarbonInventory(
            organization_id=org.id,
            reporting_period_id=period.id,
            name="Demo Carbon Inventory 2024-01",
            description="Seeded demo inventory with a completed calculation run.",
            status="calculated",
            calculation_methodology_version=METHODOLOGY_VERSION,
            gwp_dataset_code=GWP_DATASET_AR5_DEMO,
            version=1,
            calculated_at=datetime.now(UTC),
            calculated_by_user_id=actor.id,
        )
        db.add(inventory)
        db.flush()
        logger.info("seed.inventory_created", name=inventory.name)
    else:
        if inventory.status == "approved":
            return

    existing_run = db.execute(
        select(CarbonCalculationRun).where(
            CarbonCalculationRun.inventory_id == inventory.id,
            CarbonCalculationRun.run_number == 1,
        )
    ).scalar_one_or_none()
    if existing_run is not None:
        inventory.latest_run_id = existing_run.id
        return

    gwp_rows = (
        db.execute(
            select(GwpValue).where(
                GwpValue.assessment_report_code == GWP_DATASET_AR5_DEMO,
                GwpValue.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    gwp = {r.gas_code: r.gwp_value for r in gwp_rows}
    gwp_snapshot = {k: str(v) for k, v in gwp.items()}

    run = CarbonCalculationRun(
        inventory_id=inventory.id,
        run_number=1,
        status="running",
        started_at=datetime.now(UTC),
        triggered_by_user_id=actor.id,
        engine_version=ENGINE_VERSION,
        partial_calculation=False,
        gwp_snapshot_json=gwp_snapshot,
        activity_record_count=0,
        calculated_record_count=0,
        skipped_record_count=0,
        failed_record_count=0,
    )
    db.add(run)
    db.flush()

    records = list(
        db.execute(
            select(ActivityRecord).where(
                ActivityRecord.organization_id == org.id,
                ActivityRecord.reporting_period_id == period.id,
                ActivityRecord.status == "approved",
                ActivityRecord.is_archived.is_(False),
            )
        )
        .scalars()
        .all()
    )
    calculated = 0
    failed = 0
    skipped = 0
    total = Decimal("0")
    for record in records:
        match = match_emission_factor(
            db,
            organization_id=org.id,
            activity_type_id=record.activity_type_id,
            activity_date=record.activity_date or record.period_start,
            activity_unit_code=record.normalized_unit_code,
            facility_id=record.facility_id,
        )
        if match.selected is None or match.ambiguous:
            failed += 1
            db.add(
                CarbonCalculationItem(
                    calculation_run_id=run.id,
                    inventory_id=inventory.id,
                    activity_record_id=record.id,
                    activity_quantity=record.quantity,
                    activity_unit_code=record.unit_code,
                    status="failed",
                    validation_errors_json=match.errors
                    or [{"code": "no_match", "message": "No factor"}],
                )
            )
            continue
        factor = match.selected
        activity_unit = get_unit(db, record.normalized_unit_code)
        factor_unit = get_unit(db, factor.unit_code)
        qty = convert_between(record.normalized_quantity, activity_unit, factor_unit)
        result = compute_emission_result(
            normalized_quantity=qty,
            normalized_unit_code=factor.unit_code,
            factor_value=factor.factor_value,
            factor_unit_code=factor.unit_code,
            co2_factor=factor.co2_factor,
            ch4_factor=factor.ch4_factor,
            n2o_factor=factor.n2o_factor,
            biogenic_co2_factor=factor.biogenic_co2_factor,
            ch4_gwp=gwp.get("CH4"),
            n2o_gwp=gwp.get("N2O"),
            other_gases_json=factor.other_gases_json,
        )
        db.add(
            CarbonCalculationItem(
                calculation_run_id=run.id,
                inventory_id=inventory.id,
                activity_record_id=record.id,
                emission_factor_id=factor.id,
                factor_source_id=factor.source_id,
                activity_quantity=record.quantity,
                activity_unit_code=record.unit_code,
                normalized_quantity=qty,
                normalized_unit_code=factor.unit_code,
                factor_value=factor.factor_value,
                factor_unit_code=factor.unit_code,
                scope=factor.scope,
                category=factor.category,
                subcategory=factor.subcategory,
                co2_kg=result["co2_kg"],
                ch4_kg=result["ch4_kg"],
                n2o_kg=result["n2o_kg"],
                biogenic_co2_kg=result["biogenic_co2_kg"],
                total_kg_co2e=result["total_kg_co2e"],
                matching_priority=match.priority,
                matching_reason=match.reason,
                calculation_formula=result["formula"],
                calculation_snapshot_json={
                    "engineVersion": ENGINE_VERSION,
                    "gwpDatasetCode": GWP_DATASET_AR5_DEMO,
                    "gwpValues": gwp_snapshot,
                    "disclaimer": DEMO_DISCLAIMER,
                    "factorCode": factor.code,
                    "factorVersion": factor.version,
                    "seeded": True,
                },
                status="calculated",
            )
        )
        calculated += 1
        total += result["total_kg_co2e"]

    run.activity_record_count = len(records)
    run.calculated_record_count = calculated
    run.failed_record_count = failed
    run.skipped_record_count = skipped
    run.total_kg_co2e = total
    run.completed_at = datetime.now(UTC)
    run.status = "completed" if failed == 0 else "completed_with_errors"
    inventory.status = "calculated"
    inventory.latest_run_id = run.id
    inventory.calculated_at = run.completed_at
    inventory.calculated_by_user_id = actor.id
    logger.info(
        "seed.inventory_run_created",
        calculated=calculated,
        failed=failed,
        total_kg=str(total),
    )


def seed_carbon(db: Session, org: Organization, actor: User) -> None:
    seed_gwp(db)
    factors = seed_factors(db)
    seed_demo_inventory(db, org, actor, factors)
    logger.info("seed.carbon_completed")
