from __future__ import annotations
import uuid
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.ai.providers import LocalHashEmbedding, detect_language
from ecotrace.core.config import get_settings
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.application.chunking import chunk_text, content_hash
from ecotrace.modules.knowledge.infrastructure.models import KnowledgeChunk, KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeEmbedding, OrganizationAiSettings, PromptTemplate, ProviderConfig
from ecotrace.modules.organizations.infrastructure.models import Organization

def seed_ai(session: Session, org: Organization, actor: User) -> None:
    settings = get_settings()
    existing = session.execute(select(KnowledgeDocument.id).where(KnowledgeDocument.organization_id == org.id, KnowledgeDocument.slug == 'sustainability-policy-demo')).scalar_one_or_none()
    if existing:
        return
    now = datetime.now(UTC)
    body = '# EcoTrace Demo Sustainability Policy\n\n## Carbon Management\nOur organization measures Scope 1, Scope 2, and selected Scope 3 emissions using EcoTrace carbon inventories.\n\n## Product Footprints\nEcoBottle 750ml maintains a product carbon footprint and a published digital product passport.\n\n## Targets\nWe track absolute and intensity targets and review progress quarterly.\n\n## Evidence Rules\nAI answers must cite authorized EcoTrace documents and structured records only.\n'
    language = detect_language(body)
    doc = KnowledgeDocument(organization_id=org.id, title='Demo Sustainability Policy', slug='sustainability-policy-demo', document_type='policy', status='published', language_code=language, tags=['policy', 'demo', 'carbon'], permissions_json={'visibility': 'organization', 'roles': ['organization_member']}, metadata_json={'seed': True}, created_by_user_id=actor.id, published_at=now)
    session.add(doc)
    session.flush()
    version = KnowledgeDocumentVersion(document_id=doc.id, organization_id=org.id, version_number=1, status='published', file_name='sustainability-policy-demo.md', content_type='text/markdown', storage_path=f'seed://{org.id}/sustainability-policy-demo.md', checksum_sha256=content_hash(body), byte_size=len(body.encode('utf-8')), extracted_text=body, language_code=language, processing_status='completed', quality_score=0.95, created_by_user_id=actor.id, published_at=now)
    session.add(version)
    session.flush()
    doc.current_version_id = version.id
    embedder = LocalHashEmbedding()
    for piece in chunk_text(body, strategy='markdown', chunk_size=500, overlap=80):
        chunk = KnowledgeChunk(organization_id=org.id, document_id=doc.id, document_version_id=version.id, chunk_index=piece.chunk_index, content=piece.content, content_hash=content_hash(piece.content), token_estimate=piece.token_estimate, section_title=piece.section_title, language_code=language, tags=doc.tags, permissions_json=doc.permissions_json, metadata_json={'document_title': doc.title, 'document_type': doc.document_type, 'file_name': version.file_name}, is_active=True)
        session.add(chunk)
        session.flush()
        vector = embedder.embed_query(piece.content)
        session.add(KnowledgeEmbedding(organization_id=org.id, chunk_id=chunk.id, provider=embedder.name, model_name=settings.ai_embedding_model, dimensions=len(vector), vector_json=vector, permissions_json=doc.permissions_json, metadata_json={'language': language, 'document_id': str(doc.id)}))
    if not session.execute(select(OrganizationAiSettings.id).where(OrganizationAiSettings.organization_id == org.id)).scalar_one_or_none():
        session.add(OrganizationAiSettings(organization_id=org.id, preferred_provider='local_grounded', preferred_embedding_model='local-hash-384', temperature=0.1, max_tokens=1200, top_p=0.95, system_prompt='You are EcoTrace AI Sustainability Copilot. Ground answers in evidence.', citation_mode='required', language_code='auto'))
    if not session.execute(select(PromptTemplate.id).where(PromptTemplate.organization_id == org.id, PromptTemplate.code == 'copilot.system')).scalar_one_or_none():
        session.add(PromptTemplate(organization_id=org.id, owner_user_id=actor.id, code='copilot.system', name='Copilot system prompt', scope='organization', version_number=1, template_body='Answer in {{language}}. Use only authorized EcoTrace evidence. Cite every claim. Organization={{organization_name}}.', variables_json=['language', 'organization_name'], ab_group='A', is_active=True))
    for kind, name, model in (('llm', 'local_grounded', 'ecotrace-local-grounded'), ('embedding', 'local_hash', 'local-hash-384'), ('reranker', 'local_lexical', 'local-lexical'), ('ocr', 'tesseract', 'tesseract')):
        exists = session.execute(select(ProviderConfig.id).where(ProviderConfig.organization_id == org.id, ProviderConfig.provider_kind == kind, ProviderConfig.provider_name == name)).scalar_one_or_none()
        if exists:
            continue
        session.add(ProviderConfig(organization_id=org.id, provider_kind=kind, provider_name=name, model_name=model, is_enabled=True, is_default=True, config_json={'seed': True}))
    _ = uuid.uuid4()
    session.flush()
