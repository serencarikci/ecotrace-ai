from __future__ import annotations
from datetime import date
from uuid import UUID
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import PlainTextResponse
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.emission_factors.application import factor_service, import_service
from ecotrace.modules.emission_factors.application.factor_service import FactorCreate, FactorResponse, FactorUpdate
from ecotrace.modules.emission_factors.application.import_service import FactorImportResult
from ecotrace.shared.domain.schemas import CamelModel, Page
router = APIRouter(prefix='/emission-factors', tags=['Emission Factors'])

class ActivateRequest(CamelModel):
    supersede_previous: bool = True

@router.get('', response_model=Page[FactorResponse])
def list_factors(db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), source_id: UUID | None=Query(None, alias='sourceId'), activity_type_id: UUID | None=Query(None, alias='activityTypeId'), scope: str | None=None, category: str | None=None, geography_code: str | None=Query(None, alias='geographyCode'), status: str | None=None, valid_on: date | None=Query(None, alias='validOn'), search: str | None=None, include_drafts: bool=Query(False, alias='includeDrafts')) -> Page[FactorResponse]:
    return factor_service.list_factors(db, user, page=page, page_size=page_size, source_id=source_id, activity_type_id=activity_type_id, scope=scope, category=category, geography_code=geography_code, status=status, valid_on=valid_on, search=search, include_drafts=include_drafts)

@router.post('', response_model=FactorResponse, status_code=201)
def create_factor(payload: FactorCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorResponse:
    return factor_service.create_draft(db, user, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/import/template')
def download_template() -> PlainTextResponse:
    return PlainTextResponse(import_service.get_template(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=emission-factors-template.csv'})

@router.post('/import/validate', response_model=FactorImportResult)
async def validate_import(db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, file: UploadFile=File(...)) -> FactorImportResult:
    content = await file.read()
    return import_service.validate_and_import(db, user, filename=file.filename or 'factors.csv', content=content, execute=False, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/import/execute', response_model=FactorImportResult)
async def execute_import(db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, file: UploadFile=File(...)) -> FactorImportResult:
    content = await file.read()
    return import_service.validate_and_import(db, user, filename=file.filename or 'factors.csv', content=content, execute=True, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/{factor_id}', response_model=FactorResponse)
def get_factor(factor_id: UUID, db: DbSession, user: CurrentUser) -> FactorResponse:
    return factor_service.get_factor(db, user, factor_id)

@router.patch('/{factor_id}', response_model=FactorResponse)
def update_factor(factor_id: UUID, payload: FactorUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorResponse:
    return factor_service.update_draft(db, user, factor_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/{factor_id}/activate', response_model=FactorResponse)
def activate_factor(factor_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, payload: ActivateRequest | None=None) -> FactorResponse:
    return factor_service.activate_factor(db, user, factor_id, supersede_previous=payload.supersede_previous if payload else True, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/{factor_id}/supersede', response_model=FactorResponse)
def supersede_factor(factor_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorResponse:
    return factor_service.supersede_factor(db, user, factor_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/{factor_id}/archive', response_model=FactorResponse)
def archive_factor(factor_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorResponse:
    return factor_service.archive_factor(db, user, factor_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/{factor_id}/clone-version', response_model=FactorResponse, status_code=201)
def clone_version(factor_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorResponse:
    return factor_service.clone_version(db, user, factor_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/{factor_id}/versions', response_model=list[FactorResponse])
def list_versions(factor_id: UUID, db: DbSession, user: CurrentUser) -> list[FactorResponse]:
    return factor_service.list_versions(db, user, factor_id)
