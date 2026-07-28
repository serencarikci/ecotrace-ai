from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import PlainTextResponse
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.data_imports.application import import_service
from ecotrace.modules.data_imports.application.import_service import CSV_TEMPLATE, ImportJobResponse, ImportJobRowResponse
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Imports'])

@router.get('/organizations/{organization_id}/imports/activity-records/template', response_class=PlainTextResponse)
def download_template(organization_id: UUID, db: DbSession, user: CurrentUser) -> PlainTextResponse:
    ensure_org_access(db, user, organization_id)
    return PlainTextResponse(content=CSV_TEMPLATE, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="activity-records-template.csv"'})

@router.post('/organizations/{organization_id}/imports/activity-records', response_model=ImportJobResponse, status_code=201)
async def upload_import(organization_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, file: UploadFile=File(...)) -> ImportJobResponse:
    data = await file.read()
    return import_service.upload_csv(db, user, organization_id, file_name=file.filename or 'import.csv', data=data, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/imports/activity-records', response_model=Page[ImportJobResponse])
def list_imports(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), status: str | None=None) -> Page[ImportJobResponse]:
    return import_service.list_jobs(db, user, organization_id, page=page, page_size=page_size, status=status)

@router.get('/organizations/{organization_id}/imports/activity-records/{import_job_id}', response_model=ImportJobResponse)
def get_import(organization_id: UUID, import_job_id: UUID, db: DbSession, user: CurrentUser) -> ImportJobResponse:
    ensure_org_access(db, user, organization_id)
    return ImportJobResponse.model_validate(import_service.get_job(db, organization_id, import_job_id))

@router.get('/organizations/{organization_id}/imports/activity-records/{import_job_id}/rows', response_model=Page[ImportJobRowResponse])
def list_import_rows(organization_id: UUID, import_job_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), validation_status: str | None=Query(None, alias='validationStatus')) -> Page[ImportJobRowResponse]:
    return import_service.list_rows(db, user, organization_id, import_job_id, page=page, page_size=page_size, validation_status=validation_status)

@router.post('/organizations/{organization_id}/imports/activity-records/{import_job_id}/validate', response_model=ImportJobResponse)
def validate_import(organization_id: UUID, import_job_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ImportJobResponse:
    return import_service.validate_job(db, user, organization_id, import_job_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/imports/activity-records/{import_job_id}/execute', response_model=ImportJobResponse)
def execute_import(organization_id: UUID, import_job_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ImportJobResponse:
    return import_service.execute_job(db, user, organization_id, import_job_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
