from __future__ import annotations
from typing import Final
AI_ENGINE_VERSION: Final[str] = 'ecotrace-ai-copilot-0.6.0'
DEFAULT_EMBEDDING_DIM: Final[int] = 384
LLM_PROVIDERS: Final[frozenset[str]] = frozenset({'openai', 'azure_openai', 'anthropic', 'gemini', 'ollama', 'lm_studio', 'openrouter', 'local_grounded'})
EMBEDDING_PROVIDERS: Final[frozenset[str]] = frozenset({'openai', 'bge', 'e5', 'instructor', 'nomic', 'sentence_transformers', 'ollama', 'local_hash'})
VECTOR_BACKENDS: Final[frozenset[str]] = frozenset({'pgvector', 'qdrant', 'milvus', 'weaviate', 'pinecone', 'chroma'})
RERANKERS: Final[frozenset[str]] = frozenset({'none', 'cross_encoder', 'bge', 'cohere', 'jina', 'local_lexical'})
OCR_ENGINES: Final[frozenset[str]] = frozenset({'none', 'tesseract', 'easyocr', 'paddleocr'})
DOCUMENT_TYPES: Final[frozenset[str]] = frozenset({'policy', 'procedure', 'report', 'meeting_notes', 'supplier_document', 'manual', 'training', 'technical', 'passport_document', 'invoice', 'certificate', 'other'})
DOCUMENT_STATUSES: Final[frozenset[str]] = frozenset({'draft', 'processing', 'published', 'archived', 'superseded', 'failed'})
CHUNKING_STRATEGIES: Final[frozenset[str]] = frozenset({'fixed', 'semantic', 'heading', 'markdown', 'table', 'code'})
CONVERSATION_STATUSES: Final[frozenset[str]] = frozenset({'active', 'archived', 'shared', 'deleted'})
MESSAGE_ROLES: Final[frozenset[str]] = frozenset({'user', 'assistant', 'system', 'tool'})
INSUFFICIENT_EVIDENCE_EN: Final[str] = 'I could not find sufficient authorized evidence in EcoTrace data to answer this confidently. No unsupported claims are provided.'
INSUFFICIENT_EVIDENCE_TR: Final[str] = 'Bu soruyu güvenle yanıtlamak için yetkili EcoTrace verilerinde yeterli kanıt bulunamadı. Desteklenmeyen iddialar üretilmez.'
SAFE_AI_ACTIONS: Final[frozenset[str]] = frozenset({'summarize_inventory', 'compare_inventories', 'explain_emission_increase', 'highest_emitting_facility', 'explain_scope_breakdown', 'summarize_product_footprint', 'summarize_passport', 'compare_products', 'compare_scenarios', 'explain_target_progress', 'generate_sustainability_summary', 'find_related_documents', 'locate_evidence'})
