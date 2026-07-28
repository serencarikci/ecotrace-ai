from __future__ import annotations
import hashlib
import io
import re
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from pydantic import Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.lca_constants import DISCLAIMER, PASSPORT_DOC_TYPES, PASSPORT_SECTIONS, PASSPORT_STATUSES, PASSPORT_TRANSITIONS
from ecotrace.modules.activity_data.application.attachment_service import MIME_BY_EXT, sanitize_original_name
from ecotrace.modules.digital_product_passport.infrastructure.models import DigitalProductPassport, DigitalProductPassportSection, PassportDocument
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.product_carbon_footprint.application.pcf_service import get_footprint
from ecotrace.modules.product_carbon_footprint.infrastructure.models import ProductCarbonFootprint
from ecotrace.modules.products.application.product_service import get_batch, get_product, get_variant
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_passport_publish, require_product_manage, require_product_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate
SLUG_RE = re.compile('^[a-z0-9]+(?:-[a-z0-9]+)*$')

class SectionCreate(CamelModel):
    section_code: str
    title: str
    content_type: str = 'structured'
    structured_data_json: dict[str, Any] | None = None
    display_order: int = 0
    is_public: bool = True

class PassportCreate(CamelModel):
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None = None
    product_batch_id: uuid.UUID | None = None
    product_carbon_footprint_id: uuid.UUID | None = None
    passport_code: str
    title: str
    description: str | None = None
    language_code: str = 'en'
    public_slug: str
    effective_from: date | None = None
    effective_to: date | None = None
    sections: list[SectionCreate] = Field(default_factory=list)

class PassportUpdate(CamelModel):
    title: str | None = None
    description: str | None = None
    language_code: str | None = None
    product_carbon_footprint_id: uuid.UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    sections: list[SectionCreate] | None = None

class SectionResponse(CamelModel):
    id: uuid.UUID
    passport_id: uuid.UUID
    section_code: str
    title: str
    content_type: str
    structured_data_json: dict[str, Any] | None
    display_order: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

class DocumentResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    passport_id: uuid.UUID
    document_type: str
    title: str
    original_file_name: str
    content_type: str
    file_size: int
    checksum: str
    is_public: bool
    uploaded_by_user_id: uuid.UUID | None
    created_at: datetime

class PassportResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None
    product_batch_id: uuid.UUID | None
    product_carbon_footprint_id: uuid.UUID | None
    passport_code: str
    title: str
    description: str | None
    version: int
    status: str
    language_code: str
    public_slug: str
    qr_code_reference: str | None
    effective_from: date | None
    effective_to: date | None
    published_at: datetime | None
    published_by_user_id: uuid.UUID | None
    revoked_at: datetime | None
    revoked_by_user_id: uuid.UUID | None
    supersedes_passport_id: uuid.UUID | None
    sections: list[SectionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    disclaimer: str = DISCLAIMER

def get_passport(db: Session, organization_id: uuid.UUID, passport_id: uuid.UUID) -> DigitalProductPassport:
    row = db.get(DigitalProductPassport, passport_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Digital product passport not found.')
    return row

def _sections(db: Session, passport_id: uuid.UUID) -> list[DigitalProductPassportSection]:
    return list(db.execute(select(DigitalProductPassportSection).where(DigitalProductPassportSection.passport_id == passport_id).order_by(DigitalProductPassportSection.display_order.asc())).scalars().all())

def _to_response(db: Session, row: DigitalProductPassport) -> PassportResponse:
    resp = PassportResponse.model_validate(row)
    resp.sections = [SectionResponse.model_validate(s) for s in _sections(db, row.id)]
    return resp

def _public_url(slug: str) -> str:
    settings = get_settings()
    base = getattr(settings, 'public_app_base_url', None) or 'http://localhost:4200'
    return f"{base.rstrip('/')}/passport/{slug}"

def _generate_qr_png(url: str) -> bytes:
    try:
        import segno
    except ImportError as exc:
        raise BusinessRuleError('QR generation dependency missing.') from exc
    buff = io.BytesIO()
    segno.make(url, error='m').save(buff, kind='png', scale=6)
    return buff.getvalue()

def _generate_qr_svg(url: str) -> str:
    try:
        import segno
    except ImportError as exc:
        raise BusinessRuleError('QR generation dependency missing.') from exc
    return segno.make(url, error='m').svg_inline(scale=6)

def list_passports(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, status: str | None=None, product_id: uuid.UUID | None=None) -> Page[PassportResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(DigitalProductPassport).where(DigitalProductPassport.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(DigitalProductPassport.title.ilike(like), DigitalProductPassport.passport_code.ilike(like), DigitalProductPassport.public_slug.ilike(like)))
    if status:
        stmt = stmt.where(DigitalProductPassport.status == status)
    if product_id:
        stmt = stmt.where(DigitalProductPassport.product_id == product_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(DigitalProductPassport.version.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([_to_response(db, r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_passport(db: Session, user: User, organization_id: uuid.UUID, payload: PassportCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_product_write(db, user, organization_id)
    get_product(db, organization_id, payload.product_id)
    if payload.product_variant_id:
        v = get_variant(db, organization_id, payload.product_variant_id)
        if v.product_id != payload.product_id:
            raise ValidationAppError('Variant does not belong to product.')
    if payload.product_batch_id:
        b = get_batch(db, organization_id, payload.product_batch_id)
        if b.product_id != payload.product_id:
            raise ValidationAppError('Batch does not belong to product.')
    if payload.product_carbon_footprint_id:
        get_footprint(db, organization_id, payload.product_carbon_footprint_id)
    slug = payload.public_slug.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValidationAppError('publicSlug must be lowercase kebab-case.')
    code = payload.passport_code.strip()
    if db.execute(select(DigitalProductPassport.id).where(DigitalProductPassport.passport_code == code)).scalar_one_or_none():
        raise ConflictError('Passport code must be unique.')
    if db.execute(select(DigitalProductPassport.id).where(DigitalProductPassport.public_slug == slug)).scalar_one_or_none():
        raise ConflictError('Public slug must be unique.')
    for section in payload.sections:
        if section.section_code not in PASSPORT_SECTIONS:
            raise ValidationAppError(f'Unknown section code: {section.section_code}')
    row = DigitalProductPassport(organization_id=organization_id, product_id=payload.product_id, product_variant_id=payload.product_variant_id, product_batch_id=payload.product_batch_id, product_carbon_footprint_id=payload.product_carbon_footprint_id, passport_code=code, title=payload.title.strip(), description=payload.description, version=1, status='draft', language_code=payload.language_code, public_slug=slug, qr_code_reference=_public_url(slug), effective_from=payload.effective_from, effective_to=payload.effective_to)
    db.add(row)
    db.flush()
    for section in payload.sections:
        db.add(DigitalProductPassportSection(passport_id=row.id, section_code=section.section_code, title=section.title, content_type=section.content_type, structured_data_json=section.structured_data_json, display_order=section.display_order, is_public=section.is_public))
    write_audit_log(db, action='passport.created', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'passportCode': code})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def update_passport(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, payload: PassportUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_product_write(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if row.status not in {'draft', 'under_review'}:
        raise BusinessRuleError('Published passport versions are immutable. Clone a new version.')
    data = payload.model_dump(exclude_unset=True)
    sections = data.pop('sections', None)
    if data.get('product_carbon_footprint_id'):
        get_footprint(db, organization_id, data['product_carbon_footprint_id'])
    for key, value in data.items():
        setattr(row, key, value)
    if sections is not None:
        for existing in _sections(db, row.id):
            db.delete(existing)
        db.flush()
        for section in sections:
            model = SectionCreate.model_validate(section)
            if model.section_code not in PASSPORT_SECTIONS:
                raise ValidationAppError(f'Unknown section code: {model.section_code}')
            db.add(DigitalProductPassportSection(passport_id=row.id, section_code=model.section_code, title=model.title, content_type=model.content_type, structured_data_json=model.structured_data_json, display_order=model.display_order, is_public=model.is_public))
    write_audit_log(db, action='passport.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def submit_passport(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_product_write(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if 'under_review' not in PASSPORT_TRANSITIONS.get(row.status, frozenset()):
        raise BusinessRuleError('Passport cannot be submitted from current status.')
    row.status = 'under_review'
    write_audit_log(db, action='passport.submitted', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def clone_passport_version(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_product_write(db, user, organization_id)
    source = get_passport(db, organization_id, passport_id)
    sections = _sections(db, source.id)
    max_version = db.execute(select(func.coalesce(func.max(DigitalProductPassport.version), 0)).where(DigitalProductPassport.organization_id == organization_id, DigitalProductPassport.product_id == source.product_id, DigitalProductPassport.public_slug == source.public_slug)).scalar_one()
    new_code = f'{source.passport_code}-v{max_version + 1}'
    while db.execute(select(DigitalProductPassport.id).where(DigitalProductPassport.passport_code == new_code)).scalar_one_or_none():
        new_code = f'{new_code}-x'
    draft_slug = f'{source.public_slug}-draft-{max_version + 1}'
    row = DigitalProductPassport(organization_id=organization_id, product_id=source.product_id, product_variant_id=source.product_variant_id, product_batch_id=source.product_batch_id, product_carbon_footprint_id=source.product_carbon_footprint_id, passport_code=new_code, title=source.title, description=source.description, version=max_version + 1, status='draft', language_code=source.language_code, public_slug=draft_slug, qr_code_reference=_public_url(source.public_slug), effective_from=source.effective_from, effective_to=source.effective_to, supersedes_passport_id=source.id)
    db.add(row)
    db.flush()
    row.qr_code_reference = _public_url(source.public_slug)
    for section in sections:
        db.add(DigitalProductPassportSection(passport_id=row.id, section_code=section.section_code, title=section.title, content_type=section.content_type, structured_data_json=section.structured_data_json, display_order=section.display_order, is_public=section.is_public))
    write_audit_log(db, action='passport.cloned', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'sourceId': str(source.id), 'stableSlug': source.public_slug})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def publish_passport(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_passport_publish(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if row.status not in {'draft', 'under_review'}:
        raise BusinessRuleError('Only draft/under_review passports can be published.')
    product = get_product(db, organization_id, row.product_id)
    if not product.is_active:
        raise BusinessRuleError('Only active products may be published.')
    sections = _sections(db, row.id)
    codes = {s.section_code for s in sections if s.is_public}
    required = {'product_identity', 'manufacturer'}
    if not required.issubset(codes):
        raise BusinessRuleError('Required public sections missing: product_identity, manufacturer.')
    if 'carbon_footprint' in codes:
        if not row.product_carbon_footprint_id:
            raise BusinessRuleError('Carbon footprint section requires an approved footprint.')
        fp = get_footprint(db, organization_id, row.product_carbon_footprint_id)
        if fp.status != 'approved':
            raise BusinessRuleError('Carbon footprint must be approved before publication.')
    stable_slug = row.public_slug
    if '-draft-' in row.public_slug and row.qr_code_reference:
        candidate = row.qr_code_reference.rstrip('/').split('/')[-1]
        if SLUG_RE.match(candidate):
            stable_slug = candidate
    holders = list(db.execute(select(DigitalProductPassport).where(DigitalProductPassport.public_slug == stable_slug, DigitalProductPassport.id != row.id)).scalars().all())
    for prev in holders:
        prev.public_slug = f'{stable_slug}-v{prev.version}'
        if prev.status == 'published':
            prev.status = 'superseded'
    row.public_slug = stable_slug
    row.status = 'published'
    row.published_at = datetime.now(UTC)
    row.published_by_user_id = user.id
    row.qr_code_reference = _public_url(stable_slug)
    write_audit_log(db, action='passport.published', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'publicSlug': stable_slug})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def revoke_passport(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_passport_publish(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if row.status != 'published':
        raise BusinessRuleError('Only published passports can be revoked.')
    row.status = 'revoked'
    row.revoked_at = datetime.now(UTC)
    row.revoked_by_user_id = user.id
    write_audit_log(db, action='passport.revoked', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def archive_passport(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PassportResponse:
    require_product_manage(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if row.status not in PASSPORT_STATUSES:
        raise ValidationAppError('Invalid passport status.')
    if row.status == 'published':
        raise BusinessRuleError('Revoke before archiving a published passport.')
    row.status = 'archived'
    write_audit_log(db, action='passport.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='digital_product_passport', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def get_passport_detail(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID) -> PassportResponse:
    ensure_org_access(db, user, organization_id)
    return _to_response(db, get_passport(db, organization_id, passport_id))

def get_passport_qr(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID) -> dict[str, Any]:
    ensure_org_access(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    url = row.qr_code_reference or _public_url(row.public_slug)
    return {'url': url, 'pngBase64': None, 'svg': _generate_qr_svg(url)}

def upload_document(db: Session, user: User, organization_id: uuid.UUID, passport_id: uuid.UUID, *, document_type: str, title: str, file_name: str, content_type: str | None, content: bytes, is_public: bool=False, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> DocumentResponse:
    require_product_write(db, user, organization_id)
    row = get_passport(db, organization_id, passport_id)
    if row.status not in {'draft', 'under_review'}:
        raise BusinessRuleError('Cannot add documents to immutable passport versions.')
    if document_type not in PASSPORT_DOC_TYPES:
        raise ValidationAppError('Invalid document type.')
    settings = get_settings()
    max_bytes = settings.max_attachment_size_mb * 1024 * 1024
    if len(content) <= 0 or len(content) > max_bytes:
        raise ValidationAppError('Invalid file size.')
    safe_name = sanitize_original_name(file_name)
    ext = Path(safe_name).suffix.lower().lstrip('.')
    allowed = {item.lower() for item in settings.allowed_attachment_types}
    if ext not in allowed:
        raise ValidationAppError('File type is not allowed.')
    expected = MIME_BY_EXT.get(ext, set())
    resolved = (content_type or '').split(';')[0].strip().lower()
    if expected and resolved and (resolved not in expected) and (resolved != 'application/octet-stream'):
        raise ValidationAppError('Content type does not match extension.')
    if '..' in safe_name or '/' in safe_name or '\\' in safe_name:
        raise ValidationAppError('Invalid file name.')
    stored = f'{uuid.uuid4().hex}_{safe_name}'
    root = Path(settings.attachment_storage_path) / 'passports' / str(organization_id) / str(row.id)
    root.mkdir(parents=True, exist_ok=True)
    target = root / stored
    if not str(target.resolve()).startswith(str(root.resolve())):
        raise ValidationAppError('Path traversal detected.')
    target.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()
    doc = PassportDocument(organization_id=organization_id, passport_id=row.id, document_type=document_type, title=title.strip(), original_file_name=safe_name, stored_file_name=stored, content_type=resolved or next(iter(expected), 'application/octet-stream'), file_size=len(content), storage_path=str(target), checksum=checksum, is_public=is_public, uploaded_by_user_id=user.id)
    db.add(doc)
    write_audit_log(db, action='passport.document_uploaded', actor_user_id=user.id, organization_id=organization_id, entity_type='passport_document', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'documentType': document_type, 'isPublic': is_public})
    db.commit()
    db.refresh(doc)
    return DocumentResponse.model_validate(doc)

def _active_public_passport(db: Session, public_slug: str) -> DigitalProductPassport | None:
    published = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.public_slug == public_slug, DigitalProductPassport.status == 'published').order_by(DigitalProductPassport.version.desc())).scalar_one_or_none()
    if published:
        return published
    revoked = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.public_slug == public_slug, DigitalProductPassport.status == 'revoked').order_by(DigitalProductPassport.version.desc())).scalar_one_or_none()
    return revoked

def get_public_passport(db: Session, public_slug: str) -> dict[str, Any]:
    row = _active_public_passport(db, public_slug.strip().lower())
    if row is None:
        any_row = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.public_slug == public_slug.strip().lower()).order_by(DigitalProductPassport.version.desc())).scalar_one_or_none()
        if any_row is None:
            raise NotFoundError('Passport not found.')
        row = any_row
    product = get_product(db, row.organization_id, row.product_id)
    org = db.get(Organization, row.organization_id)
    sections = [{'sectionCode': s.section_code, 'title': s.title, 'contentType': s.content_type, 'structuredData': s.structured_data_json, 'displayOrder': s.display_order} for s in _sections(db, row.id) if s.is_public]
    footprint = None
    if row.product_carbon_footprint_id:
        fp = db.get(ProductCarbonFootprint, row.product_carbon_footprint_id)
        if fp and fp.status == 'approved':
            footprint = {'totalKgCO2e': str(fp.total_kg_co2e), 'cradleToGateKgCO2e': str(fp.cradle_to_gate_kg_co2e) if fp.cradle_to_gate_kg_co2e is not None else None, 'usePhaseKgCO2e': str(fp.use_phase_kg_co2e) if fp.use_phase_kg_co2e is not None else None, 'endOfLifeKgCO2e': str(fp.end_of_life_kg_co2e) if fp.end_of_life_kg_co2e is not None else None, 'functionalUnitQuantity': str(fp.functional_unit_quantity), 'functionalUnitCode': fp.functional_unit_code}
    write_audit_log(db, action='public_passport.accessed', organization_id=row.organization_id, entity_type='digital_product_passport', entity_id=str(row.id), metadata={'publicSlug': public_slug})
    db.commit()
    return {'status': row.status, 'title': row.title, 'description': row.description, 'version': row.version, 'languageCode': row.language_code, 'publicSlug': row.public_slug, 'publishedAt': row.published_at.isoformat() if row.published_at else None, 'revokedAt': row.revoked_at.isoformat() if row.revoked_at else None, 'product': {'name': product.name, 'code': product.code, 'productType': product.product_type, 'productCategory': product.product_category, 'brand': product.brand, 'model': product.model, 'countryOfOrigin': product.country_of_origin, 'recyclabilityPercentage': str(product.recyclability_percentage) if product.recyclability_percentage is not None else None, 'recycledContentPercentage': str(product.recycled_content_percentage) if product.recycled_content_percentage is not None else None, 'repairabilityScore': product.repairability_score}, 'manufacturer': {'organizationName': org.name if org else None, 'organizationSlug': org.slug if org else None}, 'sections': sections, 'carbonFootprint': footprint, 'disclaimer': DISCLAIMER, 'qrCodeReference': row.qr_code_reference}

def list_public_documents(db: Session, public_slug: str) -> list[dict[str, Any]]:
    row = _active_public_passport(db, public_slug.strip().lower())
    if row is None or row.status not in {'published', 'revoked'}:
        raise NotFoundError('Passport not found.')
    docs = list(db.execute(select(PassportDocument).where(PassportDocument.passport_id == row.id, PassportDocument.is_public.is_(True))).scalars().all())
    return [{'id': str(d.id), 'documentType': d.document_type, 'title': d.title, 'originalFileName': d.original_file_name, 'contentType': d.content_type, 'fileSize': d.file_size} for d in docs]

def get_public_document_bytes(db: Session, public_slug: str, document_id: uuid.UUID) -> tuple[PassportDocument, bytes]:
    row = _active_public_passport(db, public_slug.strip().lower())
    if row is None or row.status not in {'published', 'revoked'}:
        raise NotFoundError('Passport not found.')
    doc = db.get(PassportDocument, document_id)
    if doc is None or doc.passport_id != row.id or (not doc.is_public):
        raise NotFoundError('Document not found.')
    path = Path(doc.storage_path)
    if not path.is_file():
        raise NotFoundError('Document file missing.')
    return (doc, path.read_bytes())

def get_public_qr(db: Session, public_slug: str) -> dict[str, Any]:
    row = _active_public_passport(db, public_slug.strip().lower())
    if row is None:
        raise NotFoundError('Passport not found.')
    url = row.qr_code_reference or _public_url(row.public_slug)
    return {'url': url, 'status': row.status, 'svg': _generate_qr_svg(url), 'disclaimer': DISCLAIMER}
