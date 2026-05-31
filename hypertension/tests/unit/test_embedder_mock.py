import pytest
from hypertensiondb.index.embedder_mock import MockEmbedder


@pytest.fixture
def embedder():
    return MockEmbedder(dim=8)


@pytest.mark.unit
def test_embed_returns_correct_shape(embedder):
    texts = ["高血压治疗", "combination therapy", "ARB联合CCB"]
    result = embedder.embed(texts)
    assert len(result) == 3
    assert all(len(v) == 8 for v in result)


@pytest.mark.unit
def test_embed_returns_float_vectors(embedder):
    result = embedder.embed(["test"])
    assert all(isinstance(x, float) for x in result[0])


@pytest.mark.unit
def test_embed_same_text_same_vector(embedder):
    """Deterministic: same text → same vector."""
    v1 = embedder.embed(["高血压"])[0]
    v2 = embedder.embed(["高血压"])[0]
    assert v1 == v2


@pytest.mark.unit
def test_embed_different_text_different_vector(embedder):
    v1 = embedder.embed(["高血压"])[0]
    v2 = embedder.embed(["低血压"])[0]
    assert v1 != v2


@pytest.mark.unit
def test_dimension_property(embedder):
    assert embedder.dimension == 8


@pytest.mark.unit
def test_model_name_property(embedder):
    assert embedder.model_name == "mock"


@pytest.mark.unit
def test_embed_empty_list_returns_empty(embedder):
    assert embedder.embed([]) == []
