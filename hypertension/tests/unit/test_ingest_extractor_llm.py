import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_llm_extractor_calls_openai_with_json_mode():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    fake_payload = {
        "type": "RCT",
        "title": {"zh": "试验研究", "en": None},
        "authors": ["Peng Y"],
        "year": 2026,
        "language": "zh",
        "status": "draft",
        "tags": ["valsartan"],
        "pico": {
            "population": {"condition": "高血压", "sample_size": 612},
            "intervention": {"name": "缬沙坦+氨氯地平"},
            "outcomes": {},
        },
        "risk_of_bias": {"tool": "RoB2", "overall": "low"},
        "grade": {"level": "moderate"},
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_payload, ensure_ascii=False)))]

    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp) as mock_create:
        extractor = LLMFrontmatterExtractor(api_key="test", model="gpt-4o-mini")
        out = extractor.extract(text="some long RCT body text", evidence_type="RCT")

    mock_create.assert_called_once()
    assert out["type"] == "RCT"
    assert out["status"] == "draft"
    assert out["extracted_by"] == "llm"
    assert out["pico"]["population"]["sample_size"] == 612


@pytest.mark.unit
def test_llm_extractor_forces_status_draft_even_if_llm_says_otherwise():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    bad_payload = {
        "type": "RCT", "title": {"zh": "x"}, "authors": ["A"], "year": 2026,
        "language": "zh", "status": "published",
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(bad_payload)))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "RCT")
    assert out["status"] == "draft"


@pytest.mark.unit
def test_llm_extractor_invalid_json_returns_skeleton():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="this is not json {{"))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "META")

    assert out["status"] == "draft"
    assert out["type"] == "META"
    assert out["extracted_by"] == "llm"


@pytest.mark.unit
def test_llm_extractor_api_failure_returns_skeleton():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               side_effect=RuntimeError("API down")):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "GL")

    assert out["status"] == "draft"
    assert out["type"] == "GL"


@pytest.mark.unit
def test_llm_extractor_model_name():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor
    e = LLMFrontmatterExtractor(api_key="x", model="gpt-4o-mini")
    assert e.model_name == "gpt-4o-mini"


@pytest.mark.unit
def test_llm_extractor_truncates_long_text():
    """Text > MAX_INPUT_CHARS is truncated before sending to API."""
    from hypertensiondb.ingest.frontmatter_extractor_llm import (
        LLMFrontmatterExtractor, MAX_INPUT_CHARS,
    )

    fake_payload = {
        "type": "RCT", "title": {"zh": "x"}, "authors": ["A"], "year": 2026,
        "language": "zh", "status": "draft",
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_payload)))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp) as mock_create:
        long_text = "x" * (MAX_INPUT_CHARS + 5000)
        LLMFrontmatterExtractor(api_key="k", model="m").extract(long_text, "RCT")

    _, kwargs = mock_create.call_args
    messages = kwargs["messages"]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert len(user_content) <= MAX_INPUT_CHARS + 500
