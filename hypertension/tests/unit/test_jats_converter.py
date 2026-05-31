import pytest
from pathlib import Path

from hypertensiondb.ingest.jats_converter import jats_to_evidence


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "jats"


@pytest.fixture
def oa_rct_xml():
    return (FIXTURE_DIR / "sample_oa_rct.xml").read_text(encoding="utf-8")


@pytest.fixture
def minimal_xml():
    return (FIXTURE_DIR / "sample_minimal.xml").read_text(encoding="utf-8")


@pytest.mark.unit
def test_jats_extracts_title(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "Combination therapy" in fm["title"]["en"]


@pytest.mark.unit
def test_jats_extracts_authors(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "Smith J" in fm["authors"]
    assert any("Doe J" in a for a in fm["authors"])


@pytest.mark.unit
def test_jats_extracts_year(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["year"] == 2026


@pytest.mark.unit
def test_jats_extracts_ids(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["doi"] == "10.1234/jh.2026.001"
    assert fm["pmid"] == "39111111"


@pytest.mark.unit
def test_jats_extracts_journal(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["journal"] == "Journal of Hypertension"


@pytest.mark.unit
def test_jats_sets_language_en(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["language"] == "en"


@pytest.mark.unit
def test_jats_sets_status_draft_extracted_by_api(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["status"] == "draft"
    assert fm["extracted_by"] == "api"


@pytest.mark.unit
def test_jats_extracts_abstract_to_abstract_en(oa_rct_xml):
    _, sections = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "612 patients" in sections["abstract_en"]


@pytest.mark.unit
def test_jats_maps_imrad_sections(oa_rct_xml):
    _, sections = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "1 billion" in sections["background"]
    assert "valsartan 80mg" in sections["methods"]
    assert "8.4 mmHg" in sections["results"]
    assert "Findings consistent" in sections["discussion"]
    assert "outperforms" in sections["conclusion"]


@pytest.mark.unit
def test_jats_minimal_xml_returns_skeleton(minimal_xml):
    fm, sections = jats_to_evidence(minimal_xml, evidence_type="RCT")
    assert fm["title"]["en"] == "Tiny paper"
    assert fm["authors"] == ["Williams A"]
    assert fm["year"] == 2024
    assert fm["status"] == "draft"
    assert sections["methods"] == ""
    assert sections["results"] == ""
