from __future__ import annotations
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.ai.providers import build_embedding_provider, build_ocr_engine
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.application.chunking import chunk_text, content_hash
from ecotrace.modules.knowledge.application.ingestion import extract_text_from_bytes, sha256_bytes, slugify
from ecotrace.modules.knowledge.infrastructure.models import KnowledgeChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeEmbedding
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_ai_manage, require_ai_read, require_ai_write
from ecotrace.shared.domain.schemas import Page, paginate

def list_documents(db: Session, user: User, organization_id: uuid.UUID, *, page: int=1, page_size: int=20, q: str | None=None, status: str | None=None, document_type: str | None=None) -> Page[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.organization_id == organization_id)
    if status:
        stmt = stmt.where(KnowledgeDocument.status == status)
    if document_type:
        stmt = stmt.where(KnowledgeDocument.document_type == document_type)
    if q:
        like = f'%{q}%'
        stmt = stmt.where(or_(KnowledgeDocument.title.ilike(like), KnowledgeDocument.slug.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(KnowledgeDocument.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    items = [_serialize_document(d) for d in rows]
    return paginate(items, page=page, page_size=page_size, total_items=total)

def get_document(db: Session, user: User, organization_id: uuid.UUID, document_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    doc = _get_document(db, organization_id, document_id)
    return _serialize_document(doc, include_versions=True)

def upload_document(db: Session, user: User, organization_id: uuid.UUID, *, title: str, file_name: str, content_type: str, content: bytes, document_type: str | None=None, tags: list[str] | None=None, publish: bool=True) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    settings = get_settings()
    max_bytes = settings.max_knowledge_document_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationAppError('Document exceeds maximum allowed size.')
    ocr = build_ocr_engine(settings)
    text, meta = extract_text_from_bytes(content=content, file_name=file_name, content_type=content_type, ocr_engine=ocr)
    _virus_scan_hook(content, file_name)
    base_slug = slugify(title or file_name)
    slug = base_slug
    i = 1
    while db.execute(select(KnowledgeDocument.id).where(KnowledgeDocument.organization_id == organization_id, KnowledgeDocument.slug == slug)).scalar_one_or_none():
        slug = f'{base_slug}-{i}'
        i += 1
    storage_root = Path(settings.knowledge_storage_path) / str(organization_id)
    storage_root.mkdir(parents=True, exist_ok=True)
    checksum = sha256_bytes(content)
    storage_name = f'{uuid.uuid4().hex}_{Path(file_name).name}'
    storage_path = storage_root / storage_name
    storage_path.write_bytes(content)
    now = datetime.now(UTC)
    doc = KnowledgeDocument(organization_id=organization_id, title=title.strip() or file_name, slug=slug, document_type=document_type or meta.get('document_type') or 'other', status='processing', language_code=str(meta.get('language') or 'en'), tags=tags or [], permissions_json={'roles': ['organization_member'], 'visibility': 'organization'}, metadata_json={'ingestion': meta}, created_by_user_id=user.id)
    db.add(doc)
    db.flush()
    version = KnowledgeDocumentVersion(document_id=doc.id, organization_id=organization_id, version_number=1, status='draft', file_name=file_name, content_type=content_type or 'application/octet-stream', storage_path=str(storage_path), checksum_sha256=checksum, byte_size=len(content), extracted_text=text, page_count=None, language_code=doc.language_code, processing_status='processing', quality_score=_quality_score(text), created_by_user_id=user.id)
    db.add(version)
    db.flush()
    doc.current_version_id = version.id
    index_document_version(db, document=doc, version=version, publish=publish)
    if publish:
        version.status = 'published'
        version.published_at = now
        version.processing_status = 'completed'
        doc.status = 'published'
        doc.published_at = now
    else:
        version.status = 'draft'
        version.processing_status = 'completed'
        doc.status = 'draft'
    write_audit_log(db, actor_user_id=user.id, action='knowledge.document.uploaded', entity_type='knowledge_document', entity_id=str(doc.id), organization_id=organization_id, metadata={'title': doc.title, 'slug': doc.slug})
    db.flush()
    return _serialize_document(doc, include_versions=True)

def index_document_version(db: Session, *, document: KnowledgeDocument, version: KnowledgeDocumentVersion, publish: bool=True) -> int:
    settings = get_settings()
    text = version.extracted_text or ''
    pieces = chunk_text(text, strategy=settings.ai_chunking_strategy, chunk_size=settings.ai_chunk_size, overlap=settings.ai_chunk_overlap)
    if publish:
        existing = db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id, KnowledgeChunk.is_active.is_(True))).scalars()
        for row in existing:
            row.is_active = False
    embedder = build_embedding_provider(settings)
    created = 0
    for piece in pieces:
        chunk = KnowledgeChunk(organization_id=document.organization_id, document_id=document.id, document_version_id=version.id, chunk_index=piece.chunk_index, content=piece.content, content_hash=content_hash(piece.content), token_estimate=piece.token_estimate, page_number=piece.page_number, section_title=piece.section_title, language_code=document.language_code, tags=document.tags, permissions_json=document.permissions_json, metadata_json={'document_title': document.title, 'document_type': document.document_type, 'version_number': version.version_number, 'file_name': version.file_name}, is_active=True)
        db.add(chunk)
        db.flush()
        vector = embedder.embed_query(piece.content)
        db.add(KnowledgeEmbedding(organization_id=document.organization_id, chunk_id=chunk.id, provider=embedder.name, model_name=getattr(settings, 'ai_embedding_model', embedder.name), dimensions=len(vector), vector_json=vector, permissions_json=document.permissions_json, metadata_json={'language': document.language_code, 'document_id': str(document.id), 'tags': document.tags or []}))
        created += 1
    db.flush()
    return created

def list_chunks(db: Session, user: User, organization_id: uuid.UUID, *, document_id: uuid.UUID | None=None, page: int=1, page_size: int=20) -> Page[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.organization_id == organization_id, KnowledgeChunk.is_active.is_(True))
    if document_id:
        stmt = stmt.where(KnowledgeChunk.document_id == document_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(KnowledgeChunk.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    items = [{'id': str(c.id), 'documentId': str(c.document_id), 'chunkIndex': c.chunk_index, 'content': c.content[:500], 'pageNumber': c.page_number, 'sectionTitle': c.section_title, 'languageCode': c.language_code, 'tags': c.tags or []} for c in rows]
    return paginate(items, page=page, page_size=page_size, total_items=total)

def archive_document(db: Session, user: User, organization_id: uuid.UUID, document_id: uuid.UUID) -> dict[str, Any]:
    require_ai_manage(db, user, organization_id)
    doc = _get_document(db, organization_id, document_id)
    if doc.status == 'archived':
        raise ConflictError('Document already archived.')
    doc.status = 'archived'
    chunks = db.execute(select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)).scalars()
    for chunk in chunks:
        chunk.is_active = False
    db.flush()
    return _serialize_document(doc)

def _get_document(db: Session, organization_id: uuid.UUID, document_id: uuid.UUID) -> KnowledgeDocument:
    doc = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.organization_id == organization_id)).scalar_one_or_none()
    if doc is None:
        raise NotFoundError('Document not found.')
    return doc

def _serialize_document(doc: KnowledgeDocument, *, include_versions: bool=False) -> dict[str, Any]:
    payload: dict[str, Any] = {'id': str(doc.id), 'organizationId': str(doc.organization_id), 'title': doc.title, 'slug': doc.slug, 'documentType': doc.document_type, 'status': doc.status, 'languageCode': doc.language_code, 'tags': doc.tags or [], 'currentVersionId': str(doc.current_version_id) if doc.current_version_id else None, 'publishedAt': doc.published_at.isoformat() if doc.published_at else None, 'createdAt': doc.created_at.isoformat() if doc.created_at else None, 'updatedAt': doc.updated_at.isoformat() if doc.updated_at else None}
    if include_versions:
        payload['metadata'] = doc.metadata_json or {}
    return payload

def _quality_score(text: str) -> float:
    if not text:
        return 0.0
    length = len(text)
    if length < 40:
        return 0.2
    if length < 200:
        return 0.5
    return min(1.0, 0.6 + length / 10000)

def _virus_scan_hook(content: bytes, file_name: str) -> None:
    _ = (content, file_name)
    return None
