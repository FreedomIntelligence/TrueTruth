import pytest
from pathlib import Path

from hypertensiondb.ingest.writer import (
    write_evidence_md, write_quarantine_md, EvidenceWriteResult,
)


_FRONTMATTER = {
    "id": "EV-RCT-2026-TEST-001",
    "type": "RCT",
    "title": {"zh": "测试", "en": None},
    "authors": ["Test A"],
    "year": 2026,
    "language": "zh",
    "status": "draft",
    "extracted_by": "llm",
}

_SECTIONS = {
    "methods": "随机对照试验。",
    "results": "降压 8 mmHg。",
    "conclusion": "联合优于单药。",
}


@pytest.mark.unit
def test_write_evidence_md_creates_file(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    assert isinstance(result, EvidenceWriteResult)
    assert result.path.exists()
    assert result.path.name == "EV-RCT-2026-TEST-001.md"


@pytest.mark.unit
def test_write_evidence_md_puts_rct_in_rcts_dir(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    assert result.path.parent.name == "rcts"


@pytest.mark.unit
def test_write_evidence_md_type_to_subdir_mapping(tmp_path):
    mapping = {"RCT": "rcts", "SR": "systematic_reviews", "META": "meta_analyses",
               "GL": "guidelines", "TCM": "tcm"}
    for ev_type, subdir in mapping.items():
        fm = dict(_FRONTMATTER)
        fm["type"] = ev_type
        fm["id"] = f"EV-{ev_type}-2026-TEST-001"
        result = write_evidence_md(frontmatter=fm, sections=_SECTIONS, evidence_root=tmp_path)
        assert result.path.parent.name == subdir, f"{ev_type} → {subdir}"


@pytest.mark.unit
def test_write_evidence_md_includes_frontmatter_and_sections(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    content = result.path.read_text(encoding="utf-8")
    assert "---" in content
    assert "id: EV-RCT-2026-TEST-001" in content
    assert "## 方法 / Methods" in content or "## Methods" in content
    assert "降压 8 mmHg" in content


@pytest.mark.unit
def test_write_evidence_md_conflict_raises(tmp_path):
    write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)
    with pytest.raises(FileExistsError):
        write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)


@pytest.mark.unit
def test_write_evidence_md_overwrite_true_allowed(tmp_path):
    write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
        overwrite=True,
    )
    assert result.path.exists()


@pytest.mark.unit
def test_write_quarantine_md(tmp_path):
    bad_fm = {"type": "RCT", "title": {"zh": "bad"}, "year": "not-a-year"}
    result = write_quarantine_md(
        partial_frontmatter=bad_fm, sections={"results": "x"},
        error="ValidationError: year must be int", evidence_root=tmp_path,
        source_filename="orig.pdf",
    )
    assert result.path.parent.name == "_quarantine"
    assert result.path.exists()
    content = result.path.read_text(encoding="utf-8")
    assert "ValidationError" in content
    assert "orig.pdf" in content
