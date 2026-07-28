from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.activity_data.application import attachment_service
from ecotrace.modules.activity_data.application.attachment_service import AttachmentResponse
router = APIRouter(tags=['Attachments'])

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/attachments', response_model=AttachmentResponse, status_code=201)
async def upload_attachment(organization_id: UUID, activity_record_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader, file: UploadFile=File(...)) -> AttachmentResponse:
    data = await file.read()
    return attachment_service.upload_attachment(db, user, organization_id, activity_record_id, file_name=file.filename or 'upload.bin', content_type=file.content_type, data=data, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/activity-records/{activity_record_id}/attachments', response_model=list[AttachmentResponse])
def list_attachments(organization_id: UUID, activity_record_id: UUID, db: DbSession, user: CurrentUser) -> list[AttachmentResponse]:
    return attachment_service.list_attachments(db, user, organization_id, activity_record_id)

@router.get('/organizations/{organization_id}/activity-records/{activity_record_id}/attachments/{attachment_id}/download')
def download_attachment(organization_id: UUID, activity_record_id: UUID, attachment_id: UUID, db: DbSession, user: CurrentUser) -> FileResponse:
    attachment, path = attachment_service.download_attachment(db, user, organization_id, activity_record_id, attachment_id)
    return FileResponse(path=path, media_type=attachment.content_type, filename=attachment.original_file_name)

@router.delete('/organizations/{organization_id}/activity-records/{activity_record_id}/attachments/{attachment_id}', status_code=204)
def delete_attachment(organization_id: UUID, activity_record_id: UUID, attachment_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> Response:
    attachment_service.delete_attachment(db, user, organization_id, activity_record_id, attachment_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
    return Response(status_code=204)
