from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.activity_data.application.activity_service import get_record
from ecotrace.modules.activity_data.infrastructure.models import ActivityAttachment
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_write_operational
from ecotrace.shared.domain.schemas import CamelModel

MIME_BY_EXT: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "csv": {"text/csv", "application/csv", "text/plain"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
    "png": {"image/png"},
    "jpeg": {"image/jpeg"},
    "jpg": {"image/jpeg"},
}

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class AttachmentResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    activity_record_id: uuid.UUID
    original_file_name: str
    stored_file_name: str
    content_type: str
    file_size: int
    checksum: str
    uploaded_by_user_id: uuid.UUID | None
    created_at: datetime
    is_deleted: bool


def sanitize_original_name(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    cleaned = SAFE_NAME_RE.sub("_", base).strip("._")

    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    if not cleaned or cleaned in {".", ".."}:
        raise ValidationAppError("Invalid file name.")
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    return cleaned


def _extension(file_name: str) -> str:
    ext = Path(file_name).suffix.lower().lstrip(".")
    if ext == "jpg":
        return "jpg"
    return ext


def _validate_upload(file_name: str, content_type: str | None, size: int) -> tuple[str, str]:
    settings = get_settings()
    max_bytes = settings.max_attachment_size_mb * 1024 * 1024
    if size <= 0:
        raise ValidationAppError("Empty files are not allowed.")
    if size > max_bytes:
        raise ValidationAppError(
            f"File exceeds maximum size of {settings.max_attachment_size_mb} MB."
        )
    safe_name = sanitize_original_name(file_name)
    ext = _extension(safe_name)
    allowed = {item.lower() for item in settings.allowed_attachment_types}
    if ext not in allowed:
        raise ValidationAppError(
            "File type is not allowed.",
            details=[{"field": "file", "message": f"Extension '.{ext}' is not permitted."}],
        )
    expected = MIME_BY_EXT.get(ext, set())
    resolved_type = (content_type or "").split(";")[0].strip().lower() or next(iter(expected), "")
    allowed_mime = set(expected)
    if ext == "xlsx":
        allowed_mime.add("application/octet-stream")
    if expected and resolved_type and resolved_type not in allowed_mime:
        raise ValidationAppError(
            "Content type does not match the file extension.",
            details=[
                {
                    "field": "file",
                    "message": f"Got '{resolved_type}' for '.{ext}'.",
                }
            ],
        )
    return safe_name, resolved_type or f"application/{ext}"


def _org_storage_dir(organization_id: uuid.UUID) -> Path:
    settings = get_settings()
    root = Path(settings.attachment_storage_path).resolve()
    org_dir = (root / str(organization_id)).resolve()
    if not str(org_dir).startswith(str(root)):
        raise ValidationAppError("Invalid storage path.")
    org_dir.mkdir(parents=True, exist_ok=True)
    return org_dir


def get_attachment(
    db: Session,
    organization_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    attachment_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> ActivityAttachment:
    row = db.get(ActivityAttachment, attachment_id)
    if (
        row is None
        or row.organization_id != organization_id
        or row.activity_record_id != activity_record_id
        or (row.is_deleted and not include_deleted)
    ):
        raise NotFoundError("Attachment not found.")
    return row


def list_attachments(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    activity_record_id: uuid.UUID,
) -> list[AttachmentResponse]:
    ensure_org_access(db, user, organization_id)
    get_record(db, organization_id, activity_record_id)
    rows = list(
        db.execute(
            select(ActivityAttachment)
            .where(
                ActivityAttachment.organization_id == organization_id,
                ActivityAttachment.activity_record_id == activity_record_id,
                ActivityAttachment.is_deleted.is_(False),
            )
            .order_by(ActivityAttachment.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [AttachmentResponse.model_validate(r) for r in rows]


def upload_attachment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    *,
    file_name: str,
    content_type: str | None,
    data: bytes,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AttachmentResponse:
    require_write_operational(db, user, organization_id)
    get_record(db, organization_id, activity_record_id)
    safe_name, resolved_type = _validate_upload(file_name, content_type, len(data))
    checksum = hashlib.sha256(data).hexdigest()
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    org_dir = _org_storage_dir(organization_id)
    target = (org_dir / stored_name).resolve()
    if not str(target).startswith(str(org_dir)):
        raise ValidationAppError("Invalid storage path.")
    target.write_bytes(data)
    relative_path = f"{organization_id}/{stored_name}"
    row = ActivityAttachment(
        organization_id=organization_id,
        activity_record_id=activity_record_id,
        original_file_name=safe_name,
        stored_file_name=stored_name,
        content_type=resolved_type,
        file_size=len(data),
        storage_path=relative_path,
        checksum=checksum,
        uploaded_by_user_id=user.id,
        is_deleted=False,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="attachment.uploaded",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_attachment",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "activityRecordId": str(activity_record_id),
            "fileName": safe_name,
            "fileSize": len(data),
            "checksum": checksum,
        },
    )
    db.commit()
    db.refresh(row)
    return AttachmentResponse.model_validate(row)


def resolve_attachment_path(attachment: ActivityAttachment) -> Path:
    settings = get_settings()
    root = Path(settings.attachment_storage_path).resolve()
    path = (root / attachment.storage_path).resolve()
    if not str(path).startswith(str(root)):
        raise ValidationAppError("Invalid storage path.")
    if not path.is_file():
        raise NotFoundError("Attachment file is missing.")
    return path


def download_attachment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> tuple[ActivityAttachment, Path]:
    ensure_org_access(db, user, organization_id)
    get_record(db, organization_id, activity_record_id)
    attachment = get_attachment(db, organization_id, activity_record_id, attachment_id)
    return attachment, resolve_attachment_path(attachment)


def delete_attachment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    attachment_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    require_write_operational(db, user, organization_id)
    get_record(db, organization_id, activity_record_id)
    attachment = get_attachment(db, organization_id, activity_record_id, attachment_id)
    attachment.is_deleted = True
    write_audit_log(
        db,
        action="attachment.deleted",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_attachment",
        entity_id=str(attachment.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fileName": attachment.original_file_name},
    )
    db.commit()
