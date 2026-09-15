from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.ports import ReportingPeriodRef
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamAllocationResult,
    CbamAllocationRule,
    CbamCalculationResult,
    CbamCalculationRun,
    CbamFactorDefinition,
    CbamFactorResolution,
    CbamInstallationProfile,
    CbamProductionRecord,
    CbamPurchasedInputRecord,
    CbamReportingPeriodBinding,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.organizations.infrastructure.models import Organization


@dataclass(slots=True)
class ExportDataContext:
    organization: Organization
    binding: CbamReportingPeriodBinding
    period: ReportingPeriodRef
    installations: list[CbamInstallationProfile]
    production: list[CbamProductionRecord]
    activities: list[CbamActivityRecord]
    purchased: list[CbamPurchasedInputRecord]
    allocation_rules: list[CbamAllocationRule]
    allocation_results: list[CbamAllocationResult]
    factor_resolutions: list[CbamFactorResolution]
    factor_definitions: dict[uuid.UUID, CbamFactorDefinition]
    calculation_run: CbamCalculationRun | None
    calculation_results: list[CbamCalculationResult]
    summary_metrics: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    mapped_trace_ids: dict[str, list[str]] = field(default_factory=dict)


def load_export_context(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    calculation_run_id: uuid.UUID | None = None,
) -> ExportDataContext:
    org = db.get(Organization, organization_id)
    binding = db.get(CbamReportingPeriodBinding, binding_id)
    assert org is not None and binding is not None
    period = require_reporting_period_in_organization(
        db, organization_id, binding.reporting_period_id
    )

    installations = list(
        db.execute(
            select(CbamInstallationProfile)
            .where(
                CbamInstallationProfile.organization_id == organization_id,
                CbamInstallationProfile.status != "archived",
            )
            .order_by(CbamInstallationProfile.code.asc())
        ).scalars()
    )
    production = list(
        db.execute(
            select(CbamProductionRecord)
            .where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.status == "active",
            )
            .order_by(
                CbamProductionRecord.production_date.asc().nulls_last(),
                CbamProductionRecord.id.asc(),
            )
        ).scalars()
    )
    activities = list(
        db.execute(
            select(CbamActivityRecord)
            .where(
                CbamActivityRecord.organization_id == organization_id,
                CbamActivityRecord.reporting_period_binding_id == binding_id,
                CbamActivityRecord.status == "active",
            )
            .order_by(
                CbamActivityRecord.activity_group.asc(),
                CbamActivityRecord.activity_type.asc(),
                CbamActivityRecord.activity_date.asc().nulls_last(),
                CbamActivityRecord.id.asc(),
            )
        ).scalars()
    )
    purchased = list(
        db.execute(
            select(CbamPurchasedInputRecord)
            .where(
                CbamPurchasedInputRecord.organization_id == organization_id,
                CbamPurchasedInputRecord.reporting_period_binding_id == binding_id,
                CbamPurchasedInputRecord.status == "active",
            )
            .order_by(
                CbamPurchasedInputRecord.input_name.asc(),
                CbamPurchasedInputRecord.supplier_name.asc().nulls_last(),
                CbamPurchasedInputRecord.id.asc(),
            )
        ).scalars()
    )
    allocation_rules = list(
        db.execute(
            select(CbamAllocationRule)
            .where(
                CbamAllocationRule.organization_id == organization_id,
                CbamAllocationRule.reporting_period_binding_id == binding_id,
            )
            .order_by(CbamAllocationRule.name.asc())
        ).scalars()
    )
    allocation_results = list(
        db.execute(
            select(CbamAllocationResult)
            .where(
                CbamAllocationResult.organization_id == organization_id,
                CbamAllocationResult.reporting_period_binding_id == binding_id,
                CbamAllocationResult.is_current.is_(True),
            )
            .order_by(
                CbamAllocationResult.source_type.asc(),
                CbamAllocationResult.source_id.asc(),
            )
        ).scalars()
    )
    factor_resolutions = list(
        db.execute(
            select(CbamFactorResolution)
            .where(
                CbamFactorResolution.organization_id == organization_id,
                CbamFactorResolution.reporting_period_binding_id == binding_id,
                CbamFactorResolution.is_current.is_(True),
            )
            .order_by(
                CbamFactorResolution.source_type.asc(),
                CbamFactorResolution.factor_definition_id.asc(),
                CbamFactorResolution.source_id.asc(),
            )
        ).scalars()
    )
    defs = {row.id: row for row in db.execute(select(CbamFactorDefinition)).scalars().all()}

    calc_run: CbamCalculationRun | None = None
    if calculation_run_id is not None:
        calc_run = db.execute(
            select(CbamCalculationRun).where(
                CbamCalculationRun.id == calculation_run_id,
                CbamCalculationRun.organization_id == organization_id,
                CbamCalculationRun.reporting_period_binding_id == binding_id,
            )
        ).scalar_one_or_none()
    else:
        calc_run = db.execute(
            select(CbamCalculationRun)
            .where(
                CbamCalculationRun.organization_id == organization_id,
                CbamCalculationRun.reporting_period_binding_id == binding_id,
                CbamCalculationRun.status.in_({"COMPLETED", "PARTIALLY_COMPLETED", "FAILED"}),
            )
            .order_by(CbamCalculationRun.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    calc_results: list[CbamCalculationResult] = []
    if calc_run is not None:
        calc_results = list(
            db.execute(
                select(CbamCalculationResult)
                .where(
                    CbamCalculationResult.organization_id == organization_id,
                    CbamCalculationResult.calculation_run_id == calc_run.id,
                    CbamCalculationResult.is_current.is_(True),
                )
                .order_by(
                    CbamCalculationResult.source_type.asc(),
                    CbamCalculationResult.source_id.asc(),
                )
            ).scalars()
        )

    primary = sum(1 for r in factor_resolutions if r.resolution_status == "RESOLVED_PRIMARY")
    default = sum(1 for r in factor_resolutions if r.resolution_status == "RESOLVED_DEFAULT")
    unresolved = sum(1 for r in factor_resolutions if r.resolution_status == "UNRESOLVED")
    ambiguous = sum(1 for r in factor_resolutions if r.resolution_status == "AMBIGUOUS")
    calculated = [r for r in calc_results if r.status == "CALCULATED"]
    blocked = [
        r
        for r in calc_results
        if r.status
        in {
            "BLOCKED",
            "UNRESOLVED_FACTOR",
            "AMBIGUOUS_FACTOR",
            "INCOMPATIBLE_UNIT",
            "INVALID_INPUT",
            "UNSUPPORTED_FORMULA",
        }
    ]
    units = {r.result_unit for r in calculated if r.result_unit}
    technical_total: Decimal | None = None
    technical_unit: str | None = None
    if len(units) == 1:
        technical_unit = next(iter(units))
        technical_total = sum(
            (r.result_value for r in calculated if r.result_value is not None),
            Decimal("0"),
        )

    warnings: list[str] = []
    if blocked:
        warnings.append(
            f"{len(blocked)} blocked/invalid calculation result(s) will not be exported as zero."
        )
    if unresolved:
        warnings.append(f"{unresolved} unresolved factor resolution(s).")
    if ambiguous:
        warnings.append(f"{ambiguous} ambiguous factor resolution(s).")

    metrics: dict[str, object] = {
        "production_record_count": len(production),
        "activity_record_count": len(activities),
        "purchased_input_count": len(purchased),
        "allocation_rule_count": len(allocation_rules),
        "allocation_result_count": len(allocation_results),
        "resolved_primary_factor_count": primary,
        "resolved_default_factor_count": default,
        "unresolved_factor_count": unresolved,
        "ambiguous_factor_count": ambiguous,
        "calculated_result_count": len(calculated),
        "blocked_calculation_count": len(blocked),
        "technical_total": technical_total,
        "technical_total_unit": technical_unit,
        "export_date": datetime.now(UTC).date().isoformat(),
        "export_readiness": None,
    }

    return ExportDataContext(
        organization=org,
        binding=binding,
        period=period,
        installations=installations,
        production=production,
        activities=activities,
        purchased=purchased,
        allocation_rules=allocation_rules,
        allocation_results=allocation_results,
        factor_resolutions=factor_resolutions,
        factor_definitions=defs,
        calculation_run=calc_run,
        calculation_results=calc_results,
        summary_metrics=metrics,
        warnings=warnings,
        mapped_trace_ids={
            "allocationResultIds": [str(r.id) for r in allocation_results],
            "factorResolutionIds": [str(r.id) for r in factor_resolutions],
            "calculationResultIds": [str(r.id) for r in calc_results],
        },
    )


def scalar_source_value(ctx: ExportDataContext, source_path: str) -> object | None:
    constants = {
        "constant.internal_disclaimer": (
            "INTERNAL DEVELOPMENT TEMPLATE — NOT AN OFFICIAL CBAM SUBMISSION FORMAT"
        ),
    }
    if source_path in constants:
        return constants[source_path]

    org = ctx.organization
    period = ctx.period
    installation = ctx.installations[0] if ctx.installations else None

    scalars: dict[str, object | None] = {
        "organization.name": org.name,
        "organization.code": getattr(org, "slug", None) or getattr(org, "code", None),
        "installation.code": installation.code if installation else None,
        "installation.name": installation.name if installation else None,
        "reporting_period.label": f"{period.code}: {period.start_date} → {period.end_date}",
        "reporting_period.start_date": period.start_date,
        "reporting_period.end_date": period.end_date,
        "summary.production_record_count": ctx.summary_metrics["production_record_count"],
        "summary.activity_record_count": ctx.summary_metrics["activity_record_count"],
        "summary.purchased_input_count": ctx.summary_metrics["purchased_input_count"],
        "summary.allocation_result_count": ctx.summary_metrics["allocation_result_count"],
        "summary.resolved_primary_factor_count": ctx.summary_metrics[
            "resolved_primary_factor_count"
        ],
        "summary.resolved_default_factor_count": ctx.summary_metrics[
            "resolved_default_factor_count"
        ],
        "summary.unresolved_factor_count": ctx.summary_metrics["unresolved_factor_count"],
        "summary.ambiguous_factor_count": ctx.summary_metrics["ambiguous_factor_count"],
        "summary.calculated_result_count": ctx.summary_metrics["calculated_result_count"],
        "summary.blocked_calculation_count": ctx.summary_metrics["blocked_calculation_count"],
        "summary.technical_total": ctx.summary_metrics["technical_total"],
        "summary.technical_total_unit": ctx.summary_metrics["technical_total_unit"],
        "summary.export_date": ctx.summary_metrics["export_date"],
        "summary.export_readiness": ctx.summary_metrics["export_readiness"],
    }
    if source_path not in scalars:
        raise KeyError(f"Unsupported export source path: {source_path}")
    return scalars[source_path]


def _fmt_date(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def repeating_rows(ctx: ExportDataContext, source_path: str) -> list[dict[str, object | None]]:
    if source_path == "production.rows":
        return [
            {
                "product": str(r.product_profile_version_id or ""),
                "quantity": r.quantity,
                "unit": r.unit,
                "date": _fmt_date(r.production_date),
                "id": str(r.id),
            }
            for r in ctx.production
        ]
    if source_path == "activity.rows":
        return [
            {
                "group": r.activity_group,
                "type": r.activity_type,
                "quantity": r.quantity,
                "unit": r.unit,
                "data_source": r.data_source_type,
                "date": _fmt_date(r.activity_date),
                "id": str(r.id),
            }
            for r in ctx.activities
        ]
    if source_path == "purchased.rows":
        return [
            {
                "input_name": r.input_name,
                "supplier": r.supplier_name,
                "purchased_quantity": r.quantity,
                "consumed_quantity": r.consumed_quantity,
                "unit": r.unit,
                "embedded_value": r.embedded_emission_value,
                "embedded_unit": r.embedded_emission_unit,
                "id": str(r.id),
            }
            for r in ctx.purchased
        ]
    if source_path == "allocation.rows":
        return [
            {
                "source_type": r.source_type,
                "source_id": str(r.source_id),
                "method": r.allocation_method,
                "ratio": r.allocation_ratio,
                "allocated_quantity": r.allocated_quantity,
                "allocated_unit": r.allocated_unit,
                "id": str(r.id),
            }
            for r in ctx.allocation_results
        ]
    if source_path == "factor.rows":
        factor_rows: list[dict[str, object | None]] = []
        for resolution in ctx.factor_resolutions:
            definition = ctx.factor_definitions.get(resolution.factor_definition_id)
            factor_rows.append(
                {
                    "source_type": resolution.source_type,
                    "source_id": str(resolution.source_id),
                    "definition": (
                        definition.code if definition else str(resolution.factor_definition_id)
                    ),
                    "selected_value": resolution.selected_value,
                    "unit": resolution.selected_unit,
                    "precedence": resolution.source_precedence,
                    "status": resolution.resolution_status,
                    "id": str(resolution.id),
                }
            )
        return factor_rows
    if source_path == "calculation.rows":
        calc_rows: list[dict[str, object | None]] = []
        for result in ctx.calculation_results:
            is_calculated = result.status == "CALCULATED"
            calc_rows.append(
                {
                    "source_type": result.source_type,
                    "source_id": str(result.source_id),
                    "quantity": result.source_quantity,
                    "quantity_unit": result.source_unit,
                    "factor": result.factor_value,
                    "factor_unit": result.factor_unit,
                    "result": result.result_value if is_calculated else None,
                    "result_unit": result.result_unit if is_calculated else None,
                    "status": result.status,
                    "error": result.error_message,
                    "id": str(result.id),
                }
            )
        return calc_rows
    raise KeyError(f"Unsupported repeating source path: {source_path}")
