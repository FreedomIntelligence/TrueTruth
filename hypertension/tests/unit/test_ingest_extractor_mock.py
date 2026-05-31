import pytest

from hypertensiondb.ingest.frontmatter_extractor import (
    BaseFrontmatterExtractor, MockFrontmatterExtractor,
)


@pytest.fixture
def extractor():
    return MockFrontmatterExtractor()


@pytest.mark.unit
def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseFrontmatterExtractor()


@pytest.mark.unit
def test_mock_extractor_returns_dict(extractor):
    result = extractor.extract(text="random text", evidence_type="RCT")
    assert isinstance(result, dict)


@pytest.mark.unit
def test_mock_extractor_has_required_fields(extractor):
    result = extractor.extract(text="some text", evidence_type="RCT")
    assert "type" in result and result["type"] == "RCT"
    assert "title" in result
    assert "authors" in result
    assert "year" in result
    assert "language" in result
    assert "status" in result and result["status"] == "draft"


@pytest.mark.unit
def test_mock_extractor_sets_extracted_by(extractor):
    result = extractor.extract(text="x", evidence_type="META")
    assert result.get("extracted_by") == "llm"


@pytest.mark.unit
def test_mock_extractor_returns_minimal_pico_for_rct(extractor):
    result = extractor.extract(text="x", evidence_type="RCT")
    assert "pico" in result
    assert "population" in result["pico"]


@pytest.mark.unit
def test_mock_extractor_no_pico_for_guideline(extractor):
    """Guidelines don't have PICO."""
    result = extractor.extract(text="x", evidence_type="GL")
    assert "pico" not in result or result.get("pico") is None


@pytest.mark.unit
def test_mock_extractor_model_name(extractor):
    assert extractor.model_name == "mock"
