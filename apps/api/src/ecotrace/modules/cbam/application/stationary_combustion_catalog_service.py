from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError, ValidationAppError
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionParameterSet,
)
from ecotrace.shared.domain.schemas import CamelModel

RESOLUTION_RESOLVED = 'RESOLVED'
RESOLUTION_UNRESOLVED = 'UNRESOLVED'
RESOLUTION_AMBIGUOUS = 'AMBIGUOUS'

ALLOWED_NCV_UNITS = frozenset({'TJ/Gg'})
ALLOWED_CO2_UNITS = frozenset({'kgCO2/TJ'})
ALLOWED_DENSITY_UNITS = frozenset({'kg/Sm3', 'kg/m3'})
ALLOWED_INPUT_BASIS = frozenset({'VOLUME', 'MASS'})
ALLOWED_ACTIVITY_UNITS = frozenset({'Sm3', 'm3', 'kg', 't', 'Gg'})
ALLOWED_PARAM_STATUSES = frozenset({'DRAFT', 'ACTIVE', 'ARCHIVED'})


class ProvenanceDTO(CamelModel):
    reference_source_id: uuid.UUID
    source_document: str
    source_table: str


class ResolvedStationaryCombustionParameters(CamelModel):
    fuel_id: uuid.UUID
    fuel_code: str
    fuel_name: str
    input_basis: str
    default_activity_unit: str
    parameter_set_id: uuid.UUID
    dataset_code: str
    dataset_version: str
    valid_from: date
    valid_until: date | None
    net_calorific_value: Decimal
    net_calorific_value_unit: str
    fossil_co2_emission_factor: Decimal
    fossil_co2_emission_factor_unit: str
    oxidation_factor: Decimal
    reference_density: Decimal | None
    reference_density_unit: str | None
    ncv_provenance: ProvenanceDTO
    co2_provenance: ProvenanceDTO
    oxidation_provenance: ProvenanceDTO


class StationaryCombustionParameterResolution(CamelModel):
    status: str
    message: str
    parameters: ResolvedStationaryCombustionParameters | None = None
    candidate_parameter_set_ids: list[uuid.UUID] = Field(default_factory=list)


class StationaryCombustionFuelCreate(CamelModel):
    code: str
    name: str
    input_basis: str
    default_activity_unit: str
    status: str = 'ACTIVE'
    description: str | None = None


class StationaryCombustionParameterSetCreate(CamelModel):
    fuel_id: uuid.UUID
    dataset_code: str
    dataset_version: str
    valid_from: date
    valid_until: date | None = None
    status: str = 'DRAFT'
    net_calorific_value: Decimal
    net_calorific_value_unit: str
    fossil_co2_emission_factor: Decimal
    fossil_co2_emission_factor_unit: str
    oxidation_factor: Decimal
    reference_density: Decimal | None = None
    reference_density_unit: str | None = None
    ncv_reference_source_id: uuid.UUID
    ncv_source_document: str
    ncv_source_table: str
    co2_reference_source_id: uuid.UUID
    co2_source_document: str
    co2_source_table: str
    oxidation_reference_source_id: uuid.UUID
    oxidation_source_document: str
    oxidation_source_table: str
    notes: str | None = None


def _periods_overlap(
    a_from: date,
    a_until: date | None,
    b_from: date,
    b_until: date | None,
) -> bool:
    a_end = a_until or date.max
    b_end = b_until or date.max
    return a_from <= b_end and b_from <= a_end


