from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import Response
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.digital_product_passport.application import passport_service
from ecotrace.modules.digital_product_passport.application.passport_service import DocumentResponse, PassportCreate, PassportResponse, PassportUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Digital Product Passports'])
public_router = APIRouter(tags=['Public Passports'])

@router.get('/organizations/{organization_id}/digital-product-passports', response_model=Page[PassportResponse])
def list_passports(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), search: str | None=None, status: str | None=None, product_id: UUID | None=Query(None, alias='productId')) -> Page[PassportResponse]:
    return passport_service.list_passports(db, user, organization_id, page=page, page_size=page_size, search=search, status=status, product_id=product_id)

@router.post('/organizations/{organization_id}/digital-product-passports', response_model=PassportResponse, status_code=201)
def create_passport(organization_id: UUID, payload: PassportCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.create_passport(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/digital-product-passports/{passport_id}', response_model=PassportResponse)
def get_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser) -> PassportResponse:
    return passport_service.get_passport_detail(db, user, organization_id, passport_id)

@router.patch('/organizations/{organization_id}/digital-product-passports/{passport_id}', response_model=PassportResponse)
def update_passport(organization_id: UUID, passport_id: UUID, payload: PassportUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.update_passport(db, user, organization_id, passport_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/submit-review', response_model=PassportResponse)
def submit_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.submit_passport(db, user, organization_id, passport_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/publish', response_model=PassportResponse)
def publish_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.publish_passport(db, user, organization_id, passport_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/clone-version', response_model=PassportResponse)
def clone_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.clone_passport_version(db, user, organization_id, passport_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/revoke', response_model=PassportResponse)
def revoke_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.revoke_passport(db, user, organization_id, passport_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/archive', response_model=PassportResponse)
def archive_passport(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PassportResponse:
    return passport_service.archive_passport(db, user, organization_id, passport_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/digital-product-passports/{passport_id}/qr')
def passport_qr(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    return passport_service.get_passport_qr(db, user, organization_id, passport_id)

@router.post('/organizations/{organization_id}/digital-product-passports/{passport_id}/documents', response_model=DocumentResponse, status_code=201)
async def upload_document(organization_id: UUID, passport_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, file: UploadFile=File(...), document_type: str=Form(..., alias='documentType'), title: str=Form(...), is_public: bool=Form(False, alias='isPublic')) -> DocumentResponse:
    content = await file.read()
    return passport_service.upload_document(db, user, organization_id, passport_id, document_type=document_type, title=title, file_name=file.filename or 'upload.bin', content_type=file.content_type, content=content, is_public=is_public, request_id=request_id, ip_address=ip, user_agent=user_agent)

@public_router.get('/public/passports/{public_slug}')
def public_passport(public_slug: str, db: DbSession) -> dict[str, Any]:
    return passport_service.get_public_passport(db, public_slug)

@public_router.get('/public/passports/{public_slug}/documents')
def public_documents(public_slug: str, db: DbSession) -> list[dict[str, Any]]:
    return passport_service.list_public_documents(db, public_slug)

@public_router.get('/public/passports/{public_slug}/documents/{document_id}')
def public_document(public_slug: str, document_id: UUID, db: DbSession) -> Response:
    doc, content = passport_service.get_public_document_bytes(db, public_slug, document_id)
    return Response(content=content, media_type=doc.content_type, headers={'Content-Disposition': f'attachment; filename="{doc.original_file_name}"'})

@public_router.get('/public/passports/{public_slug}/qr')
def public_qr(public_slug: str, db: DbSession) -> dict[str, Any]:
    return passport_service.get_public_qr(db, public_slug)
