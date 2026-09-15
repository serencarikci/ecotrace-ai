from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.infrastructure.models import CbamFactorDefinition, CbamReferenceSource

PLATFORM_SOURCES: tuple[dict[str, str | None], ...] = (
    {
        "id": "a1000000-0000-4000-8000-000000000001",
        "code": "IPCC",
        "name": "IPCC",
        "source_type": "STANDARD_REFERENCE",
        "publisher": "IPCC",
        "description": "Platform source metadata only. No numerical factors are seeded.",
    },
    {
        "id": "a1000000-0000-4000-8000-000000000002",
        "code": "DEFRA",
        "name": "DEFRA",
        "source_type": "STANDARD_REFERENCE",
        "publisher": "DEFRA",
        "description": "Platform source metadata only. No numerical factors are seeded.",
    },
    {
        "id": "a1000000-0000-4000-8000-000000000003",
        "code": "EPA",
        "name": "EPA",
        "source_type": "STANDARD_REFERENCE",
        "publisher": "EPA",
        "description": "Platform source metadata only. No numerical factors are seeded.",
    },
    {
        "id": "a1000000-0000-4000-8000-000000000004",
        "code": "PRIMARY_MEASUREMENT",
        "name": "Primary measurement",
        "source_type": "PRIMARY_MEASUREMENT",
        "publisher": None,
        "description": "Customer/supplier measured value metadata label.",
    },
    {
        "id": "a1000000-0000-4000-8000-000000000005",
        "code": "SUPPLIER",
        "name": "Supplier declaration",
        "source_type": "SUPPLIER_DECLARATION",
        "publisher": None,
        "description": "Supplier-declared value metadata label.",
    },
    {
        "id": "a1000000-0000-4000-8000-000000000006",
        "code": "MANUAL_APPROVED_REFERENCE",
        "name": "Manual approved reference",
        "source_type": "MANUAL_APPROVED",
        "publisher": None,
        "description": "Manually approved organization/platform reference metadata label.",
    },
)

PLATFORM_DEFINITIONS: tuple[dict[str, str | None], ...] = (
    {
        "id": "b1000000-0000-4000-8000-000000000001",
        "code": "NET_CALORIFIC_VALUE",
        "name": "Net calorific value",
        "factor_category": "ACTIVITY_PROPERTY",
        "property_code": "NET_CALORIFIC_VALUE",
        "description": "Activity property definition. No numerical defaults are seeded.",
    },
    {
        "id": "b1000000-0000-4000-8000-000000000002",
        "code": "GENERIC_EMISSION_FACTOR",
        "name": "Generic emission factor (metadata)",
        "factor_category": "EMISSION_FACTOR",
        "property_code": None,
        "description": "Placeholder emission-factor definition. No numerical factors are seeded.",
    },
    {
        "id": "b1000000-0000-4000-8000-000000000003",
        "code": "SUPPLIER_EMBEDDED_EMISSION",
        "name": "Supplier embedded emission declaration",
        "factor_category": "EMBEDDED_EMISSION_FACTOR",
        "property_code": None,
        "description": (
            "Resolves supplier-declared embedded emission fields on purchased inputs. "
            "No numerical defaults are seeded."
        ),
    },
    {
        "id": "b1000000-0000-4000-8000-000000000004",
        "code": "ELECTRICITY_GRID_EMISSION_FACTOR",
        "name": "Purchased electricity grid emission factor",
        "factor_category": "EMISSION_FACTOR",
        "activity_type": "ELECTRICITY",
        "property_code": None,
        "description": (
            "Platform extension point for purchased-electricity indirect emissions "
            "(PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1). No numerical Turkey/default "
            "factor is seeded until authoritative provenance (source document, dataset/"
            "version, effective dates, unit) is available. Workbook example 0.439 tCO2/MWh "
            "lacks provenance in local reference files."
        ),
    },
)


def ensure_platform_factor_catalog(db: Session) -> None:
    for item in PLATFORM_SOURCES:
        code = item["code"]
        assert code is not None
        exists = db.execute(
            select(CbamReferenceSource.id).where(
                CbamReferenceSource.organization_id.is_(None),
                CbamReferenceSource.code == code,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                CbamReferenceSource(
                    id=uuid.UUID(str(item["id"])),
                    organization_id=None,
                    code=code,
                    name=item["name"] or code,
                    source_type=item["source_type"] or "OTHER",
                    publisher=item["publisher"],
                    description=item["description"],
                    status="ACTIVE",
                )
            )
    for item in PLATFORM_DEFINITIONS:
        code = item["code"]
        assert code is not None
        exists = db.execute(
            select(CbamFactorDefinition.id).where(CbamFactorDefinition.code == code)
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                CbamFactorDefinition(
                    id=uuid.UUID(str(item["id"])),
                    code=code,
                    name=item["name"] or code,
                    factor_category=item["factor_category"] or "OTHER",
                    activity_type=item.get("activity_type"),
                    property_code=item["property_code"],
                    description=item["description"],
                    status="ACTIVE",
                )
            )
    db.flush()
