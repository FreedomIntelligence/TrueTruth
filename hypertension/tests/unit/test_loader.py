import pytest
from pathlib import Path
from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.schema.rct import RctFrontmatter

VALID_RCT = Path("tests/fixtures/schema/valid_rct.md")
INVALID_GRADE = Path("tests/fixtures/schema/invalid_bad_grade.md")
INVALID_ID = Path("tests/fixtures/schema/invalid_missing_id.md")


@pytest.mark.unit
def test_load_valid_rct_returns_correct_type():
    fm, sections = load_evidence(VALID_RCT)
    assert isinstance(fm, RctFrontmatter)
    assert fm.id == "EV-RCT-2026-PENG-001"


@pytest.mark.unit
def test_load_valid_rct_sections_present():
    fm, sections = load_evidence(VALID_RCT)
    assert "clinical_bottom_line" in sections
    assert len(sections["results"]) > 0


@pytest.mark.unit
def test_load_invalid_grade_raises():
    with pytest.raises(Exception):
        load_evidence(INVALID_GRADE)


@pytest.mark.unit
def test_load_missing_id_raises():
    with pytest.raises(Exception):
        load_evidence(INVALID_ID)
