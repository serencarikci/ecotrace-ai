"""Product embedded-emissions roll-up (SEE D_Processes → Summary_Products).

Read-only consumer of the direct/indirect allocation engines, Conventional production
processes and purchased precursors. It never recalculates DEA/IEA/precursor math and
never mutates their results — it only combines immutable current values.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.modules.cbam.application.calculation_math import quantize_result
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.decimal_leontief import LeontiefError
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    get_direct_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    get_indirect_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import to_tonnes
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.precursor_constants import (
    READINESS_READY as PRECURSOR_READINESS_READY,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    CODE_DEA_NOT_READY,
    CODE_DEA_PRODUCT_ROW_MISSING,
    CODE_DEA_STALE,
    CODE_IEA_NOT_READY,
    CODE_IEA_PRODUCT_ROW_MISSING,
    CODE_IEA_STALE,
    CODE_INTERNAL_PRODUCT_FLOW_INVALID,
    CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE,
    CODE_METHODOLOGY_UNSUPPORTED,
    CODE_NO_ELIGIBLE_PRODUCTS,
    CODE_PRECURSOR_NOT_READY,
    CODE_PRECURSOR_SPECIFIC_VALUES_MISSING,
    CODE_PRECURSOR_USE_UNIT_INVALID,
    CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT,
    CODE_PROCESS_METHOD_UNSUPPORTED,
    CODE_PROCESS_MISSING_FOR_PRODUCT,
    CODE_PROCESS_NOT_READY,
    CODE_PRODUCT_DENOMINATOR_MISMATCH,
    CODE_PRODUCT_DENOMINATOR_MISSING,
    CODE_PRODUCT_DENOMINATOR_ZERO,
    CODE_PRODUCT_PROFILE_NOT_LINKABLE,
    DEA_SOURCE_UNIT_TCO2,
    DEFAULT_METHODOLOGY_CODE,
    DENOMINATOR_NOTE,
    EXECUTION_STATUS_COMPLETED,
    EXPORTED_ELECTRICITY_NOTE_CODE,
    GWP_EQUIVALENCE_NOTE,
    METHODOLOGY_CODE,
    METHODOLOGY_CODE_V2,
    METHODOLOGY_VERSION_BY_CODE,
    RESULT_UNIT_TCO2E,
    SPECIFIC_UNIT_TCO2E_PER_T,
    STALE_DEA_CURRENT_RESULT_CHANGED,
    STALE_DEA_PRODUCT_VALUE_CHANGED,
    STALE_DEA_STALE,
    STALE_IEA_CURRENT_RESULT_CHANGED,
    STALE_IEA_PRODUCT_VALUE_CHANGED,
    STALE_IEA_STALE,
    STALE_INTERNAL_PRODUCT_FLOW_CHANGED,
    STALE_INTERNAL_PRODUCT_FLOW_SET_CHANGED,
    STALE_METHODOLOGY_OR_WORKBOOK_CHANGED,
    STALE_NOT_READY,
    STALE_PRECURSOR_CHANGED,
    STALE_PRECURSOR_DEFAULT_SNAPSHOT_CHANGED,
    STALE_PRECURSOR_PRODUCT_USE_CHANGED,
    STALE_PRECURSOR_SET_CHANGED,
    STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED,
    STALE_PROCESS_CHANGED,
    STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED,
    STALE_PROCESS_HEAT_OR_WASTE_GAS_CHANGED,
    STALE_PROCESS_PRODUCED_QUANTITY_CHANGED,
    STALE_PRODUCT_DENOMINATOR_CHANGED,
    STALE_PRODUCT_SET_CHANGED,
    STALE_PRODUCTION_RECORDS_CHANGED,
    SUPPORTED_METHODOLOGY_CODES,
    WORKBOOK_FILENAME,
    WORKBOOK_GAS,
    WORKBOOK_GWP,
    WORKBOOK_GWP_FACTOR,
    WORKBOOK_SHA256,
    exported_electricity_note_for,
    internal_precursor_note_for,
    workbook_formula_refs_for,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_idempotency import (
    ExportedElectricityFingerprint,
    InternalFlowFingerprint,
    PrecursorContributionFingerprint,
    ProductFingerprint,
    build_product_embedded_emissions_fingerprint,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_math import (
    ZERO,
    PrecursorContribution,
    ProductSpecifics,
    ProductTotals,
    assert_product_identities,
    compute_own_process_emissions,
    compute_precursor_contribution,
    compute_product_specifics,
    compute_product_totals,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_v2_math import (
    InternalContribution,
    InternalFlowInput,
    ProductV2Input,
    compute_v2_rollup,
)
from ecotrace.modules.cbam.application.production_process_constants import (
    METHOD_CONVENTIONAL,
)
from ecotrace.modules.cbam.application.production_process_constants import (
    READINESS_READY as PROCESS_READINESS_READY,
)
from ecotrace.modules.cbam.application.production_process_service import (
    ProductionProcessResponse,
    list_production_processes,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PrecursorProductUseResponse,
    PurchasedPrecursorResponse,
    list_purchased_precursors,
)
from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    canonicalize_decimal,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamDeaProductAllocation,
    CbamIeaProductAllocation,
    CbamProductEmbeddedEmissionsCurrent,
    CbamProductEmbeddedEmissionsInternalContribution,
    CbamProductEmbeddedEmissionsPrecursorContribution,
    CbamProductEmbeddedEmissionsProduct,
    CbamProductEmbeddedEmissionsResult,
    CbamProductionRecord,
    CbamProductProfileVersion,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate, to_camel

ReadinessStatus = Literal['READY', 'NOT_READY']

# Binding-scoped drafts are bounded in practice; the workbook itself caps process and
# precursor slots at 20 each.
_MAX_ROWS = 500


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ProductEmbeddedEmissionsExecuteRequest(CamelModel):
    # Totals are server-authoritative: any client-supplied figure is rejected outright.
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra='forbid',
    )

    client_request_id: uuid.UUID
    methodology_code: str = DEFAULT_METHODOLOGY_CODE


class ProductEmbeddedEmissionsExecutionResponse(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    methodology_code: str
    methodology_version: str
    product_count: int
    precursor_contribution_count: int
    internal_contribution_count: int
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal
    result_unit: str
    specific_unit: str
    client_request_id: uuid.UUID
    idempotent_replay: bool
    created_at: datetime


class ProductEmbeddedEmissionsProductReadiness(CamelModel):
    product_profile_version_id: uuid.UUID
    product_id: uuid.UUID | None
    cn_normalized_code: str | None
    process_id: uuid.UUID | None
    status: ReadinessStatus
    blocking_issue_codes: list[str]
    informational_codes: list[str]
    denominator_tonnes: Decimal | None
    production_records_tonnes: Decimal | None
    precursor_use_count: int


class ProductEmbeddedEmissionsReadiness(CamelModel):
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    status: ReadinessStatus
    rollup_ready: bool
    blocking_issue_codes: list[str]
    informational_codes: list[str]
    direct_emissions_allocation_result_id: uuid.UUID | None
    direct_emissions_allocation_stale: bool
    indirect_emissions_allocation_result_id: uuid.UUID | None
    indirect_emissions_allocation_stale: bool
    eligible_product_count: int
    blocked_product_count: int
    precursor_contribution_count: int
    products: list[ProductEmbeddedEmissionsProductReadiness]
    current_result_id: uuid.UUID | None
    current_is_stale: bool
    stale_reason_codes: list[str]
    exported_electricity_note_code: str
    exported_electricity_note: str
    internal_precursor_note_code: str
    internal_precursor_note: str


class ProductEmbeddedEmissionsResultSummary(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    product_count: int
    precursor_contribution_count: int
    internal_contribution_count: int
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal
    result_unit: str
    specific_unit: str
    created_at: datetime


class ProductEmbeddedEmissionsResultDetail(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    workbook_filename: str
    workbook_sha256: str
    workbook_formula_refs: str
    client_request_id: uuid.UUID
    request_fingerprint: str
    status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    product_count: int
    precursor_contribution_count: int
    internal_contribution_count: int
    total_direct_tco2e_raw: Decimal
    total_indirect_tco2e_raw: Decimal
    total_embedded_tco2e_raw: Decimal
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal
    result_unit: str
    specific_unit: str
    dea_source_unit: str
    workbook_gas: str
    workbook_gwp: str
    workbook_gwp_factor: str
    gwp_equivalence_note: str
    denominator_note: str
    exported_electricity_note_code: str
    exported_electricity_note: str
    internal_precursor_note_code: str
    internal_precursor_note: str
    direct_emissions_allocation_result_id: uuid.UUID | None
    indirect_emissions_allocation_result_id: uuid.UUID | None
    informational_codes: list[str]
    products: list[dict[str, Any]]
    precursor_contributions: list[dict[str, Any]]
    internal_contributions: list[dict[str, Any]]
    created_at: datetime
    created_by_user_id: uuid.UUID | None


class ProductEmbeddedEmissionsPeriodSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    current_result_id: uuid.UUID | None
    current_is_stale: bool
    stale_reason_codes: list[str]
    product_count: int | None
    precursor_contribution_count: int | None
    internal_contribution_count: int | None
    total_direct_tco2e: Decimal | None
    total_indirect_tco2e: Decimal | None
    total_embedded_tco2e: Decimal | None
    result_unit: str
    specific_unit: str
    totals_by_product: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Context resolution
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _ContributionCandidate:
    precursor: PurchasedPrecursorResponse
    use: PrecursorProductUseResponse
    quantity_tonnes: Decimal
    specific_direct: Decimal
    specific_indirect: Decimal
    value_source: str


@dataclass(slots=True)
class _InternalFlowCandidate:
    product_use_id: uuid.UUID
    product_use_row_version: int
    supplier_process_id: uuid.UUID
    supplier_process_row_version: int
    supplier_product_profile_version_id: uuid.UUID
    consumer_product_profile_version_id: uuid.UUID
    product_use_quantity: Decimal
    product_use_unit: str
    quantity_tonnes: Decimal
    consumer_denominator_tonnes: Decimal


@dataclass(slots=True)
class _ProductCandidate:
    profile: CbamProductProfileVersion
    process: ProductionProcessResponse
    denominator_tonnes: Decimal
    produced_quantity: Decimal
    produced_quantity_unit: str
    production_record_ids: list[uuid.UUID]
    production_records_tonnes: Decimal | None
    production_record_quantities: list[tuple[uuid.UUID, Decimal, str]]
    dea_row: CbamDeaProductAllocation
    iea_row: CbamIeaProductAllocation
    heat_attributed: Decimal
    waste_gas_attributed: Decimal
    contributions: list[_ContributionCandidate] = field(default_factory=list)
    informational: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _LiveProductState:
    """Material live values of one product, captured even when the product is blocked.

    Stale evaluation compares snapshots against this so that a result reports *why* it
    went stale instead of collapsing into a bare "not ready".
    """

    process_id: uuid.UUID | None
    produced_quantity: Decimal | None
    produced_quantity_unit: str | None
    denominator_tonnes: Decimal | None
    has_measurable_heat: bool | None
    has_waste_gas: bool | None
    heat_attributed: Decimal
    waste_gas_attributed: Decimal
    dea_direct: Decimal | None
    iea_indirect: Decimal | None
    production_record_ids: list[uuid.UUID]
    production_records_tonnes: Decimal | None
    contributions: list[_ContributionCandidate]
    has_exported_electricity: bool | None = None
    exported_electricity_mwh: Decimal | None = None
    exported_electricity_emission_factor: Decimal | None = None
    exported_electricity_direct_tco2e: Decimal = ZERO
    exported_electricity_reconciliation_status: str | None = None
    internal_flows: list[_InternalFlowCandidate] = field(default_factory=list)


@dataclass(slots=True)
class _RollupContext:
    blocking: list[str]
    informational: list[str]
    dea_result_id: uuid.UUID | None
    dea_stale: bool
    iea_result_id: uuid.UUID | None
    iea_stale: bool
    eligible: list[_ProductCandidate]
    live_by_profile: dict[uuid.UUID, _LiveProductState]
    product_readiness: list[ProductEmbeddedEmissionsProductReadiness]


def _validate_methodology_code(methodology_code: str) -> str:
    if methodology_code not in SUPPORTED_METHODOLOGY_CODES:
        raise BusinessRuleError(
            f'Unsupported product embedded-emissions methodology: {methodology_code}',
            details=[{'code': CODE_METHODOLOGY_UNSUPPORTED, 'methodologyCode': methodology_code}],
        )
    return methodology_code


def _methodology_version(methodology_code: str) -> str:
    return METHODOLOGY_VERSION_BY_CODE[methodology_code]


def _t72_attributed(process: ProductionProcessResponse) -> Decimal:
    attributed = process.process_exported_electricity.attributed_direct_tco2e
    return attributed if attributed is not None else ZERO


def _gather_internal_flows(
    eligible: list[_ProductCandidate],
) -> list[_InternalFlowCandidate]:
    """Process product-uses between READY candidates as Leontief internal edges.

    Supplier = process product profile; consumer = product-use target profile. Non-CBAM
    quantities never enter product-uses, so they stay outside the matrix.
    """
    by_profile = {candidate.profile.id: candidate for candidate in eligible}
    flows: list[_InternalFlowCandidate] = []
    for supplier in eligible:
        supplier_profile_id = supplier.profile.id
        for use in supplier.process.distribution.product_uses:
            consumer_profile_id = use.target_product_profile_version_id
            if consumer_profile_id not in by_profile:
                continue
            if consumer_profile_id == supplier_profile_id:
                raise BusinessRuleError(
                    'A process cannot consume its own CBAM product output.',
                    details=[{'code': CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE}],
                )
            if use.quantity_tonnes is None:
                continue
            consumer = by_profile[consumer_profile_id]
            flows.append(
                _InternalFlowCandidate(
                    product_use_id=use.id,
                    product_use_row_version=use.row_version,
                    supplier_process_id=supplier.process.id,
                    supplier_process_row_version=supplier.process.row_version,
                    supplier_product_profile_version_id=supplier_profile_id,
                    consumer_product_profile_version_id=consumer_profile_id,
                    product_use_quantity=use.quantity,
                    product_use_unit=use.unit,
                    quantity_tonnes=use.quantity_tonnes,
                    consumer_denominator_tonnes=consumer.denominator_tonnes,
                )
            )
    flows.sort(key=lambda item: str(item.product_use_id))
    return flows


def _dedupe(codes: list[str]) -> list[str]:
    out: list[str] = []
    for code in codes:
        if code not in out:
            out.append(code)
    return out


def _same_decimal(left: Decimal | None, right: Decimal | None) -> bool:
    return canonicalize_decimal(left) == canonicalize_decimal(right)


def _profile_linkable(profile: CbamProductProfileVersion) -> bool:
    return profile.classification_ready and profile.status in ('active', 'superseded')


def _resolve_context(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    methodology_code: str = DEFAULT_METHODOLOGY_CODE,
) -> _RollupContext:
    get_binding_for_org(db, organization_id, binding_id)
    blocking: list[str] = []
    informational: list[str] = []

    dea_summary = get_direct_emissions_allocation_summary(db, user, organization_id, binding_id)
    iea_summary = get_indirect_emissions_allocation_summary(db, user, organization_id, binding_id)
    dea_result_id = dea_summary.current_result_id
    iea_result_id = iea_summary.current_result_id
    dea_stale = bool(dea_summary.current_is_stale)
    iea_stale = bool(iea_summary.current_is_stale)

    if dea_result_id is None:
        blocking.append(CODE_DEA_NOT_READY)
    elif dea_stale:
        blocking.append(CODE_DEA_STALE)
    if iea_result_id is None:
        blocking.append(CODE_IEA_NOT_READY)
    elif iea_stale:
        blocking.append(CODE_IEA_STALE)

    dea_rows: dict[uuid.UUID, CbamDeaProductAllocation] = {}
    if dea_result_id is not None and not dea_stale:
        dea_rows = {
            row.product_profile_version_id: row
            for row in db.execute(
                select(CbamDeaProductAllocation).where(
                    CbamDeaProductAllocation.result_id == dea_result_id
                )
            ).scalars()
        }
    iea_rows: dict[uuid.UUID, CbamIeaProductAllocation] = {}
    if iea_result_id is not None and not iea_stale:
        iea_rows = {
            row.product_profile_version_id: row
            for row in db.execute(
                select(CbamIeaProductAllocation).where(
                    CbamIeaProductAllocation.result_id == iea_result_id
                )
            ).scalars()
        }

    processes = list_production_processes(
        db, user, organization_id, binding_id, page=1, page_size=_MAX_ROWS
    ).items
    by_profile: dict[uuid.UUID, list[ProductionProcessResponse]] = {}
    for process_row in processes:
        if process_row.product_profile_version_id is None:
            continue
        by_profile.setdefault(process_row.product_profile_version_id, []).append(process_row)

    precursors = list_purchased_precursors(
        db, user, organization_id, binding_id, page=1, page_size=_MAX_ROWS
    ).items
    uses_by_profile: dict[uuid.UUID, list[tuple[PurchasedPrecursorResponse, PrecursorProductUseResponse]]] = {}
    for precursor in precursors:
        for use in precursor.distribution.product_uses:
            uses_by_profile.setdefault(use.target_product_profile_version_id, []).append(
                (precursor, use)
            )

    profile_ids = set(by_profile) | set(uses_by_profile)
    profiles: dict[uuid.UUID, CbamProductProfileVersion] = {}
    if profile_ids:
        profiles = {
            p.id: p
            for p in db.execute(
                select(CbamProductProfileVersion).where(
                    CbamProductProfileVersion.id.in_(profile_ids),
                    CbamProductProfileVersion.organization_id == organization_id,
                )
            ).scalars()
        }

    production_by_profile: dict[uuid.UUID, list[CbamProductionRecord]] = {}
    for record in db.execute(
        select(CbamProductionRecord).where(
            CbamProductionRecord.organization_id == organization_id,
            CbamProductionRecord.reporting_period_binding_id == binding_id,
            CbamProductionRecord.status == 'active',
        )
    ).scalars():
        if record.product_profile_version_id is None:
            continue
        production_by_profile.setdefault(record.product_profile_version_id, []).append(record)

    eligible: list[_ProductCandidate] = []
    live_by_profile: dict[uuid.UUID, _LiveProductState] = {}
    readiness_rows: list[ProductEmbeddedEmissionsProductReadiness] = []

    for profile_id in sorted(by_profile, key=str):
        product_blocking: list[str] = []
        product_informational: list[str] = []
        candidates = by_profile[profile_id]
        profile = profiles.get(profile_id)
        process: ProductionProcessResponse | None = candidates[0]
        if len(candidates) > 1:
            product_blocking.append(CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT)
            process = None
        if profile is None or not _profile_linkable(profile):
            product_blocking.append(CODE_PRODUCT_PROFILE_NOT_LINKABLE)

        denominator: Decimal | None = None
        records_tonnes: Decimal | None = None
        record_ids: list[uuid.UUID] = []
        record_quantities: list[tuple[uuid.UUID, Decimal, str]] = []
        records = production_by_profile.get(profile_id, [])
        if records:
            records_tonnes = ZERO
            for record in records:
                record_ids.append(record.id)
                try:
                    records_tonnes += to_tonnes(record.quantity, record.unit)
                except Exception:
                    records_tonnes = None
                    break
                record_quantities.append((record.id, record.quantity, record.unit))

        if process is not None:
            if process.calculation_method != METHOD_CONVENTIONAL:
                product_blocking.append(CODE_PROCESS_METHOD_UNSUPPORTED)
            if process.readiness.status != PROCESS_READINESS_READY:
                product_blocking.append(CODE_PROCESS_NOT_READY)
            denominator = process.distribution.produced_tonnes
            if denominator is None:
                product_blocking.append(CODE_PRODUCT_DENOMINATOR_MISSING)
            elif denominator <= 0:
                product_blocking.append(CODE_PRODUCT_DENOMINATOR_ZERO)
            elif records and (records_tonnes is None or records_tonnes != denominator):
                product_blocking.append(CODE_PRODUCT_DENOMINATOR_MISMATCH)
            if methodology_code == METHODOLOGY_CODE:
                exported = process.exported_electricity.exported_electricity_mwh
                if exported is not None and exported > 0:
                    product_informational.append(EXPORTED_ELECTRICITY_NOTE_CODE)

        dea_row = dea_rows.get(profile_id)
        iea_row = iea_rows.get(profile_id)
        if dea_result_id is not None and not dea_stale and dea_row is None:
            product_blocking.append(CODE_DEA_PRODUCT_ROW_MISSING)
        if iea_result_id is not None and not iea_stale and iea_row is None:
            product_blocking.append(CODE_IEA_PRODUCT_ROW_MISSING)

        contributions: list[_ContributionCandidate] = []
        for precursor, use in sorted(
            uses_by_profile.get(profile_id, []), key=lambda pair: str(pair[1].id)
        ):
            if precursor.readiness.status != PRECURSOR_READINESS_READY:
                product_blocking.append(CODE_PRECURSOR_NOT_READY)
                continue
            specific_direct = precursor.calculation.specific_direct_embedded_emissions
            specific_indirect = precursor.calculation.specific_indirect_embedded_emissions
            value_source = precursor.calculation.value_source
            if specific_direct is None or specific_indirect is None or value_source is None:
                product_blocking.append(CODE_PRECURSOR_SPECIFIC_VALUES_MISSING)
                continue
            if use.quantity_tonnes is None:
                product_blocking.append(CODE_PRECURSOR_USE_UNIT_INVALID)
                continue
            contributions.append(
                _ContributionCandidate(
                    precursor=precursor,
                    use=use,
                    quantity_tonnes=use.quantity_tonnes,
                    specific_direct=specific_direct,
                    specific_indirect=specific_indirect,
                    value_source=value_source,
                )
            )

        product_blocking = _dedupe(product_blocking)
        process_exported = process.process_exported_electricity if process is not None else None
        live_by_profile[profile_id] = _LiveProductState(
            process_id=process.id if process is not None else None,
            produced_quantity=(
                process.distribution.produced_quantity if process is not None else None
            ),
            produced_quantity_unit=(
                process.distribution.produced_quantity_unit if process is not None else None
            ),
            denominator_tonnes=denominator,
            has_measurable_heat=(
                process.measurable_heat.has_measurable_heat if process is not None else None
            ),
            has_waste_gas=process.waste_gas.has_waste_gas if process is not None else None,
            heat_attributed=(
                (process.measurable_heat.attributed_tco2 or ZERO) if process is not None else ZERO
            ),
            waste_gas_attributed=(
                (process.waste_gas.attributed_tco2 or ZERO) if process is not None else ZERO
            ),
            dea_direct=(
                dea_row.final_allocated_fossil_co2_tonnes if dea_row is not None else None
            ),
            iea_indirect=(
                iea_row.final_allocated_indirect_emissions_tco2e if iea_row is not None else None
            ),
            production_record_ids=sorted(record_ids, key=str),
            production_records_tonnes=records_tonnes,
            contributions=contributions,
            has_exported_electricity=(
                process_exported.has_exported_electricity if process_exported is not None else None
            ),
            exported_electricity_mwh=(
                process_exported.quantity_mwh if process_exported is not None else None
            ),
            exported_electricity_emission_factor=(
                process_exported.emission_factor if process_exported is not None else None
            ),
            exported_electricity_direct_tco2e=(
                _t72_attributed(process) if process is not None else ZERO
            ),
            exported_electricity_reconciliation_status=(
                process_exported.reconciliation_status if process_exported is not None else None
            ),
        )
        readiness_rows.append(
            ProductEmbeddedEmissionsProductReadiness(
                product_profile_version_id=profile_id,
                product_id=profile.product_id if profile is not None else None,
                cn_normalized_code=profile.cn_normalized_code if profile is not None else None,
                process_id=process.id if process is not None else None,
                status='READY' if not product_blocking else 'NOT_READY',
                blocking_issue_codes=product_blocking,
                informational_codes=_dedupe(product_informational),
                denominator_tonnes=denominator,
                production_records_tonnes=records_tonnes,
                precursor_use_count=len(contributions),
            )
        )
        blocking.extend(product_blocking)
        informational.extend(product_informational)

        if product_blocking or process is None or profile is None:
            continue
        assert denominator is not None
        assert dea_row is not None and iea_row is not None
        produced_quantity = process.distribution.produced_quantity
        produced_unit = process.distribution.produced_quantity_unit
        assert produced_quantity is not None and produced_unit is not None
        eligible.append(
            _ProductCandidate(
                profile=profile,
                process=process,
                denominator_tonnes=denominator,
                produced_quantity=produced_quantity,
                produced_quantity_unit=produced_unit,
                production_record_ids=sorted(record_ids, key=str),
                production_records_tonnes=records_tonnes,
                production_record_quantities=record_quantities,
                dea_row=dea_row,
                iea_row=iea_row,
                heat_attributed=process.measurable_heat.attributed_tco2 or ZERO,
                waste_gas_attributed=process.waste_gas.attributed_tco2 or ZERO,
                contributions=contributions,
                informational=_dedupe(product_informational),
            )
        )

    # Precursor uses that target a product without any Conventional process.
    for profile_id in sorted(set(uses_by_profile) - set(by_profile), key=str):
        blocking.append(CODE_PROCESS_MISSING_FOR_PRODUCT)
        readiness_rows.append(
            ProductEmbeddedEmissionsProductReadiness(
                product_profile_version_id=profile_id,
                product_id=profiles[profile_id].product_id if profile_id in profiles else None,
                cn_normalized_code=(
                    profiles[profile_id].cn_normalized_code if profile_id in profiles else None
                ),
                process_id=None,
                status='NOT_READY',
                blocking_issue_codes=[CODE_PROCESS_MISSING_FOR_PRODUCT],
                informational_codes=[],
                denominator_tonnes=None,
                production_records_tonnes=None,
                precursor_use_count=len(uses_by_profile[profile_id]),
            )
        )

    if not eligible:
        blocking.append(CODE_NO_ELIGIBLE_PRODUCTS)

    try:
        internal_flows = _gather_internal_flows(eligible)
    except BusinessRuleError as exc:
        for detail in exc.details or []:
            if isinstance(detail, dict) and detail.get('code'):
                blocking.append(str(detail['code']))
        if CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE not in blocking:
            blocking.append(CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE)
        internal_flows = []

    flows_by_consumer: dict[uuid.UUID, list[_InternalFlowCandidate]] = {}
    for flow in internal_flows:
        flows_by_consumer.setdefault(flow.consumer_product_profile_version_id, []).append(flow)
    for profile_id, live in live_by_profile.items():
        live.internal_flows = list(flows_by_consumer.get(profile_id, []))

    return _RollupContext(
        blocking=_dedupe(blocking),
        informational=_dedupe(informational),
        dea_result_id=dea_result_id,
        dea_stale=dea_stale,
        iea_result_id=iea_result_id,
        iea_stale=iea_stale,
        eligible=eligible,
        live_by_profile=live_by_profile,
        product_readiness=readiness_rows,
    )


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _ComputedProduct:
    candidate: _ProductCandidate
    contributions: list[PrecursorContribution]
    totals: ProductTotals
    specifics: ProductSpecifics
    dea_direct: Decimal
    iea_indirect: Decimal
    exported_electricity_direct_tco2e: Decimal = ZERO
    internal_direct_tco2e: Decimal = ZERO
    internal_indirect_tco2e: Decimal = ZERO
    internal_contributions: tuple[InternalContribution, ...] = ()
    has_exported_electricity: bool | None = None
    exported_electricity_mwh: Decimal | None = None
    exported_electricity_emission_factor: Decimal | None = None


def _compute_products_v1(context: _RollupContext) -> list[_ComputedProduct]:
    computed: list[_ComputedProduct] = []
    for candidate in context.eligible:
        dea_direct = candidate.dea_row.final_allocated_fossil_co2_tonnes
        iea_indirect = candidate.iea_row.final_allocated_indirect_emissions_tco2e
        own = compute_own_process_emissions(
            dea_direct_tco2=dea_direct,
            heat_attributed_tco2e=candidate.heat_attributed,
            waste_gas_attributed_tco2e=candidate.waste_gas_attributed,
            iea_indirect_tco2e=iea_indirect,
            exported_electricity_direct_tco2e=ZERO,
        )
        contributions = [
            compute_precursor_contribution(
                precursor_id=item.precursor.id,
                product_use_id=item.use.id,
                quantity_tonnes=item.quantity_tonnes,
                specific_direct=item.specific_direct,
                specific_indirect=item.specific_indirect,
            )
            for item in candidate.contributions
        ]
        totals = compute_product_totals(own=own, contributions=contributions)
        specifics = compute_product_specifics(
            totals=totals, denominator_tonnes=candidate.denominator_tonnes
        )
        assert_product_identities(totals=totals, specifics=specifics)
        computed.append(
            _ComputedProduct(
                candidate=candidate,
                contributions=contributions,
                totals=totals,
                specifics=specifics,
                dea_direct=dea_direct,
                iea_indirect=iea_indirect,
                exported_electricity_direct_tco2e=ZERO,
            )
        )
    return computed


def _compute_products_v2(context: _RollupContext) -> list[_ComputedProduct]:
    flows = _gather_internal_flows(context.eligible)
    own_by_profile: dict[uuid.UUID, tuple[_ProductCandidate, Decimal, Decimal, list[PrecursorContribution]]] = {}
    v2_inputs: list[ProductV2Input] = []

    for candidate in context.eligible:
        dea_direct = candidate.dea_row.final_allocated_fossil_co2_tonnes
        iea_indirect = candidate.iea_row.final_allocated_indirect_emissions_tco2e
        t72 = _t72_attributed(candidate.process)
        own = compute_own_process_emissions(
            dea_direct_tco2=dea_direct,
            heat_attributed_tco2e=candidate.heat_attributed,
            waste_gas_attributed_tco2e=candidate.waste_gas_attributed,
            iea_indirect_tco2e=iea_indirect,
            exported_electricity_direct_tco2e=t72,
        )
        contributions = [
            compute_precursor_contribution(
                precursor_id=item.precursor.id,
                product_use_id=item.use.id,
                quantity_tonnes=item.quantity_tonnes,
                specific_direct=item.specific_direct,
                specific_indirect=item.specific_indirect,
            )
            for item in candidate.contributions
        ]
        purchased_direct = sum((c.contribution_direct_tco2e for c in contributions), ZERO)
        purchased_indirect = sum((c.contribution_indirect_tco2e for c in contributions), ZERO)
        own_by_profile[candidate.profile.id] = (candidate, t72, dea_direct, contributions)
        # Store iea for later via candidate
        v2_inputs.append(
            ProductV2Input(
                product_profile_version_id=candidate.profile.id,
                denominator_tonnes=candidate.denominator_tonnes,
                own_direct_tco2e=own.own_direct_tco2e,
                own_indirect_tco2e=own.own_indirect_tco2e,
                purchased_direct_tco2e=purchased_direct,
                purchased_indirect_tco2e=purchased_indirect,
            )
        )

    try:
        rollup = compute_v2_rollup(
            products=v2_inputs,
            flows=[
                InternalFlowInput(
                    product_use_id=flow.product_use_id,
                    consumer_product_profile_version_id=flow.consumer_product_profile_version_id,
                    supplier_product_profile_version_id=flow.supplier_product_profile_version_id,
                    quantity_tonnes=flow.quantity_tonnes,
                )
                for flow in flows
            ],
        )
    except LeontiefError as exc:
        raise BusinessRuleError(
            'Internal product-flow Leontief system cannot be solved.',
            details=[{'code': exc.code}],
        ) from exc

    computed: list[_ComputedProduct] = []
    for candidate in context.eligible:
        result = rollup.results[candidate.profile.id]
        _, t72, dea_direct, contributions = own_by_profile[candidate.profile.id]
        iea_indirect = candidate.iea_row.final_allocated_indirect_emissions_tco2e
        totals = ProductTotals(
            own_direct_tco2e=result.totals.own_direct_tco2e,
            own_indirect_tco2e=result.totals.own_indirect_tco2e,
            precursor_direct_tco2e=result.totals.precursor_direct_tco2e,
            precursor_indirect_tco2e=result.totals.precursor_indirect_tco2e,
            total_direct_tco2e=result.totals.total_direct_tco2e,
            total_indirect_tco2e=result.totals.total_indirect_tco2e,
            total_embedded_tco2e=result.totals.total_embedded_tco2e,
        )
        specifics = ProductSpecifics(
            denominator_tonnes=result.specifics.denominator_tonnes,
            specific_direct=result.specifics.specific_direct,
            specific_indirect=result.specifics.specific_indirect,
            specific_total=result.specifics.specific_total,
        )
        process_exported = candidate.process.process_exported_electricity
        computed.append(
            _ComputedProduct(
                candidate=candidate,
                contributions=contributions,
                totals=totals,
                specifics=specifics,
                dea_direct=dea_direct,
                iea_indirect=iea_indirect,
                exported_electricity_direct_tco2e=t72,
                internal_direct_tco2e=result.totals.internal_direct_tco2e,
                internal_indirect_tco2e=result.totals.internal_indirect_tco2e,
                internal_contributions=result.internal_contributions,
                has_exported_electricity=process_exported.has_exported_electricity,
                exported_electricity_mwh=process_exported.quantity_mwh,
                exported_electricity_emission_factor=process_exported.emission_factor,
            )
        )
    return computed


def _compute_products(
    context: _RollupContext, *, methodology_code: str
) -> list[_ComputedProduct]:
    if methodology_code == METHODOLOGY_CODE_V2:
        return _compute_products_v2(context)
    return _compute_products_v1(context)


def _exported_electricity_fingerprint(
    process: ProductionProcessResponse,
) -> ExportedElectricityFingerprint:
    exported = process.process_exported_electricity
    return ExportedElectricityFingerprint(
        has_exported_electricity=exported.has_exported_electricity,
        quantity_mwh=exported.quantity_mwh,
        emission_factor=exported.emission_factor,
        provenance=exported.provenance,
        installation_facility_exported_mwh=exported.installation_facility_exported_electricity_mwh,
        installation_process_exported_mwh=exported.installation_process_exported_electricity_mwh,
        reconciliation_status=exported.reconciliation_status,
    )


def _build_fingerprint(
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    context: _RollupContext,
    methodology_code: str,
) -> str:
    is_v2 = methodology_code == METHODOLOGY_CODE_V2
    flows_by_consumer: dict[uuid.UUID, list[_InternalFlowCandidate]] = {}
    if is_v2:
        for flow in _gather_internal_flows(context.eligible):
            flows_by_consumer.setdefault(flow.consumer_product_profile_version_id, []).append(
                flow
            )

    products: list[ProductFingerprint] = []
    for candidate in context.eligible:
        contributions = tuple(
            PrecursorContributionFingerprint(
                precursor_id=item.precursor.id,
                precursor_row_version=item.precursor.row_version,
                data_source_mode=item.precursor.data_source_mode,
                specific_direct=item.specific_direct,
                specific_indirect=item.specific_indirect,
                value_source=item.value_source,
                default_dataset_id=item.precursor.default_source.dataset_id,
                default_value_id=item.precursor.default_source.default_value_id,
                product_use_id=item.use.id,
                product_use_row_version=item.use.row_version,
                product_use_quantity=item.use.quantity,
                product_use_unit=item.use.unit,
                target_product_profile_version_id=item.use.target_product_profile_version_id,
            )
            for item in candidate.contributions
        )
        t72 = _t72_attributed(candidate.process) if is_v2 else ZERO
        consumer_flows = flows_by_consumer.get(candidate.profile.id, [])
        products.append(
            ProductFingerprint(
                product_profile_version_id=candidate.profile.id,
                profile_version=candidate.profile.version,
                process_id=candidate.process.id,
                process_row_version=candidate.process.row_version,
                produced_quantity=candidate.produced_quantity,
                produced_quantity_unit=candidate.produced_quantity_unit,
                denominator_tonnes=candidate.denominator_tonnes,
                has_measurable_heat=candidate.process.measurable_heat.has_measurable_heat,
                heat_attributed_tco2e=candidate.heat_attributed,
                has_waste_gas=candidate.process.waste_gas.has_waste_gas,
                waste_gas_attributed_tco2e=candidate.waste_gas_attributed,
                exported_electricity_direct_tco2e=t72,
                dea_result_id=candidate.dea_row.result_id,
                dea_product_value=candidate.dea_row.final_allocated_fossil_co2_tonnes,
                iea_result_id=candidate.iea_row.result_id,
                iea_product_value=candidate.iea_row.final_allocated_indirect_emissions_tco2e,
                production_records=tuple(candidate.production_record_quantities),
                contributions=contributions,
                exported_electricity=(
                    _exported_electricity_fingerprint(candidate.process) if is_v2 else None
                ),
                internal_flows=tuple(
                    InternalFlowFingerprint(
                        product_use_id=flow.product_use_id,
                        product_use_row_version=flow.product_use_row_version,
                        supplier_process_id=flow.supplier_process_id,
                        supplier_process_row_version=flow.supplier_process_row_version,
                        supplier_product_profile_version_id=(
                            flow.supplier_product_profile_version_id
                        ),
                        consumer_product_profile_version_id=(
                            flow.consumer_product_profile_version_id
                        ),
                        product_use_quantity=flow.product_use_quantity,
                        product_use_unit=flow.product_use_unit,
                        quantity_tonnes=flow.quantity_tonnes,
                        consumer_denominator_tonnes=flow.consumer_denominator_tonnes,
                    )
                    for flow in consumer_flows
                ),
            )
        )
    return build_product_embedded_emissions_fingerprint(
        organization_id=organization_id,
        binding_id=binding_id,
        dea_result_id=context.dea_result_id,
        iea_result_id=context.iea_result_id,
        products=products,
        methodology_code=methodology_code,
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    methodology_code: str,
) -> CbamProductEmbeddedEmissionsCurrent | None:
    return db.execute(
        select(CbamProductEmbeddedEmissionsCurrent).where(
            CbamProductEmbeddedEmissionsCurrent.organization_id == organization_id,
            CbamProductEmbeddedEmissionsCurrent.reporting_period_binding_id == binding_id,
            CbamProductEmbeddedEmissionsCurrent.methodology_code == methodology_code,
        )
    ).scalar_one_or_none()


def _preferred_current_pointer(
    db: Session, *, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> CbamProductEmbeddedEmissionsCurrent | None:
    """Prefer the V2 current pointer when present; otherwise fall back to V1."""
    v2 = _current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE_V2,
    )
    if v2 is not None:
        return v2
    return _current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
    )


def _set_current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
    methodology_code: str,
) -> None:
    now = datetime.now(UTC)
    stmt = (
        pg_insert(CbamProductEmbeddedEmissionsCurrent)
        .values(
            id=uuid.uuid4(),
            organization_id=organization_id,
            reporting_period_binding_id=binding_id,
            methodology_code=methodology_code,
            current_result_id=result_id,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint='uq_cbam_pee_current_org_binding_method',
            set_={'current_result_id': result_id, 'updated_at': now},
        )
    )
    db.execute(stmt)


def _find_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamProductEmbeddedEmissionsResult | None:
    return db.execute(
        select(CbamProductEmbeddedEmissionsResult).where(
            CbamProductEmbeddedEmissionsResult.organization_id == organization_id,
            CbamProductEmbeddedEmissionsResult.reporting_period_binding_id == binding_id,
            CbamProductEmbeddedEmissionsResult.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def _product_rows(
    db: Session, result_id: uuid.UUID
) -> list[CbamProductEmbeddedEmissionsProduct]:
    return list(
        db.execute(
            select(CbamProductEmbeddedEmissionsProduct)
            .where(CbamProductEmbeddedEmissionsProduct.result_id == result_id)
            .order_by(CbamProductEmbeddedEmissionsProduct.product_profile_version_id.asc())
        )
        .scalars()
        .all()
    )


def _contribution_rows(
    db: Session, result_id: uuid.UUID
) -> list[CbamProductEmbeddedEmissionsPrecursorContribution]:
    return list(
        db.execute(
            select(CbamProductEmbeddedEmissionsPrecursorContribution)
            .where(CbamProductEmbeddedEmissionsPrecursorContribution.result_id == result_id)
            .order_by(
                CbamProductEmbeddedEmissionsPrecursorContribution.product_profile_version_id.asc(),
                CbamProductEmbeddedEmissionsPrecursorContribution.product_use_id.asc(),
            )
        )
        .scalars()
        .all()
    )


def _internal_contribution_rows(
    db: Session, result_id: uuid.UUID
) -> list[CbamProductEmbeddedEmissionsInternalContribution]:
    return list(
        db.execute(
            select(CbamProductEmbeddedEmissionsInternalContribution)
            .where(CbamProductEmbeddedEmissionsInternalContribution.result_id == result_id)
            .order_by(
                CbamProductEmbeddedEmissionsInternalContribution.consumer_product_profile_version_id.asc(),
                CbamProductEmbeddedEmissionsInternalContribution.product_use_id.asc(),
            )
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# Stale evaluation
# ---------------------------------------------------------------------------
def compute_product_embedded_emissions_stale_reasons(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result: CbamProductEmbeddedEmissionsResult,
    *,
    context: _RollupContext | None = None,
) -> list[str]:
    """Compare immutable snapshots to live material identity (never recomputes upstream)."""
    reasons: list[str] = []
    expected_version = _methodology_version(result.methodology_code)
    if (
        result.methodology_code not in SUPPORTED_METHODOLOGY_CODES
        or result.methodology_version != expected_version
        or result.workbook_sha256 != WORKBOOK_SHA256
    ):
        reasons.append(STALE_METHODOLOGY_OR_WORKBOOK_CHANGED)

    ctx = context or _resolve_context(
        db,
        user,
        organization_id,
        binding_id,
        methodology_code=result.methodology_code,
    )
    if ctx.dea_result_id != result.dea_result_id:
        reasons.append(STALE_DEA_CURRENT_RESULT_CHANGED)
    if ctx.dea_stale:
        reasons.append(STALE_DEA_STALE)
    if ctx.iea_result_id != result.iea_result_id:
        reasons.append(STALE_IEA_CURRENT_RESULT_CHANGED)
    if ctx.iea_stale:
        reasons.append(STALE_IEA_STALE)

    snapshots = _product_rows(db, result.id)
    snapshot_ids = {row.product_profile_version_id for row in snapshots}
    if snapshot_ids != {c.profile.id for c in ctx.eligible}:
        reasons.append(STALE_PRODUCT_SET_CHANGED)

    contributions = _contribution_rows(db, result.id)
    contributions_by_profile: dict[
        uuid.UUID, list[CbamProductEmbeddedEmissionsPrecursorContribution]
    ] = {}
    for row in contributions:
        contributions_by_profile.setdefault(row.product_profile_version_id, []).append(row)

    is_v2 = result.methodology_code == METHODOLOGY_CODE_V2
    internal_rows: list[CbamProductEmbeddedEmissionsInternalContribution] = (
        _internal_contribution_rows(db, result.id) if is_v2 else []
    )
    internal_by_consumer: dict[
        uuid.UUID, list[CbamProductEmbeddedEmissionsInternalContribution]
    ] = {}
    for internal_row in internal_rows:
        internal_by_consumer.setdefault(
            internal_row.consumer_product_profile_version_id, []
        ).append(internal_row)

    for snapshot in snapshots:
        live = ctx.live_by_profile.get(snapshot.product_profile_version_id)
        if live is None:
            continue
        # Row versions are part of the idempotency fingerprint but deliberately not of
        # the stale evaluation: renaming a process must not invalidate a result.
        if live.process_id is not None and live.process_id != snapshot.process_id:
            reasons.append(STALE_PROCESS_CHANGED)
        if not _same_decimal(live.produced_quantity, snapshot.process_produced_quantity) or (
            live.produced_quantity_unit != snapshot.process_produced_quantity_unit
        ):
            reasons.append(STALE_PROCESS_PRODUCED_QUANTITY_CHANGED)
        if not _same_decimal(live.denominator_tonnes, snapshot.denominator_tonnes):
            reasons.append(STALE_PRODUCT_DENOMINATOR_CHANGED)
        if (
            live.has_measurable_heat != snapshot.has_measurable_heat
            or live.has_waste_gas != snapshot.has_waste_gas
            or not _same_decimal(live.heat_attributed, snapshot.heat_attributed_tco2e)
            or not _same_decimal(live.waste_gas_attributed, snapshot.waste_gas_attributed_tco2e)
        ):
            reasons.append(STALE_PROCESS_HEAT_OR_WASTE_GAS_CHANGED)
        if live.dea_direct is not None and not _same_decimal(
            live.dea_direct, snapshot.dea_direct_tco2
        ):
            reasons.append(STALE_DEA_PRODUCT_VALUE_CHANGED)
        if live.iea_indirect is not None and not _same_decimal(
            live.iea_indirect, snapshot.iea_indirect_tco2e
        ):
            reasons.append(STALE_IEA_PRODUCT_VALUE_CHANGED)
        snapshot_records = {str(x) for x in (snapshot.production_record_ids or [])}
        if snapshot_records != {str(x) for x in live.production_record_ids} or not _same_decimal(
            live.production_records_tonnes, snapshot.production_records_tonnes
        ):
            reasons.append(STALE_PRODUCTION_RECORDS_CHANGED)

        live_contributions = {item.use.id: item for item in live.contributions}
        snapshot_contributions = {
            row.product_use_id: row
            for row in contributions_by_profile.get(snapshot.product_profile_version_id, [])
        }
        if set(live_contributions) != set(snapshot_contributions):
            reasons.append(STALE_PRECURSOR_SET_CHANGED)
        for use_id, snapshot_row in snapshot_contributions.items():
            live_item = live_contributions.get(use_id)
            if live_item is None:
                continue
            if (
                live_item.precursor.data_source_mode != snapshot_row.data_source_mode
                or live_item.value_source != snapshot_row.value_source
            ):
                reasons.append(STALE_PRECURSOR_CHANGED)
            if (
                not _same_decimal(live_item.use.quantity, snapshot_row.product_use_quantity)
                or live_item.use.unit != snapshot_row.product_use_unit
                or not _same_decimal(live_item.quantity_tonnes, snapshot_row.quantity_tonnes)
            ):
                reasons.append(STALE_PRECURSOR_PRODUCT_USE_CHANGED)
            if not _same_decimal(
                live_item.specific_direct, snapshot_row.specific_direct
            ) or not _same_decimal(live_item.specific_indirect, snapshot_row.specific_indirect):
                reasons.append(STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED)
            if (
                live_item.precursor.default_source.dataset_id != snapshot_row.default_dataset_id
                or live_item.precursor.default_source.default_value_id
                != snapshot_row.default_value_id
            ):
                reasons.append(STALE_PRECURSOR_DEFAULT_SNAPSHOT_CHANGED)

        if is_v2:
            if (
                live.has_exported_electricity != snapshot.has_exported_electricity
                or not _same_decimal(live.exported_electricity_mwh, snapshot.exported_electricity_mwh)
                or not _same_decimal(
                    live.exported_electricity_emission_factor,
                    snapshot.exported_electricity_emission_factor,
                )
                or not _same_decimal(
                    live.exported_electricity_direct_tco2e,
                    snapshot.exported_electricity_direct_tco2e,
                )
            ):
                reasons.append(STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED)

            live_flows = {flow.product_use_id: flow for flow in live.internal_flows}
            snapshot_flows = {
                row.product_use_id: row
                for row in internal_by_consumer.get(snapshot.product_profile_version_id, [])
            }
            if set(live_flows) != set(snapshot_flows):
                reasons.append(STALE_INTERNAL_PRODUCT_FLOW_SET_CHANGED)
            for use_id, snapshot_flow in snapshot_flows.items():
                live_flow = live_flows.get(use_id)
                if live_flow is None:
                    continue
                if (
                    live_flow.supplier_product_profile_version_id
                    != snapshot_flow.supplier_product_profile_version_id
                    or live_flow.consumer_product_profile_version_id
                    != snapshot_flow.consumer_product_profile_version_id
                    or not _same_decimal(
                        live_flow.product_use_quantity, snapshot_flow.product_use_quantity
                    )
                    or live_flow.product_use_unit != snapshot_flow.product_use_unit
                    or not _same_decimal(live_flow.quantity_tonnes, snapshot_flow.quantity_tonnes)
                ):
                    reasons.append(STALE_INTERNAL_PRODUCT_FLOW_CHANGED)

    if ctx.blocking:
        reasons.append(STALE_NOT_READY)
    return _dedupe(reasons)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_product_embedded_emissions_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    methodology_code: str = DEFAULT_METHODOLOGY_CODE,
) -> ProductEmbeddedEmissionsReadiness:
    require_cbam_view(db, user, organization_id)
    methodology_code = _validate_methodology_code(methodology_code)
    ctx = _resolve_context(
        db, user, organization_id, binding_id, methodology_code=methodology_code
    )
    pointer = _current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        methodology_code=methodology_code,
    )
    stale_codes: list[str] = []
    current_id = pointer.current_result_id if pointer is not None else None
    if pointer is not None:
        result = db.get(CbamProductEmbeddedEmissionsResult, pointer.current_result_id)
        if result is not None:
            stale_codes = compute_product_embedded_emissions_stale_reasons(
                db, user, organization_id, binding_id, result, context=ctx
            )
    ready = not ctx.blocking
    export_code, export_note = exported_electricity_note_for(methodology_code)
    internal_code, internal_note = internal_precursor_note_for(methodology_code)
    return ProductEmbeddedEmissionsReadiness(
        reporting_period_binding_id=binding_id,
        methodology_code=methodology_code,
        status='READY' if ready else 'NOT_READY',
        rollup_ready=ready,
        blocking_issue_codes=ctx.blocking,
        informational_codes=ctx.informational,
        direct_emissions_allocation_result_id=ctx.dea_result_id,
        direct_emissions_allocation_stale=ctx.dea_stale,
        indirect_emissions_allocation_result_id=ctx.iea_result_id,
        indirect_emissions_allocation_stale=ctx.iea_stale,
        eligible_product_count=len(ctx.eligible),
        blocked_product_count=sum(
            1 for row in ctx.product_readiness if row.status == 'NOT_READY'
        ),
        precursor_contribution_count=sum(len(c.contributions) for c in ctx.eligible),
        products=ctx.product_readiness,
        current_result_id=current_id,
        current_is_stale=bool(stale_codes),
        stale_reason_codes=stale_codes,
        exported_electricity_note_code=export_code,
        exported_electricity_note=export_note,
        internal_precursor_note_code=internal_code,
        internal_precursor_note=internal_note,
    )


def _execution_response(
    result: CbamProductEmbeddedEmissionsResult, *, idempotent_replay: bool
) -> ProductEmbeddedEmissionsExecutionResponse:
    return ProductEmbeddedEmissionsExecutionResponse(
        result_id=result.id,
        run_id=result.id,
        status=result.status,
        methodology_code=result.methodology_code,
        methodology_version=result.methodology_version,
        product_count=result.product_count,
        precursor_contribution_count=result.precursor_contribution_count,
        internal_contribution_count=result.internal_contribution_count,
        total_direct_tco2e=result.total_direct_tco2e,
        total_indirect_tco2e=result.total_indirect_tco2e,
        total_embedded_tco2e=result.total_embedded_tco2e,
        result_unit=result.result_unit,
        specific_unit=result.specific_unit,
        client_request_id=result.client_request_id,
        idempotent_replay=idempotent_replay,
        created_at=result.created_at,
    )


def execute_product_embedded_emissions(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: ProductEmbeddedEmissionsExecuteRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductEmbeddedEmissionsExecutionResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)

    methodology_code = _validate_methodology_code(payload.methodology_code)
    methodology_version = _methodology_version(methodology_code)
    is_v2 = methodology_code == METHODOLOGY_CODE_V2
    export_code, export_note = exported_electricity_note_for(methodology_code)
    internal_code, internal_note = internal_precursor_note_for(methodology_code)

    ctx = _resolve_context(
        db, user, organization_id, binding_id, methodology_code=methodology_code
    )
    if ctx.blocking:
        raise BusinessRuleError(
            'Product embedded-emissions roll-up is not ready.',
            details=[{'code': code} for code in ctx.blocking],
        )

    fingerprint = _build_fingerprint(
        organization_id=organization_id,
        binding_id=binding_id,
        context=ctx,
        methodology_code=methodology_code,
    )
    existing = _find_by_client_request(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        client_request_id=payload.client_request_id,
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise ConflictError(
                'This client request id was already used with different inputs.',
                details=[{'code': 'IDEMPOTENCY_KEY_REUSED'}],
            )
        return _execution_response(existing, idempotent_replay=True)

    computed = _compute_products(ctx, methodology_code=methodology_code)
    total_direct_raw = sum((c.totals.total_direct_tco2e for c in computed), ZERO)
    total_indirect_raw = sum((c.totals.total_indirect_tco2e for c in computed), ZERO)
    total_embedded_raw = total_direct_raw + total_indirect_raw
    contribution_count = sum(len(c.contributions) for c in computed)
    internal_count = sum(len(c.internal_contributions) for c in computed)

    # Supplier process lookup for internal contribution persistence.
    supplier_by_profile = {
        candidate.profile.id: candidate.process for candidate in ctx.eligible
    }

    result_id = uuid.uuid4()
    result = CbamProductEmbeddedEmissionsResult(
        id=result_id,
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        methodology_code=methodology_code,
        methodology_version=methodology_version,
        workbook_filename=WORKBOOK_FILENAME,
        workbook_sha256=WORKBOOK_SHA256,
        workbook_formula_refs=workbook_formula_refs_for(methodology_code),
        client_request_id=payload.client_request_id,
        request_fingerprint=fingerprint,
        status=EXECUTION_STATUS_COMPLETED,
        product_count=len(computed),
        precursor_contribution_count=contribution_count,
        internal_contribution_count=internal_count,
        total_direct_tco2e_raw=total_direct_raw,
        total_indirect_tco2e_raw=total_indirect_raw,
        total_embedded_tco2e_raw=total_embedded_raw,
        total_direct_tco2e=quantize_result(total_direct_raw),
        total_indirect_tco2e=quantize_result(total_indirect_raw),
        total_embedded_tco2e=quantize_result(total_embedded_raw),
        result_unit=RESULT_UNIT_TCO2E,
        specific_unit=SPECIFIC_UNIT_TCO2E_PER_T,
        dea_source_unit=DEA_SOURCE_UNIT_TCO2,
        workbook_gas=WORKBOOK_GAS,
        workbook_gwp=WORKBOOK_GWP,
        workbook_gwp_factor=WORKBOOK_GWP_FACTOR,
        dea_result_id=ctx.dea_result_id,
        iea_result_id=ctx.iea_result_id,
        informational_codes_json=list(ctx.informational),
        notes_json={
            'gwpEquivalence': GWP_EQUIVALENCE_NOTE,
            'denominator': DENOMINATOR_NOTE,
            'exportedElectricity': export_note,
            'exportedElectricityCode': export_code,
            'internalPrecursors': internal_note,
            'internalPrecursorsCode': internal_code,
        },
        created_by_user_id=user.id,
    )

    try:
        db.add(result)
        db.flush()
        for item in computed:
            candidate = item.candidate
            product_row_id = uuid.uuid4()
            components: dict[str, Any] = {
                'ownDirect': {
                    'deaDirectTco2': str(item.dea_direct),
                    'heatAttributedTco2e': str(candidate.heat_attributed),
                    'wasteGasAttributedTco2e': str(candidate.waste_gas_attributed),
                    'exportedElectricityDirectTco2e': str(item.exported_electricity_direct_tco2e),
                    'formula': 'T54 + T58 + T62 + T72',
                },
                'ownIndirect': {
                    'ieaIndirectTco2e': str(item.iea_indirect),
                    'formula': 'T66 via current IEA product row',
                },
                'precursors': {
                    'directTco2e': str(item.totals.precursor_direct_tco2e),
                    'indirectTco2e': str(item.totals.precursor_indirect_tco2e),
                    'formula': 'Σ productUseTonnes × precursorSpecific',
                },
                'denominator': {
                    'tonnes': str(candidate.denominator_tonnes),
                    'source': 'PROCESS_PRODUCED_QUANTITY',
                    'note': DENOMINATOR_NOTE,
                },
            }
            if is_v2:
                components['internal'] = {
                    'directTco2e': str(item.internal_direct_tco2e),
                    'indirectTco2e': str(item.internal_indirect_tco2e),
                    'formula': 'Σ qty × supplierSEE via (I-A)^-1',
                }
            db.add(
                CbamProductEmbeddedEmissionsProduct(
                    id=product_row_id,
                    result_id=result_id,
                    organization_id=organization_id,
                    reporting_period_binding_id=binding_id,
                    product_id=candidate.profile.product_id,
                    product_profile_version_id=candidate.profile.id,
                    profile_version=candidate.profile.version,
                    cn_normalized_code=candidate.profile.cn_normalized_code,
                    cn_display_code=candidate.profile.cn_display_code,
                    product_name=candidate.profile.product_name,
                    process_id=candidate.process.id,
                    process_row_version=candidate.process.row_version,
                    process_produced_quantity=candidate.produced_quantity,
                    process_produced_quantity_unit=candidate.produced_quantity_unit,
                    denominator_tonnes=candidate.denominator_tonnes,
                    production_record_count=len(candidate.production_record_ids),
                    production_records_tonnes=candidate.production_records_tonnes,
                    production_record_ids=[str(x) for x in candidate.production_record_ids],
                    dea_result_id=candidate.dea_row.result_id,
                    dea_product_allocation_id=candidate.dea_row.id,
                    dea_direct_tco2=item.dea_direct,
                    iea_result_id=candidate.iea_row.result_id,
                    iea_product_allocation_id=candidate.iea_row.id,
                    iea_indirect_tco2e=item.iea_indirect,
                    has_measurable_heat=candidate.process.measurable_heat.has_measurable_heat,
                    heat_attributed_tco2e=candidate.heat_attributed,
                    has_waste_gas=candidate.process.waste_gas.has_waste_gas,
                    waste_gas_attributed_tco2e=candidate.waste_gas_attributed,
                    exported_electricity_direct_tco2e=item.exported_electricity_direct_tco2e,
                    exported_electricity_note_code=export_code,
                    has_exported_electricity=item.has_exported_electricity,
                    exported_electricity_mwh=item.exported_electricity_mwh,
                    exported_electricity_emission_factor=item.exported_electricity_emission_factor,
                    own_direct_tco2e_raw=item.totals.own_direct_tco2e,
                    own_indirect_tco2e_raw=item.totals.own_indirect_tco2e,
                    precursor_direct_tco2e_raw=item.totals.precursor_direct_tco2e,
                    precursor_indirect_tco2e_raw=item.totals.precursor_indirect_tco2e,
                    internal_direct_tco2e_raw=item.internal_direct_tco2e,
                    internal_indirect_tco2e_raw=item.internal_indirect_tco2e,
                    total_direct_tco2e_raw=item.totals.total_direct_tco2e,
                    total_indirect_tco2e_raw=item.totals.total_indirect_tco2e,
                    total_embedded_tco2e_raw=item.totals.total_embedded_tco2e,
                    own_direct_tco2e=quantize_result(item.totals.own_direct_tco2e),
                    own_indirect_tco2e=quantize_result(item.totals.own_indirect_tco2e),
                    precursor_direct_tco2e=quantize_result(item.totals.precursor_direct_tco2e),
                    precursor_indirect_tco2e=quantize_result(
                        item.totals.precursor_indirect_tco2e
                    ),
                    internal_direct_tco2e=quantize_result(item.internal_direct_tco2e),
                    internal_indirect_tco2e=quantize_result(item.internal_indirect_tco2e),
                    total_direct_tco2e=quantize_result(item.totals.total_direct_tco2e),
                    total_indirect_tco2e=quantize_result(item.totals.total_indirect_tco2e),
                    total_embedded_tco2e=quantize_result(item.totals.total_embedded_tco2e),
                    specific_direct_raw=item.specifics.specific_direct,
                    specific_indirect_raw=item.specifics.specific_indirect,
                    specific_total_raw=item.specifics.specific_total,
                    specific_direct=quantize_result(item.specifics.specific_direct),
                    specific_indirect=quantize_result(item.specifics.specific_indirect),
                    specific_total=quantize_result(item.specifics.specific_total),
                    precursor_contribution_count=len(item.contributions),
                    internal_contribution_count=len(item.internal_contributions),
                    result_unit=RESULT_UNIT_TCO2E,
                    specific_unit=SPECIFIC_UNIT_TCO2E_PER_T,
                    dea_source_unit=DEA_SOURCE_UNIT_TCO2,
                    components_json=components,
                    provenance_json={
                        'processId': str(candidate.process.id),
                        'processRowVersion': candidate.process.row_version,
                        'deaResultId': str(candidate.dea_row.result_id),
                        'deaProductAllocationId': str(candidate.dea_row.id),
                        'ieaResultId': str(candidate.iea_row.result_id),
                        'ieaProductAllocationId': str(candidate.iea_row.id),
                        'productionRecordIds': [
                            str(x) for x in candidate.production_record_ids
                        ],
                        'informationalCodes': candidate.informational,
                        'methodologyCode': methodology_code,
                    },
                )
            )
            # The composite FK (product_row_id, result_id) is not backed by a
            # relationship, so the product row must reach the database first.
            db.flush()
            by_use = {c.product_use_id: c for c in item.contributions}
            for source in candidate.contributions:
                contribution = by_use[source.use.id]
                db.add(
                    CbamProductEmbeddedEmissionsPrecursorContribution(
                        id=uuid.uuid4(),
                        result_id=result_id,
                        product_row_id=product_row_id,
                        organization_id=organization_id,
                        reporting_period_binding_id=binding_id,
                        product_profile_version_id=candidate.profile.id,
                        precursor_id=source.precursor.id,
                        precursor_row_version=source.precursor.row_version,
                        precursor_name=source.precursor.name,
                        precursor_cn_normalized_code=source.precursor.cn_normalized_code,
                        precursor_cn_display_code=source.precursor.cn_display_code,
                        data_source_mode=source.precursor.data_source_mode,
                        value_source=source.value_source,
                        product_use_id=source.use.id,
                        product_use_row_version=source.use.row_version,
                        product_use_quantity=source.use.quantity,
                        product_use_unit=source.use.unit,
                        quantity_tonnes=contribution.quantity_tonnes,
                        specific_direct=contribution.specific_direct,
                        specific_indirect=contribution.specific_indirect,
                        contribution_direct_tco2e_raw=contribution.contribution_direct_tco2e,
                        contribution_indirect_tco2e_raw=contribution.contribution_indirect_tco2e,
                        contribution_direct_tco2e=quantize_result(
                            contribution.contribution_direct_tco2e
                        ),
                        contribution_indirect_tco2e=quantize_result(
                            contribution.contribution_indirect_tco2e
                        ),
                        default_dataset_id=source.precursor.default_source.dataset_id,
                        default_value_id=source.precursor.default_source.default_value_id,
                        default_snapshot_json=source.precursor.default_source.snapshot,
                        result_unit=RESULT_UNIT_TCO2E,
                        specific_unit=SPECIFIC_UNIT_TCO2E_PER_T,
                    )
                )
            for internal in item.internal_contributions:
                supplier_process = supplier_by_profile[internal.supplier_product_profile_version_id]
                # Recover product-use metadata from the supplier process distribution.
                use_meta = next(
                    (
                        use
                        for use in supplier_process.distribution.product_uses
                        if use.id == internal.product_use_id
                    ),
                    None,
                )
                if use_meta is None:
                    raise BusinessRuleError(
                        'Internal product-use metadata missing during persistence.',
                        details=[{'code': CODE_INTERNAL_PRODUCT_FLOW_INVALID}],
                    )
                db.add(
                    CbamProductEmbeddedEmissionsInternalContribution(
                        id=uuid.uuid4(),
                        result_id=result_id,
                        product_row_id=product_row_id,
                        organization_id=organization_id,
                        reporting_period_binding_id=binding_id,
                        consumer_product_profile_version_id=(
                            internal.consumer_product_profile_version_id
                        ),
                        supplier_product_profile_version_id=(
                            internal.supplier_product_profile_version_id
                        ),
                        consumer_process_id=candidate.process.id,
                        supplier_process_id=supplier_process.id,
                        supplier_process_row_version=supplier_process.row_version,
                        product_use_id=internal.product_use_id,
                        product_use_row_version=use_meta.row_version,
                        product_use_quantity=use_meta.quantity,
                        product_use_unit=use_meta.unit,
                        quantity_tonnes=internal.quantity_tonnes,
                        consumer_denominator_tonnes=internal.consumer_denominator_tonnes,
                        a_coefficient=internal.a_coefficient,
                        supplier_specific_direct=internal.supplier_specific_direct,
                        supplier_specific_indirect=internal.supplier_specific_indirect,
                        contribution_direct_tco2e_raw=internal.contribution_direct_tco2e,
                        contribution_indirect_tco2e_raw=internal.contribution_indirect_tco2e,
                        contribution_direct_tco2e=quantize_result(
                            internal.contribution_direct_tco2e
                        ),
                        contribution_indirect_tco2e=quantize_result(
                            internal.contribution_indirect_tco2e
                        ),
                        result_unit=RESULT_UNIT_TCO2E,
                        specific_unit=SPECIFIC_UNIT_TCO2E_PER_T,
                    )
                )

        _set_current_pointer(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            result_id=result_id,
            methodology_code=methodology_code,
        )
        write_audit_log(
            db,
            action='cbam.product_embedded_emissions.executed',
            actor_user_id=user.id,
            organization_id=organization_id,
            entity_type='cbam_product_embedded_emissions_results',
            entity_id=str(result_id),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                'clientRequestId': str(payload.client_request_id),
                'methodologyCode': methodology_code,
            },
        )
        db.commit()
        db.refresh(result)
        return _execution_response(result, idempotent_replay=False)
    except IntegrityError:
        db.rollback()
        winner = _find_by_client_request(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            client_request_id=payload.client_request_id,
        )
        if winner is None:
            raise ConflictError(
                'Product embedded-emissions persistence conflict.',
                details=[{'code': 'PRODUCT_EMBEDDED_EMISSIONS_RESULT_CONFLICT'}],
            ) from None
        if winner.request_fingerprint != fingerprint:
            raise ConflictError(
                'This client request id was already used with different inputs.',
                details=[{'code': 'IDEMPOTENCY_KEY_REUSED'}],
            ) from None
        return _execution_response(winner, idempotent_replay=True)



def list_product_embedded_emissions_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[ProductEmbeddedEmissionsResultSummary]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamProductEmbeddedEmissionsResult).where(
        CbamProductEmbeddedEmissionsResult.organization_id == organization_id,
        CbamProductEmbeddedEmissionsResult.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamProductEmbeddedEmissionsResult.created_at.desc(),
                CbamProductEmbeddedEmissionsResult.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    current_by_method: dict[str, uuid.UUID] = {}
    for code in SUPPORTED_METHODOLOGY_CODES:
        pointer = _current_pointer(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            methodology_code=code,
        )
        if pointer is not None:
            current_by_method[code] = pointer.current_result_id
    context_by_method: dict[str, _RollupContext] = {}
    items: list[ProductEmbeddedEmissionsResultSummary] = []
    for row in rows:
        current_id = current_by_method.get(row.methodology_code)
        is_current = row.id == current_id
        stale_codes: list[str] = []
        if is_current:
            if row.methodology_code not in context_by_method:
                context_by_method[row.methodology_code] = _resolve_context(
                    db,
                    user,
                    organization_id,
                    binding_id,
                    methodology_code=row.methodology_code,
                )
            stale_codes = compute_product_embedded_emissions_stale_reasons(
                db,
                user,
                organization_id,
                binding_id,
                row,
                context=context_by_method[row.methodology_code],
            )
        items.append(
            ProductEmbeddedEmissionsResultSummary(
                result_id=row.id,
                run_id=row.id,
                methodology_code=row.methodology_code,
                methodology_version=row.methodology_version,
                status=row.status,
                is_current=is_current,
                is_stale=bool(stale_codes),
                stale_reason_codes=stale_codes,
                product_count=row.product_count,
                precursor_contribution_count=row.precursor_contribution_count,
                internal_contribution_count=row.internal_contribution_count,
                total_direct_tco2e=row.total_direct_tco2e,
                total_indirect_tco2e=row.total_indirect_tco2e,
                total_embedded_tco2e=row.total_embedded_tco2e,
                result_unit=row.result_unit,
                specific_unit=row.specific_unit,
                created_at=row.created_at,
            )
        )
    return paginate(items, page=page, page_size=page_size, total_items=int(total))


def _product_payload(row: CbamProductEmbeddedEmissionsProduct) -> dict[str, Any]:
    return {
        'productId': str(row.product_id),
        'productProfileVersionId': str(row.product_profile_version_id),
        'profileVersion': row.profile_version,
        'cnNormalizedCode': row.cn_normalized_code,
        'cnDisplayCode': row.cn_display_code,
        'productName': row.product_name,
        'processId': str(row.process_id),
        'processRowVersion': row.process_row_version,
        'processProducedQuantity': str(row.process_produced_quantity),
        'processProducedQuantityUnit': row.process_produced_quantity_unit,
        'denominatorTonnes': str(row.denominator_tonnes),
        'productionRecordCount': row.production_record_count,
        'productionRecordsTonnes': (
            str(row.production_records_tonnes)
            if row.production_records_tonnes is not None
            else None
        ),
        'productionRecordIds': row.production_record_ids,
        'deaResultId': str(row.dea_result_id),
        'deaProductAllocationId': (
            str(row.dea_product_allocation_id)
            if row.dea_product_allocation_id is not None
            else None
        ),
        'deaDirectTco2': str(row.dea_direct_tco2),
        'ieaResultId': str(row.iea_result_id),
        'ieaProductAllocationId': (
            str(row.iea_product_allocation_id)
            if row.iea_product_allocation_id is not None
            else None
        ),
        'ieaIndirectTco2e': str(row.iea_indirect_tco2e),
        'hasMeasurableHeat': row.has_measurable_heat,
        'heatAttributedTco2e': str(row.heat_attributed_tco2e),
        'hasWasteGas': row.has_waste_gas,
        'wasteGasAttributedTco2e': str(row.waste_gas_attributed_tco2e),
        'exportedElectricityDirectTco2e': str(row.exported_electricity_direct_tco2e),
        'exportedElectricityNoteCode': row.exported_electricity_note_code,
        'hasExportedElectricity': row.has_exported_electricity,
        'exportedElectricityMwh': (
            str(row.exported_electricity_mwh)
            if row.exported_electricity_mwh is not None
            else None
        ),
        'exportedElectricityEmissionFactor': (
            str(row.exported_electricity_emission_factor)
            if row.exported_electricity_emission_factor is not None
            else None
        ),
        'ownDirectTco2eRaw': str(row.own_direct_tco2e_raw),
        'ownIndirectTco2eRaw': str(row.own_indirect_tco2e_raw),
        'precursorDirectTco2eRaw': str(row.precursor_direct_tco2e_raw),
        'precursorIndirectTco2eRaw': str(row.precursor_indirect_tco2e_raw),
        'internalDirectTco2eRaw': str(row.internal_direct_tco2e_raw),
        'internalIndirectTco2eRaw': str(row.internal_indirect_tco2e_raw),
        'totalDirectTco2eRaw': str(row.total_direct_tco2e_raw),
        'totalIndirectTco2eRaw': str(row.total_indirect_tco2e_raw),
        'totalEmbeddedTco2eRaw': str(row.total_embedded_tco2e_raw),
        'ownDirectTco2e': str(row.own_direct_tco2e),
        'ownIndirectTco2e': str(row.own_indirect_tco2e),
        'precursorDirectTco2e': str(row.precursor_direct_tco2e),
        'precursorIndirectTco2e': str(row.precursor_indirect_tco2e),
        'internalDirectTco2e': str(row.internal_direct_tco2e),
        'internalIndirectTco2e': str(row.internal_indirect_tco2e),
        'totalDirectTco2e': str(row.total_direct_tco2e),
        'totalIndirectTco2e': str(row.total_indirect_tco2e),
        'totalEmbeddedTco2e': str(row.total_embedded_tco2e),
        'specificDirectRaw': str(row.specific_direct_raw),
        'specificIndirectRaw': str(row.specific_indirect_raw),
        'specificTotalRaw': str(row.specific_total_raw),
        'specificDirect': str(row.specific_direct),
        'specificIndirect': str(row.specific_indirect),
        'specificTotal': str(row.specific_total),
        'precursorContributionCount': row.precursor_contribution_count,
        'internalContributionCount': row.internal_contribution_count,
        'resultUnit': row.result_unit,
        'specificUnit': row.specific_unit,
        'deaSourceUnit': row.dea_source_unit,
        'components': row.components_json,
        'provenance': row.provenance_json,
    }


def _contribution_payload(
    row: CbamProductEmbeddedEmissionsPrecursorContribution,
) -> dict[str, Any]:
    return {
        'productProfileVersionId': str(row.product_profile_version_id),
        'precursorId': str(row.precursor_id),
        'precursorRowVersion': row.precursor_row_version,
        'precursorName': row.precursor_name,
        'precursorCnNormalizedCode': row.precursor_cn_normalized_code,
        'precursorCnDisplayCode': row.precursor_cn_display_code,
        'dataSourceMode': row.data_source_mode,
        'valueSource': row.value_source,
        'productUseId': str(row.product_use_id),
        'productUseRowVersion': row.product_use_row_version,
        'productUseQuantity': str(row.product_use_quantity),
        'productUseUnit': row.product_use_unit,
        'quantityTonnes': str(row.quantity_tonnes),
        'specificDirect': str(row.specific_direct),
        'specificIndirect': str(row.specific_indirect),
        'contributionDirectTco2eRaw': str(row.contribution_direct_tco2e_raw),
        'contributionIndirectTco2eRaw': str(row.contribution_indirect_tco2e_raw),
        'contributionDirectTco2e': str(row.contribution_direct_tco2e),
        'contributionIndirectTco2e': str(row.contribution_indirect_tco2e),
        'defaultDatasetId': (
            str(row.default_dataset_id) if row.default_dataset_id is not None else None
        ),
        'defaultValueId': (
            str(row.default_value_id) if row.default_value_id is not None else None
        ),
        'defaultSnapshot': row.default_snapshot_json,
        'resultUnit': row.result_unit,
        'specificUnit': row.specific_unit,
    }


def _internal_contribution_payload(
    row: CbamProductEmbeddedEmissionsInternalContribution,
) -> dict[str, Any]:
    return {
        'consumerProductProfileVersionId': str(row.consumer_product_profile_version_id),
        'supplierProductProfileVersionId': str(row.supplier_product_profile_version_id),
        'consumerProcessId': str(row.consumer_process_id),
        'supplierProcessId': str(row.supplier_process_id),
        'supplierProcessRowVersion': row.supplier_process_row_version,
        'productUseId': str(row.product_use_id),
        'productUseRowVersion': row.product_use_row_version,
        'productUseQuantity': str(row.product_use_quantity),
        'productUseUnit': row.product_use_unit,
        'quantityTonnes': str(row.quantity_tonnes),
        'consumerDenominatorTonnes': str(row.consumer_denominator_tonnes),
        'aCoefficient': str(row.a_coefficient),
        'supplierSpecificDirect': str(row.supplier_specific_direct),
        'supplierSpecificIndirect': str(row.supplier_specific_indirect),
        'contributionDirectTco2eRaw': str(row.contribution_direct_tco2e_raw),
        'contributionIndirectTco2eRaw': str(row.contribution_indirect_tco2e_raw),
        'contributionDirectTco2e': str(row.contribution_direct_tco2e),
        'contributionIndirectTco2e': str(row.contribution_indirect_tco2e),
        'resultUnit': row.result_unit,
        'specificUnit': row.specific_unit,
    }


def get_product_embedded_emissions_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> ProductEmbeddedEmissionsResultDetail:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    row = db.execute(
        select(CbamProductEmbeddedEmissionsResult).where(
            CbamProductEmbeddedEmissionsResult.id == result_id,
            CbamProductEmbeddedEmissionsResult.organization_id == organization_id,
            CbamProductEmbeddedEmissionsResult.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Product embedded-emissions result not found.')

    pointer = _current_pointer(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        methodology_code=row.methodology_code,
    )
    is_current = pointer is not None and pointer.current_result_id == row.id
    stale_codes = (
        compute_product_embedded_emissions_stale_reasons(
            db, user, organization_id, binding_id, row
        )
        if is_current
        else []
    )
    export_code, export_note = exported_electricity_note_for(row.methodology_code)
    internal_code, internal_note = internal_precursor_note_for(row.methodology_code)
    return ProductEmbeddedEmissionsResultDetail(
        result_id=row.id,
        run_id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        methodology_code=row.methodology_code,
        methodology_version=row.methodology_version,
        workbook_filename=row.workbook_filename,
        workbook_sha256=row.workbook_sha256,
        workbook_formula_refs=row.workbook_formula_refs,
        client_request_id=row.client_request_id,
        request_fingerprint=row.request_fingerprint,
        status=row.status,
        is_current=is_current,
        is_stale=bool(stale_codes),
        stale_reason_codes=stale_codes,
        product_count=row.product_count,
        precursor_contribution_count=row.precursor_contribution_count,
        internal_contribution_count=row.internal_contribution_count,
        total_direct_tco2e_raw=row.total_direct_tco2e_raw,
        total_indirect_tco2e_raw=row.total_indirect_tco2e_raw,
        total_embedded_tco2e_raw=row.total_embedded_tco2e_raw,
        total_direct_tco2e=row.total_direct_tco2e,
        total_indirect_tco2e=row.total_indirect_tco2e,
        total_embedded_tco2e=row.total_embedded_tco2e,
        result_unit=row.result_unit,
        specific_unit=row.specific_unit,
        dea_source_unit=row.dea_source_unit,
        workbook_gas=row.workbook_gas,
        workbook_gwp=row.workbook_gwp,
        workbook_gwp_factor=row.workbook_gwp_factor,
        gwp_equivalence_note=GWP_EQUIVALENCE_NOTE,
        denominator_note=DENOMINATOR_NOTE,
        exported_electricity_note_code=export_code,
        exported_electricity_note=export_note,
        internal_precursor_note_code=internal_code,
        internal_precursor_note=internal_note,
        direct_emissions_allocation_result_id=row.dea_result_id,
        indirect_emissions_allocation_result_id=row.iea_result_id,
        informational_codes=[str(code) for code in (row.informational_codes_json or [])],
        products=[_product_payload(p) for p in _product_rows(db, row.id)],
        precursor_contributions=[
            _contribution_payload(c) for c in _contribution_rows(db, row.id)
        ],
        internal_contributions=[
            _internal_contribution_payload(c)
            for c in _internal_contribution_rows(db, row.id)
        ],
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


def get_product_embedded_emissions_summary(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> ProductEmbeddedEmissionsPeriodSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    pointer = _preferred_current_pointer(
        db, organization_id=organization_id, binding_id=binding_id
    )
    if pointer is None:
        return ProductEmbeddedEmissionsPeriodSummary(
            reporting_period_binding_id=binding_id,
            methodology_code=DEFAULT_METHODOLOGY_CODE,
            current_result_id=None,
            current_is_stale=False,
            stale_reason_codes=[],
            product_count=None,
            precursor_contribution_count=None,
            internal_contribution_count=None,
            total_direct_tco2e=None,
            total_indirect_tco2e=None,
            total_embedded_tco2e=None,
            result_unit=RESULT_UNIT_TCO2E,
            specific_unit=SPECIFIC_UNIT_TCO2E_PER_T,
            totals_by_product=[],
        )
    detail = get_product_embedded_emissions_result(
        db, user, organization_id, binding_id, pointer.current_result_id
    )
    return ProductEmbeddedEmissionsPeriodSummary(
        reporting_period_binding_id=binding_id,
        methodology_code=detail.methodology_code,
        current_result_id=detail.result_id,
        current_is_stale=detail.is_stale,
        stale_reason_codes=detail.stale_reason_codes,
        product_count=detail.product_count,
        precursor_contribution_count=detail.precursor_contribution_count,
        internal_contribution_count=detail.internal_contribution_count,
        total_direct_tco2e=detail.total_direct_tco2e,
        total_indirect_tco2e=detail.total_indirect_tco2e,
        total_embedded_tco2e=detail.total_embedded_tco2e,
        result_unit=detail.result_unit,
        specific_unit=detail.specific_unit,
        totals_by_product=detail.products,
    )




__all__ = [
    'ProductEmbeddedEmissionsExecuteRequest',
    'ProductEmbeddedEmissionsExecutionResponse',
    'ProductEmbeddedEmissionsPeriodSummary',
    'ProductEmbeddedEmissionsProductReadiness',
    'ProductEmbeddedEmissionsReadiness',
    'ProductEmbeddedEmissionsResultDetail',
    'ProductEmbeddedEmissionsResultSummary',
    'compute_product_embedded_emissions_stale_reasons',
    'execute_product_embedded_emissions',
    'get_product_embedded_emissions_readiness',
    'get_product_embedded_emissions_result',
    'get_product_embedded_emissions_summary',
    'list_product_embedded_emissions_results',
]
