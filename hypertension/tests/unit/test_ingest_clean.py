import pytest

from hypertensiondb.ingest.clean import (
    fix_hyphenation, merge_broken_lines, remove_repeating_lines,
    normalize_whitespace, clean_text,
)


@pytest.mark.unit
def test_fix_hyphenation():
    text = "Hyper-\ntension is common."
    assert fix_hyphenation(text) == "Hypertension is common."


@pytest.mark.unit
def test_fix_hyphenation_keeps_real_hyphens():
    text = "Cardio-vascular events"
    assert fix_hyphenation(text) == "Cardio-vascular events"


@pytest.mark.unit
def test_fix_hyphenation_chinese_unaffected():
    text = "高血\n压"
    assert fix_hyphenation(text) == "高血\n压"


@pytest.mark.unit
def test_merge_broken_lines_within_paragraph():
    text = "This is a sentence\nthat wraps across lines."
    result = merge_broken_lines(text)
    assert result == "This is a sentence that wraps across lines."


@pytest.mark.unit
def test_merge_broken_lines_preserves_paragraph_breaks():
    text = "Paragraph one.\n\nParagraph two."
    result = merge_broken_lines(text)
    assert "\n\n" in result


@pytest.mark.unit
def test_merge_broken_lines_chinese_no_space():
    text = "原发性高血压是\n心血管疾病的危险因素。"
    result = merge_broken_lines(text)
    assert result == "原发性高血压是心血管疾病的危险因素。"


@pytest.mark.unit
def test_remove_repeating_lines():
    pages = [
        "Header X\nReal content of page 1\nFooter 123",
        "Header X\nReal content of page 2\nFooter 124",
        "Header X\nReal content of page 3\nFooter 125",
    ]
    cleaned = remove_repeating_lines(pages, min_occurrences_ratio=0.66)
    assert all("Header X" not in p for p in cleaned)
    assert all("Real content" in p for p in cleaned)


@pytest.mark.unit
def test_remove_repeating_lines_keeps_unique():
    pages = ["unique 1", "unique 2"]
    cleaned = remove_repeating_lines(pages, min_occurrences_ratio=0.66)
    assert cleaned == pages


@pytest.mark.unit
def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("a    b\t\tc") == "a b c"


@pytest.mark.unit
def test_normalize_whitespace_preserves_newlines():
    assert normalize_whitespace("para1\n\npara2") == "para1\n\npara2"


@pytest.mark.unit
def test_clean_text_full_pipeline():
    pages = [
        "Header X\nHyper-\ntension is\ncommon.\n\nMore content here.\nFooter 1",
        "Header X\nAnother sentence.\nFooter 2",
    ]
    cleaned = clean_text(pages)
    assert "Header X" not in cleaned
    assert "Hypertension" in cleaned
    assert "is common" in cleaned
