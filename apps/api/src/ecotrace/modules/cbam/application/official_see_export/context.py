"""Deterministic Official SEE export snapshot from EcoTrace (stable slot then UUID sort)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.official_see_export.capacity import (
    CapacityUsage,
    assess_capacity,
)
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CAPACITY_PRECURSOR_PRODUCT_USE_ROWS,
    CAPACITY_PROCESS_PRODUCT_USE_ROWS,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.precursor_constants import PRECURSOR_STATUS_ARCHIVED
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    DEFAULT_METHODOLOGY_CODE,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    list_product_profiles_for_binding,
)
from ecotrace.modules.cbam.application.production_process_constants import PROCESS_STATUS_ARCHIVED
from ecotrace.modules.cbam.infrastructure.models import (
    CbamDeaProductAllocation,
    CbamDirectEmissionsAllocationCurrent,
    CbamIeaProductAllocation,
    CbamIndirectEmissionsAllocationCurrent,
    CbamInstallationProfile,
    CbamProductEmbeddedEmissionsCurrent,
    CbamProductEmbeddedEmissionsProduct,
    CbamProductEmbeddedEmissionsResult,
    CbamProductionProcess,
    CbamProductionProcessProductUse,
    CbamPurchasedPrecursor,
    CbamPurchasedPrecursorProductUse,
    CbamStationaryCombustionCurrentResult,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization


def _dec(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


@dataclass(slots=True)
class OfficialSeeExportContext:
    organization_id: uuid.UUID
    organization_name: str
    binding_id: uuid.UUID
    installation: dict[str, Any]
    reporting_period: dict[str, Any]
    goods: list[dict[str, Any]]
    processes: list[dict[str, Any]]
    precursors: list[dict[str, Any]]
    fuels: list[dict[str, Any]]
    pee_products: list[dict[str, Any]]
    pee_result_id: uuid.UUID | None
    dea_result_id: uuid.UUID | None
    iea_result_id: uuid.UUID | None
    process_ids: list[uuid.UUID] = field(default_factory=list)
    precursor_ids: list[uuid.UUID] = field(default_factory=list)
    capacity_usage: CapacityUsage | None = None
    expected_outputs: dict[tuple[str, str], Any] = field(default_factory=dict)
    source_fingerprint: str = ""

    def input_values(self) -> dict[tuple[str, str], Any]:
        """Resolve manifest source paths to cell values for used INPUT slots."""
        values: dict[tuple[str, str], Any] = {}
        # Populated by writer via resolve_source against this context.
        return values


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_official_see_context(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> OfficialSeeExportContext:
    require_cbam_view(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    org = db.get(Organization, organization_id)
    org_name = org.name if org is not None else str(organization_id)

    period = require_reporting_period_in_organization(
        db, organization_id, binding.reporting_period_id
    )

    processes = list(
        db.execute(
            select(CbamProductionProcess)
            .where(
                CbamProductionProcess.organization_id == organization_id,
                CbamProductionProcess.reporting_period_binding_id == binding_id,
                CbamProductionProcess.status != PROCESS_STATUS_ARCHIVED,
            )
            .order_by(CbamProductionProcess.id.asc())
        )
        .scalars()
        .all()
    )
    # Stable workbook slot order: slot by sorted UUID then assign 0..n-1
    processes_sorted = sorted(processes, key=lambda p: (p.id,))
    installation_id = processes_sorted[0].installation_profile_id if processes_sorted else None
    installation_row = db.get(CbamInstallationProfile, installation_id) if installation_id else None
    installation = {
        "id": str(installation_row.id) if installation_row else None,
        "name": installation_row.name if installation_row else org_name,
        "address": None,
        "city": None,
        "country_code": None,
        "postal_code": None,
        "unlocode": None,
        "contact_name": None,
        "email": None,
        "telephone": None,
        "code": installation_row.code if installation_row else None,
    }

    profiles = list_product_profiles_for_binding(
        db, user, organization_id, binding_id, page=1, page_size=100
    ).items
    ready_profiles = sorted(
        [p for p in profiles if p.classification_ready],
        key=lambda p: p.id,
    )
    goods: list[dict[str, Any]] = []
    seen_goods: set[str] = set()
    for profile in ready_profiles:
        # Goods type label: SEE expects aggregated goods category strings from CN lists.
        label = "Iron or steel products"
        key = profile.cn_normalized_code or label
        if key in seen_goods:
            continue
        seen_goods.add(key)
        goods.append({"goods_type": label, "profile_id": str(profile.id)})

    dea_pointer = db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.organization_id == organization_id,
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    dea_by_profile: dict[uuid.UUID, Decimal] = {}
    if dea_pointer is not None:
        for dea_row in db.execute(
            select(CbamDeaProductAllocation).where(
                CbamDeaProductAllocation.result_id == dea_pointer.current_result_id
            )
        ).scalars():
            dea_by_profile[dea_row.product_profile_version_id] = (
                dea_row.final_allocated_fossil_co2_tonnes
            )

    iea_pointer = db.execute(
        select(CbamIndirectEmissionsAllocationCurrent).where(
            CbamIndirectEmissionsAllocationCurrent.organization_id == organization_id,
            CbamIndirectEmissionsAllocationCurrent.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    iea_mwh: dict[uuid.UUID, Decimal] = {}
    iea_tco2e: dict[uuid.UUID, Decimal] = {}
    if iea_pointer is not None:
        for iea_row in db.execute(
            select(CbamIeaProductAllocation).where(
                CbamIeaProductAllocation.result_id == iea_pointer.current_result_id
            )
        ).scalars():
            iea_mwh[iea_row.product_profile_version_id] = iea_row.final_allocated_electricity_mwh
            iea_tco2e[iea_row.product_profile_version_id] = (
                iea_row.final_allocated_indirect_emissions_tco2e
            )

    profile_to_process_slot: dict[uuid.UUID, int] = {}
    for slot, process in enumerate(processes_sorted):
        if process.product_profile_version_id is not None:
            profile_to_process_slot[process.product_profile_version_id] = slot

    process_payloads: list[dict[str, Any]] = []
    max_process_uses = 0
    n_processes = len(processes_sorted)
    for slot, process in enumerate(processes_sorted):
        process_uses = list(
            db.execute(
                select(CbamProductionProcessProductUse)
                .where(CbamProductionProcessProductUse.process_id == process.id)
                .order_by(CbamProductionProcessProductUse.id.asc())
            )
            .scalars()
            .all()
        )
        max_process_uses = max(max_process_uses, len(process_uses))
        # Workbook L32+i on the supplier sheet maps to *other* processes in ascending
        # slot order (skipping self), matching D_Processes S-column numbering.
        by_consumer: dict[int, Decimal] = {}
        for use in process_uses:
            consumer_slot = profile_to_process_slot.get(use.target_product_profile_version_id)
            if consumer_slot is None or consumer_slot == slot:
                continue
            by_consumer[consumer_slot] = use.quantity
        other_slots = [i for i in range(n_processes) if i != slot]
        mapped_uses: list[dict[str, Any]] = []
        for consumer_slot in other_slots:
            qty = by_consumer.get(consumer_slot)
            mapped_uses.append(
                {
                    "quantity": _dec(qty),
                    "target_product_profile_version_id": (
                        str(processes_sorted[consumer_slot].product_profile_version_id)
                        if processes_sorted[consumer_slot].product_profile_version_id
                        else None
                    ),
                }
            )
        while len(mapped_uses) < CAPACITY_PROCESS_PRODUCT_USE_ROWS:
            mapped_uses.append({"quantity": None, "target_product_profile_version_id": None})
        mapped_uses = mapped_uses[:CAPACITY_PROCESS_PRODUCT_USE_ROWS]

        profile_id = process.product_profile_version_id
        direct = dea_by_profile.get(profile_id) if profile_id else None
        elec_mwh = iea_mwh.get(profile_id) if profile_id else None
        elec_t = iea_tco2e.get(profile_id) if profile_id else None
        elec_ef = None
        if elec_mwh is not None and elec_t is not None and elec_mwh != 0:
            elec_ef = elec_t / elec_mwh
        process_payloads.append(
            {
                "slot_index": slot,
                "id": str(process.id),
                "name": process.name or f"Process {slot + 1}",
                "goods_type": "Iron or steel products",
                "produced_quantity": _dec(process.produced_quantity),
                "marketed_quantity": _dec(process.marketed_quantity),
                "non_cbam_quantity": _dec(process.non_cbam_quantity),
                "allocated_direct_tco2e": _dec(direct),
                "allocated_electricity_mwh": _dec(elec_mwh),
                "electricity_ef": _dec(elec_ef),
                "electricity_ef_source": "D.4(b)",
                "exported_electricity_mwh": _dec(process.exported_electricity_quantity),
                "exported_electricity_ef": _dec(process.exported_electricity_emission_factor),
                "has_measurable_heat": process.has_measurable_heat,
                "has_waste_gas": process.has_waste_gas,
                "heat_import_tj": _dec(process.heat_imported_quantity),
                "heat_export_tj": _dec(process.heat_exported_quantity),
                "heat_import_ef": _dec(process.heat_imported_ef),
                "heat_export_ef": _dec(process.heat_exported_ef),
                "waste_import_tj": _dec(process.waste_gas_imported_quantity),
                "waste_export_tj": _dec(process.waste_gas_exported_quantity),
                "product_uses": mapped_uses,
                "product_use_count": len(process_uses),
            }
        )

    precursors = list(
        db.execute(
            select(CbamPurchasedPrecursor)
            .where(
                CbamPurchasedPrecursor.organization_id == organization_id,
                CbamPurchasedPrecursor.reporting_period_binding_id == binding_id,
                CbamPurchasedPrecursor.status != PRECURSOR_STATUS_ARCHIVED,
            )
            .order_by(CbamPurchasedPrecursor.id.asc())
        )
        .scalars()
        .all()
    )
    precursors_sorted = sorted(precursors, key=lambda p: p.id)
    precursor_payloads: list[dict[str, Any]] = []
    max_precursor_uses = 0
    for slot, precursor in enumerate(precursors_sorted):
        precursor_uses = list(
            db.execute(
                select(CbamPurchasedPrecursorProductUse)
                .where(CbamPurchasedPrecursorProductUse.precursor_id == precursor.id)
                .order_by(CbamPurchasedPrecursorProductUse.id.asc())
            )
            .scalars()
            .all()
        )
        max_precursor_uses = max(max_precursor_uses, len(precursor_uses))
        total_qty = precursor.quantity
        # E_PurchPrec L28+i maps directly to process index i (1-based D column).
        precursor_use_slots: list[dict[str, Any]] = [
            {"quantity": None} for _ in range(CAPACITY_PRECURSOR_PRODUCT_USE_ROWS)
        ]
        for p_use in precursor_uses:
            consumer_slot = profile_to_process_slot.get(p_use.target_product_profile_version_id)
            if consumer_slot is None or consumer_slot >= CAPACITY_PRECURSOR_PRODUCT_USE_ROWS:
                continue
            precursor_use_slots[consumer_slot] = {"quantity": _dec(p_use.quantity)}
        precursor_payloads.append(
            {
                "slot_index": slot,
                "id": str(precursor.id),
                "name": precursor.name or f"Precursor {slot + 1}",
                "goods_type": precursor.aggregated_goods_category or "Iron or steel products",
                "country_code": precursor.country_of_origin,
                "routes": [_dec(total_qty)] + [None] * 7,
                "non_cbam_quantity": _dec(precursor.non_cbam_quantity),
                "specific_direct_tco2e_per_t": _dec(precursor.specific_direct_embedded_emissions),
                "electricity_mwh_per_t": _dec(precursor.electricity_consumption_intensity),
                "electricity_ef": _dec(precursor.electricity_emission_factor),
                "product_uses": precursor_use_slots,
                "product_use_count": len(precursor_uses),
            }
        )

    pee_pointer = db.execute(
        select(CbamProductEmbeddedEmissionsCurrent).where(
            CbamProductEmbeddedEmissionsCurrent.organization_id == organization_id,
            CbamProductEmbeddedEmissionsCurrent.reporting_period_binding_id == binding_id,
            CbamProductEmbeddedEmissionsCurrent.methodology_code == DEFAULT_METHODOLOGY_CODE,
        )
    ).scalar_one_or_none()
    pee_products: list[dict[str, Any]] = []
    pee_result_id = pee_pointer.current_result_id if pee_pointer else None
    expected_outputs: dict[tuple[str, str], Any] = {}
    if pee_result_id is not None:
        result = db.get(CbamProductEmbeddedEmissionsResult, pee_result_id)
        product_rows = list(
            db.execute(
                select(CbamProductEmbeddedEmissionsProduct)
                .where(CbamProductEmbeddedEmissionsProduct.result_id == pee_result_id)
                .order_by(CbamProductEmbeddedEmissionsProduct.id.asc())
            )
            .scalars()
            .all()
        )
        product_rows = sorted(product_rows, key=lambda r: r.id)
        for idx, pee_row in enumerate(product_rows):
            name: str | None = None
            cn: str | None = None
            for proc in process_payloads:
                if proc.get("id") and pee_row.process_id and str(pee_row.process_id) == proc["id"]:
                    name = proc["name"]
                    break
            profile_match = next(
                (p for p in ready_profiles if p.id == pee_row.product_profile_version_id),
                None,
            )
            if profile_match is not None:
                cn = profile_match.cn_normalized_code
                if name is None:
                    name = profile_match.product_name
            if name is None:
                name = pee_row.product_name
            if cn is None:
                cn = pee_row.cn_normalized_code
            steel: dict[str, Any] = {
                "reducing_agent": None,
                "steel_mill_identification_number": None,
                "percent_mn": None,
                "percent_cr": None,
                "percent_ni": None,
                "percent_other_alloys": None,
                "percent_other_materials": None,
            }
            if profile_match is not None:
                steel = {
                    "reducing_agent": profile_match.reducing_agent,
                    "steel_mill_identification_number": (
                        profile_match.steel_mill_identification_number
                    ),
                    "percent_mn": _dec(profile_match.percent_mn),
                    "percent_cr": _dec(profile_match.percent_cr),
                    "percent_ni": _dec(profile_match.percent_ni),
                    "percent_other_alloys": _dec(profile_match.percent_other_alloys),
                    "percent_other_materials": _dec(profile_match.percent_other_materials),
                }
            pee_products.append(
                {
                    "slot_index": idx,
                    "name": name or f"Product {idx + 1}",
                    "cn_code": cn,
                    "description": None,
                    # Keep Decimal strings for pee payload; expected_outputs use DB Decimals.
                    "specific_direct": str(pee_row.specific_direct),
                    "specific_indirect": str(pee_row.specific_indirect),
                    "specific_total": str(pee_row.specific_total),
                    **steel,
                }
            )
            excel_row = 10 + idx
            # Immutable PEE V2 snapshot only — never invent workbook tolerances here.
            expected_outputs[("Summary_Products", f"I{excel_row}")] = pee_row.specific_direct
            expected_outputs[("Summary_Products", f"J{excel_row}")] = pee_row.specific_indirect
            expected_outputs[("Summary_Products", f"K{excel_row}")] = pee_row.specific_total
        _ = result

    # Stationary combustion → B_EmInst fuel slots (deterministic by activity/result id).
    sc_pointers = list(
        db.execute(
            select(CbamStationaryCombustionCurrentResult).where(
                CbamStationaryCombustionCurrentResult.organization_id == organization_id,
                CbamStationaryCombustionCurrentResult.reporting_period_binding_id == binding_id,
            )
        )
        .scalars()
        .all()
    )
    sc_pointers_sorted = sorted(sc_pointers, key=lambda p: (p.activity_record_id, p.id))
    fuel_payloads: list[dict[str, Any]] = []
    for slot, pointer in enumerate(sc_pointers_sorted):
        sc_row = db.get(CbamStationaryCombustionResult, pointer.current_result_id)
        if sc_row is None:
            continue
        fuel_payloads.append(
            {
                "slot_index": slot,
                "id": str(sc_row.id),
                "activity_record_id": str(sc_row.activity_record_id),
                "monitoring_approach": "Combustion",
                "fuel_name": sc_row.fuel_name,
                "activity_amount": _dec(sc_row.activity_quantity),
                "activity_unit": sc_row.activity_unit,
                "ncv": _dec(sc_row.net_calorific_value),
                "ef": _dec(sc_row.fossil_co2_emission_factor),
                "density": _dec(sc_row.density_value),
                "density_unit": sc_row.density_unit,
                "oxidation_factor": _dec(sc_row.oxidation_factor),
            }
        )

    usage = CapacityUsage(
        installations=1,
        goods=len(goods),
        processes=len(process_payloads),
        precursors=len(precursor_payloads),
        max_process_product_uses=max_process_uses,
        max_precursor_product_uses=max_precursor_uses,
        fuel_activities=len(fuel_payloads),
    )
    overflow = assess_capacity(usage)
    if overflow:
        from ecotrace.core.exceptions import BusinessRuleError

        raise BusinessRuleError(
            "Official SEE capacity exceeded.",
            details=[{"code": code} for code in overflow],
        )

    start = getattr(period, "start_date", None) or getattr(period, "period_start", None)
    end = getattr(period, "end_date", None) or getattr(period, "period_end", None)
    fp_payload = {
        "organizationId": str(organization_id),
        "bindingId": str(binding_id),
        "peeResultId": str(pee_result_id) if pee_result_id else None,
        "deaResultId": str(dea_pointer.current_result_id) if dea_pointer else None,
        "ieaResultId": str(iea_pointer.current_result_id) if iea_pointer else None,
        "processIds": [p["id"] for p in process_payloads],
        "precursorIds": [p["id"] for p in precursor_payloads],
        "fuelIds": [p["id"] for p in fuel_payloads],
        "peeProductIds": [str(p.get("slot_index")) for p in pee_products],
    }

    return OfficialSeeExportContext(
        organization_id=organization_id,
        organization_name=org_name,
        binding_id=binding_id,
        installation=installation,
        reporting_period={
            "start_date": start.isoformat() if isinstance(start, date) else start,
            "end_date": end.isoformat() if isinstance(end, date) else end,
            "label": f"{start}_{end}" if start and end else str(binding_id),
        },
        goods=goods,
        processes=process_payloads,
        precursors=precursor_payloads,
        fuels=fuel_payloads,
        pee_products=pee_products,
        pee_result_id=pee_result_id,
        dea_result_id=dea_pointer.current_result_id if dea_pointer else None,
        iea_result_id=iea_pointer.current_result_id if iea_pointer else None,
        process_ids=[uuid.UUID(p["id"]) for p in process_payloads],
        precursor_ids=[uuid.UUID(p["id"]) for p in precursor_payloads],
        capacity_usage=usage,
        expected_outputs=expected_outputs,
        source_fingerprint=_fingerprint(fp_payload),
    )


def resolve_source(ctx: OfficialSeeExportContext, source: str) -> Any:
    """Resolve a manifest ``source`` path against the snapshot context."""
    if not source or source.startswith("example") or source.startswith("constant"):
        if source == "constant.blank":
            return None
        if source == "constant.COMBUSTION":
            return "Combustion"
        return None
    if source == "organization.name":
        return ctx.organization_name
    if source == "installation.name":
        return ctx.installation.get("name")
    if source == "installation.address":
        return ctx.installation.get("address")
    if source == "installation.city":
        return ctx.installation.get("city")
    if source == "installation.country_code":
        return ctx.installation.get("country_code")
    if source == "installation.postal_code":
        return ctx.installation.get("postal_code")
    if source == "installation.unlocode":
        return ctx.installation.get("unlocode")
    if source == "installation.contact_name":
        return ctx.installation.get("contact_name")
    if source == "installation.email":
        return ctx.installation.get("email")
    if source == "installation.telephone":
        return ctx.installation.get("telephone")
    if source == "reporting_period.start_date":
        return ctx.reporting_period.get("start_date")
    if source == "reporting_period.end_date":
        return ctx.reporting_period.get("end_date")

    # Indexed paths: goods[i].goods_type, processes[i].*, precursors[i].*, pee.products[i].*
    import re

    m = re.fullmatch(r"goods\[(\d+)\]\.(\w+)", source)
    if m:
        idx, key = int(m.group(1)), m.group(2)
        if idx < len(ctx.goods):
            return ctx.goods[idx].get(key)
        return None

    m = re.fullmatch(r"processes\[(\d+)\]\.(.+)", source)
    if m:
        idx = int(m.group(1))
        path = m.group(2)
        if idx >= len(ctx.processes):
            return None
        proc = ctx.processes[idx]
        use_m = re.fullmatch(r"product_uses\[(\d+)\]\.(\w+)", path)
        if use_m:
            uidx, ukey = int(use_m.group(1)), use_m.group(2)
            uses = proc.get("product_uses") or []
            if uidx < len(uses):
                return uses[uidx].get(ukey)
            return None
        return proc.get(path)

    m = re.fullmatch(r"precursors\[(\d+)\]\.(.+)", source)
    if m:
        idx = int(m.group(1))
        path = m.group(2)
        if idx >= len(ctx.precursors):
            return None
        prec = ctx.precursors[idx]
        route_m = re.fullmatch(r"routes\[(\d+)\]", path)
        if route_m:
            ridx = int(route_m.group(1))
            routes = prec.get("routes") or []
            if ridx < len(routes):
                return routes[ridx]
            return None
        use_m = re.fullmatch(r"product_uses\[(\d+)\]\.(\w+)", path)
        if use_m:
            uidx, ukey = int(use_m.group(1)), use_m.group(2)
            uses = prec.get("product_uses") or []
            if uidx < len(uses):
                return uses[uidx].get(ukey)
            return None
        return prec.get(path)

    m = re.fullmatch(r"pee\.products\[(\d+)\]\.(\w+)", source)
    if m:
        idx, key = int(m.group(1)), m.group(2)
        if idx < len(ctx.pee_products):
            return ctx.pee_products[idx].get(key)
        return None

    m = re.fullmatch(r"fuels\[(\d+)\]\.(\w+)", source)
    if m:
        idx, key = int(m.group(1)), m.group(2)
        if idx < len(ctx.fuels):
            return ctx.fuels[idx].get(key)
        return None

    return None
