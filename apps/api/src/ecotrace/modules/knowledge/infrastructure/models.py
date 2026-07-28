from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from ecotrace.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class KnowledgeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'knowledge_documents'
    __table_args__ = (UniqueConstraint('organization_id', 'slug', name='uq_knowledge_documents_org_slug'), Index('ix_knowledge_documents_organization_id', 'organization_id'), Index('ix_knowledge_documents_status', 'status'), Index('ix_knowledge_documents_document_type', 'document_type'), Index('ix_knowledge_documents_language', 'language_code'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default='other')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_record_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    permissions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class KnowledgeDocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'knowledge_document_versions'
    __table_args__ = (UniqueConstraint('document_id', 'version_number', name='uq_knowledge_doc_version'), Index('ix_knowledge_document_versions_document_id', 'document_id'), Index('ix_knowledge_document_versions_status', 'status'))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending')
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('knowledge_document_versions.id', ondelete='SET NULL'), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class KnowledgeChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'knowledge_chunks'
    __table_args__ = (UniqueConstraint('document_version_id', 'chunk_index', name='uq_knowledge_chunks_version_index'), Index('ix_knowledge_chunks_organization_id', 'organization_id'), Index('ix_knowledge_chunks_document_id', 'document_id'), Index('ix_knowledge_chunks_document_version_id', 'document_version_id'), Index('ix_knowledge_chunks_language', 'language_code'), Index('ix_knowledge_chunks_content_hash', 'content_hash'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False)
    document_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('knowledge_document_versions.id', ondelete='CASCADE'), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    permissions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class KnowledgeEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'knowledge_embeddings'
    __table_args__ = (UniqueConstraint('chunk_id', 'model_name', name='uq_knowledge_embeddings_chunk_model'), Index('ix_knowledge_embeddings_organization_id', 'organization_id'), Index('ix_knowledge_embeddings_chunk_id', 'chunk_id'), Index('ix_knowledge_embeddings_model_name', 'model_name'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('knowledge_chunks.id', ondelete='CASCADE'), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_json: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    permissions_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ChatFolder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'chat_folders'
    __table_args__ = (UniqueConstraint('organization_id', 'owner_user_id', 'name', name='uq_chat_folders_owner_name'), Index('ix_chat_folders_organization_id', 'organization_id'), Index('ix_chat_folders_owner_user_id', 'owner_user_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_folders.id', ondelete='SET NULL'), nullable=True)

class ChatConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'chat_conversations'
    __table_args__ = (Index('ix_chat_conversations_organization_id', 'organization_id'), Index('ix_chat_conversations_owner_user_id', 'owner_user_id'), Index('ix_chat_conversations_status', 'status'), Index('ix_chat_conversations_pinned', 'is_pinned'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_folders.id', ondelete='SET NULL'), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default='New chat')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='active')
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_shared_org: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memory_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'chat_messages'
    __table_args__ = (Index('ix_chat_messages_conversation_id', 'conversation_id'), Index('ix_chat_messages_organization_id', 'organization_id'), Index('ix_chat_messages_role', 'role'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='en')
    citations_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_calls_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class PromptTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'prompt_templates'
    __table_args__ = (UniqueConstraint('organization_id', 'code', 'version_number', name='uq_prompt_templates_org_code_ver'), Index('ix_prompt_templates_organization_id', 'organization_id'), Index('ix_prompt_templates_scope', 'scope'), Index('ix_prompt_templates_is_active', 'is_active'))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default='system')
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    ab_group: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ProviderConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'provider_configs'
    __table_args__ = (UniqueConstraint('organization_id', 'provider_kind', 'provider_name', name='uq_provider_configs_org_kind'), Index('ix_provider_configs_organization_id', 'organization_id'))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    provider_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

class OrganizationAiSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'organization_ai_settings'
    __table_args__ = (UniqueConstraint('organization_id', name='uq_organization_ai_settings_org'), Index('ix_organization_ai_settings_organization_id', 'organization_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    preferred_provider: Mapped[str] = mapped_column(String(64), nullable=False, default='local_grounded')
    preferred_embedding_model: Mapped[str] = mapped_column(String(128), nullable=False, default='local-hash-384')
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    top_p: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    frequency_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    presence_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default='required')
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default='auto')
    monthly_budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class RetrievalLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'retrieval_logs'
    __table_args__ = (Index('ix_retrieval_logs_organization_id', 'organization_id'), Index('ix_retrieval_logs_conversation_id', 'conversation_id'), Index('ix_retrieval_logs_created_at', 'created_at'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_conversations.id', ondelete='SET NULL'), nullable=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    expanded_queries_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    candidate_chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reranked_chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_usage_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

class ConversationFeedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'conversation_feedback'
    __table_args__ = (UniqueConstraint('message_id', 'user_id', name='uq_conversation_feedback_message_user'), Index('ix_conversation_feedback_organization_id', 'organization_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, default='answer')

class EvaluationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'evaluation_runs'
    __table_args__ = (Index('ix_evaluation_runs_organization_id', 'organization_id'),)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='completed')
    dataset_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

class SavedSearch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'saved_searches'
    __table_args__ = (UniqueConstraint('organization_id', 'owner_user_id', 'name', name='uq_saved_searches_owner_name'), Index('ix_saved_searches_organization_id', 'organization_id'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    search_mode: Mapped[str] = mapped_column(String(32), nullable=False, default='hybrid')

class AiMemory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'ai_memories'
    __table_args__ = (Index('ix_ai_memories_organization_id', 'organization_id'), Index('ix_ai_memories_user_id', 'user_id'), Index('ix_ai_memories_scope', 'scope'))
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
