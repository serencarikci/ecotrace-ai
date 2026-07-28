from __future__ import annotations
import hashlib
import math
import re
from dataclasses import dataclass

@dataclass(slots=True)
class TextChunk:
    content: str
    chunk_index: int
    section_title: str | None = None
    page_number: int | None = None
    token_estimate: int = 0

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def clean_text(text: str) -> str:
    text = text.replace('\x00', ' ')
    text = re.sub('[ \\t]+', ' ', text)
    text = re.sub('\\n{3,}', '\n\n', text)
    return text.strip()

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def chunk_text(text: str, *, strategy: str='markdown', chunk_size: int=800, overlap: int=120) -> list[TextChunk]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    if strategy in {'heading', 'markdown'}:
        return _chunk_markdown(cleaned, chunk_size=chunk_size, overlap=overlap)
    if strategy == 'table':
        return _chunk_tables(cleaned, chunk_size=chunk_size, overlap=overlap)
    if strategy == 'code':
        return _chunk_code(cleaned, chunk_size=chunk_size, overlap=overlap)
    if strategy == 'semantic':
        return _chunk_semantic(cleaned, chunk_size=chunk_size, overlap=overlap)
    return _chunk_fixed(cleaned, chunk_size=chunk_size, overlap=overlap)

def _chunk_fixed(text: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(TextChunk(content=piece, chunk_index=index, token_estimate=estimate_tokens(piece)))
            index += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return _dedupe(chunks)

def _chunk_markdown(text: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    sections = re.split('(?m)(?=^#{1,6}\\s+)', text)
    chunks: list[TextChunk] = []
    index = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match('^(#{1,6})\\s+(.+)$', section, flags=re.M)
        title = title_match.group(2).strip() if title_match else None
        if len(section) <= chunk_size:
            chunks.append(TextChunk(content=section, chunk_index=index, section_title=title, token_estimate=estimate_tokens(section)))
            index += 1
            continue
        for piece in _chunk_fixed(section, chunk_size=chunk_size, overlap=overlap):
            chunks.append(TextChunk(content=piece.content, chunk_index=index, section_title=title, token_estimate=piece.token_estimate))
            index += 1
    return _dedupe(chunks)

def _chunk_tables(text: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    blocks = re.split('\\n\\s*\\n', text)
    chunks: list[TextChunk] = []
    index = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if '|' in block or '\t' in block:
            chunks.append(TextChunk(content=block[:chunk_size * 2], chunk_index=index, section_title='table', token_estimate=estimate_tokens(block)))
            index += 1
        else:
            for piece in _chunk_fixed(block, chunk_size=chunk_size, overlap=overlap):
                chunks.append(TextChunk(content=piece.content, chunk_index=index, token_estimate=piece.token_estimate))
                index += 1
    return _dedupe(chunks)

def _chunk_code(text: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    parts = re.split('(```[\\s\\S]*?```)', text)
    chunks: list[TextChunk] = []
    index = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        label = 'code' if part.startswith('```') else None
        for piece in _chunk_fixed(part, chunk_size=chunk_size, overlap=overlap):
            chunks.append(TextChunk(content=piece.content, chunk_index=index, section_title=label, token_estimate=piece.token_estimate))
            index += 1
    return _dedupe(chunks)

def _chunk_semantic(text: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    sentences = re.split('(?<=[.!?])\\s+', text)
    chunks: list[TextChunk] = []
    buf: list[str] = []
    index = 0
    size = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if size + len(sentence) > chunk_size and buf:
            content = ' '.join(buf)
            chunks.append(TextChunk(content=content, chunk_index=index, token_estimate=estimate_tokens(content)))
            index += 1
            overlap_text = content[-overlap:] if overlap else ''
            buf = [overlap_text, sentence] if overlap_text else [sentence]
            size = sum((len(x) for x in buf))
        else:
            buf.append(sentence)
            size += len(sentence)
    if buf:
        content = ' '.join(buf).strip()
        if content:
            chunks.append(TextChunk(content=content, chunk_index=index, token_estimate=estimate_tokens(content)))
    return _dedupe(chunks)

def _dedupe(chunks: list[TextChunk]) -> list[TextChunk]:
    seen: set[str] = set()
    out: list[TextChunk] = []
    for chunk in chunks:
        digest = content_hash(chunk.content)
        if digest in seen:
            continue
        seen.add(digest)
        out.append(chunk)
    for i, chunk in enumerate(out):
        chunk.chunk_index = i
    return out

def bm25_score(query_tokens: set[str], doc_tokens: set[str], *, avgdl: float, dl: int) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    k1 = 1.5
    b = 0.75
    score = 0.0
    for token in query_tokens:
        if token not in doc_tokens:
            continue
        tf = 1.0
        idf = math.log(1.0 + 1.0)
        denom = tf + k1 * (1 - b + b * (dl / max(avgdl, 1.0)))
        score += idf * (tf * (k1 + 1) / denom)
    return float(score)
