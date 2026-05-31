import pytest
from qdrant_client import models as qm

from hypertensiondb.retrieval.filters import build_qdrant_filter, SearchFilters


@pytest.mark.unit
def test_empty_filters_returns_none():
    assert build_qdrant_filter(SearchFilters()) is None


@pytest.mark.unit
def test_type_filter():
    f = build_qdrant_filter(SearchFilters(types=["RCT", "META"]))
    assert isinstance(f, qm.Filter)
    must = f.must
    assert len(must) >= 1
    type_cond = next(c for c in must if c.key == "type")
    assert set(type_cond.match.any) == {"RCT", "META"}


@pytest.mark.unit
def test_language_filter():
    f = build_qdrant_filter(SearchFilters(languages=["zh"]))
    lang_cond = next(c for c in f.must if c.key == "language")
    assert lang_cond.match.any == ["zh"]


@pytest.mark.unit
def test_year_range_filter():
    f = build_qdrant_filter(SearchFilters(year_min=2020, year_max=2026))
    year_cond = next(c for c in f.must if c.key == "year")
    assert year_cond.range.gte == 2020
    assert year_cond.range.lte == 2026


@pytest.mark.unit
def test_year_min_only():
    f = build_qdrant_filter(SearchFilters(year_min=2024))
    year_cond = next(c for c in f.must if c.key == "year")
    assert year_cond.range.gte == 2024
    assert year_cond.range.lte is None


@pytest.mark.unit
def test_grade_min_filter():
    """grade_min=moderate accepts moderate and high (not low/very_low)."""
    f = build_qdrant_filter(SearchFilters(grade_min="moderate"))
    grade_cond = next(c for c in f.must if c.key == "grade_level")
    assert set(grade_cond.match.any) == {"moderate", "high"}


@pytest.mark.unit
def test_grade_min_high_only_accepts_high():
    f = build_qdrant_filter(SearchFilters(grade_min="high"))
    grade_cond = next(c for c in f.must if c.key == "grade_level")
    assert grade_cond.match.any == ["high"]


@pytest.mark.unit
def test_tags_filter():
    f = build_qdrant_filter(SearchFilters(tags=["ARB", "CCB"]))
    tags_cond = next(c for c in f.must if c.key == "tags")
    assert set(tags_cond.match.any) == {"ARB", "CCB"}


@pytest.mark.unit
def test_section_filter():
    f = build_qdrant_filter(SearchFilters(sections=["results", "conclusion"]))
    sec_cond = next(c for c in f.must if c.key == "section_name")
    assert set(sec_cond.match.any) == {"results", "conclusion"}


@pytest.mark.unit
def test_include_draft_false_excludes_drafts():
    """By default (include_draft=False), only reviewed/published indexed."""
    f = build_qdrant_filter(SearchFilters(include_draft=False))
    status_cond = next(c for c in f.must if c.key == "status")
    assert set(status_cond.match.any) == {"reviewed", "published"}


@pytest.mark.unit
def test_include_draft_true_no_status_filter():
    f = build_qdrant_filter(SearchFilters(include_draft=True))
    if f is None:
        return
    keys = [c.key for c in (f.must or [])]
    assert "status" not in keys


@pytest.mark.unit
def test_combined_filters():
    f = build_qdrant_filter(SearchFilters(
        types=["RCT"], year_min=2024, grade_min="high", tags=["ARB"]
    ))
    keys = {c.key for c in f.must}
    assert "type" in keys
    assert "year" in keys
    assert "grade_level" in keys
    assert "tags" in keys
