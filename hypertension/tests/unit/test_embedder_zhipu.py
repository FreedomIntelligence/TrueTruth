import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_zhipu_embedder_calls_api(monkeypatch):
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder

    fake_result = [[0.1] * 2048, [0.2] * 2048]

    with patch("hypertensiondb.index.embedder_zhipu.ZhipuEmbedder._call_api",
               return_value=fake_result) as mock_call:
        embedder = ZhipuEmbedder(api_key="test-key")
        result = embedder.embed(["text1", "text2"])

    mock_call.assert_called_once_with(["text1", "text2"])
    assert len(result) == 2
    assert len(result[0]) == 2048


@pytest.mark.unit
def test_zhipu_embedder_dimension():
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
    e = ZhipuEmbedder(api_key="x")
    assert e.dimension == 2048


@pytest.mark.unit
def test_zhipu_embedder_model_name():
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
    e = ZhipuEmbedder(api_key="x")
    assert e.model_name == "embedding-3"
