"""Conventional production-process CRUD, distribution, readiness."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import MASS_ACTIVITY_UNITS, require_unit
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    get_installation_for_org,
    get_product_profile_for_org,
    require_non_negative,
    require_usable_installation,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    get_direct_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    get_indirect_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import to_tonnes
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.production_process_constants import (
    ALL_CALCULATION_METHODS,
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    CANONICAL_MASS_UNIT,
    CODE_DATA_QUALITY_CODE_INVALID,
    CODE_DIRECT_EMISSIONS_ALLOCATION_NOT_READY,
    CODE_EXPORTED_ELECTRICITY_DATA_INCOMPLETE,
    CODE_EXPORTED_ELECTRICITY_FACTOR_REQUIRED,
    CODE_EXPORTED_ELECTRICITY_FIELDS_NOT_ALLOWED,
    CODE_EXPORTED_ELECTRICITY_PROVENANCE_REQUIRED,
    CODE_EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCH,
    CODE_HEAT_FIELDS_NOT_ALLOWED,
    CODE_INCOMPATIBLE_MASS_UNIT,
    CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY,
    CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING,
    CODE_MEASURABLE_HEAT_DATA_INCOMPLETE,
    CODE_PROCESS_ARCHIVED,
    CODE_PROCESS_METHOD_REQUIRED,
    CODE_PROCESS_METHOD_UNSUPPORTED,
    CODE_PROCESS_NAME_REQUIRED,
    CODE_PROCESS_PRODUCT_REQUIRED,
    CODE_PRODUCT_DISTRIBUTION_INCOMPLETE,
    CODE_PRODUCT_DISTRIBUTION_UNBALANCED,
    CODE_PRODUCTION_QUANTITY_MISSING,
    CODE_TARGET_PRODUCT_INVALID,
    CODE_WASTE_GAS_DATA_INCOMPLETE,
    CODE_WASTE_GAS_FIELDS_NOT_ALLOWED,
    DISABLED_CALCULATION_METHODS,
    ELECTRICITY_UNIT_MWH,
    EXPORTED_ELECTRICITY_FACTOR_UNIT,
    EXPORTED_ELECTRICITY_QUANTITY_UNIT,
    EXPORTED_ELECTRICITY_RECONCILIATION_MATCHED,
    EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCHED,
    EXPORTED_ELECTRICITY_RECONCILIATION_NOT_APPLICABLE,
    EXPORTED_ELECTRICITY_RECONCILIATION_NOT_COMPARABLE,
    EXPORTED_ELECTRICITY_RECONCILIATION_NOTE,
    HEAT_FACTOR_UNIT,
    HEAT_QUANTITY_UNIT,
    METHOD_CONVENTIONAL,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    PROCESS_STATUS_ARCHIVED,
    PROCESS_STATUS_DRAFT,
    PRODUCTION_QUANTITY_SOURCE,
    PRODUCTION_QUANTITY_SOURCE_NOTE,
    READINESS_EMPTY,
    READINESS_INCOMPLETE,
    READINESS_READY,
    READINESS_STALE,
    READINESS_UNBALANCED,
    RESULT_UNIT_TCO2,
    RESULT_UNIT_TCO2E,
    SUPPORTED_CALCULATION_METHODS,
    WASTE_GAS_QUANTITY_UNIT,
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.production_process_controlled_lists import (
    PROCESS_FIELD_MAP,
    data_quality_codes,
    data_quality_justification_codes,
    data_verification_codes,
    get_production_process_controlled_list,
    list_production_process_controlled_lists,
    workbook_extraction_metadata,
)
from ecotrace.modules.cbam.application.production_process_math import (
    compute_distribution_balance,
    compute_exported_electricity_attribution,
    compute_measurable_heat_attribution,
    compute_waste_gas_attribution,
)
from ecotrace.modules.cbam.application.production_profile_link import (
    require_linkable_product_profile,
)
from ecotrace.modules.cbam.application.purchased_electricity_math import to_mwh
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    get_exported_electricity_mwh_by_installation,
    get_purchased_electricity_summary,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamProductionProcess,
    CbamProductionProcessProductUse,
    CbamProductionRecord,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

ReadinessStatus = Literal["EMPTY", "INCOMPLETE", "UNBALANCED", "STALE", "READY"]


class ProductionProcessCreate(CamelModel):
    installation_profile_id: uuid.UUID
    name: str | None = None
    identifier: str | None = None
    calculation_method: str = METHOD_CONVENTIONAL
    product_profile_version_id: uuid.UUID | None = None
    produced_quantity: Decimal | None = None
    produced_quantity_unit: str | None = None
    marketed_quantity: Decimal | None = None
    marketed_quantity_unit: str | None = None
    non_cbam_quantity: Decimal | None = None
    non_cbam_quantity_unit: str | None = None
    has_measurable_heat: bool | None = None
    heat_imported_quantity: Decimal | None = None
    heat_imported_unit: str | None = None
    heat_exported_quantity: Decimal | None = None
    heat_exported_unit: str | None = None
    heat_imported_ef: Decimal | None = None
    heat_exported_ef: Decimal | None = None
    heat_ef_unit: str | None = None
    heat_factor_source: str | None = None
    heat_factor_document: str | None = None
    has_waste_gas: bool | None = None
    waste_gas_imported_quantity: Decimal | None = None
    waste_gas_imported_unit: str | None = None
    waste_gas_exported_quantity: Decimal | None = None
    waste_gas_exported_unit: str | None = None
    waste_gas_provenance: str | None = None
    has_exported_electricity: bool | None = None
    exported_electricity_quantity: Decimal | None = None
    exported_electricity_unit: str | None = None
    exported_electricity_emission_factor: Decimal | None = None
    exported_electricity_ef_unit: str | None = None
    exported_electricity_provenance: str | None = None
    data_quality_code: str | None = None
    data_verification_code: str | None = None
    data_quality_justification_code: str | None = None
    notes: str | None = None


class ProductionProcessUpdate(CamelModel):
    row_version: int
    name: str | None = None
    identifier: str | None = None
    calculation_method: str | None = None
    product_profile_version_id: uuid.UUID | None = None
    produced_quantity: Decimal | None = None
    produced_quantity_unit: str | None = None
    marketed_quantity: Decimal | None = None
    marketed_quantity_unit: str | None = None
    non_cbam_quantity: Decimal | None = None
    non_cbam_quantity_unit: str | None = None
    has_measurable_heat: bool | None = None
    heat_imported_quantity: Decimal | None = None
    heat_imported_unit: str | None = None
    heat_exported_quantity: Decimal | None = None
    heat_exported_unit: str | None = None
    heat_imported_ef: Decimal | None = None
    heat_exported_ef: Decimal | None = None
    heat_ef_unit: str | None = None
    heat_factor_source: str | None = None
    heat_factor_document: str | None = None
    has_waste_gas: bool | None = None
    waste_gas_imported_quantity: Decimal | None = None
    waste_gas_imported_unit: str | None = None
    waste_gas_exported_quantity: Decimal | None = None
    waste_gas_exported_unit: str | None = None
    waste_gas_provenance: str | None = None
    has_exported_electricity: bool | None = None
    exported_electricity_quantity: Decimal | None = None
    exported_electricity_unit: str | None = None
    exported_electricity_emission_factor: Decimal | None = None
    exported_electricity_ef_unit: str | None = None
    exported_electricity_provenance: str | None = None
    data_quality_code: str | None = None
    data_verification_code: str | None = None
    data_quality_justification_code: str | None = None
    notes: str | None = None


class ProductionProcessVersionRequest(CamelModel):
    row_version: int


class ProductUseCreate(CamelModel):
    target_product_profile_version_id: uuid.UUID
    quantity: Decimal
    unit: str = CANONICAL_MASS_UNIT
    notes: str | None = None


class ProductUseUpdate(CamelModel):
    row_version: int
    quantity: Decimal | None = None
    unit: str | None = None
    notes: str | None = None
    target_product_profile_version_id: uuid.UUID | None = None


class ProductUseResponse(CamelModel):
    id: uuid.UUID
    process_id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    source_product_profile_version_id: uuid.UUID | None
    target_product_profile_version_id: uuid.UUID
    quantity: Decimal
    unit: str
    quantity_tonnes: Decimal | None
    notes: str | None
    row_version: int


class ControlledListItemResponse(CamelModel):
    code: str
    label_en: str
    description_en: str | None
    sort_order: int
    workbook_ref: str


class ControlledListResponse(CamelModel):
    list_code: str
    title_en: str
    workbook_named_range: str
    workbook_sheet: str
    help_en: str | None
    items: list[ControlledListItemResponse]


class ProductionProcessMetadataResponse(CamelModel):
    methodology_code: str
    methodology_version: str
    workbook_filename: str
    workbook_sha256: str
    workbook_formula_refs: str
    supported_calculation_methods: list[str]
    disabled_calculation_methods: list[str]
    production_quantity_source: str
    production_quantity_source_note: str
    field_map: dict[str, dict[str, str]]
    extraction: dict[str, str]
    controlled_lists: list[ControlledListResponse]


class AllocationLinkView(CamelModel):
    """Read-only link to current DEA/IEA allocation for the process product profile.

    For IEA, ``product_allocated_value`` and ``allocated_indirect_emissions_tco2e`` are the
    same immutable product-row tCO2e; ``allocated_electricity_mwh`` is the matching MWh.
    Values are never recalculated here — only resolved from the current snapshot.
    """

    current_result_id: uuid.UUID | None
    is_ready: bool
    is_stale: bool
    stale_reason_codes: list[str]
    product_allocated_value: Decimal | None
    allocated_electricity_mwh: Decimal | None = None
    allocated_indirect_emissions_tco2e: Decimal | None = None
    result_unit: str | None
    electricity_unit: str | None = None
    blocking_code: str | None


class ExportedElectricityView(CamelModel):
    exported_electricity_mwh: Decimal | None
    electricity_unit: str
    source: str
    note: str


class ProcessExportedElectricityView(CamelModel):
    """Process-level D_Processes L71/L72 entry plus the server-calculated T72 term.

    ``attributed_direct_tco2e`` is the workbook ``T72 = -L71*L72``; it is always computed
    by the server and is never derived from the facility purchased-electricity export.
    """

    has_exported_electricity: bool | None
    quantity: Decimal | None
    quantity_unit: str | None
    quantity_mwh: Decimal | None
    emission_factor: Decimal | None
    ef_unit: str | None
    provenance: str | None
    calculation_status: str
    attributed_direct_tco2e: Decimal | None
    formula_ref: str | None
    facility_exported_electricity_mwh: Decimal | None
    installation_facility_exported_electricity_mwh: Decimal | None
    installation_process_exported_electricity_mwh: Decimal | None
    reconciliation_status: str
    reconciliation_difference_mwh: Decimal | None
    reconciliation_note: str
    electricity_unit: str
    factor_unit: str


class _IeaProductSnapshot:
    __slots__ = ("electricity_mwh", "emissions_tco2e")

    def __init__(self, electricity_mwh: Decimal, emissions_tco2e: Decimal) -> None:
        self.electricity_mwh = electricity_mwh
        self.emissions_tco2e = emissions_tco2e


class _BindingAllocationBundle:
    """Bounded binding-scoped DEA/IEA/PE snapshots for process list/detail (no N+1)."""

    __slots__ = (
        "dea_by_profile",
        "dea_current_result_id",
        "dea_is_stale",
        "dea_result_unit",
        "dea_stale_reason_codes",
        "exported_electricity",
        "facility_exported_by_installation",
        "iea_by_profile",
        "iea_current_result_id",
        "iea_emissions_unit",
        "iea_is_stale",
        "iea_stale_reason_codes",
        "process_exported_by_installation",
    )

    def __init__(
        self,
        *,
        dea_current_result_id: uuid.UUID | None,
        dea_is_stale: bool,
        dea_stale_reason_codes: list[str],
        dea_result_unit: str | None,
        dea_by_profile: dict[uuid.UUID, Decimal],
        iea_current_result_id: uuid.UUID | None,
        iea_is_stale: bool,
        iea_stale_reason_codes: list[str],
        iea_emissions_unit: str | None,
        iea_by_profile: dict[uuid.UUID, _IeaProductSnapshot],
        exported_electricity: ExportedElectricityView,
        facility_exported_by_installation: dict[uuid.UUID, Decimal],
        process_exported_by_installation: dict[uuid.UUID, Decimal],
    ) -> None:
        self.dea_current_result_id = dea_current_result_id
        self.dea_is_stale = dea_is_stale
        self.dea_stale_reason_codes = dea_stale_reason_codes
        self.dea_result_unit = dea_result_unit
        self.dea_by_profile = dea_by_profile
        self.iea_current_result_id = iea_current_result_id
        self.iea_is_stale = iea_is_stale
        self.iea_stale_reason_codes = iea_stale_reason_codes
        self.iea_emissions_unit = iea_emissions_unit
        self.iea_by_profile = iea_by_profile
        self.exported_electricity = exported_electricity
        self.facility_exported_by_installation = facility_exported_by_installation
        self.process_exported_by_installation = process_exported_by_installation


class ProductionReconciliationView(CamelModel):
    process_produced_tonnes: Decimal | None
    production_records_tonnes: Decimal | None
    difference_tonnes: Decimal | None
    source: str
    note: str


class HeatView(CamelModel):
    has_measurable_heat: bool | None
    imported_quantity: Decimal | None
    imported_unit: str | None
    exported_quantity: Decimal | None
    exported_unit: str | None
    imported_ef: Decimal | None
    exported_ef: Decimal | None
    ef_unit: str | None
    factor_source: str | None
    factor_document: str | None
    calculation_status: str
    attributed_tco2: Decimal | None
    formula_ref: str | None


class WasteGasView(CamelModel):
    has_waste_gas: bool | None
    imported_quantity: Decimal | None
    imported_unit: str | None
    exported_quantity: Decimal | None
    exported_unit: str | None
    provenance: str | None
    calculation_status: str
    attributed_tco2: Decimal | None
    ef_tco2_per_tj: Decimal | None
    formula_ref: str | None
    note: str | None


class DistributionView(CamelModel):
    produced_quantity: Decimal | None
    produced_quantity_unit: str | None
    produced_tonnes: Decimal | None
    marketed_quantity: Decimal | None
    marketed_quantity_unit: str | None
    marketed_tonnes: Decimal | None
    other_cbam_tonnes: Decimal
    non_cbam_quantity: Decimal | None
    non_cbam_quantity_unit: str | None
    non_cbam_tonnes: Decimal | None
    distributed_tonnes: Decimal | None
    remaining_tonnes: Decimal | None
    balance_status: str
    all_to_market: bool | None
    market_share: Decimal | None
    product_uses: list[ProductUseResponse]


class ProductionProcessReadiness(CamelModel):
    process_id: uuid.UUID | None
    reporting_period_binding_id: uuid.UUID
    status: ReadinessStatus
    blocking_issue_codes: list[str]
    informational_codes: list[str]
    balance_status: str | None
    remaining_tonnes: Decimal | None


class ProductionProcessSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    process_count: int
    draft_count: int
    archived_count: int
    ready_count: int
    unbalanced_count: int
    processes: list[ProductionProcessReadiness]


class ProductionProcessResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None
    name: str | None
    identifier: str | None
    calculation_method: str
    status: str
    notes: str | None
    row_version: int
    readiness: ProductionProcessReadiness
    distribution: DistributionView
    production_reconciliation: ProductionReconciliationView
    direct_emissions_allocation: AllocationLinkView
    indirect_emissions_allocation: AllocationLinkView
    exported_electricity: ExportedElectricityView
    process_exported_electricity: ProcessExportedElectricityView
    measurable_heat: HeatView
    waste_gas: WasteGasView
    data_quality_code: str | None
    data_verification_code: str | None
    data_quality_justification_code: str | None


def _require_mass_unit(unit: str | None, *, field: str) -> str | None:
    if unit is None:
        return None
    normalized = require_unit(unit)
    if normalized not in MASS_ACTIVITY_UNITS:
        raise ValidationAppError(
            f"{field} must use a mass unit (kg, t, or Gg).",
            details=[{"code": CODE_INCOMPATIBLE_MASS_UNIT, "field": field}],
        )
    return normalized


def _optional_tonnes(quantity: Decimal | None, unit: str | None) -> Decimal | None:
    if quantity is None or unit is None:
        return None
    return to_tonnes(quantity, unit)


def _validate_method(method: str) -> str:
    if method not in ALL_CALCULATION_METHODS:
        raise ValidationAppError(
            f"Unknown calculation method: {method}",
            details=[{"code": CODE_PROCESS_METHOD_REQUIRED, "method": method}],
        )
    if method in DISABLED_CALCULATION_METHODS:
        raise BusinessRuleError(
            f"Calculation method {method} is not supported in Phase 9A. "
            f"Only {METHOD_CONVENTIONAL} is active.",
            details=[{"code": CODE_PROCESS_METHOD_UNSUPPORTED, "method": method}],
        )
    if method not in SUPPORTED_CALCULATION_METHODS:
        raise BusinessRuleError(
            f"Calculation method {method} is not supported.",
            details=[{"code": CODE_PROCESS_METHOD_UNSUPPORTED, "method": method}],
        )
    return method


def _validate_dq_codes(
    quality: str | None,
    verification: str | None,
    justification: str | None,
) -> None:
    if quality is not None and quality not in data_quality_codes():
        raise ValidationAppError(
            f"Invalid data quality code: {quality}",
            details=[{"code": CODE_DATA_QUALITY_CODE_INVALID, "field": "dataQualityCode"}],
        )
    if verification is not None and verification not in data_verification_codes():
        raise ValidationAppError(
            f"Invalid data verification code: {verification}",
            details=[{"code": CODE_DATA_QUALITY_CODE_INVALID, "field": "dataVerificationCode"}],
        )
    if justification is not None and justification not in data_quality_justification_codes():
        raise ValidationAppError(
            f"Invalid data quality justification code: {justification}",
            details=[
                {
                    "code": CODE_DATA_QUALITY_CODE_INVALID,
                    "field": "dataQualityJustificationCode",
                }
            ],
        )


def _exported_quantity_mwh(row: CbamProductionProcess) -> Decimal | None:
    """Process L71 in MWh, or ``None`` when the entry is absent or not convertible."""
    quantity = row.exported_electricity_quantity
    unit = row.exported_electricity_unit
    if quantity is None or unit is None:
        return None
    try:
        return to_mwh(quantity, unit)
    except ValueError:
        return None


def _clear_heat_fields(row: CbamProductionProcess) -> None:
    row.heat_imported_quantity = None
    row.heat_imported_unit = None
    row.heat_exported_quantity = None
    row.heat_exported_unit = None
    row.heat_imported_ef = None
    row.heat_exported_ef = None
    row.heat_ef_unit = None
    row.heat_factor_source = None
    row.heat_factor_document = None


def _clear_waste_fields(row: CbamProductionProcess) -> None:
    row.waste_gas_imported_quantity = None
    row.waste_gas_imported_unit = None
    row.waste_gas_exported_quantity = None
    row.waste_gas_exported_unit = None
    row.waste_gas_provenance = None


_EXPORTED_ELECTRICITY_FIELDS = (
    "exported_electricity_quantity",
    "exported_electricity_unit",
    "exported_electricity_emission_factor",
    "exported_electricity_ef_unit",
    "exported_electricity_provenance",
)


def _clear_exported_electricity_fields(row: CbamProductionProcess) -> None:
    for field in _EXPORTED_ELECTRICITY_FIELDS:
        setattr(row, field, None)


def _validate_exported_electricity_quantity_unit(unit: str) -> str:
    normalized = require_unit(unit)
    if normalized != EXPORTED_ELECTRICITY_QUANTITY_UNIT:
        raise ValidationAppError(
            f"Exported electricity unit must be {EXPORTED_ELECTRICITY_QUANTITY_UNIT}.",
            details=[{"field": "exportedElectricityUnit"}],
        )
    return normalized


def _validate_exported_electricity_ef_unit(unit: str) -> str:
    if unit != EXPORTED_ELECTRICITY_FACTOR_UNIT:
        raise ValidationAppError(
            f"Exported electricity factor unit must be {EXPORTED_ELECTRICITY_FACTOR_UNIT}.",
            details=[{"field": "exportedElectricityEfUnit"}],
        )
    return unit


def _apply_exported_electricity_constraints(
    *,
    has_exported: bool | None,
    quantity: Decimal | None,
    quantity_unit: str | None,
    emission_factor: Decimal | None,
    ef_unit: str | None,
    provenance: str | None,
    reject_fields_when_false: bool,
) -> dict[str, Any]:
    values = (quantity, quantity_unit, emission_factor, ef_unit, provenance)
    if has_exported is False:
        if reject_fields_when_false and any(v is not None for v in values):
            raise ValidationAppError(
                "Exported-electricity fields must be null when hasExportedElectricity is false.",
                details=[{"code": CODE_EXPORTED_ELECTRICITY_FIELDS_NOT_ALLOWED}],
            )
        return {
            "has_exported_electricity": False,
            "exported_electricity_quantity": None,
            "exported_electricity_unit": None,
            "exported_electricity_emission_factor": None,
            "exported_electricity_ef_unit": None,
            "exported_electricity_provenance": None,
        }
    out: dict[str, Any] = {"has_exported_electricity": has_exported}
    if quantity is not None:
        require_non_negative(quantity, field="exportedElectricityQuantity")
        out["exported_electricity_quantity"] = quantity
    if quantity_unit is not None:
        out["exported_electricity_unit"] = _validate_exported_electricity_quantity_unit(
            quantity_unit
        )
    if emission_factor is not None:
        require_non_negative(emission_factor, field="exportedElectricityEmissionFactor")
        out["exported_electricity_emission_factor"] = emission_factor
    if ef_unit is not None:
        out["exported_electricity_ef_unit"] = _validate_exported_electricity_ef_unit(ef_unit)
    if provenance is not None:
        out["exported_electricity_provenance"] = provenance.strip() or None
    return out


def _exported_electricity_blocking_codes(row: CbamProductionProcess) -> list[str]:
    """Readiness codes for a process that answered "yes" to exported electricity."""
    if row.has_exported_electricity is not True:
        return []
    codes: list[str] = []
    if row.exported_electricity_quantity is None or row.exported_electricity_unit is None:
        codes.append(CODE_EXPORTED_ELECTRICITY_DATA_INCOMPLETE)
    if row.exported_electricity_emission_factor is None or row.exported_electricity_ef_unit is None:
        codes.append(CODE_EXPORTED_ELECTRICITY_FACTOR_REQUIRED)
    if not (row.exported_electricity_provenance or "").strip():
        codes.append(CODE_EXPORTED_ELECTRICITY_PROVENANCE_REQUIRED)
    return codes


def _process_exported_electricity_view(
    row: CbamProductionProcess,
    bundle: _BindingAllocationBundle,
) -> ProcessExportedElectricityView:
    attribution = compute_exported_electricity_attribution(
        has_exported_electricity=row.has_exported_electricity,
        quantity_mwh=_exported_quantity_mwh(row),
        emission_factor=row.exported_electricity_emission_factor,
    )
    installation_facility = bundle.facility_exported_by_installation.get(
        row.installation_profile_id
    )
    installation_process = bundle.process_exported_by_installation.get(row.installation_profile_id)
    difference: Decimal | None = None
    if installation_facility is None and installation_process is None:
        status = EXPORTED_ELECTRICITY_RECONCILIATION_NOT_APPLICABLE
    elif installation_facility is None or installation_process is None:
        status = EXPORTED_ELECTRICITY_RECONCILIATION_NOT_COMPARABLE
    else:
        difference = installation_process - installation_facility
        status = (
            EXPORTED_ELECTRICITY_RECONCILIATION_MATCHED
            if difference == Decimal("0")
            else EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCHED
        )
    return ProcessExportedElectricityView(
        has_exported_electricity=row.has_exported_electricity,
        quantity=row.exported_electricity_quantity,
        quantity_unit=row.exported_electricity_unit,
        quantity_mwh=_exported_quantity_mwh(row),
        emission_factor=row.exported_electricity_emission_factor,
        ef_unit=row.exported_electricity_ef_unit,
        provenance=row.exported_electricity_provenance,
        calculation_status=attribution.status,
        attributed_direct_tco2e=attribution.attributed_direct_tco2e,
        formula_ref=attribution.formula_ref,
        facility_exported_electricity_mwh=(bundle.exported_electricity.exported_electricity_mwh),
        installation_facility_exported_electricity_mwh=installation_facility,
        installation_process_exported_electricity_mwh=installation_process,
        reconciliation_status=status,
        reconciliation_difference_mwh=difference,
        reconciliation_note=EXPORTED_ELECTRICITY_RECONCILIATION_NOTE,
        electricity_unit=EXPORTED_ELECTRICITY_QUANTITY_UNIT,
        factor_unit=EXPORTED_ELECTRICITY_FACTOR_UNIT,
    )


def _apply_heat_constraints(
    *,
    has_heat: bool | None,
    imported_q: Decimal | None,
    imported_u: str | None,
    exported_q: Decimal | None,
    exported_u: str | None,
    imported_ef: Decimal | None,
    exported_ef: Decimal | None,
    ef_unit: str | None,
    factor_source: str | None,
    factor_document: str | None,
    reject_fields_when_false: bool,
) -> dict[str, Any]:
    heat_fields = (
        imported_q,
        imported_u,
        exported_q,
        exported_u,
        imported_ef,
        exported_ef,
        ef_unit,
        factor_source,
        factor_document,
    )
    if has_heat is False:
        if reject_fields_when_false and any(v is not None for v in heat_fields):
            raise ValidationAppError(
                "Measurable-heat fields must be null when hasMeasurableHeat is false.",
                details=[{"code": CODE_HEAT_FIELDS_NOT_ALLOWED}],
            )
        return {
            "has_measurable_heat": False,
            "heat_imported_quantity": None,
            "heat_imported_unit": None,
            "heat_exported_quantity": None,
            "heat_exported_unit": None,
            "heat_imported_ef": None,
            "heat_exported_ef": None,
            "heat_ef_unit": None,
            "heat_factor_source": None,
            "heat_factor_document": None,
        }
    out: dict[str, Any] = {"has_measurable_heat": has_heat}
    if imported_q is not None:
        require_non_negative(imported_q, field="heatImportedQuantity")
        out["heat_imported_quantity"] = imported_q
    if exported_q is not None:
        require_non_negative(exported_q, field="heatExportedQuantity")
        out["heat_exported_quantity"] = exported_q
    if imported_u is not None:
        u = require_unit(imported_u)
        if u != HEAT_QUANTITY_UNIT:
            raise ValidationAppError(
                f"Heat quantity unit must be {HEAT_QUANTITY_UNIT}.",
                details=[{"field": "heatImportedUnit"}],
            )
        out["heat_imported_unit"] = u
    if exported_u is not None:
        u = require_unit(exported_u)
        if u != HEAT_QUANTITY_UNIT:
            raise ValidationAppError(
                f"Heat quantity unit must be {HEAT_QUANTITY_UNIT}.",
                details=[{"field": "heatExportedUnit"}],
            )
        out["heat_exported_unit"] = u
    if imported_ef is not None:
        require_non_negative(imported_ef, field="heatImportedEf")
        out["heat_imported_ef"] = imported_ef
    if exported_ef is not None:
        require_non_negative(exported_ef, field="heatExportedEf")
        out["heat_exported_ef"] = exported_ef
    if ef_unit is not None:
        if ef_unit != HEAT_FACTOR_UNIT:
            raise ValidationAppError(
                f"Heat EF unit must be {HEAT_FACTOR_UNIT}.",
                details=[{"field": "heatEfUnit"}],
            )
        out["heat_ef_unit"] = ef_unit
    if factor_source is not None:
        out["heat_factor_source"] = factor_source.strip() or None
    if factor_document is not None:
        out["heat_factor_document"] = factor_document.strip() or None
    return out


def _apply_waste_constraints(
    *,
    has_waste: bool | None,
    imported_q: Decimal | None,
    imported_u: str | None,
    exported_q: Decimal | None,
    exported_u: str | None,
    provenance: str | None,
    reject_fields_when_false: bool,
) -> dict[str, Any]:
    waste_fields = (imported_q, imported_u, exported_q, exported_u, provenance)
    if has_waste is False:
        if reject_fields_when_false and any(v is not None for v in waste_fields):
            raise ValidationAppError(
                "Waste-gas fields must be null when hasWasteGas is false.",
                details=[{"code": CODE_WASTE_GAS_FIELDS_NOT_ALLOWED}],
            )
        return {
            "has_waste_gas": False,
            "waste_gas_imported_quantity": None,
            "waste_gas_imported_unit": None,
            "waste_gas_exported_quantity": None,
            "waste_gas_exported_unit": None,
            "waste_gas_provenance": None,
        }
    out: dict[str, Any] = {"has_waste_gas": has_waste}
    if imported_q is not None:
        require_non_negative(imported_q, field="wasteGasImportedQuantity")
        out["waste_gas_imported_quantity"] = imported_q
    if exported_q is not None:
        require_non_negative(exported_q, field="wasteGasExportedQuantity")
        out["waste_gas_exported_quantity"] = exported_q
    if imported_u is not None:
        u = require_unit(imported_u)
        if u != WASTE_GAS_QUANTITY_UNIT:
            raise ValidationAppError(
                f"Waste-gas quantity unit must be {WASTE_GAS_QUANTITY_UNIT}.",
                details=[{"field": "wasteGasImportedUnit"}],
            )
        out["waste_gas_imported_unit"] = u
    if exported_u is not None:
        u = require_unit(exported_u)
        if u != WASTE_GAS_QUANTITY_UNIT:
            raise ValidationAppError(
                f"Waste-gas quantity unit must be {WASTE_GAS_QUANTITY_UNIT}.",
                details=[{"field": "wasteGasExportedUnit"}],
            )
        out["waste_gas_exported_unit"] = u
    if provenance is not None:
        out["waste_gas_provenance"] = provenance.strip() or None
    return out


def _get_process(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
) -> CbamProductionProcess:
    row = db.get(CbamProductionProcess, process_id)
    if (
        row is None
        or row.organization_id != organization_id
        or row.reporting_period_binding_id != binding_id
    ):
        raise NotFoundError("CBAM production process not found.")
    return row


def _list_uses(db: Session, process_id: uuid.UUID) -> list[CbamProductionProcessProductUse]:
    return list(
        db.execute(
            select(CbamProductionProcessProductUse).where(
                CbamProductionProcessProductUse.process_id == process_id
            )
        )
        .scalars()
        .all()
    )


def _list_uses_for_processes(
    db: Session, process_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[CbamProductionProcessProductUse]]:
    if not process_ids:
        return {}
    rows = list(
        db.execute(
            select(CbamProductionProcessProductUse).where(
                CbamProductionProcessProductUse.process_id.in_(process_ids)
            )
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, list[CbamProductionProcessProductUse]] = {pid: [] for pid in process_ids}
    for row in rows:
        out.setdefault(row.process_id, []).append(row)
    return out


def _sum_production_records_tonnes(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    profile_id: uuid.UUID | None,
) -> Decimal | None:
    if profile_id is None:
        return None
    rows = list(
        db.execute(
            select(CbamProductionRecord).where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.product_profile_version_id == profile_id,
                CbamProductionRecord.status == "active",
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return Decimal("0")
    total = Decimal("0")
    for r in rows:
        total += to_tonnes(r.quantity, r.unit)
    return total


def _product_use_response(
    use: CbamProductionProcessProductUse,
    *,
    source_profile_id: uuid.UUID | None,
) -> ProductUseResponse:
    qty_t: Decimal | None = None
    try:
        qty_t = to_tonnes(use.quantity, use.unit)
    except Exception:
        qty_t = None
    return ProductUseResponse(
        id=use.id,
        process_id=use.process_id,
        organization_id=use.organization_id,
        reporting_period_binding_id=use.reporting_period_binding_id,
        source_product_profile_version_id=source_profile_id,
        target_product_profile_version_id=use.target_product_profile_version_id,
        quantity=use.quantity,
        unit=use.unit,
        quantity_tonnes=qty_t,
        notes=use.notes,
        row_version=use.row_version,
    )


def _load_binding_allocation_bundle(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> _BindingAllocationBundle:
    """Load DEA/IEA/PE current snapshots once per binding (bounded query set)."""
    dea_summary = get_direct_emissions_allocation_summary(db, user, organization_id, binding_id)
    iea_summary = get_indirect_emissions_allocation_summary(db, user, organization_id, binding_id)
    pe = get_purchased_electricity_summary(db, user, organization_id, binding_id)

    dea_by_profile: dict[uuid.UUID, Decimal] = {}
    if dea_summary.current_result_id is not None and not dea_summary.current_is_stale:
        for item in dea_summary.totals_by_product_profile:
            profile_key = item.get("productProfileVersionId")
            value = item.get("finalAllocatedFossilCo2Tonnes")
            if profile_key is None or value is None:
                continue
            dea_by_profile[uuid.UUID(str(profile_key))] = Decimal(str(value))

    iea_by_profile: dict[uuid.UUID, _IeaProductSnapshot] = {}
    if iea_summary.current_result_id is not None and not iea_summary.current_is_stale:
        for item in iea_summary.totals_by_product_profile:
            profile_key = item.get("productProfileVersionId")
            elec = item.get("finalAllocatedElectricityMwh")
            emissions = item.get("finalAllocatedIndirectEmissionsTco2e")
            if profile_key is None or elec is None or emissions is None:
                continue
            iea_by_profile[uuid.UUID(str(profile_key))] = _IeaProductSnapshot(
                electricity_mwh=Decimal(str(elec)),
                emissions_tco2e=Decimal(str(emissions)),
            )

    exported = ExportedElectricityView(
        exported_electricity_mwh=pe.total_exported_electricity_mwh,
        electricity_unit=ELECTRICITY_UNIT_MWH,
        source="purchased_electricity_current",
        note=(
            "Reused from purchased-electricity immutable/current results. "
            "Not subtracted from indirect consumption (SEE T66 vs T72)."
        ),
    )
    facility_exported = get_exported_electricity_mwh_by_installation(
        db, organization_id, binding_id
    )
    process_exported: dict[uuid.UUID, Decimal] = {}
    for process_row in db.execute(
        select(CbamProductionProcess).where(
            CbamProductionProcess.organization_id == organization_id,
            CbamProductionProcess.reporting_period_binding_id == binding_id,
            CbamProductionProcess.status == PROCESS_STATUS_DRAFT,
            CbamProductionProcess.has_exported_electricity.is_(True),
        )
    ).scalars():
        mwh = _exported_quantity_mwh(process_row)
        if mwh is None:
            continue
        key = process_row.installation_profile_id
        process_exported[key] = process_exported.get(key, Decimal("0")) + mwh

    return _BindingAllocationBundle(
        dea_current_result_id=dea_summary.current_result_id,
        dea_is_stale=bool(dea_summary.current_is_stale),
        dea_stale_reason_codes=list(dea_summary.stale_reason_codes),
        dea_result_unit=dea_summary.result_unit
        if dea_summary.current_result_id is not None
        else RESULT_UNIT_TCO2,
        dea_by_profile=dea_by_profile,
        iea_current_result_id=iea_summary.current_result_id,
        iea_is_stale=bool(iea_summary.current_is_stale),
        iea_stale_reason_codes=list(iea_summary.stale_reason_codes),
        iea_emissions_unit=iea_summary.emissions_unit
        if iea_summary.current_result_id is not None
        else RESULT_UNIT_TCO2E,
        iea_by_profile=iea_by_profile,
        exported_electricity=exported,
        facility_exported_by_installation=facility_exported,
        process_exported_by_installation=process_exported,
    )


def _dea_link_from_bundle(
    bundle: _BindingAllocationBundle,
    profile_id: uuid.UUID | None,
) -> AllocationLinkView:
    if bundle.dea_current_result_id is None:
        return AllocationLinkView(
            current_result_id=None,
            is_ready=False,
            is_stale=False,
            stale_reason_codes=[],
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=RESULT_UNIT_TCO2,
            electricity_unit=None,
            blocking_code=CODE_DIRECT_EMISSIONS_ALLOCATION_NOT_READY,
        )
    if bundle.dea_is_stale:
        return AllocationLinkView(
            current_result_id=bundle.dea_current_result_id,
            is_ready=False,
            is_stale=True,
            stale_reason_codes=list(bundle.dea_stale_reason_codes),
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=bundle.dea_result_unit,
            electricity_unit=None,
            blocking_code=CODE_DIRECT_EMISSIONS_ALLOCATION_NOT_READY,
        )
    allocated = bundle.dea_by_profile.get(profile_id) if profile_id is not None else None
    return AllocationLinkView(
        current_result_id=bundle.dea_current_result_id,
        is_ready=True,
        is_stale=False,
        stale_reason_codes=[],
        product_allocated_value=allocated,
        allocated_electricity_mwh=None,
        allocated_indirect_emissions_tco2e=None,
        result_unit=bundle.dea_result_unit,
        electricity_unit=None,
        blocking_code=None,
    )


def _iea_link_from_bundle(
    bundle: _BindingAllocationBundle,
    profile_id: uuid.UUID | None,
) -> AllocationLinkView:
    if bundle.iea_current_result_id is None:
        return AllocationLinkView(
            current_result_id=None,
            is_ready=False,
            is_stale=False,
            stale_reason_codes=[],
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=RESULT_UNIT_TCO2E,
            electricity_unit=ELECTRICITY_UNIT_MWH,
            blocking_code=CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY,
        )
    if bundle.iea_is_stale:
        return AllocationLinkView(
            current_result_id=bundle.iea_current_result_id,
            is_ready=False,
            is_stale=True,
            stale_reason_codes=list(bundle.iea_stale_reason_codes),
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=bundle.iea_emissions_unit,
            electricity_unit=ELECTRICITY_UNIT_MWH,
            blocking_code=CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY,
        )
    if profile_id is None:
        return AllocationLinkView(
            current_result_id=bundle.iea_current_result_id,
            is_ready=True,
            is_stale=False,
            stale_reason_codes=[],
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=bundle.iea_emissions_unit,
            electricity_unit=ELECTRICITY_UNIT_MWH,
            blocking_code=None,
        )
    snap = bundle.iea_by_profile.get(profile_id)
    if snap is None:
        return AllocationLinkView(
            current_result_id=bundle.iea_current_result_id,
            is_ready=False,
            is_stale=False,
            stale_reason_codes=[],
            product_allocated_value=None,
            allocated_electricity_mwh=None,
            allocated_indirect_emissions_tco2e=None,
            result_unit=bundle.iea_emissions_unit,
            electricity_unit=ELECTRICITY_UNIT_MWH,
            blocking_code=CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING,
        )
    return AllocationLinkView(
        current_result_id=bundle.iea_current_result_id,
        is_ready=True,
        is_stale=False,
        stale_reason_codes=[],
        product_allocated_value=snap.emissions_tco2e,
        allocated_electricity_mwh=snap.electricity_mwh,
        allocated_indirect_emissions_tco2e=snap.emissions_tco2e,
        result_unit=bundle.iea_emissions_unit,
        electricity_unit=ELECTRICITY_UNIT_MWH,
        blocking_code=None,
    )


def _dea_link(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    profile_id: uuid.UUID | None,
) -> AllocationLinkView:
    bundle = _load_binding_allocation_bundle(db, user, organization_id, binding_id)
    return _dea_link_from_bundle(bundle, profile_id)


def _iea_link(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    profile_id: uuid.UUID | None,
) -> AllocationLinkView:
    bundle = _load_binding_allocation_bundle(db, user, organization_id, binding_id)
    return _iea_link_from_bundle(bundle, profile_id)


def _exported_electricity_view(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> ExportedElectricityView:
    return _load_binding_allocation_bundle(
        db, user, organization_id, binding_id
    ).exported_electricity


def _compute_readiness(
    *,
    row: CbamProductionProcess,
    balance_status: str,
    remaining: Decimal | None,
    heat_status: str,
    waste_status: str,
    dea: AllocationLinkView,
    iea: AllocationLinkView,
    uses: list[CbamProductionProcessProductUse],
    target_blocking: list[str],
    exported_electricity: ProcessExportedElectricityView,
) -> ProductionProcessReadiness:
    blocking: list[str] = []

    if row.status == PROCESS_STATUS_ARCHIVED:
        return ProductionProcessReadiness(
            process_id=row.id,
            reporting_period_binding_id=row.reporting_period_binding_id,
            status=READINESS_INCOMPLETE,
            blocking_issue_codes=[CODE_PROCESS_ARCHIVED],
            informational_codes=[],
            balance_status=balance_status,
            remaining_tonnes=remaining,
        )

    empty = (
        not row.name
        and row.product_profile_version_id is None
        and row.produced_quantity is None
        and row.marketed_quantity is None
        and row.non_cbam_quantity is None
        and not uses
        and row.has_measurable_heat is None
        and row.has_waste_gas is None
        and row.has_exported_electricity is None
    )
    if empty:
        return ProductionProcessReadiness(
            process_id=row.id,
            reporting_period_binding_id=row.reporting_period_binding_id,
            status=READINESS_EMPTY,
            blocking_issue_codes=[
                CODE_PROCESS_NAME_REQUIRED,
                CODE_PROCESS_PRODUCT_REQUIRED,
                CODE_PRODUCTION_QUANTITY_MISSING,
                CODE_PRODUCT_DISTRIBUTION_INCOMPLETE,
            ],
            informational_codes=[],
            balance_status=balance_status,
            remaining_tonnes=remaining,
        )

    if not (row.name and row.name.strip()):
        blocking.append(CODE_PROCESS_NAME_REQUIRED)
    if row.product_profile_version_id is None:
        blocking.append(CODE_PROCESS_PRODUCT_REQUIRED)
    if row.calculation_method not in SUPPORTED_CALCULATION_METHODS:
        blocking.append(CODE_PROCESS_METHOD_UNSUPPORTED)
    if row.produced_quantity is None or row.produced_quantity_unit is None:
        blocking.append(CODE_PRODUCTION_QUANTITY_MISSING)
    if balance_status == BALANCE_INCOMPLETE:
        blocking.append(CODE_PRODUCT_DISTRIBUTION_INCOMPLETE)
    elif balance_status != BALANCE_BALANCED:
        blocking.append(CODE_PRODUCT_DISTRIBUTION_UNBALANCED)

    blocking.extend(target_blocking)

    if heat_status == "INCOMPLETE":
        blocking.append(CODE_MEASURABLE_HEAT_DATA_INCOMPLETE)
    if waste_status == "INCOMPLETE":
        blocking.append(CODE_WASTE_GAS_DATA_INCOMPLETE)

    informational: list[str] = []
    blocking.extend(_exported_electricity_blocking_codes(row))
    mismatched = (
        exported_electricity.reconciliation_status == EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCHED
    )
    if mismatched:
        # Only a process that declares its own L71 entry is blocked; sibling processes of
        # the same installation just surface the installation-level difference.
        if row.has_exported_electricity is True:
            blocking.append(CODE_EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCH)
        else:
            informational.append(CODE_EXPORTED_ELECTRICITY_RECONCILIATION_MISMATCH)

    stale = False
    if not dea.is_ready:
        blocking.append(dea.blocking_code or CODE_DIRECT_EMISSIONS_ALLOCATION_NOT_READY)
        if dea.is_stale:
            stale = True
    if not iea.is_ready:
        blocking.append(iea.blocking_code or CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY)
        if iea.is_stale:
            stale = True

    seen: set[str] = set()
    ordered: list[str] = []
    for c in blocking:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    status: ReadinessStatus
    if not ordered:
        status = cast(ReadinessStatus, READINESS_READY)
    elif CODE_PRODUCT_DISTRIBUTION_UNBALANCED in ordered:
        status = cast(ReadinessStatus, READINESS_UNBALANCED)
    elif stale:
        status = cast(ReadinessStatus, READINESS_STALE)
    else:
        status = cast(ReadinessStatus, READINESS_INCOMPLETE)

    return ProductionProcessReadiness(
        process_id=row.id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        status=status,
        blocking_issue_codes=ordered,
        informational_codes=informational,
        balance_status=balance_status,
        remaining_tonnes=remaining,
    )


def _validate_use_targets(
    db: Session,
    organization_id: uuid.UUID,
    uses: list[CbamProductionProcessProductUse],
) -> list[str]:
    codes: list[str] = []
    for use in uses:
        try:
            get_product_profile_for_org(db, organization_id, use.target_product_profile_version_id)
        except NotFoundError:
            codes.append(CODE_TARGET_PRODUCT_INVALID)
    return codes


def _to_response(
    db: Session,
    user: User,
    row: CbamProductionProcess,
    *,
    allocation_bundle: _BindingAllocationBundle | None = None,
    uses: list[CbamProductionProcessProductUse] | None = None,
) -> ProductionProcessResponse:
    if uses is None:
        uses = _list_uses(db, row.id)
    use_tonnes = Decimal("0")
    use_resps: list[ProductUseResponse] = []
    for u in uses:
        resp = _product_use_response(u, source_profile_id=row.product_profile_version_id)
        use_resps.append(resp)
        if resp.quantity_tonnes is not None:
            use_tonnes += resp.quantity_tonnes

    produced_t = _optional_tonnes(row.produced_quantity, row.produced_quantity_unit)
    marketed_t = _optional_tonnes(row.marketed_quantity, row.marketed_quantity_unit)
    non_cbam_t = _optional_tonnes(row.non_cbam_quantity, row.non_cbam_quantity_unit)
    balance = compute_distribution_balance(
        produced_tonnes=produced_t,
        marketed_tonnes=marketed_t,
        other_cbam_tonnes=use_tonnes,
        non_cbam_tonnes=non_cbam_t,
    )

    heat = compute_measurable_heat_attribution(
        has_measurable_heat=row.has_measurable_heat,
        imported_tj=row.heat_imported_quantity,
        exported_tj=row.heat_exported_quantity,
        imported_ef=row.heat_imported_ef,
        exported_ef=row.heat_exported_ef,
    )
    waste = compute_waste_gas_attribution(
        has_waste_gas=row.has_waste_gas,
        imported_tj=row.waste_gas_imported_quantity,
        exported_tj=row.waste_gas_exported_quantity,
    )

    bundle = allocation_bundle or _load_binding_allocation_bundle(
        db, user, row.organization_id, row.reporting_period_binding_id
    )
    dea = _dea_link_from_bundle(bundle, row.product_profile_version_id)
    iea = _iea_link_from_bundle(bundle, row.product_profile_version_id)
    exported = bundle.exported_electricity
    process_exported = _process_exported_electricity_view(row, bundle)

    records_t = _sum_production_records_tonnes(
        db,
        organization_id=row.organization_id,
        binding_id=row.reporting_period_binding_id,
        profile_id=row.product_profile_version_id,
    )
    diff: Decimal | None = None
    if produced_t is not None and records_t is not None:
        diff = produced_t - records_t

    target_blocking = _validate_use_targets(db, row.organization_id, uses)
    readiness = _compute_readiness(
        row=row,
        balance_status=balance.balance_status,
        remaining=balance.remaining_tonnes,
        heat_status=heat.status,
        waste_status=waste.status,
        dea=dea,
        iea=iea,
        uses=uses,
        target_blocking=target_blocking,
        exported_electricity=process_exported,
    )

    return ProductionProcessResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        installation_profile_id=row.installation_profile_id,
        product_profile_version_id=row.product_profile_version_id,
        name=row.name,
        identifier=row.identifier,
        calculation_method=row.calculation_method,
        status=row.status,
        notes=row.notes,
        row_version=row.row_version,
        readiness=readiness,
        distribution=DistributionView(
            produced_quantity=row.produced_quantity,
            produced_quantity_unit=row.produced_quantity_unit,
            produced_tonnes=balance.produced_tonnes,
            marketed_quantity=row.marketed_quantity,
            marketed_quantity_unit=row.marketed_quantity_unit,
            marketed_tonnes=balance.marketed_tonnes,
            other_cbam_tonnes=balance.other_cbam_tonnes,
            non_cbam_quantity=row.non_cbam_quantity,
            non_cbam_quantity_unit=row.non_cbam_quantity_unit,
            non_cbam_tonnes=balance.non_cbam_tonnes,
            distributed_tonnes=balance.distributed_tonnes,
            remaining_tonnes=balance.remaining_tonnes,
            balance_status=balance.balance_status,
            all_to_market=balance.all_to_market,
            market_share=balance.market_share,
            product_uses=use_resps,
        ),
        production_reconciliation=ProductionReconciliationView(
            process_produced_tonnes=produced_t,
            production_records_tonnes=records_t,
            difference_tonnes=diff,
            source=PRODUCTION_QUANTITY_SOURCE,
            note=PRODUCTION_QUANTITY_SOURCE_NOTE,
        ),
        direct_emissions_allocation=dea,
        indirect_emissions_allocation=iea,
        exported_electricity=exported,
        process_exported_electricity=process_exported,
        measurable_heat=HeatView(
            has_measurable_heat=row.has_measurable_heat,
            imported_quantity=row.heat_imported_quantity,
            imported_unit=row.heat_imported_unit,
            exported_quantity=row.heat_exported_quantity,
            exported_unit=row.heat_exported_unit,
            imported_ef=row.heat_imported_ef,
            exported_ef=row.heat_exported_ef,
            ef_unit=row.heat_ef_unit,
            factor_source=row.heat_factor_source,
            factor_document=row.heat_factor_document,
            calculation_status=heat.status,
            attributed_tco2=heat.attributed_tco2,
            formula_ref=heat.formula_ref,
        ),
        waste_gas=WasteGasView(
            has_waste_gas=row.has_waste_gas,
            imported_quantity=row.waste_gas_imported_quantity,
            imported_unit=row.waste_gas_imported_unit,
            exported_quantity=row.waste_gas_exported_quantity,
            exported_unit=row.waste_gas_exported_unit,
            provenance=row.waste_gas_provenance,
            calculation_status=waste.status,
            attributed_tco2=waste.attributed_tco2,
            ef_tco2_per_tj=waste.ef_tco2_per_tj,
            formula_ref=waste.formula_ref,
            note=waste.note,
        ),
        data_quality_code=row.data_quality_code,
        data_verification_code=row.data_verification_code,
        data_quality_justification_code=row.data_quality_justification_code,
    )


def get_production_process_metadata(
    db: Session, user: User, organization_id: uuid.UUID
) -> ProductionProcessMetadataResponse:
    require_cbam_view(db, user, organization_id)
    lists = [
        ControlledListResponse(
            list_code=lst.list_code,
            title_en=lst.title_en,
            workbook_named_range=lst.workbook_named_range,
            workbook_sheet=lst.workbook_sheet,
            help_en=lst.help_en,
            items=[
                ControlledListItemResponse(
                    code=i.code,
                    label_en=i.label_en,
                    description_en=i.description_en,
                    sort_order=i.sort_order,
                    workbook_ref=i.workbook_ref,
                )
                for i in lst.items
            ],
        )
        for lst in list_production_process_controlled_lists()
    ]
    return ProductionProcessMetadataResponse(
        methodology_code=METHODOLOGY_CODE,
        methodology_version=METHODOLOGY_VERSION,
        workbook_filename=WORKBOOK_FILENAME,
        workbook_sha256=WORKBOOK_SHA256,
        workbook_formula_refs=WORKBOOK_FORMULA_REFS,
        supported_calculation_methods=sorted(SUPPORTED_CALCULATION_METHODS),
        disabled_calculation_methods=sorted(DISABLED_CALCULATION_METHODS),
        production_quantity_source=PRODUCTION_QUANTITY_SOURCE,
        production_quantity_source_note=PRODUCTION_QUANTITY_SOURCE_NOTE,
        field_map=PROCESS_FIELD_MAP,
        extraction=workbook_extraction_metadata(),
        controlled_lists=lists,
    )


def list_controlled_lists_for_processes(
    db: Session, user: User, organization_id: uuid.UUID
) -> list[ControlledListResponse]:
    return get_production_process_metadata(db, user, organization_id).controlled_lists


def get_controlled_list_for_processes(
    db: Session, user: User, organization_id: uuid.UUID, list_code: str
) -> ControlledListResponse:
    require_cbam_view(db, user, organization_id)
    lst = get_production_process_controlled_list(list_code)
    if lst is None:
        raise NotFoundError(f"Controlled list not found: {list_code}")
    return ControlledListResponse(
        list_code=lst.list_code,
        title_en=lst.title_en,
        workbook_named_range=lst.workbook_named_range,
        workbook_sheet=lst.workbook_sheet,
        help_en=lst.help_en,
        items=[
            ControlledListItemResponse(
                code=i.code,
                label_en=i.label_en,
                description_en=i.description_en,
                sort_order=i.sort_order,
                workbook_ref=i.workbook_ref,
            )
            for i in lst.items
        ],
    )


def list_production_processes(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
) -> Page[ProductionProcessResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamProductionProcess).where(
        CbamProductionProcess.organization_id == organization_id,
        CbamProductionProcess.reporting_period_binding_id == binding_id,
    )
    if not include_archived:
        stmt = stmt.where(CbamProductionProcess.status == PROCESS_STATUS_DRAFT)
    stmt = stmt.order_by(CbamProductionProcess.created_at.asc())
    rows = list(db.execute(stmt).scalars().all())
    uses_by_process = _list_uses_for_processes(db, [r.id for r in rows])
    bundle = _load_binding_allocation_bundle(db, user, organization_id, binding_id)
    items = [
        _to_response(
            db,
            user,
            r,
            allocation_bundle=bundle,
            uses=uses_by_process.get(r.id, []),
        )
        for r in rows
    ]
    start = (page - 1) * page_size
    end = start + page_size
    return paginate(items[start:end], page=page, page_size=page_size, total_items=len(items))


def get_production_process(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
) -> ProductionProcessResponse:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    row = _get_process(db, organization_id, binding_id, process_id)
    bundle = _load_binding_allocation_bundle(db, user, organization_id, binding_id)
    return _to_response(db, user, row, allocation_bundle=bundle)


def get_production_process_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
) -> ProductionProcessReadiness:
    return get_production_process(db, user, organization_id, binding_id, process_id).readiness


def get_production_process_binding_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> ProductionProcessSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    rows = list(
        db.execute(
            select(CbamProductionProcess).where(
                CbamProductionProcess.organization_id == organization_id,
                CbamProductionProcess.reporting_period_binding_id == binding_id,
            )
        )
        .scalars()
        .all()
    )
    uses_by_process = _list_uses_for_processes(db, [r.id for r in rows])
    bundle = _load_binding_allocation_bundle(db, user, organization_id, binding_id)
    readiness_list = [
        _to_response(
            db,
            user,
            r,
            allocation_bundle=bundle,
            uses=uses_by_process.get(r.id, []),
        ).readiness
        for r in rows
    ]
    return ProductionProcessSummary(
        reporting_period_binding_id=binding_id,
        process_count=len(rows),
        draft_count=sum(1 for r in rows if r.status == PROCESS_STATUS_DRAFT),
        archived_count=sum(1 for r in rows if r.status == PROCESS_STATUS_ARCHIVED),
        ready_count=sum(1 for r in readiness_list if r.status == READINESS_READY),
        unbalanced_count=sum(1 for r in readiness_list if r.status == READINESS_UNBALANCED),
        processes=readiness_list,
    )


def create_production_process(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: ProductionProcessCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionProcessResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)
    method = _validate_method(payload.calculation_method)
    _validate_dq_codes(
        payload.data_quality_code,
        payload.data_verification_code,
        payload.data_quality_justification_code,
    )

    profile_id = payload.product_profile_version_id
    if profile_id is not None:
        require_linkable_product_profile(db, organization_id, profile_id)

    produced_unit = _require_mass_unit(payload.produced_quantity_unit, field="producedQuantityUnit")
    marketed_unit = _require_mass_unit(payload.marketed_quantity_unit, field="marketedQuantityUnit")
    non_cbam_unit = _require_mass_unit(payload.non_cbam_quantity_unit, field="nonCbamQuantityUnit")
    if payload.produced_quantity is not None:
        require_non_negative(payload.produced_quantity, field="producedQuantity")
    if payload.marketed_quantity is not None:
        require_non_negative(payload.marketed_quantity, field="marketedQuantity")
    if payload.non_cbam_quantity is not None:
        require_non_negative(payload.non_cbam_quantity, field="nonCbamQuantity")

    heat = _apply_heat_constraints(
        has_heat=payload.has_measurable_heat,
        imported_q=payload.heat_imported_quantity,
        imported_u=payload.heat_imported_unit,
        exported_q=payload.heat_exported_quantity,
        exported_u=payload.heat_exported_unit,
        imported_ef=payload.heat_imported_ef,
        exported_ef=payload.heat_exported_ef,
        ef_unit=payload.heat_ef_unit,
        factor_source=payload.heat_factor_source,
        factor_document=payload.heat_factor_document,
        reject_fields_when_false=True,
    )
    waste = _apply_waste_constraints(
        has_waste=payload.has_waste_gas,
        imported_q=payload.waste_gas_imported_quantity,
        imported_u=payload.waste_gas_imported_unit,
        exported_q=payload.waste_gas_exported_quantity,
        exported_u=payload.waste_gas_exported_unit,
        provenance=payload.waste_gas_provenance,
        reject_fields_when_false=True,
    )
    exported_electricity = _apply_exported_electricity_constraints(
        has_exported=payload.has_exported_electricity,
        quantity=payload.exported_electricity_quantity,
        quantity_unit=payload.exported_electricity_unit,
        emission_factor=payload.exported_electricity_emission_factor,
        ef_unit=payload.exported_electricity_ef_unit,
        provenance=payload.exported_electricity_provenance,
        reject_fields_when_false=True,
    )

    row = CbamProductionProcess(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        installation_profile_id=installation.id,
        product_profile_version_id=profile_id,
        name=(payload.name.strip() if payload.name else None) or None,
        identifier=(payload.identifier.strip() if payload.identifier else None) or None,
        calculation_method=method,
        status=PROCESS_STATUS_DRAFT,
        produced_quantity=payload.produced_quantity,
        produced_quantity_unit=produced_unit,
        marketed_quantity=payload.marketed_quantity,
        marketed_quantity_unit=marketed_unit,
        non_cbam_quantity=payload.non_cbam_quantity,
        non_cbam_quantity_unit=non_cbam_unit,
        data_quality_code=payload.data_quality_code,
        data_verification_code=payload.data_verification_code,
        data_quality_justification_code=payload.data_quality_justification_code,
        notes=payload.notes,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        **heat,
        **waste,
        **exported_electricity,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.created",
        entity_type="cbam_production_process",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"id": str(row.id), "method": method},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, user, row)


def update_production_process_draft(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
    payload: ProductionProcessUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionProcessResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    row = _get_process(db, organization_id, binding_id, process_id)
    if row.status == PROCESS_STATUS_ARCHIVED:
        raise BusinessRuleError(
            "Archived production processes cannot be edited.",
            details=[{"code": CODE_PROCESS_ARCHIVED}],
        )
    check_row_version(row.row_version, payload.row_version, entity="CBAM production process")
    data = payload.model_dump(exclude_unset=True)
    data.pop("row_version", None)

    if "calculation_method" in data and data["calculation_method"] is not None:
        row.calculation_method = _validate_method(data["calculation_method"])
    if "product_profile_version_id" in data:
        pid = data["product_profile_version_id"]
        if pid is not None:
            require_linkable_product_profile(db, organization_id, pid)
        row.product_profile_version_id = pid
    if "name" in data:
        row.name = (data["name"].strip() if data["name"] else None) or None
    if "identifier" in data:
        row.identifier = (data["identifier"].strip() if data["identifier"] else None) or None
    if "notes" in data:
        row.notes = data["notes"]

    for qty_field, unit_field in (
        ("produced_quantity", "produced_quantity_unit"),
        ("marketed_quantity", "marketed_quantity_unit"),
        ("non_cbam_quantity", "non_cbam_quantity_unit"),
    ):
        if qty_field in data:
            val = data[qty_field]
            if val is not None:
                require_non_negative(val, field=qty_field)
            setattr(row, qty_field, val)
        if unit_field in data:
            setattr(row, unit_field, _require_mass_unit(data[unit_field], field=unit_field))

    dq_q = data.get("data_quality_code", row.data_quality_code)
    dq_v = data.get("data_verification_code", row.data_verification_code)
    dq_j = data.get("data_quality_justification_code", row.data_quality_justification_code)
    if any(
        k in data
        for k in (
            "data_quality_code",
            "data_verification_code",
            "data_quality_justification_code",
        )
    ):
        _validate_dq_codes(dq_q, dq_v, dq_j)
        if "data_quality_code" in data:
            row.data_quality_code = data["data_quality_code"]
        if "data_verification_code" in data:
            row.data_verification_code = data["data_verification_code"]
        if "data_quality_justification_code" in data:
            row.data_quality_justification_code = data["data_quality_justification_code"]

    has_heat = data.get("has_measurable_heat", row.has_measurable_heat)
    if "has_measurable_heat" in data or any(k.startswith("heat_") for k in data):
        if has_heat is False:
            if any(
                data.get(k) is not None
                for k in (
                    "heat_imported_quantity",
                    "heat_imported_unit",
                    "heat_exported_quantity",
                    "heat_exported_unit",
                    "heat_imported_ef",
                    "heat_exported_ef",
                    "heat_ef_unit",
                    "heat_factor_source",
                    "heat_factor_document",
                )
                if k in data
            ):
                raise ValidationAppError(
                    "Measurable-heat fields must be null when hasMeasurableHeat is false.",
                    details=[{"code": CODE_HEAT_FIELDS_NOT_ALLOWED}],
                )
            row.has_measurable_heat = False
            _clear_heat_fields(row)
        else:
            if "has_measurable_heat" in data:
                row.has_measurable_heat = data["has_measurable_heat"]
            for field in (
                "heat_imported_quantity",
                "heat_imported_unit",
                "heat_exported_quantity",
                "heat_exported_unit",
                "heat_imported_ef",
                "heat_exported_ef",
                "heat_ef_unit",
                "heat_factor_source",
                "heat_factor_document",
            ):
                if field in data and has_heat is not False:
                    if (field.endswith("_quantity") or field.endswith("_ef")) and data[
                        field
                    ] is not None:
                        require_non_negative(data[field], field=field)
                    if field.endswith("_unit") and data[field] is not None:
                        if "ef" in field:
                            if data[field] != HEAT_FACTOR_UNIT:
                                raise ValidationAppError(
                                    f"Heat EF unit must be {HEAT_FACTOR_UNIT}."
                                )
                        else:
                            u = require_unit(data[field])
                            if u != HEAT_QUANTITY_UNIT:
                                raise ValidationAppError(
                                    f"Heat quantity unit must be {HEAT_QUANTITY_UNIT}."
                                )
                            data[field] = u
                    setattr(row, field, data[field])

    has_waste = data.get("has_waste_gas", row.has_waste_gas)
    if "has_waste_gas" in data or any(k.startswith("waste_gas_") for k in data):
        if has_waste is False:
            if any(
                data.get(k) is not None
                for k in (
                    "waste_gas_imported_quantity",
                    "waste_gas_imported_unit",
                    "waste_gas_exported_quantity",
                    "waste_gas_exported_unit",
                    "waste_gas_provenance",
                )
                if k in data
            ):
                raise ValidationAppError(
                    "Waste-gas fields must be null when hasWasteGas is false.",
                    details=[{"code": CODE_WASTE_GAS_FIELDS_NOT_ALLOWED}],
                )
            row.has_waste_gas = False
            _clear_waste_fields(row)
        else:
            if "has_waste_gas" in data:
                row.has_waste_gas = data["has_waste_gas"]
            for field in (
                "waste_gas_imported_quantity",
                "waste_gas_imported_unit",
                "waste_gas_exported_quantity",
                "waste_gas_exported_unit",
                "waste_gas_provenance",
            ):
                if field in data:
                    if field.endswith("_quantity") and data[field] is not None:
                        require_non_negative(data[field], field=field)
                    if field.endswith("_unit") and data[field] is not None:
                        u = require_unit(data[field])
                        if u != WASTE_GAS_QUANTITY_UNIT:
                            raise ValidationAppError(
                                f"Waste-gas quantity unit must be {WASTE_GAS_QUANTITY_UNIT}."
                            )
                        data[field] = u
                    setattr(row, field, data[field])

    has_exported = data.get("has_exported_electricity", row.has_exported_electricity)
    if "has_exported_electricity" in data or any(
        k.startswith("exported_electricity_") for k in data
    ):
        if has_exported is False:
            if any(data.get(k) is not None for k in _EXPORTED_ELECTRICITY_FIELDS if k in data):
                raise ValidationAppError(
                    "Exported-electricity fields must be null when "
                    "hasExportedElectricity is false.",
                    details=[{"code": CODE_EXPORTED_ELECTRICITY_FIELDS_NOT_ALLOWED}],
                )
            row.has_exported_electricity = False
            _clear_exported_electricity_fields(row)
        else:
            if "has_exported_electricity" in data:
                row.has_exported_electricity = data["has_exported_electricity"]
            for field in _EXPORTED_ELECTRICITY_FIELDS:
                if field not in data:
                    continue
                value = data[field]
                if value is not None:
                    if field == "exported_electricity_quantity":
                        require_non_negative(value, field="exportedElectricityQuantity")
                    elif field == "exported_electricity_emission_factor":
                        require_non_negative(value, field="exportedElectricityEmissionFactor")
                    elif field == "exported_electricity_unit":
                        value = _validate_exported_electricity_quantity_unit(value)
                    elif field == "exported_electricity_ef_unit":
                        value = _validate_exported_electricity_ef_unit(value)
                    elif field == "exported_electricity_provenance":
                        value = value.strip() or None
                setattr(row, field, value)

    row.row_version += 1
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.updated",
        entity_type="cbam_production_process",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"rowVersion": row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, user, row)


def archive_production_process(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
    payload: ProductionProcessVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionProcessResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    row = _get_process(db, organization_id, binding_id, process_id)
    check_row_version(row.row_version, payload.row_version, entity="CBAM production process")
    if row.status == PROCESS_STATUS_ARCHIVED:
        return _to_response(db, user, row)
    row.status = PROCESS_STATUS_ARCHIVED
    row.row_version += 1
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.archived",
        entity_type="cbam_production_process",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, user, row)


def create_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
    payload: ProductUseCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductUseResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    process = _get_process(db, organization_id, binding_id, process_id)
    if process.status == PROCESS_STATUS_ARCHIVED:
        raise BusinessRuleError(
            "Cannot add product uses to an archived process.",
            details=[{"code": CODE_PROCESS_ARCHIVED}],
        )
    target = require_linkable_product_profile(
        db, organization_id, payload.target_product_profile_version_id
    )
    if (
        process.product_profile_version_id is not None
        and target.id == process.product_profile_version_id
    ):
        raise BusinessRuleError(
            "Target product profile must differ from the source process product profile.",
            details=[{"code": CODE_TARGET_PRODUCT_INVALID}],
        )
    unit = _require_mass_unit(payload.unit, field="unit")
    assert unit is not None
    require_non_negative(payload.quantity, field="quantity")

    existing = db.execute(
        select(CbamProductionProcessProductUse).where(
            CbamProductionProcessProductUse.process_id == process_id,
            CbamProductionProcessProductUse.target_product_profile_version_id == target.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise BusinessRuleError(
            "A product-use row for this target profile already exists on the process.",
            details=[{"code": "PRODUCT_USE_DUPLICATE"}],
        )

    use = CbamProductionProcessProductUse(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        process_id=process_id,
        target_product_profile_version_id=target.id,
        quantity=payload.quantity,
        unit=unit,
        notes=payload.notes,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(use)
    process.row_version += 1
    process.updated_by_user_id = user.id
    db.flush()
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.product_use.created",
        entity_type="cbam_production_process_product_use",
        entity_id=str(use.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(use)
    return _product_use_response(use, source_profile_id=process.product_profile_version_id)


def update_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
    use_id: uuid.UUID,
    payload: ProductUseUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductUseResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    process = _get_process(db, organization_id, binding_id, process_id)
    if process.status == PROCESS_STATUS_ARCHIVED:
        raise BusinessRuleError(
            "Cannot update product uses on an archived process.",
            details=[{"code": CODE_PROCESS_ARCHIVED}],
        )
    use = db.get(CbamProductionProcessProductUse, use_id)
    if (
        use is None
        or use.organization_id != organization_id
        or use.reporting_period_binding_id != binding_id
        or use.process_id != process_id
    ):
        raise NotFoundError("Product-use distribution row not found.")
    check_row_version(
        use.row_version, payload.row_version, entity="CBAM production process product use"
    )
    data = payload.model_dump(exclude_unset=True)
    data.pop("row_version", None)
    if data.get("target_product_profile_version_id"):
        target = require_linkable_product_profile(
            db, organization_id, data["target_product_profile_version_id"]
        )
        use.target_product_profile_version_id = target.id
    if "quantity" in data and data["quantity"] is not None:
        require_non_negative(data["quantity"], field="quantity")
        use.quantity = data["quantity"]
    if "unit" in data and data["unit"] is not None:
        use.unit = _require_mass_unit(data["unit"], field="unit")  # type: ignore[assignment]
    if "notes" in data:
        use.notes = data["notes"]
    use.row_version += 1
    use.updated_by_user_id = user.id
    process.row_version += 1
    process.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.product_use.updated",
        entity_type="cbam_production_process_product_use",
        entity_id=str(use.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(use)
    return _product_use_response(use, source_profile_id=process.product_profile_version_id)


def delete_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    process_id: uuid.UUID,
    use_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    process = _get_process(db, organization_id, binding_id, process_id)
    if process.status == PROCESS_STATUS_ARCHIVED:
        raise BusinessRuleError(
            "Cannot delete product uses on an archived process.",
            details=[{"code": CODE_PROCESS_ARCHIVED}],
        )
    use = db.get(CbamProductionProcessProductUse, use_id)
    if (
        use is None
        or use.organization_id != organization_id
        or use.reporting_period_binding_id != binding_id
        or use.process_id != process_id
    ):
        raise NotFoundError("Product-use distribution row not found.")
    db.delete(use)
    process.row_version += 1
    process.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.production_process.product_use.deleted",
        entity_type="cbam_production_process_product_use",
        entity_id=str(use_id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
