from __future__ import annotations

import hashlib
import math
import re
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from ecotrace.core.ai.protocols import (
    ChatMessage,
    EmbeddingProvider,
    LLMProvider,
    LLMResult,
    OCREngine,
    Reranker,
)
from ecotrace.core.ai_constants import (
    DEFAULT_EMBEDDING_DIM,
    INSUFFICIENT_EVIDENCE_EN,
)


def tokenize_text(text: str) -> set[str]:
    return {t for t in re.findall("[a-zA-Z0-9]{2,}", text.lower())}


def _tokenize(text: str) -> set[str]:
    return tokenize_text(text)


def detect_language(text: str) -> str:
    _ = text
    return "en"


class LocalHashEmbedding:
    name = "local_hash"
    dimensions = DEFAULT_EMBEDDING_DIM

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self.dimensions:
            seed = hashlib.sha256(seed).digest()
            for b in seed:
                values.append(b / 255.0 * 2.0 - 1.0)
                if len(values) >= self.dimensions:
                    break
        for token in sorted(_tokenize(text))[:64]:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % self.dimensions
            values[idx] = min(1.0, max(-1.0, values[idx] + 0.15))
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class LocalLexicalReranker:
    name = "local_lexical"

    def rerank(
        self, *, query: str, documents: Sequence[str], top_k: int
    ) -> list[tuple[int, float]]:
        q = _tokenize(query)
        scored: list[tuple[int, float]] = []
        for idx, doc in enumerate(documents):
            d = _tokenize(doc)
            if not q or not d:
                scored.append((idx, 0.0))
                continue
            overlap = len(q & d)
            score = overlap / math.sqrt(len(q) * len(d))
            scored.append((idx, float(score)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class LocalGroundedLLM:
    name = "local_grounded"

    def complete(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float,
        max_tokens: int,
        top_p: float,
        language: str,
    ) -> LLMResult:
        _ = (temperature, max_tokens, top_p)
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        system = next((m.content for m in messages if m.role == "system"), "")
        content = self._synthesize(user=user, system=system, language=language)
        return LLMResult(
            content=content,
            provider=self.name,
            model="ecotrace-local-grounded",
            prompt_tokens=max(1, len(system) // 4),
            completion_tokens=max(1, len(content) // 4),
        )

    async def stream(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float,
        max_tokens: int,
        top_p: float,
        language: str,
    ) -> AsyncIterator[str]:
        result = self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            language=language,
        )
        for token in _chunk_tokens(result.content):
            yield token

    def _synthesize(self, *, user: str, system: str, language: str) -> str:
        _ = language
        evidence_blocks = re.findall("\\[E(\\d+)\\](.*?)(?=\\[E\\d+\\]|\\Z)", system, flags=re.S)
        if not evidence_blocks:
            return INSUFFICIENT_EVIDENCE_EN
        lines: list[str] = []
        lines.append("Answer grounded in authorized EcoTrace evidence:")
        for idx, body in evidence_blocks[:5]:
            snippet = " ".join(body.strip().split())[:280]
            lines.append(f"- {snippet} [E{idx}]")
        lines.append("")
        lines.append(f"Question context: {user[:240]}")
        lines.append("Confidence: medium (evidence-backed, not certified).")
        return "\n".join(lines)


class HttpOpenAICompatibleLLM:
    name = "openai"

    def __init__(
        self, *, api_key: str, base_url: str, model: str, provider_name: str = "openai"
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = provider_name

    def complete(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float,
        max_tokens: int,
        top_p: float,
        language: str,
    ) -> LLMResult:
        import httpx

        _ = language
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return LLMResult(
            content=choice["message"]["content"],
            provider=self.name,
            model=self.model,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            finish_reason=str(choice.get("finish_reason") or "stop"),
            raw=data,
        )

    async def stream(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float,
        max_tokens: int,
        top_p: float,
        language: str,
    ) -> AsyncIterator[str]:
        result = self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            language=language,
        )
        for token in _chunk_tokens(result.content):
            yield token


class TesseractOCR:
    name = "tesseract"

    def extract_text(self, *, content: bytes, content_type: str, file_name: str) -> str:
        _ = (content_type, file_name)
        try:
            import io

            import pytesseract
            from PIL import Image
        except ImportError:
            return ""
        try:
            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image) or ""
        except Exception:
            return ""


class NoOCR:
    name = "none"

    def extract_text(self, *, content: bytes, content_type: str, file_name: str) -> str:
        _ = (content, content_type, file_name)
        return ""


def _chunk_tokens(text: str) -> Iterator[str]:
    words = text.split(" ")
    buf: list[str] = []
    for word in words:
        buf.append(word)
        if len(buf) >= 4:
            yield (" ".join(buf) + " ")
            buf = []
    if buf:
        yield " ".join(buf)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    an = math.sqrt(sum(x * x for x in a)) or 1.0
    bn = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum((x * y for x, y in zip(a, b, strict=False))) / (an * bn)


def build_llm_provider(settings: Any) -> LLMProvider:
    provider = getattr(settings, "ai_llm_provider", "local_grounded")
    if provider == "local_grounded" or not getattr(settings, "ai_llm_api_key", None):
        return LocalGroundedLLM()
    model = getattr(settings, "ai_llm_model", "gpt-4o-mini")
    base = getattr(settings, "ai_llm_base_url", "https://api.openai.com/v1")
    key = settings.ai_llm_api_key
    mapping = {
        "openai": ("openai", base or "https://api.openai.com/v1"),
        "azure_openai": ("azure_openai", base),
        "openrouter": ("openrouter", base or "https://openrouter.ai/api/v1"),
        "ollama": ("ollama", base or "http://localhost:11434/v1"),
        "lm_studio": ("lm_studio", base or "http://localhost:1234/v1"),
        "anthropic": ("anthropic", base or "https://api.anthropic.com/v1"),
        "gemini": ("gemini", base or "https://generativelanguage.googleapis.com/v1beta/openai"),
    }
    name, url = mapping.get(provider, (provider, base or "https://api.openai.com/v1"))
    return HttpOpenAICompatibleLLM(api_key=key, base_url=url, model=model, provider_name=name)


def build_embedding_provider(settings: Any) -> EmbeddingProvider:
    provider = getattr(settings, "ai_embedding_provider", "local_hash")
    if provider == "local_hash" or not getattr(settings, "ai_embedding_api_key", None):
        return LocalHashEmbedding()
    return LocalHashEmbedding()


def build_reranker(settings: Any) -> Reranker:
    name = getattr(settings, "ai_reranker", "local_lexical")
    if name in {"none"}:
        return LocalLexicalReranker()
    return LocalLexicalReranker()


def build_ocr_engine(settings: Any) -> OCREngine:
    name = getattr(settings, "ai_ocr_engine", "tesseract")
    if name == "tesseract":
        return TesseractOCR()
    return NoOCR()
