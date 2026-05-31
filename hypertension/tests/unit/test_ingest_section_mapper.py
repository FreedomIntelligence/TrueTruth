import pytest

from hypertensiondb.ingest.section_mapper import detect_sections, STANDARD_SECTIONS


@pytest.mark.unit
def test_detect_sections_finds_english_imrad():
    text = """Abstract
We studied hypertension.

Methods
RCT design with 612 patients.

Results
SBP decreased by 8 mmHg.

Conclusion
Combination is better.
"""
    sections = detect_sections(text)
    assert "methods" in sections and sections["methods"].strip()
    assert "results" in sections and "SBP" in sections["results"]
    assert "conclusion" in sections


@pytest.mark.unit
def test_detect_sections_finds_chinese_headings():
    text = """摘要
研究高血压。

方法
随机对照试验。

结果
SBP下降8 mmHg。

结论
联合优于单药。
"""
    sections = detect_sections(text)
    assert sections["methods"].strip()
    assert "SBP" in sections["results"]
    assert "联合" in sections["conclusion"]


@pytest.mark.unit
def test_detect_sections_fallback_all_in_results():
    text = "Just a single block of text without any section headings whatsoever."
    sections = detect_sections(text)
    assert sections["results"].strip() == text.strip()
    assert sections.get("methods", "") == ""


@pytest.mark.unit
def test_detect_sections_returns_all_standard_keys():
    text = "Methods\nFoo.\n\nResults\nBar."
    sections = detect_sections(text)
    for key in STANDARD_SECTIONS:
        assert key in sections


@pytest.mark.unit
def test_detect_sections_handles_mixed_zh_en():
    text = """Background / 背景
Hypertension is common.

Methods / 方法
Randomized trial.

Results / 结果
SBP down 8mmHg.
"""
    sections = detect_sections(text)
    assert sections["methods"].strip()
    assert "SBP" in sections["results"]


@pytest.mark.unit
def test_detect_sections_strips_section_titles_from_body():
    text = "Methods\nThis is the methods body.\n\nResults\nThis is results."
    sections = detect_sections(text)
    assert not sections["methods"].lower().startswith("methods\n")
    assert "This is the methods body" in sections["methods"]


@pytest.mark.unit
def test_standard_sections_contains_expected_keys():
    expected = {"clinical_bottom_line", "abstract_zh", "abstract_en",
                "background", "methods", "results", "discussion", "conclusion"}
    assert set(STANDARD_SECTIONS) == expected
