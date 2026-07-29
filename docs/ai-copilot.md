# AI Sustainability Copilot & Enterprise Knowledge Platform

**Version:** 0.6.0  
**Status:** Delivered (local-grounded default provider)

## Summary

EcoTrace AI provides a grounded sustainability intelligence platform. The copilot answers only from authorized organization evidence (documents + structured services), always attaches citations, and refuses unsupported claims.

## AI architecture

```
User question
    → AuthZ / org membership
    → Permission filtering (before retrieval)
    → Query expansion
    → Embedding + BM25/keyword hybrid search
    → Reranking
    → Context + prompt assembly
    → LLM provider abstraction
    → Grounded answer + citations + confidence + reasoning
```

Modules:

| Module | Responsibility |
|--------|----------------|
| `core/ai` | Protocols + provider factories (LLM, embeddings, OCR, rerank, vector) |
| `modules/knowledge` | Documents, versions, chunks, embeddings, ingestion/chunking |
| `modules/retrieval` | Hybrid search, context/citation builders |
| `modules/ai_copilot` | Chat, memory, prompts, tools, evaluation |
| `modules/enterprise_search` | Universal search, autocomplete, saved searches, analytics |

## RAG pipeline

1. **Permission filtering** — org scope + published status + role visibility on documents/chunks  
2. **Query expansion** — domain synonyms (emissions/inventory/passport/targets)  
3. **Embedding search** — configurable embedding provider (default `local_hash`)  
4. **Hybrid fusion** — semantic + BM25 + keyword overlap  
5. **Reranking** — configurable reranker (default `local_lexical`)  
6. **Context building** — numbered `[E#]` evidence blocks  
7. **Prompt generation** — org system prompt + evidence + short-term history  
8. **LLM** — interchangeable provider  
9. **Grounding** — if no evidence/tools → insufficient-evidence response  
10. **Citations** — document name, page, chunk id, DB source, record id, URL  

## Provider abstraction

Configured via settings / org AI settings:

- LLM: OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, LM Studio, OpenRouter, `local_grounded`
- Embeddings: OpenAI, BGE, E5, Instructor, Nomic, Sentence Transformers, Ollama, `local_hash`
- Vector backends: pgvector (default storage JSONB + optional extension), Qdrant, Milvus, Weaviate, Pinecone, Chroma
- Rerankers: none, cross-encoder, BGE, Cohere, Jina, `local_lexical`
- OCR: none, Tesseract, EasyOCR, PaddleOCR (soft imports)

Business code depends only on protocols in `ecotrace.core.ai.protocols`.

## Embedding strategy

- Default deterministic `local_hash` (384-d) for offline/dev/test
- Vectors stored in `knowledge_embeddings.vector_json` (portable)
- Migration enables `vector` + `pg_trgm` when available for production scale-out
- Chunk metadata always includes organization, permissions, language, document, tags

## Hybrid search

Semantic cosine + BM25-style lexical + keyword overlap, then rerank. Filters:

- organization
- permissions
- document type
- language
- published-only (default)

## Security model

- `require_ai_read/write/manage/admin` gates
- Retrieval never runs before org authorization
- Cross-org ids return 404/403
- Chunks inherit document permissions JSON
- LLM tools call backend service helpers — no direct arbitrary SQL from the model
- Chat actions are limited to `SAFE_AI_ACTIONS` (no destructive operations)

## Citation system

Every assistant message stores `citations_json` with:

- label (`E#` / `T#`)
- document name / tool name
- page number
- chunk id
- database source
- record id
- optional public URL
- snippet + score

UI renders citation cards and source preview.

## Prompt management

`prompt_templates` supports system / organization / user scopes, variables (`{{name}}`), versioning, and A/B groups. Org AI settings store preferred provider, temperature, max tokens, citation mode, language, budget.

## Memory

`ai_memories` scopes: short-term (conversation), plus extension points for long-term / org / user memory with session isolation via conversation and user foreign keys.

## Evaluation methodology

`evaluation_runs` computes:

precision, recall, MRR, NDCG, faithfulness, answer relevance, citation accuracy, latency, hallucination rate, context precision.

## Observability & cost

`retrieval_logs` tracks retrieval/embedding/LLM latency, tokens, cache hits, provider, tool usage. Admin cost dashboard aggregates token estimates.

## Frontend

Angular Material pages:

- `/app/ai` — chat (history, citations, confidence, reasoning, copy/feedback/retry/stop)
- `/app/ai/documents` — upload & index
- `/app/ai/search` — enterprise hybrid search
- `/app/ai/admin` — providers, prompts, logs, cost, evaluations, settings, chunks

## API surface (org-scoped)

- `POST /ai/chat`, `POST /ai/chat/stream`
- Conversations CRUD + export + folders + feedback
- Knowledge document upload/list/get/archive + chunks
- `POST /search`, autocomplete, saved searches
- AI settings, prompts, evaluations, analytics, retrieval logs, providers, cost dashboard

## Database (`0006_ai`)

documents, document_versions, chunks, embeddings, chat_folders/conversations/messages, prompt_templates, provider_configs, organization_ai_settings, retrieval_logs, conversation_feedback, evaluation_runs, saved_searches, ai_memories

## Performance notes

- Designed for 100k+ chunks via indexed org/document filters + optional pgvector/trgm
- Streaming SSE for chat
- Response/embedding cache hooks (`AI_ENABLE_RESPONSE_CACHE`)
- Connection pooling via existing SQLAlchemy engine

## Known limitations

- External LLM/embedding HTTP providers use OpenAI-compatible chat completions when API keys are set; otherwise local grounded synthesizer is used
- OCR/PDF advanced extractors are soft-dependent (Tesseract/pypdf optional)
- Vector backends beyond JSONB/pgvector are abstracted but default runtime uses in-DB JSON vectors
- Angular chat renders markdown as preformatted text (tables/code highlighted structurally via citations/reasoning panels)
- Docker Compose health not re-validated in this delivery pass unless run separately

## Extension points

Prepared but **not implemented**:

- autonomous sustainability agents
- workflow automation / scheduled AI reports
- anomaly detection & forecasting
- optimization engine
- supplier AI assistant / regulatory intelligence
- MCP / Model Context Protocol tool ecosystem
- virus-scan hook already stubbed in ingestion

Further automation modules are documented separately.

> Note: Platform completed in v0.7.1. See docs/automation-intelligence.md and docs/final-system-overview.md.
