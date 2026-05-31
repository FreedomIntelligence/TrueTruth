import pytest
from pathlib import Path
from hypertensiondb.index.chunker import split_evidence_into_chunks

VALID_RCT = Path("tests/fixtures/schema/valid_rct.md")


@pytest.mark.unit
def test_valid_rct_produces_chunks():
    """A reviewed/published-status file produces at least one chunk per non-empty section."""
    # valid_rct.md has status=draft — chunker skips draft files
    chunks = split_evidence_into_chunks(VALID_RCT)
    assert chunks == []  # draft → empty


@pytest.mark.unit
def test_reviewed_file_produces_chunks(tmp_path):
    """A file with status=reviewed produces chunks for non-empty sections."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    md.write_text("""\
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 临床要点 / Clinical Bottom Line

联合治疗优于单药。

## 方法 / Methods

随机双盲设计。

## 结果 / Results

SBP 下降 8 mmHg。

## 结论 / Conclusion

联合治疗显著降压。
""", encoding="utf-8")
    chunks = split_evidence_into_chunks(md)
    assert len(chunks) >= 4
    section_names = [c.section_name for c in chunks]
    assert "clinical_bottom_line" in section_names
    assert "results" in section_names


@pytest.mark.unit
def test_chunk_has_required_fields(tmp_path):
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    md.write_text("""\
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 结果 / Results

SBP 下降 8 mmHg。
""", encoding="utf-8")
    chunks = split_evidence_into_chunks(md)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.evidence_id == "EV-RCT-2026-TEST-001"
    assert c.section_name == "results"
    assert "SBP" in c.text
    assert c.is_clinical_bottom_line is False
    assert c.metadata["type"] == "RCT"
    assert len(c.point_id) == 36  # UUID format


@pytest.mark.unit
def test_clinical_bottom_line_flagged(tmp_path):
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    md.write_text("""\
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 临床要点 / Clinical Bottom Line

联合治疗优于单药。
""", encoding="utf-8")
    chunks = split_evidence_into_chunks(md)
    assert len(chunks) == 1
    assert chunks[0].is_clinical_bottom_line is True


@pytest.mark.unit
def test_empty_sections_skipped(tmp_path):
    """Sections with no text content are not chunked."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    md.write_text("""\
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 方法 / Methods

## 结果 / Results

有内容的节区。
""", encoding="utf-8")
    chunks = split_evidence_into_chunks(md)
    section_names = [c.section_name for c in chunks]
    assert "methods" not in section_names  # empty → skipped
    assert "results" in section_names
