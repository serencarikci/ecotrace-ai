from __future__ import annotations
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str

@dataclass(slots=True)
class LLMResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = 'stop'
    raw: dict[str, Any] = field(default_factory=dict)

class LLMProvider(Protocol):
    name: str

    def complete(self, *, messages: Sequence[ChatMessage], temperature: float, max_tokens: int, top_p: float, language: str) -> LLMResult:
        ...

    def stream(self, *, messages: Sequence[ChatMessage], temperature: float, max_tokens: int, top_p: float, language: str) -> AsyncIterator[str]:
        ...

class EmbeddingProvider(Protocol):
    name: str
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...

class Reranker(Protocol):
    name: str

    def rerank(self, *, query: str, documents: Sequence[str], top_k: int) -> list[tuple[int, float]]:
        ...

class OCREngine(Protocol):
    name: str

    def extract_text(self, *, content: bytes, content_type: str, file_name: str) -> str:
        ...
