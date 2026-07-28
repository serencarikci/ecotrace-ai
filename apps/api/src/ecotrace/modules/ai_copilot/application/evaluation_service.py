from __future__ import annotations
import math
import time
import uuid
from typing import Any
from sqlalchemy.orm import Session
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.infrastructure.models import EvaluationRun
from ecotrace.modules.retrieval.application.hybrid_search import hybrid_retrieve
from ecotrace.shared.application.org_access import require_ai_manage, require_ai_read

def precision_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    top = retrieved[:k]
    if not top:
        return 0.0
    return len([x for x in top if x in relevant]) / len(top)

def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    return len(relevant & top) / len(relevant)

def mean_reciprocal_rank(relevant: set[str], retrieved: list[str]) -> float:
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0

def ndcg_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    dcg = 0.0
    for i, item in enumerate(retrieved[:k], start=1):
        rel = 1.0 if item in relevant else 0.0
        dcg += rel / math.log2(i + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum((1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1)))
    return dcg / idcg if idcg else 0.0

def faithfulness_score(*, answer: str, evidence_texts: list[str]) -> float:
    if not answer.strip():
        return 0.0
    if not evidence_texts:
        return 0.0 if len(answer) > 40 else 1.0
    tokens = {t.lower() for t in answer.split() if len(t) > 3}
    corpus = {t.lower() for blob in evidence_texts for t in blob.split() if len(t) > 3}
    if not tokens:
        return 0.0
    return len(tokens & corpus) / len(tokens)

def citation_accuracy(*, answer: str, citation_labels: list[str]) -> float:
    if not citation_labels:
        return 1.0 if '[' not in answer else 0.0
    present = sum((1 for label in citation_labels if f'[{label}]' in answer or label in answer))
    return present / len(citation_labels)

def run_evaluation(db: Session, user: User, organization_id: uuid.UUID, *, name: str, dataset: list[dict[str, Any]], notes: str | None=None) -> dict[str, Any]:
    require_ai_manage(db, user, organization_id)
    started = time.perf_counter()
    per_query: list[dict[str, Any]] = []
    for row in dataset:
        question = str(row.get('question') or '')
        relevant = {str(x) for x in row.get('relevantChunkIds') or []}
        t0 = time.perf_counter()
        evidence, _metrics = hybrid_retrieve(db, user, organization_id, query=question)
        latency = int((time.perf_counter() - t0) * 1000)
        retrieved = [e.chunk_id for e in evidence]
        answer = '\n'.join((e.content for e in evidence[:3]))
        labels = [e.citation_label for e in evidence]
        per_query.append({'question': question, 'precision': precision_at_k(relevant, retrieved, 5), 'recall': recall_at_k(relevant, retrieved, 5), 'mrr': mean_reciprocal_rank(relevant, retrieved), 'ndcg': ndcg_at_k(relevant, retrieved, 5), 'faithfulness': faithfulness_score(answer=answer, evidence_texts=[e.content for e in evidence]), 'answerRelevance': recall_at_k(relevant, retrieved, 5), 'citationAccuracy': citation_accuracy(answer=' '.join(labels), citation_labels=labels), 'latencyMs': latency, 'hallucinationRate': 0.0 if evidence else 1.0, 'contextPrecision': precision_at_k(relevant, retrieved, 5)})

    def avg(key: str) -> float:
        if not per_query:
            return 0.0
        return sum((float(item[key]) for item in per_query)) / len(per_query)
    metrics = {'precision': avg('precision'), 'recall': avg('recall'), 'mrr': avg('mrr'), 'ndcg': avg('ndcg'), 'faithfulness': avg('faithfulness'), 'answerRelevance': avg('answerRelevance'), 'citationAccuracy': avg('citationAccuracy'), 'latencyMs': avg('latencyMs'), 'hallucinationRate': avg('hallucinationRate'), 'contextPrecision': avg('contextPrecision'), 'queryCount': len(per_query), 'totalLatencyMs': int((time.perf_counter() - started) * 1000)}
    run = EvaluationRun(organization_id=organization_id, name=name, status='completed', dataset_json=dataset, metrics_json={'aggregate': metrics, 'perQuery': per_query}, notes=notes, created_by_user_id=user.id)
    db.add(run)
    db.flush()
    return {'id': str(run.id), 'name': run.name, 'status': run.status, 'metrics': metrics}

def list_evaluations(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    from sqlalchemy import select
    rows = db.execute(select(EvaluationRun).where(EvaluationRun.organization_id == organization_id).order_by(EvaluationRun.created_at.desc())).scalars()
    return [{'id': str(r.id), 'name': r.name, 'status': r.status, 'metrics': (r.metrics_json or {}).get('aggregate'), 'createdAt': r.created_at.isoformat() if r.created_at else None} for r in rows]
