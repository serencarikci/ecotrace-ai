"""Purchased-precursor CRUD, distribution, default resolution, readiness."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal, cast

from sqlalchemy import func, select
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
from ecotrace.modules.cbam.application.monthly_production_basis_service import to_tonnes
from ecotrace.modules.cbam.application.permissions import (
    require_cbam_configure,
    require_cbam_view,
)
from ecotrace.modules.cbam.application.precursor_constants import (
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    CALC_STATUS_NOT_CALCULATED,
    CANONICAL_MASS_UNIT,
    CODE_DEFAULT_VALUE_AMBIGUOUS,
    CODE_DEFAULT_VALUE_NOT_NUMERIC,
    CODE_DEFAULT_VALUE_UNRESOLVED,
    CODE_ELECTRICITY_SOURCE_CODE_INVALID,
    CODE_INCOMPATIBLE_MASS_UNIT,
    CODE_JUSTIFICATION_CODE_INVALID,
    CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED,
    CODE_PARAMETER_SOURCE_CODE_INVALID,
    CODE_PRECURSOR_ARCHIVED,
    CODE_PRECURSOR_CN_REQUIRED,
    CODE_PRECURSOR_COUNTRY_REQUIRED,
    CODE_PRECURSOR_DISTRIBUTION_INCOMPLETE,
    CODE_PRECURSOR_DISTRIBUTION_UNBALANCED,
    CODE_PRECURSOR_MODE_UNSUPPORTED,
    CODE_PRECURSOR_NAME_REQUIRED,
    CODE_PRECURSOR_QUANTITY_MISSING,
    CODE_PURCHASED_INPUT_INVALID,
    CODE_SUPPLIER_DIRECT_EMISSIONS_MISSING,
    CODE_SUPPLIER_ELECTRICITY_DATA_INCOMPLETE,
    CODE_SUPPLIER_PROVENANCE_REQUIRED,
    CODE_TARGET_PRODUCT_INVALID,
    DV_STATUS_NUMERIC,
    ELECTRICITY_EF_UNIT,
    ELECTRICITY_INTENSITY_UNIT,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    MODE_EU_DEFAULT,
    MODE_SUPPLIER_DATA,
    OTHER_COUNTRIES_FALLBACK_NOTE,
    PRECURSOR_STATUS_ARCHIVED,
    PRECURSOR_STATUS_DRAFT,
    PRODUCT_TOTALS_ROLLUP_NOTE,
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
    RESULT_UNIT_TCO2E,
    SPECIFIC_DIRECT_UNIT,
    SPECIFIC_INDIRECT_UNIT,
    SUPPORTED_DATA_SOURCE_MODES,
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_PRIMARY_SHEET,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.precursor_controlled_lists import (
    PRECURSOR_FIELD_MAP,
    default_justification_codes,
    electricity_source_codes,
    get_precursor_controlled_list,
    list_precursor_controlled_lists,
    parameter_source_codes,
    workbook_extraction_metadata,
)
from ecotrace.modules.cbam.application.precursor_default_catalog_seed import build_lookup_key
from ecotrace.modules.cbam.application.precursor_default_catalog_service import (
    PrecursorDefaultDatasetResponse,
    PrecursorDefaultResolution,
    build_default_snapshot,
    get_active_dataset,
    normalize_country_name,
    normalize_precursor_cn_code,
    resolve_default_value,
    snapshot_specific_values,
)
from ecotrace.modules.cbam.application.precursor_math import (
    compute_precursor_distribution_balance,
    compute_specific_indirect,
    compute_total_embedded,
)
from ecotrace.modules.cbam.application.production_profile_link import (
    require_linkable_product_profile,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamPrecursorDefaultValue,
    CbamPurchasedInputRecord,
    CbamPurchasedPrecursor,
    CbamPurchasedPrecursorProductUse,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.suppliers.application.supplier_service import get_supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

ReadinessStatus = Literal["EMPTY", "INCOMPLETE", "UNBALANCED", "UNRESOLVED", "AMBIGUOUS", "READY"]

SUPPLIER_EMISSION_FIELDS: tuple[str, ...] = (
    "specific_direct_embedded_emissions",
    "specific_direct_unit",
    "specific_direct_source_code",
    "electricity_consumption_intensity",
    "electricity_intensity_unit",
    "electricity_intensity_source_code",
    "electricity_emission_factor",
    "electricity_ef_unit",
    "electricity_ef_source_code",
)

SUPPLIER_NUMERIC_FIELDS: tuple[str, ...] = (
    "specific_direct_embedded_emissions",
    "electricity_consumption_intensity",
    "electricity_emission_factor",
)

DEFAULT_SOURCE_FIELDS: tuple[str, ...] = (
    "default_value_id",
    "default_justification_code",
)


class PurchasedPrecursorCreate(CamelModel):
    installation_profile_id: uuid.UUID
    data_source_mode: str = MODE_SUPPLIER_DATA
    name: str | None = None
    identifier: str | None = None
    aggregated_goods_category: str | None = None
    cn_code: str | None = None
    country_of_origin: str | None = None
    production_route: str | None = None
    purchased_input_record_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    quantity: Decimal | None = None
    quantity_unit: str | None = None
    non_cbam_quantity: Decimal | None = None
    non_cbam_quantity_unit: str | None = None
    specific_direct_embedded_emissions: Decimal | None = None
    specific_direct_unit: str | None = None
    specific_direct_source_code: str | None = None
    electricity_consumption_intensity: Decimal | None = None
    electricity_intensity_unit: str | None = None
    electricity_intensity_source_code: str | None = None
    electricity_emission_factor: Decimal | None = None
    electricity_ef_unit: str | None = None
    electricity_ef_source_code: str | None = None
    default_value_id: uuid.UUID | None = None
    default_justification_code: str | None = None
    provenance_notes: str | None = None
    evidence_reference: str | None = None
    notes: str | None = None


class PurchasedPrecursorUpdate(CamelModel):
    row_version: int
    data_source_mode: str | None = None
    name: str | None = None
    identifier: str | None = None
    aggregated_goods_category: str | None = None
    cn_code: str | None = None
    country_of_origin: str | None = None
    production_route: str | None = None
    purchased_input_record_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    quantity: Decimal | None = None
    quantity_unit: str | None = None
    non_cbam_quantity: Decimal | None = None
    non_cbam_quantity_unit: str | None = None
    specific_direct_embedded_emissions: Decimal | None = None
    specific_direct_unit: str | None = None
    specific_direct_source_code: str | None = None
    electricity_consumption_intensity: Decimal | None = None
    electricity_intensity_unit: str | None = None
    electricity_intensity_source_code: str | None = None
    electricity_emission_factor: Decimal | None = None
    electricity_ef_unit: str | None = None
    electricity_ef_source_code: str | None = None
    default_value_id: uuid.UUID | None = None
    default_justification_code: str | None = None
    provenance_notes: str | None = None
    evidence_reference: str | None = None
    notes: str | None = None


class PurchasedPrecursorVersionRequest(CamelModel):
    row_version: int


class PrecursorProductUseCreate(CamelModel):
    target_product_profile_version_id: uuid.UUID
    quantity: Decimal
    unit: str = CANONICAL_MASS_UNIT
    notes: str | None = None


class PrecursorProductUseUpdate(CamelModel):
    row_version: int
    target_product_profile_version_id: uuid.UUID | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    notes: str | None = None


class PrecursorProductUseResponse(CamelModel):
    id: uuid.UUID
    precursor_id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    target_product_profile_version_id: uuid.UUID
    quantity: Decimal
    unit: str
    quantity_tonnes: Decimal | None
    notes: str | None
    row_version: int


class PrecursorDistributionView(CamelModel):
    quantity: Decimal | None
    quantity_unit: str | None
    purchased_tonnes: Decimal | None
    non_cbam_quantity: Decimal | None
    non_cbam_quantity_unit: str | None
    non_cbam_tonnes: Decimal | None
    product_use_tonnes: Decimal
    distributed_tonnes: Decimal | None
    remaining_tonnes: Decimal | None
    balance_status: str
    formula_ref: str
    product_uses: list[PrecursorProductUseResponse]


class PrecursorSupplierDataView(CamelModel):
    applicable: bool
    specific_direct_embedded_emissions: Decimal | None
    specific_direct_unit: str | None
    specific_direct_source_code: str | None
    electricity_consumption_intensity: Decimal | None
    electricity_intensity_unit: str | None
    electricity_intensity_source_code: str | None
    electricity_emission_factor: Decimal | None
    electricity_ef_unit: str | None
    electricity_ef_source_code: str | None
    specific_indirect_embedded_emissions: Decimal | None
    specific_indirect_unit: str | None
    provenance_notes: str | None
    evidence_reference: str | None


class PrecursorDefaultSourceView(CamelModel):
    applicable: bool
    resolution_status: str
    issue_code: str | None
    from_snapshot: bool
    dataset_id: uuid.UUID | None
    dataset_code: str | None
    dataset_version: str | None
    content_checksum: str | None
    default_value_id: uuid.UUID | None
    lookup_key: str | None
    specific_direct_embedded_emissions: Decimal | None
    specific_direct_status: str | None
    specific_direct_unit: str | None
    specific_indirect_embedded_emissions: Decimal | None
    specific_indirect_status: str | None
    specific_indirect_unit: str | None
    justification_code: str | None
    candidate_count: int
    snapshot: dict[str, Any] | None
    other_countries_note: str


class PrecursorCalculationView(CamelModel):
    status: str
    value_source: str | None
    quantity_tonnes: Decimal | None
    specific_direct_embedded_emissions: Decimal | None
    specific_indirect_embedded_emissions: Decimal | None
    total_direct_embedded_emissions: Decimal | None
    total_indirect_embedded_emissions: Decimal | None
    total_embedded_emissions: Decimal | None
    result_unit: str
    formula_refs: str
    rollup_note: str


class PurchasedPrecursorReadiness(CamelModel):
    precursor_id: uuid.UUID | None
    reporting_period_binding_id: uuid.UUID
    status: ReadinessStatus
    blocking_issue_codes: list[str]
    informational_codes: list[str]
    balance_status: str | None
    remaining_tonnes: Decimal | None
    resolution_status: str


class PurchasedPrecursorResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    purchased_input_record_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    name: str | None
    identifier: str | None
    aggregated_goods_category: str | None
    cn_normalized_code: str | None
    cn_display_code: str | None
    country_of_origin: str | None
    production_route: str | None
    data_source_mode: str
    status: str
    notes: str | None
    row_version: int
    readiness: PurchasedPrecursorReadiness
    distribution: PrecursorDistributionView
    supplier_data: PrecursorSupplierDataView
    default_source: PrecursorDefaultSourceView
    calculation: PrecursorCalculationView


class PurchasedPrecursorSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    precursor_count: int
    draft_count: int
    archived_count: int
    ready_count: int
    unbalanced_count: int
    unresolved_count: int
    ambiguous_count: int
    precursors: list[PurchasedPrecursorReadiness]


class PrecursorControlledListItemResponse(CamelModel):
    code: str
    label_en: str
    description_en: str | None
    sort_order: int
    workbook_ref: str


class PrecursorControlledListResponse(CamelModel):
    list_code: str
    title_en: str
    workbook_named_range: str
    workbook_sheet: str
    help_en: str | None
    items: list[PrecursorControlledListItemResponse]


class PurchasedPrecursorMetadataResponse(CamelModel):
    methodology_code: str
    methodology_version: str
    workbook_filename: str
    workbook_sha256: str
    workbook_primary_sheet: str
    workbook_formula_refs: str
    supported_data_source_modes: list[str]
    units: dict[str, str]
    field_map: dict[str, dict[str, str]]
    extraction: dict[str, str]
    controlled_lists: list[PrecursorControlledListResponse]
    default_value_dataset: PrecursorDefaultDatasetResponse
    other_countries_note: str
    rollup_note: str


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


def _validate_mode(mode: str) -> str:
    if mode not in SUPPORTED_DATA_SOURCE_MODES:
        raise BusinessRuleError(
            f"Data source mode {mode} is not supported in Phase 10A. "
            f"Use {MODE_SUPPLIER_DATA} or {MODE_EU_DEFAULT}.",
            details=[{"code": CODE_PRECURSOR_MODE_UNSUPPORTED, "mode": mode}],
        )
    return mode


def _validate_fixed_unit(unit: str | None, expected: str, *, field: str) -> str | None:
    if unit is None:
        return None
    normalized = unit.strip()
    if normalized != expected:
        raise ValidationAppError(
            f"{field} must be {expected}.",
            details=[{"field": field, "expected": expected}],
        )
    return normalized


def _validate_source_codes(
    *,
    specific_direct_source_code: str | None,
    electricity_intensity_source_code: str | None,
    electricity_ef_source_code: str | None,
    default_justification_code: str | None,
) -> None:
    for value, field in (
        (specific_direct_source_code, "specificDirectSourceCode"),
        (electricity_intensity_source_code, "electricityIntensitySourceCode"),
    ):
        if value is not None and value not in parameter_source_codes():
            raise ValidationAppError(
                f"Invalid parameter determination code: {value}",
                details=[{"code": CODE_PARAMETER_SOURCE_CODE_INVALID, "field": field}],
            )
    if (
        electricity_ef_source_code is not None
        and electricity_ef_source_code not in electricity_source_codes()
    ):
        raise ValidationAppError(
            f"Invalid electricity emission-factor source code: {electricity_ef_source_code}",
            details=[
                {
                    "code": CODE_ELECTRICITY_SOURCE_CODE_INVALID,
                    "field": "electricityEfSourceCode",
                }
            ],
        )
    if (
        default_justification_code is not None
        and default_justification_code not in default_justification_codes()
    ):
        raise ValidationAppError(
            f"Invalid default-value justification code: {default_justification_code}",
            details=[
                {"code": CODE_JUSTIFICATION_CODE_INVALID, "field": "defaultJustificationCode"}
            ],
        )


def _reject_mixed_source(mode: str, submitted: dict[str, Any]) -> None:
    if mode == MODE_SUPPLIER_DATA:
        offending = [f for f in DEFAULT_SOURCE_FIELDS if submitted.get(f) is not None]
        if offending:
            raise BusinessRuleError(
                "EU default-value fields cannot be combined with supplier data in one "
                "purchased precursor.",
                details=[{"code": CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED, "fields": offending}],
            )
        return
    offending = [f for f in SUPPLIER_EMISSION_FIELDS if submitted.get(f) is not None]
    if offending:
        raise BusinessRuleError(
            "Supplier emission fields cannot be combined with the EU default-value mode.",
            details=[{"code": CODE_MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED, "fields": offending}],
        )


def _require_supplier_provenance(
    *,
    numeric_values_present: bool,
    provenance_notes: str | None,
    evidence_reference: str | None,
) -> None:
    if not numeric_values_present:
        return
    if (provenance_notes and provenance_notes.strip()) or (
        evidence_reference and evidence_reference.strip()
    ):
        return
    raise BusinessRuleError(
        "Supplier emission values require provenanceNotes or evidenceReference.",
        details=[{"code": CODE_SUPPLIER_PROVENANCE_REQUIRED}],
    )


def _clear_supplier_fields(row: CbamPurchasedPrecursor) -> None:
    row.specific_direct_embedded_emissions = None
    row.specific_direct_unit = None
    row.specific_direct_source_code = None
    row.electricity_consumption_intensity = None
    row.electricity_intensity_unit = None
    row.electricity_intensity_source_code = None
    row.electricity_emission_factor = None
    row.electricity_ef_unit = None
    row.electricity_ef_source_code = None
    row.specific_indirect_embedded_emissions = None
    row.specific_indirect_unit = None


def _clear_default_fields(row: CbamPurchasedPrecursor) -> None:
    row.default_dataset_id = None
    row.default_value_id = None
    row.default_snapshot_json = None
    row.default_justification_code = None


def _apply_supplier_derivation(row: CbamPurchasedPrecursor) -> None:
    """Persist workbook L52 = L50*L51 for supplier-provided data."""
    indirect = compute_specific_indirect(
        electricity_intensity=row.electricity_consumption_intensity,
        electricity_emission_factor=row.electricity_emission_factor,
    )
    row.specific_indirect_embedded_emissions = indirect
    row.specific_indirect_unit = SPECIFIC_INDIRECT_UNIT if indirect is not None else None
    if row.specific_direct_embedded_emissions is not None and not row.specific_direct_unit:
        row.specific_direct_unit = SPECIFIC_DIRECT_UNIT
    if row.electricity_consumption_intensity is not None and not row.electricity_intensity_unit:
        row.electricity_intensity_unit = ELECTRICITY_INTENSITY_UNIT
    if row.electricity_emission_factor is not None and not row.electricity_ef_unit:
        row.electricity_ef_unit = ELECTRICITY_EF_UNIT


def _get_default_value_for_dataset(
    db: Session, dataset_id: uuid.UUID, value_id: uuid.UUID
) -> CbamPrecursorDefaultValue:
    value = db.get(CbamPrecursorDefaultValue, value_id)
    if value is None or value.dataset_id != dataset_id:
        raise NotFoundError("EU default value not found in the active dataset.")
    return value


def _apply_default_resolution(
    db: Session, row: CbamPurchasedPrecursor, *, explicit_value_id: uuid.UUID | None
) -> None:
    """Resolve and snapshot the EU default value onto the record (immutable JSON)."""
    dataset = get_active_dataset(db)
    lookup_key = build_lookup_key(
        country_name=row.country_of_origin,
        cn_normalized_code=row.cn_normalized_code,
        production_route=row.production_route,
        goods_description=None,
    )

    if explicit_value_id is not None:
        value = _get_default_value_for_dataset(db, dataset.id, explicit_value_id)
        _require_default_value_matches_identity(row, value)
    else:
        resolution = resolve_default_value(
            db,
            country_of_origin=row.country_of_origin,
            cn_code=row.cn_normalized_code,
            production_route=row.production_route,
            dataset=dataset,
        )
        if resolution.status != RESOLUTION_RESOLVED or resolution.value is None:
            row.default_dataset_id = None
            row.default_value_id = None
            row.default_snapshot_json = None
            return
        value = _get_default_value_for_dataset(db, dataset.id, resolution.value.id)

    row.default_dataset_id = dataset.id
    row.default_value_id = value.id
    row.default_snapshot_json = build_default_snapshot(
        dataset=dataset,
        value=value,
        lookup_key=lookup_key,
        requested_country=row.country_of_origin,
        requested_cn=row.cn_normalized_code,
        requested_route=row.production_route,
        requested_description=None,
    )


def _require_default_value_matches_identity(
    row: CbamPurchasedPrecursor, value: CbamPrecursorDefaultValue
) -> None:
    mismatches: list[dict[str, str | None]] = []
    if (
        row.country_of_origin
        and normalize_country_name(row.country_of_origin).lower() != value.country_name.lower()
    ):
        mismatches.append({"field": "countryOfOrigin", "expected": value.country_name})
    if row.cn_normalized_code and row.cn_normalized_code != value.cn_normalized_code:
        mismatches.append({"field": "cnCode", "expected": value.cn_display_code})
    row_route = (row.production_route or "").strip().lower()
    value_route = (value.production_route or "").strip().lower()
    if row_route != value_route:
        mismatches.append({"field": "productionRoute", "expected": value.production_route})
    if mismatches:
        raise BusinessRuleError(
            "The selected EU default value does not match the precursor identity.",
            details=[{"code": CODE_DEFAULT_VALUE_UNRESOLVED, "mismatches": mismatches}],
        )


def _get_precursor(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
) -> CbamPurchasedPrecursor:
    row = db.get(CbamPurchasedPrecursor, precursor_id)
    if (
        row is None
        or row.organization_id != organization_id
        or row.reporting_period_binding_id != binding_id
    ):
        raise NotFoundError("CBAM purchased precursor not found.")
    return row


def _require_purchased_input(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    record_id: uuid.UUID,
) -> CbamPurchasedInputRecord:
    record = db.get(CbamPurchasedInputRecord, record_id)
    if (
        record is None
        or record.organization_id != organization_id
        or record.reporting_period_binding_id != binding_id
    ):
        raise BusinessRuleError(
            "The linked purchased input record must belong to the same organization and "
            "reporting period binding.",
            details=[{"code": CODE_PURCHASED_INPUT_INVALID}],
        )
    return record


def _list_uses(db: Session, precursor_id: uuid.UUID) -> list[CbamPurchasedPrecursorProductUse]:
    return list(
        db.execute(
            select(CbamPurchasedPrecursorProductUse).where(
                CbamPurchasedPrecursorProductUse.precursor_id == precursor_id
            )
        )
        .scalars()
        .all()
    )


def _list_uses_for_precursors(
    db: Session, precursor_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[CbamPurchasedPrecursorProductUse]]:
    if not precursor_ids:
        return {}
    rows = list(
        db.execute(
            select(CbamPurchasedPrecursorProductUse).where(
                CbamPurchasedPrecursorProductUse.precursor_id.in_(precursor_ids)
            )
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, list[CbamPurchasedPrecursorProductUse]] = {
        pid: [] for pid in precursor_ids
    }
    for row in rows:
        out.setdefault(row.precursor_id, []).append(row)
    return out


def _product_use_response(
    use: CbamPurchasedPrecursorProductUse,
) -> PrecursorProductUseResponse:
    try:
        qty_t: Decimal | None = to_tonnes(use.quantity, use.unit)
    except ValidationAppError:
        qty_t = None
    return PrecursorProductUseResponse(
        id=use.id,
        precursor_id=use.precursor_id,
        organization_id=use.organization_id,
        reporting_period_binding_id=use.reporting_period_binding_id,
        target_product_profile_version_id=use.target_product_profile_version_id,
        quantity=use.quantity,
        unit=use.unit,
        quantity_tonnes=qty_t,
        notes=use.notes,
        row_version=use.row_version,
    )


def _validate_use_targets(
    db: Session,
    organization_id: uuid.UUID,
    uses: list[CbamPurchasedPrecursorProductUse],
) -> list[str]:
    codes: list[str] = []
    for use in uses:
        try:
            get_product_profile_for_org(db, organization_id, use.target_product_profile_version_id)
        except NotFoundError:
            codes.append(CODE_TARGET_PRODUCT_INVALID)
    return codes


def _live_resolution(db: Session, row: CbamPurchasedPrecursor) -> PrecursorDefaultResolution | None:
    """Live catalog lookup only for drafts without a snapshot."""
    if row.data_source_mode != MODE_EU_DEFAULT or row.default_snapshot_json:
        return None
    return resolve_default_value(
        db,
        country_of_origin=row.country_of_origin,
        cn_code=row.cn_normalized_code,
        production_route=row.production_route,
    )


def _default_source_view(
    row: CbamPurchasedPrecursor,
    resolution: PrecursorDefaultResolution | None,
) -> PrecursorDefaultSourceView:
    if row.data_source_mode != MODE_EU_DEFAULT:
        return PrecursorDefaultSourceView(
            applicable=False,
            resolution_status=RESOLUTION_NOT_APPLICABLE,
            issue_code=None,
            from_snapshot=False,
            dataset_id=None,
            dataset_code=None,
            dataset_version=None,
            content_checksum=None,
            default_value_id=None,
            lookup_key=None,
            specific_direct_embedded_emissions=None,
            specific_direct_status=None,
            specific_direct_unit=None,
            specific_indirect_embedded_emissions=None,
            specific_indirect_status=None,
            specific_indirect_unit=None,
            justification_code=None,
            candidate_count=0,
            snapshot=None,
            other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
        )

    snapshot = row.default_snapshot_json
    if snapshot:
        dataset_meta = snapshot.get("dataset", {})
        value_meta = snapshot.get("value", {})
        units_meta = snapshot.get("units", {})
        direct, indirect = snapshot_specific_values(snapshot)
        return PrecursorDefaultSourceView(
            applicable=True,
            resolution_status=RESOLUTION_RESOLVED,
            issue_code=None,
            from_snapshot=True,
            dataset_id=row.default_dataset_id,
            dataset_code=dataset_meta.get("datasetCode"),
            dataset_version=dataset_meta.get("datasetVersion"),
            content_checksum=dataset_meta.get("contentChecksum"),
            default_value_id=row.default_value_id,
            lookup_key=value_meta.get("lookupKey"),
            specific_direct_embedded_emissions=direct,
            specific_direct_status=value_meta.get("directValueStatus"),
            specific_direct_unit=units_meta.get("specificDirect", SPECIFIC_DIRECT_UNIT),
            specific_indirect_embedded_emissions=indirect,
            specific_indirect_status=value_meta.get("indirectValueStatus"),
            specific_indirect_unit=units_meta.get("specificIndirect", SPECIFIC_INDIRECT_UNIT),
            justification_code=row.default_justification_code,
            candidate_count=1,
            snapshot=snapshot,
            other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
        )

    status = resolution.status if resolution is not None else RESOLUTION_UNRESOLVED
    issue_code = resolution.issue_code if resolution is not None else CODE_DEFAULT_VALUE_UNRESOLVED
    return PrecursorDefaultSourceView(
        applicable=True,
        resolution_status=status,
        issue_code=issue_code,
        from_snapshot=False,
        dataset_id=None,
        dataset_code=resolution.dataset.dataset_code if resolution and resolution.dataset else None,
        dataset_version=(
            resolution.dataset.dataset_version if resolution and resolution.dataset else None
        ),
        content_checksum=(
            resolution.dataset.content_checksum if resolution and resolution.dataset else None
        ),
        default_value_id=None,
        lookup_key=resolution.lookup_key if resolution is not None else None,
        specific_direct_embedded_emissions=None,
        specific_direct_status=None,
        specific_direct_unit=SPECIFIC_DIRECT_UNIT,
        specific_indirect_embedded_emissions=None,
        specific_indirect_status=None,
        specific_indirect_unit=SPECIFIC_INDIRECT_UNIT,
        justification_code=row.default_justification_code,
        candidate_count=resolution.candidate_count if resolution is not None else 0,
        snapshot=None,
        other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
    )


def _effective_specific_values(
    row: CbamPurchasedPrecursor,
    default_view: PrecursorDefaultSourceView,
) -> tuple[Decimal | None, Decimal | None, str | None]:
    if row.data_source_mode == MODE_SUPPLIER_DATA:
        return (
            row.specific_direct_embedded_emissions,
            row.specific_indirect_embedded_emissions,
            MODE_SUPPLIER_DATA,
        )
    if default_view.resolution_status != RESOLUTION_RESOLVED:
        return None, None, None
    return (
        default_view.specific_direct_embedded_emissions,
        default_view.specific_indirect_embedded_emissions,
        "EU_DEFAULT_SNAPSHOT",
    )


def _calculation_view(
    *,
    quantity_tonnes: Decimal | None,
    specific_direct: Decimal | None,
    specific_indirect: Decimal | None,
    value_source: str | None,
) -> PrecursorCalculationView:
    if value_source is None:
        return PrecursorCalculationView(
            status=CALC_STATUS_NOT_CALCULATED,
            value_source=None,
            quantity_tonnes=quantity_tonnes,
            specific_direct_embedded_emissions=None,
            specific_indirect_embedded_emissions=None,
            total_direct_embedded_emissions=None,
            total_indirect_embedded_emissions=None,
            total_embedded_emissions=None,
            result_unit=RESULT_UNIT_TCO2E,
            formula_refs=WORKBOOK_FORMULA_REFS,
            rollup_note=PRODUCT_TOTALS_ROLLUP_NOTE,
        )
    totals = compute_total_embedded(
        quantity_tonnes=quantity_tonnes,
        specific_direct=specific_direct,
        specific_indirect=specific_indirect,
    )
    return PrecursorCalculationView(
        status=totals.status,
        value_source=value_source,
        quantity_tonnes=totals.quantity_tonnes,
        specific_direct_embedded_emissions=totals.specific_direct,
        specific_indirect_embedded_emissions=totals.specific_indirect,
        total_direct_embedded_emissions=totals.total_direct_tco2e,
        total_indirect_embedded_emissions=totals.total_indirect_tco2e,
        total_embedded_emissions=totals.total_tco2e,
        result_unit=RESULT_UNIT_TCO2E,
        formula_refs=WORKBOOK_FORMULA_REFS,
        rollup_note=PRODUCT_TOTALS_ROLLUP_NOTE,
    )


def _is_empty(row: CbamPurchasedPrecursor, uses: list[CbamPurchasedPrecursorProductUse]) -> bool:
    return (
        not row.name
        and not row.cn_normalized_code
        and not row.country_of_origin
        and row.quantity is None
        and row.non_cbam_quantity is None
        and not uses
        and row.specific_direct_embedded_emissions is None
        and row.electricity_consumption_intensity is None
        and row.electricity_emission_factor is None
        and row.default_snapshot_json is None
    )


def _compute_readiness(
    *,
    row: CbamPurchasedPrecursor,
    uses: list[CbamPurchasedPrecursorProductUse],
    balance_status: str,
    remaining: Decimal | None,
    default_view: PrecursorDefaultSourceView,
    target_blocking: list[str],
) -> PurchasedPrecursorReadiness:
    resolution_status = default_view.resolution_status
    if row.status == PRECURSOR_STATUS_ARCHIVED:
        return PurchasedPrecursorReadiness(
            precursor_id=row.id,
            reporting_period_binding_id=row.reporting_period_binding_id,
            status=cast(ReadinessStatus, READINESS_INCOMPLETE),
            blocking_issue_codes=[CODE_PRECURSOR_ARCHIVED],
            informational_codes=[],
            balance_status=balance_status,
            remaining_tonnes=remaining,
            resolution_status=resolution_status,
        )

    if _is_empty(row, uses):
        return PurchasedPrecursorReadiness(
            precursor_id=row.id,
            reporting_period_binding_id=row.reporting_period_binding_id,
            status=cast(ReadinessStatus, READINESS_EMPTY),
            blocking_issue_codes=[
                CODE_PRECURSOR_NAME_REQUIRED,
                CODE_PRECURSOR_QUANTITY_MISSING,
                CODE_PRECURSOR_DISTRIBUTION_INCOMPLETE,
            ],
            informational_codes=[],
            balance_status=balance_status,
            remaining_tonnes=remaining,
            resolution_status=resolution_status,
        )

    blocking: list[str] = []
    if not (row.name and row.name.strip()):
        blocking.append(CODE_PRECURSOR_NAME_REQUIRED)
    if row.data_source_mode not in SUPPORTED_DATA_SOURCE_MODES:
        blocking.append(CODE_PRECURSOR_MODE_UNSUPPORTED)
    if row.quantity is None or row.quantity_unit is None:
        blocking.append(CODE_PRECURSOR_QUANTITY_MISSING)
    if balance_status == BALANCE_INCOMPLETE:
        blocking.append(CODE_PRECURSOR_DISTRIBUTION_INCOMPLETE)
    elif balance_status != BALANCE_BALANCED:
        blocking.append(CODE_PRECURSOR_DISTRIBUTION_UNBALANCED)
    blocking.extend(target_blocking)

    if row.data_source_mode == MODE_SUPPLIER_DATA:
        if row.specific_direct_embedded_emissions is None:
            blocking.append(CODE_SUPPLIER_DIRECT_EMISSIONS_MISSING)
        if row.electricity_consumption_intensity is None or row.electricity_emission_factor is None:
            blocking.append(CODE_SUPPLIER_ELECTRICITY_DATA_INCOMPLETE)
        numeric_present = any(getattr(row, field) is not None for field in SUPPLIER_NUMERIC_FIELDS)
        has_provenance = bool(
            (row.provenance_notes and row.provenance_notes.strip())
            or (row.evidence_reference and row.evidence_reference.strip())
        )
        if numeric_present and not has_provenance:
            blocking.append(CODE_SUPPLIER_PROVENANCE_REQUIRED)
    else:
        if not row.country_of_origin:
            blocking.append(CODE_PRECURSOR_COUNTRY_REQUIRED)
        if not row.cn_normalized_code:
            blocking.append(CODE_PRECURSOR_CN_REQUIRED)
        if resolution_status == RESOLUTION_AMBIGUOUS:
            blocking.append(CODE_DEFAULT_VALUE_AMBIGUOUS)
        elif resolution_status != RESOLUTION_RESOLVED:
            blocking.append(CODE_DEFAULT_VALUE_UNRESOLVED)
        elif (
            default_view.specific_direct_status != DV_STATUS_NUMERIC
            or default_view.specific_indirect_status != DV_STATUS_NUMERIC
        ):
            blocking.append(CODE_DEFAULT_VALUE_NOT_NUMERIC)

    seen: set[str] = set()
    ordered: list[str] = []
    for code in blocking:
        if code not in seen:
            seen.add(code)
            ordered.append(code)

    status: ReadinessStatus
    if not ordered:
        status = cast(ReadinessStatus, READINESS_READY)
    elif CODE_DEFAULT_VALUE_AMBIGUOUS in ordered:
        status = cast(ReadinessStatus, READINESS_AMBIGUOUS)
    elif CODE_DEFAULT_VALUE_UNRESOLVED in ordered:
        status = cast(ReadinessStatus, READINESS_UNRESOLVED)
    elif CODE_PRECURSOR_DISTRIBUTION_UNBALANCED in ordered:
        status = cast(ReadinessStatus, READINESS_UNBALANCED)
    else:
        status = cast(ReadinessStatus, READINESS_INCOMPLETE)

    return PurchasedPrecursorReadiness(
        precursor_id=row.id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        status=status,
        blocking_issue_codes=ordered,
        informational_codes=[],
        balance_status=balance_status,
        remaining_tonnes=remaining,
        resolution_status=resolution_status,
    )


def _to_response(
    db: Session,
    row: CbamPurchasedPrecursor,
    *,
    uses: list[CbamPurchasedPrecursorProductUse] | None = None,
) -> PurchasedPrecursorResponse:
    if uses is None:
        uses = _list_uses(db, row.id)
    use_resps: list[PrecursorProductUseResponse] = []
    use_tonnes = Decimal("0")
    for use in uses:
        resp = _product_use_response(use)
        use_resps.append(resp)
        if resp.quantity_tonnes is not None:
            use_tonnes += resp.quantity_tonnes

    purchased_t = _optional_tonnes(row.quantity, row.quantity_unit)
    non_cbam_t = _optional_tonnes(row.non_cbam_quantity, row.non_cbam_quantity_unit)
    balance = compute_precursor_distribution_balance(
        purchased_tonnes=purchased_t,
        product_use_tonnes=use_tonnes,
        non_cbam_tonnes=non_cbam_t,
    )

    default_view = _default_source_view(row, _live_resolution(db, row))
    specific_direct, specific_indirect, value_source = _effective_specific_values(row, default_view)
    calculation = _calculation_view(
        quantity_tonnes=purchased_t,
        specific_direct=specific_direct,
        specific_indirect=specific_indirect,
        value_source=value_source,
    )
    readiness = _compute_readiness(
        row=row,
        uses=uses,
        balance_status=balance.balance_status,
        remaining=balance.remaining_tonnes,
        default_view=default_view,
        target_blocking=_validate_use_targets(db, row.organization_id, uses),
    )

    return PurchasedPrecursorResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        installation_profile_id=row.installation_profile_id,
        purchased_input_record_id=row.purchased_input_record_id,
        supplier_id=row.supplier_id,
        name=row.name,
        identifier=row.identifier,
        aggregated_goods_category=row.aggregated_goods_category,
        cn_normalized_code=row.cn_normalized_code,
        cn_display_code=row.cn_display_code,
        country_of_origin=row.country_of_origin,
        production_route=row.production_route,
        data_source_mode=row.data_source_mode,
        status=row.status,
        notes=row.notes,
        row_version=row.row_version,
        readiness=readiness,
        distribution=PrecursorDistributionView(
            quantity=row.quantity,
            quantity_unit=row.quantity_unit,
            purchased_tonnes=balance.purchased_tonnes,
            non_cbam_quantity=row.non_cbam_quantity,
            non_cbam_quantity_unit=row.non_cbam_quantity_unit,
            non_cbam_tonnes=balance.non_cbam_tonnes,
            product_use_tonnes=balance.product_use_tonnes,
            distributed_tonnes=balance.distributed_tonnes,
            remaining_tonnes=balance.remaining_tonnes,
            balance_status=balance.balance_status,
            formula_ref="E_PurchPrec!L39=L25-SUM(L28:L38)",
            product_uses=use_resps,
        ),
        supplier_data=PrecursorSupplierDataView(
            applicable=row.data_source_mode == MODE_SUPPLIER_DATA,
            specific_direct_embedded_emissions=row.specific_direct_embedded_emissions,
            specific_direct_unit=row.specific_direct_unit,
            specific_direct_source_code=row.specific_direct_source_code,
            electricity_consumption_intensity=row.electricity_consumption_intensity,
            electricity_intensity_unit=row.electricity_intensity_unit,
            electricity_intensity_source_code=row.electricity_intensity_source_code,
            electricity_emission_factor=row.electricity_emission_factor,
            electricity_ef_unit=row.electricity_ef_unit,
            electricity_ef_source_code=row.electricity_ef_source_code,
            specific_indirect_embedded_emissions=row.specific_indirect_embedded_emissions,
            specific_indirect_unit=row.specific_indirect_unit,
            provenance_notes=row.provenance_notes,
            evidence_reference=row.evidence_reference,
        ),
        default_source=default_view,
        calculation=calculation,
    )


def get_purchased_precursor_metadata(
    db: Session, user: User, organization_id: uuid.UUID
) -> PurchasedPrecursorMetadataResponse:
    require_cbam_view(db, user, organization_id)
    dataset = get_active_dataset(db)
    lists = [
        PrecursorControlledListResponse(
            list_code=lst.list_code,
            title_en=lst.title_en,
            workbook_named_range=lst.workbook_named_range,
            workbook_sheet=lst.workbook_sheet,
            help_en=lst.help_en,
            items=[
                PrecursorControlledListItemResponse(
                    code=item.code,
                    label_en=item.label_en,
                    description_en=item.description_en,
                    sort_order=item.sort_order,
                    workbook_ref=item.workbook_ref,
                )
                for item in lst.items
            ],
        )
        for lst in list_precursor_controlled_lists()
    ]
    return PurchasedPrecursorMetadataResponse(
        methodology_code=METHODOLOGY_CODE,
        methodology_version=METHODOLOGY_VERSION,
        workbook_filename=WORKBOOK_FILENAME,
        workbook_sha256=WORKBOOK_SHA256,
        workbook_primary_sheet=WORKBOOK_PRIMARY_SHEET,
        workbook_formula_refs=WORKBOOK_FORMULA_REFS,
        supported_data_source_modes=sorted(SUPPORTED_DATA_SOURCE_MODES),
        units={
            "quantity": CANONICAL_MASS_UNIT,
            "specificDirect": SPECIFIC_DIRECT_UNIT,
            "specificIndirect": SPECIFIC_INDIRECT_UNIT,
            "electricityIntensity": ELECTRICITY_INTENSITY_UNIT,
            "electricityEmissionFactor": ELECTRICITY_EF_UNIT,
            "result": RESULT_UNIT_TCO2E,
        },
        field_map=PRECURSOR_FIELD_MAP,
        extraction=workbook_extraction_metadata(),
        controlled_lists=lists,
        default_value_dataset=PrecursorDefaultDatasetResponse(
            id=dataset.id,
            dataset_code=dataset.dataset_code,
            dataset_version=dataset.dataset_version,
            content_checksum=dataset.content_checksum,
            source_workbook_name=dataset.source_workbook_name,
            source_workbook_sha256=dataset.source_workbook_sha256,
            source_template_version=dataset.source_template_version,
            regulation_reference=dataset.regulation_reference,
            valid_from=dataset.valid_from,
            valid_until=dataset.valid_until,
            status=dataset.status,
            value_count=dataset.value_count,
        ),
        other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
        rollup_note=PRODUCT_TOTALS_ROLLUP_NOTE,
    )


def get_precursor_controlled_list_response(
    db: Session, user: User, organization_id: uuid.UUID, list_code: str
) -> PrecursorControlledListResponse:
    require_cbam_view(db, user, organization_id)
    lst = get_precursor_controlled_list(list_code)
    if lst is None:
        raise NotFoundError(f"Controlled list not found: {list_code}")
    return PrecursorControlledListResponse(
        list_code=lst.list_code,
        title_en=lst.title_en,
        workbook_named_range=lst.workbook_named_range,
        workbook_sheet=lst.workbook_sheet,
        help_en=lst.help_en,
        items=[
            PrecursorControlledListItemResponse(
                code=item.code,
                label_en=item.label_en,
                description_en=item.description_en,
                sort_order=item.sort_order,
                workbook_ref=item.workbook_ref,
            )
            for item in lst.items
        ],
    )


def list_purchased_precursors(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
) -> Page[PurchasedPrecursorResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamPurchasedPrecursor).where(
        CbamPurchasedPrecursor.organization_id == organization_id,
        CbamPurchasedPrecursor.reporting_period_binding_id == binding_id,
    )
    if not include_archived:
        stmt = stmt.where(CbamPurchasedPrecursor.status == PRECURSOR_STATUS_DRAFT)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamPurchasedPrecursor.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    uses_by_precursor = _list_uses_for_precursors(db, [row.id for row in rows])
    return paginate(
        [_to_response(db, row, uses=uses_by_precursor.get(row.id, [])) for row in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_purchased_precursor(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
) -> PurchasedPrecursorResponse:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    return _to_response(db, _get_precursor(db, organization_id, binding_id, precursor_id))


def get_purchased_precursor_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
) -> PurchasedPrecursorReadiness:
    return get_purchased_precursor(db, user, organization_id, binding_id, precursor_id).readiness


def get_purchased_precursor_binding_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> PurchasedPrecursorSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    rows = list(
        db.execute(
            select(CbamPurchasedPrecursor)
            .where(
                CbamPurchasedPrecursor.organization_id == organization_id,
                CbamPurchasedPrecursor.reporting_period_binding_id == binding_id,
            )
            .order_by(CbamPurchasedPrecursor.created_at.asc())
        )
        .scalars()
        .all()
    )
    uses_by_precursor = _list_uses_for_precursors(db, [row.id for row in rows])
    readiness_list = [
        _to_response(db, row, uses=uses_by_precursor.get(row.id, [])).readiness for row in rows
    ]
    return PurchasedPrecursorSummary(
        reporting_period_binding_id=binding_id,
        precursor_count=len(rows),
        draft_count=sum(1 for r in rows if r.status == PRECURSOR_STATUS_DRAFT),
        archived_count=sum(1 for r in rows if r.status == PRECURSOR_STATUS_ARCHIVED),
        ready_count=sum(1 for r in readiness_list if r.status == READINESS_READY),
        unbalanced_count=sum(1 for r in readiness_list if r.status == READINESS_UNBALANCED),
        unresolved_count=sum(1 for r in readiness_list if r.status == READINESS_UNRESOLVED),
        ambiguous_count=sum(1 for r in readiness_list if r.status == READINESS_AMBIGUOUS),
        precursors=readiness_list,
    )


def create_purchased_precursor(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PurchasedPrecursorCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedPrecursorResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)

    mode = _validate_mode(payload.data_source_mode)
    submitted = payload.model_dump(exclude_unset=True)
    _reject_mixed_source(mode, submitted)
    _validate_source_codes(
        specific_direct_source_code=payload.specific_direct_source_code,
        electricity_intensity_source_code=payload.electricity_intensity_source_code,
        electricity_ef_source_code=payload.electricity_ef_source_code,
        default_justification_code=payload.default_justification_code,
    )

    quantity_unit = _require_mass_unit(payload.quantity_unit, field="quantityUnit")
    non_cbam_unit = _require_mass_unit(payload.non_cbam_quantity_unit, field="nonCbamQuantityUnit")
    if payload.quantity is not None:
        require_non_negative(payload.quantity, field="quantity")
    if payload.non_cbam_quantity is not None:
        require_non_negative(payload.non_cbam_quantity, field="nonCbamQuantity")
    for value, field in (
        (payload.specific_direct_embedded_emissions, "specificDirectEmbeddedEmissions"),
        (payload.electricity_consumption_intensity, "electricityConsumptionIntensity"),
        (payload.electricity_emission_factor, "electricityEmissionFactor"),
    ):
        if value is not None:
            require_non_negative(value, field=field)

    if payload.purchased_input_record_id is not None:
        _require_purchased_input(db, organization_id, binding_id, payload.purchased_input_record_id)
    if payload.supplier_id is not None:
        get_supplier(db, organization_id, payload.supplier_id)

    if mode == MODE_SUPPLIER_DATA:
        _require_supplier_provenance(
            numeric_values_present=any(
                submitted.get(field) is not None for field in SUPPLIER_NUMERIC_FIELDS
            ),
            provenance_notes=payload.provenance_notes,
            evidence_reference=payload.evidence_reference,
        )

    normalized_cn = normalize_precursor_cn_code(payload.cn_code) if payload.cn_code else None
    row = CbamPurchasedPrecursor(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        installation_profile_id=installation.id,
        purchased_input_record_id=payload.purchased_input_record_id,
        supplier_id=payload.supplier_id,
        name=(payload.name.strip() if payload.name else None) or None,
        identifier=(payload.identifier.strip() if payload.identifier else None) or None,
        aggregated_goods_category=(
            payload.aggregated_goods_category.strip() if payload.aggregated_goods_category else None
        )
        or None,
        cn_normalized_code=normalized_cn or None,
        cn_display_code=(payload.cn_code.strip() if payload.cn_code else None) or None,
        country_of_origin=(
            normalize_country_name(payload.country_of_origin) if payload.country_of_origin else None
        )
        or None,
        production_route=(payload.production_route.strip() if payload.production_route else None)
        or None,
        data_source_mode=mode,
        quantity=payload.quantity,
        quantity_unit=quantity_unit,
        non_cbam_quantity=payload.non_cbam_quantity,
        non_cbam_quantity_unit=non_cbam_unit,
        provenance_notes=payload.provenance_notes,
        evidence_reference=payload.evidence_reference,
        status=PRECURSOR_STATUS_DRAFT,
        notes=payload.notes,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )

    if mode == MODE_SUPPLIER_DATA:
        row.specific_direct_embedded_emissions = payload.specific_direct_embedded_emissions
        row.specific_direct_unit = _validate_fixed_unit(
            payload.specific_direct_unit, SPECIFIC_DIRECT_UNIT, field="specificDirectUnit"
        )
        row.specific_direct_source_code = payload.specific_direct_source_code
        row.electricity_consumption_intensity = payload.electricity_consumption_intensity
        row.electricity_intensity_unit = _validate_fixed_unit(
            payload.electricity_intensity_unit,
            ELECTRICITY_INTENSITY_UNIT,
            field="electricityIntensityUnit",
        )
        row.electricity_intensity_source_code = payload.electricity_intensity_source_code
        row.electricity_emission_factor = payload.electricity_emission_factor
        row.electricity_ef_unit = _validate_fixed_unit(
            payload.electricity_ef_unit, ELECTRICITY_EF_UNIT, field="electricityEfUnit"
        )
        row.electricity_ef_source_code = payload.electricity_ef_source_code
        _apply_supplier_derivation(row)
    else:
        row.default_justification_code = payload.default_justification_code

    db.add(row)
    db.flush()
    if mode == MODE_EU_DEFAULT:
        _apply_default_resolution(db, row, explicit_value_id=payload.default_value_id)

    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.created",
        entity_type="cbam_purchased_precursor",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"id": str(row.id), "dataSourceMode": mode},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def update_purchased_precursor_draft(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    payload: PurchasedPrecursorUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedPrecursorResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    row = _get_precursor(db, organization_id, binding_id, precursor_id)
    if row.status == PRECURSOR_STATUS_ARCHIVED:
        raise BusinessRuleError(
            "Archived purchased precursors cannot be edited.",
            details=[{"code": CODE_PRECURSOR_ARCHIVED}],
        )
    check_row_version(row.row_version, payload.row_version, entity="CBAM purchased precursor")
    data = payload.model_dump(exclude_unset=True)
    data.pop("row_version", None)

    previous_mode = row.data_source_mode
    mode = _validate_mode(data.get("data_source_mode") or previous_mode)
    _reject_mixed_source(mode, data)
    _validate_source_codes(
        specific_direct_source_code=data.get(
            "specific_direct_source_code", row.specific_direct_source_code
        ),
        electricity_intensity_source_code=data.get(
            "electricity_intensity_source_code", row.electricity_intensity_source_code
        ),
        electricity_ef_source_code=data.get(
            "electricity_ef_source_code", row.electricity_ef_source_code
        ),
        default_justification_code=data.get(
            "default_justification_code", row.default_justification_code
        ),
    )

    if "purchased_input_record_id" in data:
        record_id = data["purchased_input_record_id"]
        if record_id is not None:
            _require_purchased_input(db, organization_id, binding_id, record_id)
        row.purchased_input_record_id = record_id
    if "supplier_id" in data:
        supplier_id = data["supplier_id"]
        if supplier_id is not None:
            get_supplier(db, organization_id, supplier_id)
        row.supplier_id = supplier_id

    if "name" in data:
        row.name = (data["name"].strip() if data["name"] else None) or None
    if "identifier" in data:
        row.identifier = (data["identifier"].strip() if data["identifier"] else None) or None
    if "aggregated_goods_category" in data:
        category = data["aggregated_goods_category"]
        row.aggregated_goods_category = (category.strip() if category else None) or None
    if "cn_code" in data:
        cn_code = data["cn_code"]
        row.cn_normalized_code = normalize_precursor_cn_code(cn_code) or None if cn_code else None
        row.cn_display_code = (cn_code.strip() if cn_code else None) or None
    if "country_of_origin" in data:
        country = data["country_of_origin"]
        row.country_of_origin = (normalize_country_name(country) if country else None) or None
    if "production_route" in data:
        route = data["production_route"]
        row.production_route = (route.strip() if route else None) or None
    if "notes" in data:
        row.notes = data["notes"]
    if "provenance_notes" in data:
        row.provenance_notes = data["provenance_notes"]
    if "evidence_reference" in data:
        row.evidence_reference = data["evidence_reference"]

    for qty_field, unit_field in (
        ("quantity", "quantity_unit"),
        ("non_cbam_quantity", "non_cbam_quantity_unit"),
    ):
        if qty_field in data:
            quantity = data[qty_field]
            if quantity is not None:
                require_non_negative(quantity, field=qty_field)
            setattr(row, qty_field, quantity)
        if unit_field in data:
            setattr(row, unit_field, _require_mass_unit(data[unit_field], field=unit_field))

    row.data_source_mode = mode
    if mode == MODE_SUPPLIER_DATA:
        if previous_mode != mode:
            _clear_default_fields(row)
        for field, expected_unit in (
            ("specific_direct_unit", SPECIFIC_DIRECT_UNIT),
            ("electricity_intensity_unit", ELECTRICITY_INTENSITY_UNIT),
            ("electricity_ef_unit", ELECTRICITY_EF_UNIT),
        ):
            if field in data:
                setattr(row, field, _validate_fixed_unit(data[field], expected_unit, field=field))
        for field in (
            "specific_direct_embedded_emissions",
            "electricity_consumption_intensity",
            "electricity_emission_factor",
        ):
            if field in data:
                if data[field] is not None:
                    require_non_negative(data[field], field=field)
                setattr(row, field, data[field])
        for field in (
            "specific_direct_source_code",
            "electricity_intensity_source_code",
            "electricity_ef_source_code",
        ):
            if field in data:
                setattr(row, field, data[field])
        _apply_supplier_derivation(row)
        _require_supplier_provenance(
            numeric_values_present=any(
                getattr(row, field) is not None for field in SUPPLIER_NUMERIC_FIELDS
            ),
            provenance_notes=row.provenance_notes,
            evidence_reference=row.evidence_reference,
        )
    else:
        if previous_mode != mode:
            _clear_supplier_fields(row)
        if "default_justification_code" in data:
            row.default_justification_code = data["default_justification_code"]
        identity_changed = any(
            field in data for field in ("cn_code", "country_of_origin", "production_route")
        )
        explicit_value_id = data.get("default_value_id")
        if explicit_value_id is None and not identity_changed:
            # Keep a value the declarant picked earlier to settle an ambiguous match.
            explicit_value_id = row.default_value_id
        _apply_default_resolution(db, row, explicit_value_id=explicit_value_id)

    row.row_version += 1
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.updated",
        entity_type="cbam_purchased_precursor",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"rowVersion": row.row_version, "dataSourceMode": mode},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def archive_purchased_precursor(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    payload: PurchasedPrecursorVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedPrecursorResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    row = _get_precursor(db, organization_id, binding_id, precursor_id)
    check_row_version(row.row_version, payload.row_version, entity="CBAM purchased precursor")
    if row.status == PRECURSOR_STATUS_ARCHIVED:
        return _to_response(db, row)
    row.status = PRECURSOR_STATUS_ARCHIVED
    row.row_version += 1
    row.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.archived",
        entity_type="cbam_purchased_precursor",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def _require_editable_precursor(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    *,
    action: str,
) -> CbamPurchasedPrecursor:
    precursor = _get_precursor(db, organization_id, binding_id, precursor_id)
    if precursor.status == PRECURSOR_STATUS_ARCHIVED:
        raise BusinessRuleError(
            f"Cannot {action} product uses on an archived purchased precursor.",
            details=[{"code": CODE_PRECURSOR_ARCHIVED}],
        )
    return precursor


def create_precursor_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    payload: PrecursorProductUseCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PrecursorProductUseResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    precursor = _require_editable_precursor(
        db, organization_id, binding_id, precursor_id, action="add"
    )
    target = require_linkable_product_profile(
        db, organization_id, payload.target_product_profile_version_id
    )
    unit = _require_mass_unit(payload.unit, field="unit")
    assert unit is not None
    require_non_negative(payload.quantity, field="quantity")

    existing = db.execute(
        select(CbamPurchasedPrecursorProductUse).where(
            CbamPurchasedPrecursorProductUse.precursor_id == precursor_id,
            CbamPurchasedPrecursorProductUse.target_product_profile_version_id == target.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise BusinessRuleError(
            "A product-use row for this target profile already exists on the precursor.",
            details=[{"code": "PRODUCT_USE_DUPLICATE"}],
        )

    use = CbamPurchasedPrecursorProductUse(
        precursor_id=precursor_id,
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        target_product_profile_version_id=target.id,
        quantity=payload.quantity,
        unit=unit,
        notes=payload.notes,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(use)
    precursor.row_version += 1
    precursor.updated_by_user_id = user.id
    db.flush()
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.product_use.created",
        entity_type="cbam_purchased_precursor_product_use",
        entity_id=str(use.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(use)
    return _product_use_response(use)


def _get_product_use(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    use_id: uuid.UUID,
) -> CbamPurchasedPrecursorProductUse:
    use = db.get(CbamPurchasedPrecursorProductUse, use_id)
    if (
        use is None
        or use.organization_id != organization_id
        or use.reporting_period_binding_id != binding_id
        or use.precursor_id != precursor_id
    ):
        raise NotFoundError("Precursor product-use distribution row not found.")
    return use


def update_precursor_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    use_id: uuid.UUID,
    payload: PrecursorProductUseUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PrecursorProductUseResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    precursor = _require_editable_precursor(
        db, organization_id, binding_id, precursor_id, action="update"
    )
    use = _get_product_use(db, organization_id, binding_id, precursor_id, use_id)
    check_row_version(
        use.row_version, payload.row_version, entity="CBAM purchased precursor product use"
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
        unit = _require_mass_unit(data["unit"], field="unit")
        assert unit is not None
        use.unit = unit
    if "notes" in data:
        use.notes = data["notes"]
    use.row_version += 1
    use.updated_by_user_id = user.id
    precursor.row_version += 1
    precursor.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.product_use.updated",
        entity_type="cbam_purchased_precursor_product_use",
        entity_id=str(use.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(use)
    return _product_use_response(use)


def delete_precursor_product_use(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    precursor_id: uuid.UUID,
    use_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    precursor = _require_editable_precursor(
        db, organization_id, binding_id, precursor_id, action="delete"
    )
    use = _get_product_use(db, organization_id, binding_id, precursor_id, use_id)
    db.delete(use)
    precursor.row_version += 1
    precursor.updated_by_user_id = user.id
    write_audit_log(
        db,
        actor_user_id=user.id,
        organization_id=organization_id,
        action="cbam.purchased_precursor.product_use.deleted",
        entity_type="cbam_purchased_precursor_product_use",
        entity_id=str(use_id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
