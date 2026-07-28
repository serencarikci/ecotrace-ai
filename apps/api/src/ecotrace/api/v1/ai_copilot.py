from __future__ import annotations
from collections.abc import Iterator
from typing import Any
from uuid import UUID
from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import select
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.modules.ai_copilot.application import chat_service, evaluation_service
from ecotrace.modules.enterprise_search.application import search_service
from ecotrace.modules.knowledge.application import document_service
from ecotrace.modules.knowledge.infrastructure.models import ProviderConfig, RetrievalLog
from ecotrace.shared.application.org_access import require_ai_admin, require_ai_read
from ecotrace.shared.domain.schemas import CamelModel
router = APIRouter(prefix='/organizations/{organization_id}', tags=['AI Copilot'])

class ChatRequest(CamelModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None

class ConversationUpdate(CamelModel):
    title: str | None = None
    is_pinned: bool | None = None
    is_favorite: bool | None = None
    folder_id: UUID | None = None
    share_org: bool | None = None
    archive: bool | None = None

class FeedbackRequest(CamelModel):
    conversation_id: UUID
    message_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None

class AiSettingsUpdate(CamelModel):
    preferred_provider: str | None = None
    preferred_embedding_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    system_prompt: str | None = None
    citation_mode: str | None = None
    language_code: str | None = None
    monthly_budget_usd: float | None = None

class PromptUpsert(CamelModel):
    code: str
    name: str
    template_body: str
    scope: str = 'organization'
    variables: list[str] | None = None
    ab_group: str | None = None

class SearchRequest(CamelModel):
    query: str
    mode: str = 'hybrid'
    document_type: str | None = None
    language: str | None = None
    limit: int = 20

class SavedSearchCreate(CamelModel):
    name: str
    query_text: str
    filters: dict[str, Any] | None = None
    search_mode: str = 'hybrid'

class EvaluationRequest(CamelModel):
    name: str
    dataset: list[dict[str, Any]]
    notes: str | None = None

class FolderCreate(CamelModel):
    name: str

@router.post('/ai/chat')
def ai_chat(organization_id: UUID, payload: ChatRequest, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.chat(db, user, organization_id, message=payload.message, conversation_id=payload.conversation_id, stream=False)
    db.commit()
    return result

@router.post('/ai/chat/stream')
def ai_chat_stream(organization_id: UUID, payload: ChatRequest, db: DbSession, user: CurrentUser) -> StreamingResponse:
    token_iter = chat_service.chat(db, user, organization_id, message=payload.message, conversation_id=payload.conversation_id, stream=True)
    assert isinstance(token_iter, Iterator)

    def event_gen() -> Iterator[str]:
        try:
            yield from token_iter
        finally:
            db.commit()
    return StreamingResponse(event_gen(), media_type='text/event-stream')

@router.get('/ai/conversations')
def list_conversations(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), q: str | None=None) -> Any:
    return chat_service.list_conversations(db, user, organization_id, page=page, page_size=page_size, q=q)

@router.post('/ai/conversations')
def create_conversation(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.create_conversation(db, user, organization_id)
    db.commit()
    return result

@router.patch('/ai/conversations/{conversation_id}')
def update_conversation(organization_id: UUID, conversation_id: UUID, payload: ConversationUpdate, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.update_conversation(db, user, organization_id, conversation_id, title=payload.title, is_pinned=payload.is_pinned, is_favorite=payload.is_favorite, folder_id=payload.folder_id, share_org=payload.share_org, archive=payload.archive)
    db.commit()
    return result

@router.delete('/ai/conversations/{conversation_id}')
def delete_conversation(organization_id: UUID, conversation_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.delete_conversation(db, user, organization_id, conversation_id)
    db.commit()
    return result

@router.get('/ai/conversations/{conversation_id}/messages')
def conversation_messages(organization_id: UUID, conversation_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return chat_service.list_messages(db, user, organization_id, conversation_id)

@router.get('/ai/conversations/{conversation_id}/export')
def export_conversation(organization_id: UUID, conversation_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return chat_service.export_conversation(db, user, organization_id, conversation_id)

@router.post('/ai/folders')
def create_folder(organization_id: UUID, payload: FolderCreate, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.create_folder(db, user, organization_id, name=payload.name)
    db.commit()
    return result

@router.post('/ai/feedback')
def feedback(organization_id: UUID, payload: FeedbackRequest, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.submit_feedback(db, user, organization_id, conversation_id=payload.conversation_id, message_id=payload.message_id, rating=payload.rating, comment=payload.comment)
    db.commit()
    return result

@router.post('/knowledge/documents')
async def upload_document(organization_id: UUID, db: DbSession, user: CurrentUser, file: UploadFile=File(...), title: str | None=Form(None), document_type: str | None=Form(None), publish: bool=Form(True)) -> Any:
    content = await file.read()
    result = document_service.upload_document(db, user, organization_id, title=title or (file.filename or 'document'), file_name=file.filename or 'document.txt', content_type=file.content_type or 'application/octet-stream', content=content, document_type=document_type, publish=publish)
    db.commit()
    return result

@router.get('/knowledge/documents')
def list_documents(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), q: str | None=None, status: str | None=None, document_type: str | None=Query(None, alias='documentType')) -> Any:
    return document_service.list_documents(db, user, organization_id, page=page, page_size=page_size, q=q, status=status, document_type=document_type)

@router.get('/knowledge/documents/{document_id}')
def get_document(organization_id: UUID, document_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return document_service.get_document(db, user, organization_id, document_id)

@router.post('/knowledge/documents/{document_id}/archive')
def archive_document(organization_id: UUID, document_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = document_service.archive_document(db, user, organization_id, document_id)
    db.commit()
    return result

@router.get('/knowledge/chunks')
def list_chunks(organization_id: UUID, db: DbSession, user: CurrentUser, document_id: UUID | None=Query(None, alias='documentId'), page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize')) -> Any:
    return document_service.list_chunks(db, user, organization_id, document_id=document_id, page=page, page_size=page_size)

@router.post('/search')
def search(organization_id: UUID, payload: SearchRequest, db: DbSession, user: CurrentUser) -> Any:
    return search_service.enterprise_search(db, user, organization_id, query=payload.query, mode=payload.mode, document_type=payload.document_type, language=payload.language, limit=payload.limit)

@router.get('/search/autocomplete')
def search_autocomplete(organization_id: UUID, db: DbSession, user: CurrentUser, q: str=Query(..., min_length=1)) -> Any:
    return search_service.autocomplete(db, user, organization_id, prefix=q)

@router.post('/search/saved')
def save_search(organization_id: UUID, payload: SavedSearchCreate, db: DbSession, user: CurrentUser) -> Any:
    result = search_service.save_search(db, user, organization_id, name=payload.name, query_text=payload.query_text, filters=payload.filters, search_mode=payload.search_mode)
    db.commit()
    return result

@router.get('/search/saved')
def list_saved(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return search_service.list_saved_searches(db, user, organization_id)

@router.get('/ai/settings')
def get_settings(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return chat_service.get_ai_settings(db, user, organization_id)

@router.put('/ai/settings')
def put_settings(organization_id: UUID, payload: AiSettingsUpdate, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.update_ai_settings(db, user, organization_id, payload.model_dump(by_alias=True, exclude_none=True))
    db.commit()
    return result

@router.get('/ai/prompts')
def list_prompts(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return chat_service.list_prompt_templates(db, user, organization_id)

@router.post('/ai/prompts')
def upsert_prompt(organization_id: UUID, payload: PromptUpsert, db: DbSession, user: CurrentUser) -> Any:
    result = chat_service.upsert_prompt_template(db, user, organization_id, code=payload.code, name=payload.name, template_body=payload.template_body, scope=payload.scope, variables=payload.variables, ab_group=payload.ab_group)
    db.commit()
    return result

@router.post('/ai/evaluations')
def create_evaluation(organization_id: UUID, payload: EvaluationRequest, db: DbSession, user: CurrentUser) -> Any:
    result = evaluation_service.run_evaluation(db, user, organization_id, name=payload.name, dataset=payload.dataset, notes=payload.notes)
    db.commit()
    return result

@router.get('/ai/evaluations')
def list_evaluations(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return evaluation_service.list_evaluations(db, user, organization_id)

@router.get('/ai/analytics')
def analytics(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return search_service.conversation_analytics(db, user, organization_id)

@router.get('/ai/retrieval-logs')
def retrieval_logs(organization_id: UUID, db: DbSession, user: CurrentUser, limit: int=Query(50, ge=1, le=200)) -> Any:
    require_ai_read(db, user, organization_id)
    rows = db.execute(select(RetrievalLog).where(RetrievalLog.organization_id == organization_id).order_by(RetrievalLog.created_at.desc()).limit(limit)).scalars()
    return [{'id': str(r.id), 'queryText': r.query_text, 'retrievalLatencyMs': r.retrieval_latency_ms, 'embeddingLatencyMs': r.embedding_latency_ms, 'llmLatencyMs': r.llm_latency_ms, 'promptTokens': r.prompt_tokens, 'completionTokens': r.completion_tokens, 'cacheHit': r.cache_hit, 'provider': r.provider, 'createdAt': r.created_at.isoformat() if r.created_at else None} for r in rows]

@router.get('/ai/providers')
def list_providers(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    require_ai_admin(db, user, organization_id)
    rows = db.execute(select(ProviderConfig).where((ProviderConfig.organization_id == organization_id) | ProviderConfig.organization_id.is_(None))).scalars()
    return [{'id': str(r.id), 'providerKind': r.provider_kind, 'providerName': r.provider_name, 'modelName': r.model_name, 'isEnabled': r.is_enabled, 'isDefault': r.is_default, 'baseUrl': r.base_url, 'hasSecret': bool(r.secret_ref)} for r in rows]

@router.get('/ai/cost-dashboard')
def cost_dashboard(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    require_ai_read(db, user, organization_id)
    analytics = search_service.conversation_analytics(db, user, organization_id)
    logs = db.execute(select(RetrievalLog).where(RetrievalLog.organization_id == organization_id)).scalars()
    tokens = 0
    for row in logs:
        tokens += int(row.prompt_tokens or 0) + int(row.completion_tokens or 0)
    return {**analytics, 'totalTokens': tokens, 'estimatedCostUsd': round(tokens * 2e-07, 6)}