def _validate_parameter_payload(payload: StationaryCombustionParameterSetCreate) -> None:
    if payload.valid_until is not None and payload.valid_until < payload.valid_from:
        raise ValidationAppError(
            'valid_until must be on or after valid_from.',
            details=[{'field': 'validUntil', 'message': 'Must be >= validFrom.'}],
        )
    if payload.status not in ALLOWED_PARAM_STATUSES:
        raise ValidationAppError(f'Invalid parameter-set status: {payload.status}')
    if payload.net_calorific_value <= 0:
        raise ValidationAppError(
            'net_calorific_value must be greater than zero.',
            details=[{'field': 'netCalorificValue', 'message': 'Must be > 0.'}],
        )
    if payload.net_calorific_value_unit not in ALLOWED_NCV_UNITS:
        raise ValidationAppError(
            f'Unsupported NCV unit: {payload.net_calorific_value_unit}',
            details=[{'field': 'netCalorificValueUnit'}],
        )
    if payload.fossil_co2_emission_factor <= 0:
        raise ValidationAppError(
            'fossil_co2_emission_factor must be greater than zero.',
            details=[{'field': 'fossilCo2EmissionFactor', 'message': 'Must be > 0.'}],
        )
    if payload.fossil_co2_emission_factor_unit not in ALLOWED_CO2_UNITS:
        raise ValidationAppError(
            f'Unsupported CO2 factor unit: {payload.fossil_co2_emission_factor_unit}',
            details=[{'field': 'fossilCo2EmissionFactorUnit'}],
        )
    if payload.oxidation_factor < 0:
        raise ValidationAppError(
            'oxidation_factor cannot be negative.',
            details=[{'field': 'oxidationFactor', 'message': 'Must be >= 0.'}],
        )

    density = payload.reference_density
    density_unit = payload.reference_density_unit
    if density is None and density_unit is None:
        pass
    elif density is None or density_unit is None:
        raise ValidationAppError(
            'reference_density and reference_density_unit must both be null or both set.',
            details=[{'field': 'referenceDensity'}],
        )
    else:
        if density <= 0:
            raise ValidationAppError(
                'reference_density must be greater than zero when provided.',
                details=[{'field': 'referenceDensity', 'message': 'Must be > 0.'}],
            )
        if density_unit not in ALLOWED_DENSITY_UNITS:
            raise ValidationAppError(
                f'Unsupported density unit: {density_unit}',
                details=[{'field': 'referenceDensityUnit'}],
            )

    for field, value in (
        ('ncv_source_document', payload.ncv_source_document),
        ('ncv_source_table', payload.ncv_source_table),
        ('co2_source_document', payload.co2_source_document),
        ('co2_source_table', payload.co2_source_table),
        ('oxidation_source_document', payload.oxidation_source_document),
        ('oxidation_source_table', payload.oxidation_source_table),
    ):
        if not value.strip():
            raise ValidationAppError(f'{field} is required.')


