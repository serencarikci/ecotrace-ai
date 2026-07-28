from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.lifecycle_assessment.application import lca_service
from ecotrace.modules.lifecycle_assessment.application.lca_service import BoundaryResponse, BoundaryUpsert, DataQualityCreate, DataQualityResponse, FunctionalUnitResponse, FunctionalUnitUpsert, InventoryCreate, InventoryResponse, RunResponse, StudyCreate, StudyResponse, StudyUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['LCA Studies'])

@router.get('/organizations/{organization_id}/lca-studies', response_model=Page[StudyResponse])
def list_studies(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), search: str | None=None, status: str | None=None, study_type: str | None=Query(None, alias='studyType'), product_id: UUID | None=Query(None, alias='productId')) -> Page[StudyResponse]:
    return lca_service.list_studies(db, user, organization_id, page=page, page_size=page_size, search=search, status=status, study_type=study_type, product_id=product_id)

@router.post('/organizations/{organization_id}/lca-studies', response_model=StudyResponse, status_code=201)
def create_study(organization_id: UUID, payload: StudyCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> StudyResponse:
    return lca_service.create_study(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/lca-studies/{study_id}', response_model=StudyResponse)
def get_study(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser) -> StudyResponse:
    return lca_service.get_study_detail(db, user, organization_id, study_id)

@router.get('/organizations/{organization_id}/lca-studies/{study_id}/scope')
def get_scope(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    return lca_service.get_study_scope(db, user, organization_id, study_id)

@router.patch('/organizations/{organization_id}/lca-studies/{study_id}', response_model=StudyResponse)
def update_study(organization_id: UUID, study_id: UUID, payload: StudyUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> StudyResponse:
    return lca_service.update_study(db, user, organization_id, study_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.put('/organizations/{organization_id}/lca-studies/{study_id}/functional-unit', response_model=FunctionalUnitResponse)
def upsert_fu(organization_id: UUID, study_id: UUID, payload: FunctionalUnitUpsert, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FunctionalUnitResponse:
    return lca_service.upsert_functional_unit(db, user, organization_id, study_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.put('/organizations/{organization_id}/lca-studies/{study_id}/system-boundary', response_model=BoundaryResponse)
def upsert_boundary(organization_id: UUID, study_id: UUID, payload: BoundaryUpsert, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BoundaryResponse:
    return lca_service.upsert_boundary(db, user, organization_id, study_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/lca-studies/{study_id}/inventory-inputs', response_model=Page[InventoryResponse])
def list_inventory(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(50, ge=1, le=200, alias='pageSize'), lifecycle_stage: str | None=Query(None, alias='lifecycleStage')) -> Page[InventoryResponse]:
    return lca_service.list_inventory(db, user, organization_id, study_id, page=page, page_size=page_size, lifecycle_stage=lifecycle_stage)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/inventory-inputs', response_model=InventoryResponse, status_code=201)
def add_inventory(organization_id: UUID, study_id: UUID, payload: InventoryCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> InventoryResponse:
    return lca_service.add_inventory(db, user, organization_id, study_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/validate')
def validate_study(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> dict[str, Any]:
    return lca_service.validate_study(db, user, organization_id, study_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/calculate', response_model=RunResponse)
def calculate(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, partial: bool=Query(False)) -> RunResponse:
    return lca_service.calculate_study(db, user, organization_id, study_id, request_id=request_id, ip_address=ip, user_agent=user_agent, partial=partial)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/recalculate', response_model=RunResponse)
def recalculate(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> RunResponse:
    return lca_service.recalculate_study(db, user, organization_id, study_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/submit-review', response_model=StudyResponse)
def submit_review(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> StudyResponse:
    return lca_service.submit_study_review(db, user, organization_id, study_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/approve', response_model=StudyResponse)
def approve(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> StudyResponse:
    return lca_service.approve_study(db, user, organization_id, study_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/lca-studies/{study_id}/runs', response_model=list[RunResponse])
def list_runs(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser) -> list[RunResponse]:
    return lca_service.list_runs(db, user, organization_id, study_id)

@router.get('/organizations/{organization_id}/lca-studies/{study_id}/results')
def results(organization_id: UUID, study_id: UUID, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    return lca_service.get_results(db, user, organization_id, study_id)

@router.post('/organizations/{organization_id}/lca-studies/{study_id}/data-quality', response_model=DataQualityResponse, status_code=201)
def create_dq(organization_id: UUID, study_id: UUID, payload: DataQualityCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> DataQualityResponse:
    return lca_service.create_data_quality(db, user, organization_id, study_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)
