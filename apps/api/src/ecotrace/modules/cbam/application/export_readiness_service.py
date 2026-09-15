from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.export_context import load_export_context
from ecotrace.modules.cbam.application.export_template_service import (
    ensure_internal_export_template,
    get_active_template_for_org,
    list_template_mappings,
    verify_template_file,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel


def _metric_int(metrics: dict[str, object], key: str) -> int:
    value = metrics.get(key) or 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


class ReadinessCheckItem(CamelModel):
    code: str
    label: str
    status: str
    message: str


class ExportReadinessResponse(CamelModel):
    status: str
    checks: list[ReadinessCheckItem]
    blocking_issues: list[str]
    warnings: list[str]
    official_mapping_blocked: bool
    suggested_template_id: uuid.UUID | None
    calculation_run_id: uuid.UUID | None


def assess_export_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    template_id: uuid.UUID | None = None,
    calculation_run_id: uuid.UUID | None = None,
) -> ExportReadinessResponse:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    ensure_internal_export_template(db)
    template = get_active_template_for_org(db, organization_id, template_id)
    mappings = list_template_mappings(db, template.id)
    ctx = load_export_context(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        calculation_run_id=calculation_run_id,
    )

    checks: list[ReadinessCheckItem] = []
    blocking: list[str] = []
    warnings = list(ctx.warnings)

    def add(code: str, label: str, status: str, message: str) -> None:
        checks.append(ReadinessCheckItem(code=code, label=label, status=status, message=message))
        if status == "MISSING":
            blocking.append(message)
        elif status == "WARNING":
            warnings.append(message)

    if ctx.production:
        add("production", "Production Data", "OK", f"{len(ctx.production)} production record(s).")
    else:
        add("production", "Production Data", "WARNING", "No production records (non-blocking).")

    if ctx.activities:
        add("activity", "Activity Data", "OK", f"{len(ctx.activities)} activity record(s).")
    else:
        add("activity", "Activity Data", "MISSING", "At least one activity record is required.")

    if ctx.purchased:
        add(
            "purchased",
            "Purchased Inputs",
            "OK",
            f"{len(ctx.purchased)} purchased input record(s).",
        )
    else:
        add(
            "purchased",
            "Purchased Inputs",
            "WARNING",
            "No purchased inputs (non-blocking).",
        )

    if ctx.allocation_results:
        add(
            "allocation",
            "Allocation",
            "OK",
            f"{len(ctx.allocation_results)} current allocation result(s).",
        )
    else:
        add("allocation", "Allocation", "WARNING", "No allocation results (non-blocking).")

    if ctx.factor_resolutions:
        unresolved = _metric_int(ctx.summary_metrics, "unresolved_factor_count")
        ambiguous = _metric_int(ctx.summary_metrics, "ambiguous_factor_count")
        if unresolved or ambiguous:
            add(
                "factors",
                "Factor Resolution",
                "WARNING",
                f"{len(ctx.factor_resolutions)} resolutions; unresolved={unresolved}, "
                f"ambiguous={ambiguous}.",
            )
        else:
            add(
                "factors",
                "Factor Resolution",
                "OK",
                f"{len(ctx.factor_resolutions)} current factor resolution(s).",
            )
    else:
        add("factors", "Factor Resolution", "WARNING", "No factor resolutions yet.")

    if ctx.calculation_run is None:
        add("calculation", "Calculation", "MISSING", "A calculation run is required before export.")
    elif ctx.calculation_run.status not in {"COMPLETED", "PARTIALLY_COMPLETED"}:
        add(
            "calculation",
            "Calculation",
            "MISSING",
            f"Calculation run status {ctx.calculation_run.status} is not exportable.",
        )
    elif _metric_int(ctx.summary_metrics, "calculated_result_count") == 0:
        add(
            "calculation",
            "Calculation",
            "MISSING",
            "No CALCULATED results available to export.",
        )
    elif _metric_int(ctx.summary_metrics, "blocked_calculation_count") > 0:
        add(
            "calculation",
            "Calculation",
            "WARNING",
            "Blocked calculations present; they will not be exported as zero.",
        )
    else:
        add(
            "calculation",
            "Calculation",
            "OK",
            f"Calculation run {ctx.calculation_run.id} has "
            f"{ctx.summary_metrics['calculated_result_count']} calculated result(s).",
        )

    try:
        verify_template_file(template)
        if not mappings:
            add("mappings", "Excel Mapping", "MISSING", "Template has no mappings.")
        else:
            add(
                "mappings",
                "Excel Mapping",
                "OK",
                f"{len(mappings)} mapping(s) for {template.code} v{template.version}.",
            )
    except Exception as exc:
        add("mappings", "Excel Mapping", "MISSING", str(exc))

    if template.template_type == "INTERNAL_SKDM":
        warnings.append(
            "Official CBAM workbook mapping is BLOCKED; using internal development template only."
        )

    if any(c.status == "MISSING" for c in checks):
        status = "NOT_READY"
    elif any(c.status == "WARNING" for c in checks) or warnings:
        status = "READY_WITH_WARNINGS"
    else:
        status = "READY"

    ctx.summary_metrics["export_readiness"] = status
    return ExportReadinessResponse(
        status=status,
        checks=checks,
        blocking_issues=blocking,
        warnings=sorted(set(warnings)),
        official_mapping_blocked=True,
        suggested_template_id=template.id,
        calculation_run_id=ctx.calculation_run.id if ctx.calculation_run else None,
    )