def _assert_no_active_overlap(
    db: Session,
    *,
    fuel_id: uuid.UUID,
    valid_from: date,
    valid_until: date | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(CbamStationaryCombustionParameterSet).where(
        CbamStationaryCombustionParameterSet.fuel_id == fuel_id,
        CbamStationaryCombustionParameterSet.status == 'ACTIVE',
    )
    if exclude_id is not None:
        stmt = stmt.where(CbamStationaryCombustionParameterSet.id != exclude_id)
    for row in db.execute(stmt).scalars().all():
        if _periods_overlap(valid_from, valid_until, row.valid_from, row.valid_until):
            raise ConflictError(
                'Active stationary-combustion parameter sets cannot have overlapping '
                'validity periods for the same fuel.',
                details=[
                    {
                        'code': 'OVERLAPPING_ACTIVE_PARAMETER_SET',
                        'existingParameterSetId': str(row.id),
                        'datasetCode': row.dataset_code,
                        'datasetVersion': row.dataset_version,
                    }
                ],
            )


def create_fuel(
    db: Session,
    payload: StationaryCombustionFuelCreate,
) -> CbamStationaryCombustionFuel:
    ensure_platform_stationary_combustion_catalog(db)
    code = payload.code.strip().upper()
    if not code:
        raise ValidationAppError('Fuel code is required.')
    if payload.input_basis not in ALLOWED_INPUT_BASIS:
        raise ValidationAppError(f'Unsupported input_basis: {payload.input_basis}')
    if payload.default_activity_unit not in ALLOWED_ACTIVITY_UNITS:
        raise ValidationAppError(
            f'Unsupported default_activity_unit: {payload.default_activity_unit}'
        )
    exists = db.execute(
        select(CbamStationaryCombustionFuel.id).where(CbamStationaryCombustionFuel.code == code)
    ).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(f'Fuel code already exists: {code}')
    row = CbamStationaryCombustionFuel(
        code=code,
        name=payload.name.strip(),
        input_basis=payload.input_basis,
        default_activity_unit=payload.default_activity_unit,
        status=payload.status,
        description=payload.description,
    )
    db.add(row)
    db.flush()
    return row


def create_parameter_set(
    db: Session,
    payload: StationaryCombustionParameterSetCreate,
) -> CbamStationaryCombustionParameterSet:
    ensure_platform_stationary_combustion_catalog(db)
    _validate_parameter_payload(payload)
    fuel = db.get(CbamStationaryCombustionFuel, payload.fuel_id)
    if fuel is None:
        raise ValidationAppError('Fuel definition not found.')

    duplicate = db.execute(
        select(CbamStationaryCombustionParameterSet.id).where(
            CbamStationaryCombustionParameterSet.fuel_id == payload.fuel_id,
            CbamStationaryCombustionParameterSet.dataset_code == payload.dataset_code.strip(),
            CbamStationaryCombustionParameterSet.dataset_version
            == payload.dataset_version.strip(),
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ConflictError(
            'Dataset version already exists for this fuel.',
            details=[
                {
                    'code': 'DATASET_VERSION_NOT_UNIQUE',
                    'fuelId': str(payload.fuel_id),
                    'datasetCode': payload.dataset_code,
                    'datasetVersion': payload.dataset_version,
                }
            ],
        )

    if payload.status == 'ACTIVE':
        _assert_no_active_overlap(
            db,
            fuel_id=payload.fuel_id,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )

    row = CbamStationaryCombustionParameterSet(
        fuel_id=payload.fuel_id,
        dataset_code=payload.dataset_code.strip(),
        dataset_version=payload.dataset_version.strip(),
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        status=payload.status,
        net_calorific_value=payload.net_calorific_value,
        net_calorific_value_unit=payload.net_calorific_value_unit,
        fossil_co2_emission_factor=payload.fossil_co2_emission_factor,
        fossil_co2_emission_factor_unit=payload.fossil_co2_emission_factor_unit,
        oxidation_factor=payload.oxidation_factor,
        reference_density=payload.reference_density,
        reference_density_unit=payload.reference_density_unit,
        ncv_reference_source_id=payload.ncv_reference_source_id,
        ncv_source_document=payload.ncv_source_document.strip(),
        ncv_source_table=payload.ncv_source_table.strip(),
        co2_reference_source_id=payload.co2_reference_source_id,
        co2_source_document=payload.co2_source_document.strip(),
        co2_source_table=payload.co2_source_table.strip(),
        oxidation_reference_source_id=payload.oxidation_reference_source_id,
        oxidation_source_document=payload.oxidation_source_document.strip(),
        oxidation_source_table=payload.oxidation_source_table.strip(),
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    return row


def _to_resolved(
    fuel: CbamStationaryCombustionFuel,
    row: CbamStationaryCombustionParameterSet,
) -> ResolvedStationaryCombustionParameters:
    return ResolvedStationaryCombustionParameters(
        fuel_id=fuel.id,
        fuel_code=fuel.code,
        fuel_name=fuel.name,
        input_basis=fuel.input_basis,
        default_activity_unit=fuel.default_activity_unit,
        parameter_set_id=row.id,
        dataset_code=row.dataset_code,
        dataset_version=row.dataset_version,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        net_calorific_value=row.net_calorific_value,
        net_calorific_value_unit=row.net_calorific_value_unit,
        fossil_co2_emission_factor=row.fossil_co2_emission_factor,
        fossil_co2_emission_factor_unit=row.fossil_co2_emission_factor_unit,
        oxidation_factor=row.oxidation_factor,
        reference_density=row.reference_density,
        reference_density_unit=row.reference_density_unit,
        ncv_provenance=ProvenanceDTO(
            reference_source_id=row.ncv_reference_source_id,
            source_document=row.ncv_source_document,
            source_table=row.ncv_source_table,
        ),
        co2_provenance=ProvenanceDTO(
            reference_source_id=row.co2_reference_source_id,
            source_document=row.co2_source_document,
            source_table=row.co2_source_table,
        ),
        oxidation_provenance=ProvenanceDTO(
            reference_source_id=row.oxidation_reference_source_id,
            source_document=row.oxidation_source_document,
            source_table=row.oxidation_source_table,
        ),
    )


def resolve_stationary_combustion_parameters(
    db: Session,
    *,
    fuel_code: str,
    reference_date: date,
    dataset_version: str | None = None,
) -> StationaryCombustionParameterResolution:
    ensure_platform_stationary_combustion_catalog(db)
    code = fuel_code.strip().upper()
    fuel = db.execute(
        select(CbamStationaryCombustionFuel).where(CbamStationaryCombustionFuel.code == code)
    ).scalar_one_or_none()
    if fuel is None or fuel.status != 'ACTIVE':
        return StationaryCombustionParameterResolution(
            status=RESOLUTION_UNRESOLVED,
            message=f'No active stationary-combustion fuel found for code {code!r}.',
        )

    stmt = select(CbamStationaryCombustionParameterSet).where(
        CbamStationaryCombustionParameterSet.fuel_id == fuel.id,
        CbamStationaryCombustionParameterSet.status == 'ACTIVE',
        CbamStationaryCombustionParameterSet.valid_from <= reference_date,
        or_(
            CbamStationaryCombustionParameterSet.valid_until.is_(None),
            CbamStationaryCombustionParameterSet.valid_until >= reference_date,
        ),
    )
    if dataset_version is not None:
        stmt = stmt.where(
            CbamStationaryCombustionParameterSet.dataset_version == dataset_version.strip()
        )
    candidates = list(db.execute(stmt.order_by(CbamStationaryCombustionParameterSet.valid_from)).scalars())
    if not candidates:
        return StationaryCombustionParameterResolution(
            status=RESOLUTION_UNRESOLVED,
            message=(
                f'No active stationary-combustion parameter set applies for fuel {code!r} '
                f'on {reference_date.isoformat()}.'
            ),
        )
    if len(candidates) > 1:
        return StationaryCombustionParameterResolution(
            status=RESOLUTION_AMBIGUOUS,
            message=(
                f'More than one active stationary-combustion parameter set applies for fuel '
                f'{code!r} on {reference_date.isoformat()}.'
            ),
            candidate_parameter_set_ids=[row.id for row in candidates],
        )
    row = candidates[0]
    return StationaryCombustionParameterResolution(
        status=RESOLUTION_RESOLVED,
        message='Stationary-combustion parameters resolved.',
        parameters=_to_resolved(fuel, row),
        candidate_parameter_set_ids=[row.id],
    )


def get_parameter_set(
    db: Session,
    parameter_set_id: uuid.UUID,
) -> CbamStationaryCombustionParameterSet | None:
    return db.get(CbamStationaryCombustionParameterSet, parameter_set_id)


def list_active_parameter_sets_for_fuel(
    db: Session,
    fuel_id: uuid.UUID,
) -> list[CbamStationaryCombustionParameterSet]:
    return list(
        db.execute(
            select(CbamStationaryCombustionParameterSet).where(
                CbamStationaryCombustionParameterSet.fuel_id == fuel_id,
                CbamStationaryCombustionParameterSet.status == 'ACTIVE',
            )
        )
        .scalars()
        .all()
    )
