from types import SimpleNamespace
from typing import Callable

from app.retrieval.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProviderError,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)


def _assert_raises(
    expected_error: type[Exception],
    message: str,
    callback: Callable[[], object],
) -> None:
    try:
        callback()
    except expected_error as exc:
        assert message in str(exc)
    else:
        raise AssertionError(f"Expected {expected_error.__name__} to be raised.")


def _settings(**overrides: object) -> SimpleNamespace:
    defaults = {
        "embedding_provider": "auto",
        "embedding_dimensions": 4,
        "embedding_model": "text-embedding-3-small",
        "embedding_include_dimensions": True,
        "embedding_request_timeout_seconds": 30.0,
        "openai_api_key": None,
        "openai_base_url": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_auto_provider_uses_fake_without_api_key() -> None:
    provider = build_embedding_provider(_settings())

    assert isinstance(provider, DeterministicEmbeddingProvider)


def test_auto_provider_uses_openai_with_api_key() -> None:
    provider = build_embedding_provider(_settings(openai_api_key="test-key"))

    assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
    assert provider.api_key == "test-key"


def test_openai_provider_requires_api_key_when_forced() -> None:
    _assert_raises(
        ValueError,
        "OPENAI_API_KEY",
        lambda: build_embedding_provider(_settings(embedding_provider="openai")),
    )


def test_unsupported_provider_is_rejected() -> None:
    _assert_raises(
        ValueError,
        "Unsupported embedding provider",
        lambda: build_embedding_provider(_settings(embedding_provider="local")),
    )


def test_fake_embedding_query_matches_single_text_embedding() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    assert provider.embed_query("kafka latency") == provider.embed_texts(["kafka latency"])[0]


def test_openai_response_vectors_are_sorted_by_index() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=2,
    )

    vectors = provider._extract_vectors(
        {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_openai_response_rejects_invalid_items() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=2,
    )

    _assert_raises(
        EmbeddingProviderError,
        "invalid item",
        lambda: provider._extract_vectors({"data": ["not-a-dict"]}),
    )


def test_openai_response_rejects_non_object_json() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=2,
    )

    _assert_raises(
        EmbeddingProviderError,
        "JSON object",
        lambda: provider._extract_vectors([]),
    )


def test_openai_payload_can_omit_dimensions_for_compatible_providers() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=2,
        include_dimensions=False,
    )

    payload = provider._build_payload(["sample text"])

    assert payload == {
        "model": "text-embedding-3-small",
        "input": ["sample text"],
    }


def test_openai_payload_includes_dimensions_by_default() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=2,
    )

    payload = provider._build_payload(["sample text"])

    assert payload["dimensions"] == 2


def test_openai_vector_validation_rejects_wrong_dimensions() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=3,
    )

    _assert_raises(
        EmbeddingProviderError,
        "wrong dimensions",
        lambda: provider._validate_vectors([[0.1, 0.2]], expected_count=1),
    )
