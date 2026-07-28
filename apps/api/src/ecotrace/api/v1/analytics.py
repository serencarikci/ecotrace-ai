from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.modules.analytics.application import query_service
router = APIRouter(prefix='/organizations/{organization_id}/analytics', tags=['Analytics'])

@router.get('/dashboard')
def get_dashboard(organization_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), facility_id: UUID | None=Query(None, alias='facilityId'), comparison_inventory_id: UUID | None=Query(None, alias='comparisonInventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return query_service.dashboard(db, user, organization_id, inventory_id=inventory_id, facility_id=facility_id, comparison_inventory_id=comparison_inventory_id, allow_provisional=allow_provisional)

@router.get('/trends/monthly')
def get_monthly_trends(organization_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return query_service.monthly_trends(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)

@router.get('/breakdowns/{dimension}')
def get_breakdown(organization_id: UUID, dimension: str, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), facility_id: UUID | None=Query(None, alias='facilityId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return query_service.breakdown(db, user, organization_id, dimension, inventory_id=inventory_id, facility_id=facility_id, allow_provisional=allow_provisional)

@router.get('/intensity')
def get_intensity(organization_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return query_service.intensity_results(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)

@router.get('/kpis')
def get_kpis(organization_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return query_service.kpi_results(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)

@router.get('/decision-support')
def get_decision_support(organization_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> list[dict[str, Any]]:
    return query_service.recommendations(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
