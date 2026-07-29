from __future__ import annotations
import json
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.ai.protocols import ChatMessage as LLMChatMessage
from ecotrace.core.ai.providers import build_llm_provider, detect_language
from ecotrace.core.ai_constants import INSUFFICIENT_EVIDENCE_EN
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.ai_copilot.application.tools import run_tools, tool_evidence_blocks
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.infrastructure.models import AiMemory, ChatConversation, ChatFolder, ChatMessage, ConversationFeedback, OrganizationAiSettings, PromptTemplate, RetrievalLog
from ecotrace.modules.retrieval.application.hybrid_search import build_context_prompt, citations_from_evidence, confidence_from_evidence, hybrid_retrieve
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_ai_manage, require_ai_read, require_ai_write
from ecotrace.shared.domain.schemas import Page, paginate
_RESPONSE_CACHE: dict[str, dict[str, Any]] = {}

def list_conversations(db: Session, user: User, organization_id: uuid.UUID, *, page: int=1, page_size: int=20, q: str | None=None, include_archived: bool=False) -> Page[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    stmt = select(ChatConversation).where(ChatConversation.organization_id == organization_id, or_(ChatConversation.owner_user_id == user.id, ChatConversation.is_shared_org.is_(True)))
    if not include_archived:
        stmt = stmt.where(ChatConversation.status != 'archived')
    stmt = stmt.where(ChatConversation.status != 'deleted')
    if q:
        like = f'%{q}%'
        stmt = stmt.where(ChatConversation.title.ilike(like))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(ChatConversation.is_pinned.desc(), ChatConversation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    return paginate([_serialize_conversation(c) for c in rows], page=page, page_size=page_size, total_items=total)

def create_conversation(db: Session, user: User, organization_id: uuid.UUID, *, title: str | None=None, folder_id: uuid.UUID | None=None) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    conv = ChatConversation(organization_id=organization_id, owner_user_id=user.id, folder_id=folder_id, title=(title or 'New chat').strip()[:255], status='active', language_code='en', memory_json={'short_term': []})
    db.add(conv)
    db.flush()
    return _serialize_conversation(conv)

def update_conversation(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID, *, title: str | None=None, is_pinned: bool | None=None, is_favorite: bool | None=None, folder_id: uuid.UUID | None=None, share_org: bool | None=None, archive: bool | None=None) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    conv = _get_owned_conversation(db, user, organization_id, conversation_id)
    if title is not None:
        conv.title = title.strip()[:255] or conv.title
    if is_pinned is not None:
        conv.is_pinned = is_pinned
    if is_favorite is not None:
        conv.is_favorite = is_favorite
    if folder_id is not None:
        conv.folder_id = folder_id
    if share_org is not None:
        conv.is_shared_org = share_org
        conv.shared_at = datetime.now(UTC) if share_org else None
        conv.status = 'shared' if share_org else 'active'
    if archive:
        conv.status = 'archived'
        conv.archived_at = datetime.now(UTC)
    db.flush()
    return _serialize_conversation(conv)

def delete_conversation(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    conv = _get_owned_conversation(db, user, organization_id, conversation_id)
    conv.status = 'deleted'
    db.flush()
    return {'id': str(conv.id), 'status': conv.status}

def list_messages(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    conv = _get_accessible_conversation(db, user, organization_id, conversation_id)
    rows = db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conv.id).order_by(ChatMessage.created_at.asc())).scalars()
    return [_serialize_message(m) for m in rows]

def export_conversation(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    conv = _get_accessible_conversation(db, user, organization_id, conversation_id)
    return {'conversation': _serialize_conversation(conv), 'messages': list_messages(db, user, organization_id, conversation_id), 'exportedAt': datetime.now(UTC).isoformat()}

def create_folder(db: Session, user: User, organization_id: uuid.UUID, *, name: str) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    folder = ChatFolder(organization_id=organization_id, owner_user_id=user.id, name=name.strip()[:255])
    db.add(folder)
    db.flush()
    return {'id': str(folder.id), 'name': folder.name}

def submit_feedback(db: Session, user: User, organization_id: uuid.UUID, *, conversation_id: uuid.UUID, message_id: uuid.UUID, rating: int, comment: str | None=None) -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    if rating < 1 or rating > 5:
        raise ValidationAppError('Rating must be between 1 and 5.')
    _get_accessible_conversation(db, user, organization_id, conversation_id)
    msg = db.execute(select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.conversation_id == conversation_id, ChatMessage.organization_id == organization_id)).scalar_one_or_none()
    if msg is None:
        raise NotFoundError('Message not found.')
    row = ConversationFeedback(organization_id=organization_id, conversation_id=conversation_id, message_id=message_id, user_id=user.id, rating=rating, comment=comment)
    db.add(row)
    db.flush()
    return {'id': str(row.id), 'rating': row.rating}

def chat(db: Session, user: User, organization_id: uuid.UUID, *, message: str, conversation_id: uuid.UUID | None=None, stream: bool=False) -> dict[str, Any] | Iterator[str]:
    require_ai_write(db, user, organization_id)
    if not message.strip():
        raise ValidationAppError('Message is required.')
    if conversation_id is None:
        conv_payload = create_conversation(db, user, organization_id, title=message[:60])
        conversation_id = uuid.UUID(conv_payload['id'])
    conv = _get_owned_conversation(db, user, organization_id, conversation_id)
    language = detect_language(message)
    conv.language_code = language
    user_msg = ChatMessage(organization_id=organization_id, conversation_id=conv.id, role='user', content=message.strip(), language_code=language)
    db.add(user_msg)
    db.flush()
    result = _generate_grounded_answer(db, user=user, organization_id=organization_id, conversation=conv, question=message.strip(), language=language)
    if stream:
        return _stream_and_persist(db, conversation=conv, organization_id=organization_id, language=language, result=result)
    assistant = _persist_assistant(db, conv=conv, organization_id=organization_id, result=result)
    db.flush()
    return {'conversationId': str(conv.id), 'userMessage': _serialize_message(user_msg), 'assistantMessage': assistant, 'citations': result['citations'], 'confidence': result['confidence'], 'reasoning': result['reasoning'], 'language': language, 'grounded': result['grounded']}

def _generate_grounded_answer(db: Session, *, user: User, organization_id: uuid.UUID, conversation: ChatConversation, question: str, language: str) -> dict[str, Any]:
    settings = get_settings()
    org_settings = _get_or_create_ai_settings(db, organization_id)
    cache_key = f'{organization_id}:{question.strip().lower()}'
    if settings.ai_enable_response_cache and cache_key in _RESPONSE_CACHE:
        cached = dict(_RESPONSE_CACHE[cache_key])
        cached['cacheHit'] = True
        return cached
    evidence, retrieval_metrics = hybrid_retrieve(db, user, organization_id, query=question, language=None if org_settings.language_code == 'auto' else org_settings.language_code)
    tool_results = run_tools(db, user, organization_id, question=question)
    tool_blocks = tool_evidence_blocks(tool_results)
    citations = citations_from_evidence(evidence)
    for block in tool_blocks:
        citations.append({'label': block['label'], 'documentName': block['documentName'], 'documentId': block['documentId'], 'pageNumber': block['pageNumber'], 'chunkId': block['chunkId'], 'databaseSource': block['databaseSource'], 'recordId': block['recordId'], 'url': block['url'], 'score': block['score'], 'snippet': block['snippet']})
    grounded = bool(evidence) or bool(tool_blocks)
    confidence = confidence_from_evidence(evidence) if evidence else 0.55 if tool_blocks else 0.0
    system_parts = [org_settings.system_prompt or _default_system_prompt(language), build_context_prompt(evidence, language=language)]
    if tool_blocks:
        system_parts.append('Structured tool evidence:')
        for block in tool_blocks:
            system_parts.append(f"[{block['label']}] {block['content']}")
    history = list(db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.created_at.desc()).limit(8)).scalars())
    history.reverse()
    messages = [LLMChatMessage(role='system', content='\n\n'.join(system_parts))]
    for msg in history[-6:]:
        if msg.role in {'user', 'assistant'}:
            messages.append(LLMChatMessage(role=msg.role, content=msg.content))
    messages.append(LLMChatMessage(role='user', content=question))
    provider = build_llm_provider(settings)
    if org_settings.preferred_provider == 'local_grounded':
        from ecotrace.core.ai.providers import LocalGroundedLLM
        provider = LocalGroundedLLM()
    t0 = time.perf_counter()
    if not grounded:
        content = INSUFFICIENT_EVIDENCE_EN
        llm_meta = {'provider': 'grounding', 'model': 'insufficient-evidence', 'promptTokens': 0, 'completionTokens': len(content) // 4}
    else:
        llm_result = provider.complete(messages=messages, temperature=org_settings.temperature, max_tokens=org_settings.max_tokens, top_p=org_settings.top_p, language=language)
        content = llm_result.content
        if org_settings.citation_mode == 'required' and evidence and ('[E' not in content):
            content = content.rstrip() + '\n\n' + ' '.join((f'[{e.citation_label}]' for e in evidence[:5]))
        if tool_blocks and '[T' not in content:
            content = content.rstrip() + '\n\n' + ' '.join((f"[{b['label']}]" for b in tool_blocks))
        llm_meta = {'provider': llm_result.provider, 'model': llm_result.model, 'promptTokens': llm_result.prompt_tokens, 'completionTokens': llm_result.completion_tokens}
    llm_latency = int((time.perf_counter() - t0) * 1000)
    reasoning = {'pipeline': ['permission_filter', 'query_expansion', 'embedding_search', 'hybrid_search', 'reranking', 'context_building', 'prompt_generation', 'llm', 'citation_generation'], 'retrieval': retrieval_metrics, 'tools': [t['action'] for t in tool_results], 'grounded': grounded}
    log = RetrievalLog(organization_id=organization_id, conversation_id=conversation.id, user_id=user.id, query_text=question, expanded_queries_json=retrieval_metrics.get('expandedQueries'), filters_json={'organizationId': str(organization_id)}, candidate_chunk_ids=[e.chunk_id for e in evidence], reranked_chunk_ids=[e.chunk_id for e in evidence], retrieval_latency_ms=retrieval_metrics.get('retrievalLatencyMs'), embedding_latency_ms=retrieval_metrics.get('embeddingLatencyMs'), llm_latency_ms=llm_latency, prompt_tokens=llm_meta['promptTokens'], completion_tokens=llm_meta['completionTokens'], estimated_cost_usd=0.0, cache_hit=False, provider=llm_meta['provider'], tool_usage_json=tool_results, metadata_json={'confidence': confidence})
    db.add(log)
    _upsert_memory(db, organization_id=organization_id, user_id=user.id, conversation_id=conversation.id, scope='short_term', key='last_question', value={'question': question, 'language': language})
    payload = {'content': content, 'citations': citations, 'confidence': confidence, 'reasoning': reasoning, 'grounded': grounded, 'language': language, 'provider': llm_meta['provider'], 'model': llm_meta['model'], 'promptTokens': llm_meta['promptTokens'], 'completionTokens': llm_meta['completionTokens'], 'latencyMs': llm_latency, 'toolCalls': tool_results, 'cacheHit': False, 'retrievalLogId': str(log.id) if log.id else None}
    if settings.ai_enable_response_cache and grounded:
        _RESPONSE_CACHE[cache_key] = dict(payload)
    return payload

def _persist_assistant(db: Session, *, conv: ChatConversation, organization_id: uuid.UUID, result: dict[str, Any]) -> dict[str, Any]:
    assistant = ChatMessage(organization_id=organization_id, conversation_id=conv.id, role='assistant', content=result['content'], language_code=result['language'], citations_json=result['citations'], confidence=result['confidence'], reasoning_json=result['reasoning'], provider=result['provider'], model_name=result['model'], prompt_tokens=result['promptTokens'], completion_tokens=result['completionTokens'], latency_ms=result['latencyMs'], tool_calls_json=result['toolCalls'], metadata_json={'grounded': result['grounded'], 'cacheHit': result.get('cacheHit', False)})
    db.add(assistant)
    conv.updated_at = datetime.now(UTC)
    if conv.title == 'New chat':
        conv.title = result.get('content', 'Chat')[:60]
    db.flush()
    if result.get('retrievalLogId'):
        log = db.get(RetrievalLog, uuid.UUID(result['retrievalLogId'])) if result['retrievalLogId'] else None
        if log is None:
            logs = db.execute(select(RetrievalLog).where(RetrievalLog.conversation_id == conv.id).order_by(RetrievalLog.created_at.desc()).limit(1)).scalar_one_or_none()
            if logs:
                logs.message_id = assistant.id
        else:
            log.message_id = assistant.id
    return _serialize_message(assistant)

def _stream_and_persist(db: Session, *, conversation: ChatConversation, organization_id: uuid.UUID, language: str, result: dict[str, Any]) -> Iterator[str]:
    assistant = _persist_assistant(db, conv=conversation, organization_id=organization_id, result=result)
    meta = {'event': 'meta', 'conversationId': str(conversation.id), 'messageId': assistant['id'], 'citations': result['citations'], 'confidence': result['confidence'], 'reasoning': result['reasoning'], 'language': language, 'grounded': result['grounded']}
    yield f'data: {json.dumps(meta, ensure_ascii=False)}\n\n'
    words = result['content'].split(' ')
    buf: list[str] = []
    for word in words:
        buf.append(word)
        if len(buf) >= 3:
            chunk = ' '.join(buf) + ' '
            yield f"data: {json.dumps({'event': 'token', 'token': chunk}, ensure_ascii=False)}\n\n"
            buf = []
    if buf:
        yield f"data: {json.dumps({'event': 'token', 'token': ' '.join(buf)}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'event': 'done'})}\n\n"

def _default_system_prompt(language: str) -> str:
    _ = language
    return 'You are the EcoTrace AI Sustainability Copilot. Answer only from authorized evidence. Never invent facts. Always cite sources. Never suggest destructive actions.'

def _get_or_create_ai_settings(db: Session, organization_id: uuid.UUID) -> OrganizationAiSettings:
    row = db.execute(select(OrganizationAiSettings).where(OrganizationAiSettings.organization_id == organization_id)).scalar_one_or_none()
    if row:
        return row
    settings = get_settings()
    row = OrganizationAiSettings(organization_id=organization_id, preferred_provider=settings.ai_llm_provider, preferred_embedding_model=settings.ai_embedding_model, temperature=settings.ai_temperature, max_tokens=settings.ai_max_tokens, top_p=settings.ai_top_p, citation_mode=settings.ai_citation_mode, language_code='auto', monthly_budget_usd=settings.ai_monthly_budget_usd)
    db.add(row)
    db.flush()
    return row

def get_ai_settings(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    row = _get_or_create_ai_settings(db, organization_id)
    return _serialize_ai_settings(row)

def update_ai_settings(db: Session, user: User, organization_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_ai_manage(db, user, organization_id)
    row = _get_or_create_ai_settings(db, organization_id)
    mapping = {'preferredProvider': 'preferred_provider', 'preferred_provider': 'preferred_provider', 'preferredEmbeddingModel': 'preferred_embedding_model', 'preferred_embedding_model': 'preferred_embedding_model', 'temperature': 'temperature', 'maxTokens': 'max_tokens', 'max_tokens': 'max_tokens', 'topP': 'top_p', 'top_p': 'top_p', 'frequencyPenalty': 'frequency_penalty', 'frequency_penalty': 'frequency_penalty', 'presencePenalty': 'presence_penalty', 'presence_penalty': 'presence_penalty', 'systemPrompt': 'system_prompt', 'system_prompt': 'system_prompt', 'citationMode': 'citation_mode', 'citation_mode': 'citation_mode', 'languageCode': 'language_code', 'language_code': 'language_code', 'monthlyBudgetUsd': 'monthly_budget_usd', 'monthly_budget_usd': 'monthly_budget_usd'}
    for key, attr in mapping.items():
        if key in payload and payload[key] is not None:
            setattr(row, attr, payload[key])
    write_audit_log(db, action='ai.settings.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='organization_ai_settings', entity_id=str(row.id))
    db.flush()
    return _serialize_ai_settings(row)

def list_prompt_templates(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    rows = db.execute(select(PromptTemplate).where(or_(PromptTemplate.organization_id == organization_id, PromptTemplate.organization_id.is_(None)), PromptTemplate.is_active.is_(True))).scalars()
    return [{'id': str(r.id), 'code': r.code, 'name': r.name, 'scope': r.scope, 'versionNumber': r.version_number, 'templateBody': r.template_body, 'variables': r.variables_json or [], 'abGroup': r.ab_group} for r in rows]

def upsert_prompt_template(db: Session, user: User, organization_id: uuid.UUID, *, code: str, name: str, template_body: str, scope: str='organization', variables: list[str] | None=None, ab_group: str | None=None) -> dict[str, Any]:
    require_ai_manage(db, user, organization_id)
    existing = list(db.execute(select(PromptTemplate).where(PromptTemplate.organization_id == organization_id, PromptTemplate.code == code)).scalars())
    version = max((r.version_number for r in existing), default=0) + 1
    for row in existing:
        row.is_active = False
    row = PromptTemplate(organization_id=organization_id, owner_user_id=user.id, code=code, name=name, scope=scope, version_number=version, template_body=template_body, variables_json=variables or [], ab_group=ab_group, is_active=True)
    db.add(row)
    db.flush()
    return {'id': str(row.id), 'code': row.code, 'versionNumber': row.version_number, 'scope': row.scope}

def _upsert_memory(db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID, conversation_id: uuid.UUID, scope: str, key: str, value: dict[str, Any]) -> None:
    row = AiMemory(organization_id=organization_id, user_id=user_id, conversation_id=conversation_id, scope=scope, key=key, value_json=value)
    db.add(row)

def _get_owned_conversation(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> ChatConversation:
    conv = db.execute(select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.organization_id == organization_id, ChatConversation.owner_user_id == user.id, ChatConversation.status != 'deleted')).scalar_one_or_none()
    if conv is None:
        raise NotFoundError('Conversation not found.')
    return conv

def _get_accessible_conversation(db: Session, user: User, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> ChatConversation:
    conv = db.execute(select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.organization_id == organization_id, ChatConversation.status != 'deleted', or_(ChatConversation.owner_user_id == user.id, ChatConversation.is_shared_org.is_(True)))).scalar_one_or_none()
    if conv is None:
        raise NotFoundError('Conversation not found.')
    return conv

def _serialize_conversation(conv: ChatConversation) -> dict[str, Any]:
    return {'id': str(conv.id), 'organizationId': str(conv.organization_id), 'title': conv.title, 'status': conv.status, 'languageCode': conv.language_code, 'isPinned': conv.is_pinned, 'isFavorite': conv.is_favorite, 'isSharedOrg': conv.is_shared_org, 'folderId': str(conv.folder_id) if conv.folder_id else None, 'updatedAt': conv.updated_at.isoformat() if conv.updated_at else None, 'createdAt': conv.created_at.isoformat() if conv.created_at else None}

def _serialize_message(msg: ChatMessage) -> dict[str, Any]:
    return {'id': str(msg.id), 'conversationId': str(msg.conversation_id), 'role': msg.role, 'content': msg.content, 'languageCode': msg.language_code, 'citations': msg.citations_json or [], 'confidence': msg.confidence, 'reasoning': msg.reasoning_json, 'provider': msg.provider, 'modelName': msg.model_name, 'latencyMs': msg.latency_ms, 'createdAt': msg.created_at.isoformat() if msg.created_at else None}

def _serialize_ai_settings(row: OrganizationAiSettings) -> dict[str, Any]:
    return {'organizationId': str(row.organization_id), 'preferredProvider': row.preferred_provider, 'preferredEmbeddingModel': row.preferred_embedding_model, 'temperature': row.temperature, 'maxTokens': row.max_tokens, 'topP': row.top_p, 'frequencyPenalty': row.frequency_penalty, 'presencePenalty': row.presence_penalty, 'systemPrompt': row.system_prompt, 'citationMode': row.citation_mode, 'languageCode': row.language_code, 'monthlyBudgetUsd': row.monthly_budget_usd}
