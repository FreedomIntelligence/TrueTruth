import pytest
from pathlib import Path
from hypertensiondb.schema.sections import split_sections

FIXTURE = Path("tests/fixtures/schema/valid_rct.md")


@pytest.mark.unit
def test_split_returns_all_standard_sections():
    text = FIXTURE.read_text(encoding="utf-8")
    sections = split_sections(text)
    assert "clinical_bottom_line" in sections
    assert "background" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "conclusion" in sections


@pytest.mark.unit
def test_section_content_is_not_empty():
    text = FIXTURE.read_text(encoding="utf-8")
    sections = split_sections(text)
    assert len(sections["results"].strip()) > 10


@pytest.mark.unit
def test_missing_section_returns_empty_string():
    sections = split_sections("## 结果 / Results\n内容")
    assert sections["abstract_zh"] == ""
