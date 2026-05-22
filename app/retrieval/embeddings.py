import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class EmbeddingSettings(Protocol):
    embedding_provider: Literal["auto", "fake", "openai"]
    embedding_dimensions: int
    embedding_model: str
    embedding_include_dimensions: bool
    embedding_request_timeout_seconds: float
    openai_api_key: str | None
    openai_base_url: str | None


class DeterministicEmbeddingProvider:
    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive.")
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    api_key: str
    model: str
    dimensions: int
    base_url: str | None = None
    include_dimensions: bool = True
    timeout_seconds: float = 30.0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            import httpx
        except ModuleNotFoundError as exc:
            message = "httpx is required for OpenAI-compatible embeddings."
            raise EmbeddingProviderError(message) from exc

        url = f"{self._normalized_base_url()}/embeddings"
        payload = self._build_payload(texts)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError("Embedding API request failed.") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingProviderError("Embedding API returned invalid JSON.") from exc

        vectors = self._extract_vectors(data)
        self._validate_vectors(vectors, expected_count=len(texts))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _normalized_base_url(self) -> str:
        base_url = self.base_url or "https://api.openai.com/v1"
        return base_url.rstrip("/")

    def _build_payload(self, texts: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
        }
        if self.include_dimensions:
            payload["dimensions"] = self.dimensions
        return payload

    def _extract_vectors(self, data: Any) -> list[list[float]]:
        if not isinstance(data, dict):
            raise EmbeddingProviderError("Embedding API response must be a JSON object.")

        items = data.get("data")
        if not isinstance(items, list):
            raise EmbeddingProviderError("Embedding API response is missing a data list.")

        sorted_items = sorted(items, key=_response_index)
        vectors: list[list[float]] = []
        for item in sorted_items:
            if not isinstance(item, dict):
                raise EmbeddingProviderError("Embedding API response contains an invalid item.")
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise EmbeddingProviderError("Embedding API response contains an invalid vector.")
            vectors.append([float(value) for value in embedding])
        return vectors

    def _validate_vectors(self, vectors: list[list[float]], expected_count: int) -> None:
        if len(vectors) != expected_count:
            raise EmbeddingProviderError("Embedding API returned the wrong number of vectors.")

        for vector in vectors:
            if len(vector) != self.dimensions:
                message = "Embedding API returned a vector with wrong dimensions."
                raise EmbeddingProviderError(message)


def build_embedding_provider(settings: EmbeddingSettings) -> EmbeddingProvider:
    provider_name = settings.embedding_provider

    if provider_name == "fake":
        return DeterministicEmbeddingProvider(settings.embedding_dimensions)

    if provider_name == "openai":
        return _build_openai_provider(settings)

    if provider_name == "auto":
        if settings.openai_api_key:
            return _build_openai_provider(settings)
        return DeterministicEmbeddingProvider(settings.embedding_dimensions)

    raise ValueError(f"Unsupported embedding provider: {provider_name}")


def _build_openai_provider(settings: EmbeddingSettings) -> OpenAICompatibleEmbeddingProvider:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")

    return OpenAICompatibleEmbeddingProvider(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        include_dimensions=settings.embedding_include_dimensions,
        timeout_seconds=settings.embedding_request_timeout_seconds,
    )


def _response_index(item: Any) -> int:
    if not isinstance(item, dict):
        return 0
    try:
        return int(item.get("index", 0))
    except (TypeError, ValueError):
        return 0
