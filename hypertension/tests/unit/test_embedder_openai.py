import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_openai_embedder_calls_api(monkeypatch):
    """embed() calls openai.embeddings.create and returns float vectors."""
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder

    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 1536),
        MagicMock(embedding=[0.2] * 1536),
    ]

    with patch("hypertensiondb.index.embedder_openai.openai.embeddings.create",
               return_value=mock_response) as mock_create:
        embedder = OpenAIEmbedder(api_key="test-key", model="text-embedding-3-small", dim=1536)
        result = embedder.embed(["text1", "text2"])

    mock_create.assert_called_once()
    assert len(result) == 2
    assert len(result[0]) == 1536


@pytest.mark.unit
def test_openai_embedder_dimension():
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder
    e = OpenAIEmbedder(api_key="x", model="text-embedding-3-small", dim=1536)
    assert e.dimension == 1536


@pytest.mark.unit
def test_openai_embedder_model_name():
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder
    e = OpenAIEmbedder(api_key="x", model="text-embedding-3-small", dim=1536)
    assert e.model_name == "text-embedding-3-small"
