from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from ecotrace.api.dependencies.auth import (
    ClientIp,
    CurrentUser,
    DbSession,
    RequestId,
    UserAgentHeader,
)
from ecotrace.modules.carbon_inventory.application import inventory_service
from ecotrace.modules.carbon_inventory.application.inventory_service import (
    CalculateRequest,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
    ItemResponse,
    RunResponse,
)
from ecotrace.shared.domain.schemas import Page

router = APIRouter(
    prefix="/organizations/{organization_id}/carbon-inventories",
    tags=["Carbon Inventories"],
)
items_router = APIRouter(
    prefix="/organizations/{organization_id}/carbon-calculation-items",
    tags=["Carbon Calculation Items"],
)


@router.get("", response_model=Page[InventoryResponse])
def list_inventories(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    reporting_period_id: UUID | None = Query(None, alias="reportingPeriodId"),
) -> Page[InventoryResponse]:
    return inventory_service.list_inventories(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        status=status,
        reporting_period_id=reporting_period_id,
    )


@router.post("", response_model=InventoryResponse, status_code=201)
def create_inventory(
    organization_id: UUID,
    payload: InventoryCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InventoryResponse:
    return inventory_service.create_inventory(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(
    organization_id: UUID, inventory_id: UUID, db: DbSession, user: CurrentUser
) -> InventoryResponse:
    return inventory_service.get_inventory(db, user, organization_id, inventory_id)


@router.patch("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(
    organization_id: UUID,
    inventory_id: UUID,
    payload: InventoryUpdate,
    db: DbSession,
    user: CurrentUser,
) -> InventoryResponse:
    return inventory_service.update_inventory(db, user, organization_id, inventory_id, payload)


@router.post("/{inventory_id}/validate")
def validate_inventory(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> dict[str, Any]:
    return inventory_service.validate_inventory(
        db,
        user,
        organization_id,
        inventory_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{inventory_id}/calculate", response_model=RunResponse)
def calculate_inventory(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    payload: CalculateRequest | None = None,
) -> RunResponse:
    return inventory_service.calculate_inventory(
        db,
        user,
        organization_id,
        inventory_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{inventory_id}/submit-review", response_model=InventoryResponse)
def submit_review(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InventoryResponse:
    return inventory_service.submit_review(
        db,
        user,
        organization_id,
        inventory_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{inventory_id}/approve", response_model=InventoryResponse)
def approve_inventory(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> InventoryResponse:
    return inventory_service.approve_inventory(
        db,
        user,
        organization_id,
        inventory_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post("/{inventory_id}/recalculate", response_model=RunResponse)
def recalculate(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    payload: CalculateRequest | None = None,
) -> RunResponse:
    return inventory_service.recalculate_inventory(
        db,
        user,
        organization_id,
        inventory_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get("/{inventory_id}/runs", response_model=list[RunResponse])
def list_runs(
    organization_id: UUID, inventory_id: UUID, db: DbSession, user: CurrentUser
) -> list[RunResponse]:
    return inventory_service.list_runs(db, user, organization_id, inventory_id)


@router.get("/{inventory_id}/items", response_model=Page[ItemResponse])
def list_items(
    organization_id: UUID,
    inventory_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    run_id: UUID | None = Query(None, alias="runId"),
    status: str | None = None,
) -> Page[ItemResponse]:
    return inventory_service.list_items(
        db,
        user,
        organization_id,
        inventory_id,
        page=page,
        page_size=page_size,
        run_id=run_id,
        status=status,
    )


@router.get("/{inventory_id}/summary")
def summary(
    organization_id: UUID, inventory_id: UUID, db: DbSession, user: CurrentUser
) -> dict[str, Any]:
    return inventory_service.inventory_summary(db, user, organization_id, inventory_id)


@items_router.get("/{item_id}")
def get_item(
    organization_id: UUID, item_id: UUID, db: DbSession, user: CurrentUser
) -> dict[str, Any]:
    return inventory_service.get_item_detail(db, user, organization_id, item_id)
