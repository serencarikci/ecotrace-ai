"""Idempotency fingerprint for product embedded-emissions roll-up executions.

The fingerprint covers every material input of the roll-up. Display-only fields
(names, identifiers, notes, CN display labels) are deliberately excluded so that a
label edit never invalidates an execution.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from decimal import Decimal

from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    METHODOLOGY_VERSION_BY_CODE,
    WORKBOOK_FILENAME,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    canonicalize_decimal,
    canonicalize_optional_str,
)


def _bool(value: bool | None) -> str:
    if value is None:
        return "-"
    return "1" if value else "0"


def _uuid(value: uuid.UUID | None) -> str:
    return "-" if value is None else str(value)


@dataclass(frozen=True, slots=True)
class PrecursorContributionFingerprint:
    precursor_id: uuid.UUID
    precursor_row_version: int
    data_source_mode: str
    specific_direct: Decimal | None
    specific_indirect: Decimal | None
    value_source: str | None
    default_dataset_id: uuid.UUID | None
    default_value_id: uuid.UUID | None
    product_use_id: uuid.UUID
    product_use_row_version: int
    product_use_quantity: Decimal
    product_use_unit: str
    target_product_profile_version_id: uuid.UUID

    def canonical(self) -> str:
        return (
            f"prec:{self.precursor_id}|{self.precursor_row_version}|"
            f"{canonicalize_optional_str(self.data_source_mode)}|"
            f"{canonicalize_decimal(self.specific_direct)}|"
            f"{canonicalize_decimal(self.specific_indirect)}|"
            f"{canonicalize_optional_str(self.value_source)}|"
            f"{_uuid(self.default_dataset_id)}|{_uuid(self.default_value_id)}|"
            f"use:{self.product_use_id}|{self.product_use_row_version}|"
            f"{canonicalize_decimal(self.product_use_quantity)}|"
            f"{canonicalize_optional_str(self.product_use_unit)}|"
            f"target:{self.target_product_profile_version_id}"
        )


@dataclass(frozen=True, slots=True)
class InternalFlowFingerprint:
    """Phase 10D internal product-flow edge feeding the Leontief matrix."""

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

    def canonical(self) -> str:
        return (
            f"flow:{self.product_use_id}|{self.product_use_row_version}|"
            f"supplier:{self.supplier_process_id}|{self.supplier_process_row_version}|"
            f"{self.supplier_product_profile_version_id}|"
            f"consumer:{self.consumer_product_profile_version_id}|"
            f"{canonicalize_decimal(self.product_use_quantity)}|"
            f"{canonicalize_optional_str(self.product_use_unit)}|"
            f"{canonicalize_decimal(self.quantity_tonnes)}|"
            f"{canonicalize_decimal(self.consumer_denominator_tonnes)}"
        )


@dataclass(frozen=True, slots=True)
class ExportedElectricityFingerprint:
    """Phase 10D process-level T72 inputs (workbook L71/L72) plus reconciliation."""

    has_exported_electricity: bool | None
    quantity_mwh: Decimal | None
    emission_factor: Decimal | None
    provenance: str | None
    installation_facility_exported_mwh: Decimal | None
    installation_process_exported_mwh: Decimal | None
    reconciliation_status: str

    def canonical(self) -> str:
        return (
            f"expelec:{_bool(self.has_exported_electricity)}|"
            f"{canonicalize_decimal(self.quantity_mwh)}|"
            f"{canonicalize_decimal(self.emission_factor)}|"
            f"{canonicalize_optional_str(self.provenance)}|"
            f"{canonicalize_decimal(self.installation_facility_exported_mwh)}|"
            f"{canonicalize_decimal(self.installation_process_exported_mwh)}|"
            f"{canonicalize_optional_str(self.reconciliation_status)}"
        )


@dataclass(frozen=True, slots=True)
class ProductFingerprint:
    product_profile_version_id: uuid.UUID
    profile_version: int
    process_id: uuid.UUID
    process_row_version: int
    produced_quantity: Decimal | None
    produced_quantity_unit: str | None
    denominator_tonnes: Decimal
    has_measurable_heat: bool | None
    heat_attributed_tco2e: Decimal | None
    has_waste_gas: bool | None
    waste_gas_attributed_tco2e: Decimal | None
    exported_electricity_direct_tco2e: Decimal
    dea_result_id: uuid.UUID | None
    dea_product_value: Decimal
    iea_result_id: uuid.UUID | None
    iea_product_value: Decimal
    production_records: tuple[tuple[uuid.UUID, Decimal, str], ...]
    contributions: tuple[PrecursorContributionFingerprint, ...]
    # V2 only; ``None`` / empty keeps a V1 canonical string byte-identical to Phase 10C.
    exported_electricity: ExportedElectricityFingerprint | None = None
    internal_flows: tuple[InternalFlowFingerprint, ...] = ()

    def canonical(self) -> str:
        parts = [
            f"product:{self.product_profile_version_id}|{self.profile_version}",
            f"process:{self.process_id}|{self.process_row_version}|"
            f"{canonicalize_decimal(self.produced_quantity)}|"
            f"{canonicalize_optional_str(self.produced_quantity_unit)}|"
            f"{canonicalize_decimal(self.denominator_tonnes)}",
            f"heat:{_bool(self.has_measurable_heat)}|"
            f"{canonicalize_decimal(self.heat_attributed_tco2e)}",
            f"waste:{_bool(self.has_waste_gas)}|"
            f"{canonicalize_decimal(self.waste_gas_attributed_tco2e)}",
            f"expelec:{canonicalize_decimal(self.exported_electricity_direct_tco2e)}",
            f"dea:{_uuid(self.dea_result_id)}|{canonicalize_decimal(self.dea_product_value)}",
            f"iea:{_uuid(self.iea_result_id)}|{canonicalize_decimal(self.iea_product_value)}",
        ]
        for record_id, quantity, unit in sorted(self.production_records, key=lambda t: str(t[0])):
            parts.append(
                f"pr:{record_id}|{canonicalize_decimal(quantity)}|{canonicalize_optional_str(unit)}"
            )
        for contribution in sorted(self.contributions, key=lambda c: str(c.product_use_id)):
            parts.append(contribution.canonical())
        if self.exported_electricity is not None:
            parts.append(self.exported_electricity.canonical())
        for flow in sorted(self.internal_flows, key=lambda item: str(item.product_use_id)):
            parts.append(flow.canonical())
        return "||".join(parts)


def build_product_embedded_emissions_fingerprint(
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    dea_result_id: uuid.UUID | None,
    iea_result_id: uuid.UUID | None,
    products: list[ProductFingerprint],
    methodology_code: str = METHODOLOGY_CODE,
) -> str:
    methodology_version = METHODOLOGY_VERSION_BY_CODE.get(methodology_code, METHODOLOGY_VERSION)
    parts: list[str] = [
        str(organization_id),
        str(binding_id),
        methodology_code,
        methodology_version,
        WORKBOOK_FILENAME,
        WORKBOOK_SHA256,
        f"deaCurrent:{_uuid(dea_result_id)}",
        f"ieaCurrent:{_uuid(iea_result_id)}",
    ]
    for product in sorted(products, key=lambda p: str(p.product_profile_version_id)):
        parts.append(product.canonical())
    payload = "|||".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
