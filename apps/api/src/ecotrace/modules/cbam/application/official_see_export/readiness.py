"""Fail-closed Official SEE readiness (distinct from Phase 6 internal export)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    get_direct_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    get_indirect_emissions_allocation_summary,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    get_monthly_production_basis_summary,
)
from ecotrace.modules.cbam.application.official_see_export.capacity import (
    CapacityUsage,
    assess_capacity,
)
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_DEA_MISSING_OR_STALE,
    CODE_IEA_MISSING_OR_STALE,
    CODE_INTERNAL_FLOW_INVALID,
    CODE_MAPPING_OR_TEMPLATE_INVALID,
    CODE_MONTHLY_PRODUCTION_BASIS_NOT_READY,
    CODE_ORG_BINDING_INVALID,
    CODE_PEE_V2_MISSING_OR_STALE,
    CODE_PRECURSORS_NOT_READY_OR_UNBALANCED,
    CODE_PROCESSES_NOT_READY,
    CODE_PRODUCT_PROFILES_NOT_READY,
    CODE_PRODUCTION_PROFILE_LINK_NOT_READY,
    CODE_RECALCULATION_ENGINE_UNAVAILABLE,
    MAPPING_VERSION,
    TEMPLATE_SHA256,
    TEMPLATE_VERSION,
)
from ecotrace.modules.cbam.application.official_see_export.mapping.loader import (
    validate_manifest_or_raise,
)
from ecotrace.modules.cbam.application.official_see_export.recalc import soffice_available
from ecotrace.modules.cbam.application.official_see_export.schemas import (
    OfficialSeeExportReadiness,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.precursor_constants import (
    PRECURSOR_STATUS_ARCHIVED,
)
from ecotrace.modules.cbam.application.precursor_constants import (
    READINESS_READY as PRECURSOR_READINESS_READY,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    CODE_INTERNAL_PRODUCT_FLOW_INVALID,
    CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE,
    DEFAULT_METHODOLOGY_CODE,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_service import (
    get_product_embedded_emissions_readiness,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    list_product_profiles_for_binding,
)
from ecotrace.modules.cbam.application.production_process_constants import (
    PROCESS_STATUS_ARCHIVED,
)
from ecotrace.modules.cbam.application.production_process_constants import (
    READINESS_READY as PROCESS_READINESS_READY,
)
from ecotrace.modules.cbam.application.production_process_service import (
    get_production_process_binding_summary,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    get_purchased_precursor_binding_summary,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamInstallationProfile,
    CbamProductionProcess,
    CbamPurchasedPrecursor,
)
from ecotrace.modules.identity.infrastructure.models import User


@dataclass(frozen=True, slots=True)
class OfficialSeeReadinessAssessment:
    ready: bool
    blocking_issue_codes: list[str]
    warnings: list[str]
    snapshot_ids: dict[str, str | None]
    capacity_usage: CapacityUsage


def _dedupe(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


def assess_official_see_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    require_recalc_engine: bool = False,
) -> OfficialSeeReadinessAssessment:
    require_cbam_view(db, user, organization_id)
    blocking: list[str] = []
    warnings: list[str] = []
    snapshot_ids: dict[str, str | None] = {
        "peeResultId": None,
        "deaResultId": None,
        "ieaResultId": None,
    }

    try:
        get_binding_for_org(db, organization_id, binding_id)
    except (NotFoundError, ValidationAppError):
        return OfficialSeeReadinessAssessment(
            ready=False,
            blocking_issue_codes=[CODE_ORG_BINDING_INVALID],
            warnings=[],
            snapshot_ids=snapshot_ids,
            capacity_usage=CapacityUsage(0, 0, 0, 0, 0, 0, 0),
        )

    try:
        validate_manifest_or_raise()
    except Exception:
        blocking.append(CODE_MAPPING_OR_TEMPLATE_INVALID)

    active_processes = list(
        db.execute(
            select(CbamProductionProcess).where(
                CbamProductionProcess.organization_id == organization_id,
                CbamProductionProcess.reporting_period_binding_id == binding_id,
                CbamProductionProcess.status != PROCESS_STATUS_ARCHIVED,
            )
        )
        .scalars()
        .all()
    )
    installation_ids = {p.installation_profile_id for p in active_processes}
    if not installation_ids:
        # Fall back to any org installation for capacity messaging.
        installation_ids = set(
            db.execute(
                select(CbamInstallationProfile.id)
                .where(CbamInstallationProfile.organization_id == organization_id)
                .limit(2)
            )
            .scalars()
            .all()
        )

    profiles_page = list_product_profiles_for_binding(
        db, user, organization_id, binding_id, page=1, page_size=100
    )
    ready_profiles = [p for p in profiles_page.items if p.classification_ready]
    if not ready_profiles:
        blocking.append(CODE_PRODUCT_PROFILES_NOT_READY)

    monthly = get_monthly_production_basis_summary(db, user, organization_id, binding_id)
    if not monthly.allocation_basis_ready:
        blocking.append(CODE_MONTHLY_PRODUCTION_BASIS_NOT_READY)

    dea = get_direct_emissions_allocation_summary(db, user, organization_id, binding_id)
    if dea.current_result_id is None or dea.current_is_stale:
        blocking.append(CODE_DEA_MISSING_OR_STALE)
    else:
        snapshot_ids["deaResultId"] = str(dea.current_result_id)

    iea = get_indirect_emissions_allocation_summary(db, user, organization_id, binding_id)
    if iea.current_result_id is None or iea.current_is_stale:
        blocking.append(CODE_IEA_MISSING_OR_STALE)
    else:
        snapshot_ids["ieaResultId"] = str(iea.current_result_id)

    process_summary = get_production_process_binding_summary(db, user, organization_id, binding_id)
    active_ids = {p.id for p in active_processes}
    ready_process_ids = {
        r.process_id
        for r in process_summary.processes
        if r.status == PROCESS_READINESS_READY and r.process_id in active_ids
    }
    if not active_processes or ready_process_ids != active_ids:
        blocking.append(CODE_PROCESSES_NOT_READY)
    if any(p.product_profile_version_id is None for p in active_processes):
        blocking.append(CODE_PRODUCTION_PROFILE_LINK_NOT_READY)

    precursor_summary = get_purchased_precursor_binding_summary(
        db, user, organization_id, binding_id
    )
    active_precursors = list(
        db.execute(
            select(CbamPurchasedPrecursor).where(
                CbamPurchasedPrecursor.organization_id == organization_id,
                CbamPurchasedPrecursor.reporting_period_binding_id == binding_id,
                CbamPurchasedPrecursor.status != PRECURSOR_STATUS_ARCHIVED,
            )
        )
        .scalars()
        .all()
    )
    active_precursor_ids = {p.id for p in active_precursors}
    ready_precursor_ids = {
        r.precursor_id
        for r in precursor_summary.precursors
        if r.status == PRECURSOR_READINESS_READY and r.precursor_id in active_precursor_ids
    }
    if active_precursors and ready_precursor_ids != active_precursor_ids:
        blocking.append(CODE_PRECURSORS_NOT_READY_OR_UNBALANCED)
    if precursor_summary.unbalanced_count:
        blocking.append(CODE_PRECURSORS_NOT_READY_OR_UNBALANCED)

    pee = get_product_embedded_emissions_readiness(
        db,
        user,
        organization_id,
        binding_id,
        methodology_code=DEFAULT_METHODOLOGY_CODE,
    )
    if pee.status != "READY" or pee.current_result_id is None or pee.current_is_stale:
        blocking.append(CODE_PEE_V2_MISSING_OR_STALE)
    else:
        snapshot_ids["peeResultId"] = str(pee.current_result_id)

    flow_codes = {
        CODE_INTERNAL_PRODUCT_FLOW_INVALID,
        CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE,
        "INTERNAL_FLOW_INVALID",
    }
    if any(code in flow_codes for code in pee.blocking_issue_codes):
        blocking.append(CODE_INTERNAL_FLOW_INVALID)
    if any(code in flow_codes for code in pee.stale_reason_codes):
        blocking.append(CODE_INTERNAL_FLOW_INVALID)

    goods_count = len({p.cn_normalized_code or str(p.id) for p in ready_profiles})
    usage = CapacityUsage(
        installations=max(len(installation_ids), 1),
        goods=goods_count,
        processes=len(active_processes),
        precursors=len(active_precursors),
        max_process_product_uses=0,
        max_precursor_product_uses=0,
        fuel_activities=0,
    )
    blocking.extend(assess_capacity(usage))

    if require_recalc_engine and not soffice_available():
        blocking.append(CODE_RECALCULATION_ENGINE_UNAVAILABLE)
    elif not soffice_available():
        warnings.append(CODE_RECALCULATION_ENGINE_UNAVAILABLE)

    codes = _dedupe(blocking)
    return OfficialSeeReadinessAssessment(
        ready=not codes,
        blocking_issue_codes=codes,
        warnings=_dedupe(warnings),
        snapshot_ids=snapshot_ids,
        capacity_usage=usage,
    )


def get_official_see_export_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> OfficialSeeExportReadiness:
    assessment = assess_official_see_readiness(db, user, organization_id, binding_id)
    return OfficialSeeExportReadiness(
        ready=assessment.ready,
        blocking_issue_codes=assessment.blocking_issue_codes,
        warnings=assessment.warnings,
        mapping_version=MAPPING_VERSION,
        template_version=TEMPLATE_VERSION,
        template_sha256=TEMPLATE_SHA256,
        capacity={
            "installations": assessment.capacity_usage.installations,
            "goods": assessment.capacity_usage.goods,
            "processes": assessment.capacity_usage.processes,
            "precursors": assessment.capacity_usage.precursors,
            "fuelActivities": assessment.capacity_usage.fuel_activities,
        },
        soffice_available=soffice_available(),
        snapshot_ids=assessment.snapshot_ids,
    )
