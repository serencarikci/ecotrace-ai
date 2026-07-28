from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ecotrace.core.ai.providers import (
    build_embedding_provider,
    build_reranker,
    cosine_similarity,
    tokenize_text,
)
from ecotrace.core.config import get_settings
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.application.chunking import bm25_score
from ecotrace.modules.knowledge.infrastructure.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
)
from ecotrace.shared.application.org_access import membership_role_codes, require_ai_read


@dataclass(slots=True)
class RetrievedEvidence:
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    content: str
    score: float
    page_number: int | None
    section_title: str | None
    language_code: str
    source_kind: str
    record_id: str | None
    url: str | None
    citation_label: str


def expand_query(query: str) -> list[str]:
    base = query.strip()
    variants = [base]
    lower = base.lower()
    if "emisyon" in lower or "emission" in lower:
        variants.append(base + " carbon inventory scope")
    if "ürün" in lower or "product" in lower:
        variants.append(base + " product carbon footprint passport")
    if "hedef" in lower or "target" in lower:
        variants.append(base + " sustainability target progress")
    seen: set[str] = set()
    out: list[str] = []
    for item in variants:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def hybrid_retrieve(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    query: str,
    top_k: int | None = None,
    document_type: str | None = None,
    language: str | None = None,
    include_drafts: bool = False,
) -> tuple[list[RetrievedEvidence], dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    settings = get_settings()
    top_k = top_k or settings.ai_retrieval_top_k
    roles = membership_role_codes(db, user, organization_id)
    t0 = time.perf_counter()
    expanded = expand_query(query)
    embedder = build_embedding_provider(settings)
    t_emb0 = time.perf_counter()
    query_vector = embedder.embed_query(query)
    embedding_latency_ms = int((time.perf_counter() - t_emb0) * 1000)
    doc_stmt = select(KnowledgeDocument).where(KnowledgeDocument.organization_id == organization_id)
    if include_drafts:
        doc_stmt = doc_stmt.where(KnowledgeDocument.status.in_(["published", "draft"]))
    else:
        doc_stmt = doc_stmt.where(KnowledgeDocument.status == "published")
    if document_type:
        doc_stmt = doc_stmt.where(KnowledgeDocument.document_type == document_type)
    if language:
        doc_stmt = doc_stmt.where(
            or_(
                KnowledgeDocument.language_code == language,
                KnowledgeDocument.language_code == "multi",
            )
        )
    docs = list(db.execute(doc_stmt).scalars())
    allowed_doc_ids = {d.id for d in docs if _permission_allows(d.permissions_json, roles)}
    if not allowed_doc_ids:
        metrics = {
            "expandedQueries": expanded,
            "embeddingLatencyMs": embedding_latency_ms,
            "retrievalLatencyMs": int((time.perf_counter() - t0) * 1000),
            "candidateCount": 0,
        }
        return ([], metrics)
    chunk_stmt = select(KnowledgeChunk).where(
        KnowledgeChunk.organization_id == organization_id,
        KnowledgeChunk.is_active.is_(True),
        KnowledgeChunk.document_id.in_(allowed_doc_ids),
    )
    chunks = list(db.execute(chunk_stmt).scalars())
    if not chunks:
        metrics = {
            "expandedQueries": expanded,
            "embeddingLatencyMs": embedding_latency_ms,
            "retrievalLatencyMs": int((time.perf_counter() - t0) * 1000),
            "candidateCount": 0,
        }
        return ([], metrics)
    doc_by_id = {d.id: d for d in docs}
    emb_rows = list(
        db.execute(
            select(KnowledgeEmbedding).where(
                KnowledgeEmbedding.organization_id == organization_id,
                KnowledgeEmbedding.chunk_id.in_([c.id for c in chunks]),
            )
        ).scalars()
    )
    emb_by_chunk = {e.chunk_id: e for e in emb_rows}
    q_tokens = tokenize_text(query)
    avgdl = sum(len(tokenize_text(c.content)) for c in chunks) / max(len(chunks), 1)
    candidates: list[tuple[KnowledgeChunk, float]] = []
    for chunk in chunks:
        tokens = tokenize_text(chunk.content)
        lexical = bm25_score(q_tokens, tokens, avgdl=avgdl, dl=max(len(tokens), 1))
        keyword = len(q_tokens & tokens) / max(len(q_tokens), 1)
        semantic = 0.0
        emb = emb_by_chunk.get(chunk.id)
        if emb and emb.vector_json:
            semantic = cosine_similarity(query_vector, emb.vector_json)
        score = 0.55 * semantic + 0.3 * lexical + 0.15 * keyword
        for alt in expanded[1:]:
            alt_tokens = tokenize_text(alt)
            score += 0.05 * (len(alt_tokens & tokens) / max(len(alt_tokens), 1))
        candidates.append((chunk, float(score)))
    candidates.sort(key=lambda item: item[1], reverse=True)
    pre = candidates[: max(top_k * 3, top_k)]
    reranker = build_reranker(settings)
    documents = [c.content for c, _ in pre]
    ranked = reranker.rerank(query=query, documents=documents, top_k=top_k)
    evidence: list[RetrievedEvidence] = []
    for rank_idx, (doc_idx, rerank_score) in enumerate(ranked):
        chunk, base_score = pre[doc_idx]
        doc = doc_by_id.get(chunk.document_id)
        if doc is None:
            continue
        final = 0.7 * rerank_score + 0.3 * base_score
        label = f"E{rank_idx + 1}"
        evidence.append(
            RetrievedEvidence(
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                document_title=doc.title,
                document_type=doc.document_type,
                content=chunk.content,
                score=float(final),
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                language_code=chunk.language_code,
                source_kind="document",
                record_id=str(doc.source_record_id) if doc.source_record_id else str(doc.id),
                url=None,
                citation_label=label,
            )
        )
    metrics = {
        "expandedQueries": expanded,
        "embeddingLatencyMs": embedding_latency_ms,
        "retrievalLatencyMs": int((time.perf_counter() - t0) * 1000),
        "candidateCount": len(candidates),
        "reranker": reranker.name,
        "embeddingProvider": embedder.name,
    }
    return (evidence, metrics)


def build_context_prompt(evidence: list[RetrievedEvidence], *, language: str) -> str:
    if language == "tr":
        header = "Yalnızca aşağıdaki yetkili kanıtları kullan. Kanıt yoksa uydurma. Her iddiayı [E#] ile doğrula."
    else:
        header = "Use only the authorized evidence below. Do not invent facts. Ground every claim with [E#] citations."
    blocks = [header, ""]
    for item in evidence:
        blocks.append(
            f"[{item.citation_label}] title={item.document_title}; type={item.document_type}; page={item.page_number}; chunk={item.chunk_id}\n{item.content}"
        )
        blocks.append("")
    return "\n".join(blocks)


def citations_from_evidence(evidence: list[RetrievedEvidence]) -> list[dict[str, Any]]:
    return [
        {
            "label": e.citation_label,
            "documentName": e.document_title,
            "documentId": e.document_id,
            "pageNumber": e.page_number,
            "chunkId": e.chunk_id,
            "databaseSource": e.source_kind,
            "recordId": e.record_id,
            "url": e.url,
            "score": round(e.score, 4),
            "snippet": e.content[:240],
        }
        for e in evidence
    ]


def confidence_from_evidence(evidence: list[RetrievedEvidence]) -> float:
    if not evidence:
        return 0.0
    top = evidence[0].score
    mean = sum(e.score for e in evidence) / len(evidence)
    return float(max(0.0, min(1.0, 0.5 * top + 0.5 * mean)))


def _permission_allows(permissions: dict[str, Any] | None, roles: set[str]) -> bool:
    if permissions is None:
        return True
    visibility = permissions.get("visibility", "organization")
    if visibility == "organization":
        return True
    allowed_roles = set(permissions.get("roles") or [])
    if not allowed_roles:
        return True
    if "organization_member" in allowed_roles:
        return True
    return bool(roles.intersection(allowed_roles))
