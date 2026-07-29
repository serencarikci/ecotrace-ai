from __future__ import annotations
from ecotrace.core.ai.protocols import ChatMessage
from ecotrace.core.ai.providers import LocalGroundedLLM, LocalHashEmbedding, LocalLexicalReranker, build_embedding_provider, build_llm_provider, build_reranker, detect_language
from ecotrace.core.ai_constants import INSUFFICIENT_EVIDENCE_EN, SAFE_AI_ACTIONS
from ecotrace.modules.ai_copilot.application.evaluation_service import citation_accuracy, faithfulness_score, mean_reciprocal_rank, ndcg_at_k, precision_at_k, recall_at_k
from ecotrace.modules.ai_copilot.application.tools import detect_safe_actions
from ecotrace.modules.knowledge.application.chunking import chunk_text, clean_text
from ecotrace.modules.knowledge.application.ingestion import extract_text_from_bytes, slugify

class _Settings:
    ai_llm_provider = 'local_grounded'
    ai_llm_api_key = None
    ai_embedding_provider = 'local_hash'
    ai_embedding_api_key = None
    ai_reranker = 'local_lexical'

def test_detect_language_defaults_to_english() -> None:
    assert detect_language('What is the carbon inventory total?') == 'en'
    assert detect_language('any text') == 'en'

def test_local_hash_embedding_dimensions() -> None:
    emb = LocalHashEmbedding()
    vec = emb.embed_query('scope 1 emissions')
    assert len(vec) == emb.dimensions
    assert abs(sum((v * v for v in vec)) - 1.0) < 1e-06

def test_local_grounded_llm_requires_evidence() -> None:
    llm = LocalGroundedLLM()
    result = llm.complete(messages=[ChatMessage(role='system', content='No evidence here'), ChatMessage(role='user', content='How much CO2?')], temperature=0.1, max_tokens=100, top_p=0.9, language='en')
    assert INSUFFICIENT_EVIDENCE_EN in result.content

def test_local_grounded_llm_with_evidence() -> None:
    llm = LocalGroundedLLM()
    result = llm.complete(messages=[ChatMessage(role='system', content='[E1] Inventory total is 12.5 tCO2e for 2024.'), ChatMessage(role='user', content='What is the inventory total?')], temperature=0.1, max_tokens=200, top_p=0.9, language='en')
    assert '[E1]' in result.content
    assert '12.5' in result.content

def test_provider_factory_defaults_local() -> None:
    assert build_llm_provider(_Settings()).name == 'local_grounded'
    assert build_embedding_provider(_Settings()).name == 'local_hash'
    assert build_reranker(_Settings()).name == 'local_lexical'

def test_reranker_orders_by_overlap() -> None:
    reranker = LocalLexicalReranker()
    ranked = reranker.rerank(query='carbon inventory scope', documents=['unrelated text', 'carbon inventory scope 1 totals', 'passport slug'], top_k=2)
    assert ranked[0][0] == 1

def test_chunking_markdown_and_dedupe() -> None:
    text = '# Title\n\nParagraph one about carbon.\n\n## Section\n\nMore carbon policy text here.'
    chunks = chunk_text(text, strategy='markdown', chunk_size=200, overlap=20)
    assert chunks
    assert clean_text(' a \n\n\n b ') == 'a \n\n b'

def test_ingestion_txt_and_slug() -> None:
    text, meta = extract_text_from_bytes(content=b'Sustainability policy for carbon management.', file_name='policy.txt', content_type='text/plain')
    assert 'Sustainability' in text
    assert meta['extractor'] in {'txt', 'text'}
    assert slugify('Demo Policy 2024!') == 'demo-policy-2024'

def test_evaluation_metrics() -> None:
    relevant = {'a', 'b'}
    retrieved = ['b', 'x', 'a']
    assert precision_at_k(relevant, retrieved, 2) == 0.5
    assert recall_at_k(relevant, retrieved, 3) == 1.0
    assert mean_reciprocal_rank(relevant, retrieved) == 1.0
    assert ndcg_at_k(relevant, retrieved, 3) > 0
    assert faithfulness_score(answer='carbon inventory total', evidence_texts=['carbon inventory']) > 0
    assert citation_accuracy(answer='See [E1]', citation_labels=['E1']) == 1.0

def test_safe_actions_detection() -> None:
    actions = detect_safe_actions('summarize inventory and explain scope breakdown')
    assert 'summarize_inventory' in actions
    assert actions[0] in SAFE_AI_ACTIONS
