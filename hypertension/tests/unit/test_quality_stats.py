import pytest
from pathlib import Path

from hypertensiondb.quality.stats import compute_stats, CorpusStats


_TEMPLATE = """---
id: {id}
type: {type}
title:
  zh: 测试
authors: [A]
year: {year}
language: {language}
status: {status}
pico:
  population: {{condition: 高血压}}
  intervention: {{name: 测试}}
  outcomes: {{}}
risk_of_bias: {{tool: RoB2, overall: low}}
grade: {{level: {grade}}}
---

## 方法 / Methods

x

## 结果 / Results

y

## 结论 / Conclusion

z

## 中文摘要

a
"""


def _write(tmp_path: Path, subdir: str, id_: str, **kwargs) -> None:
    defaults = {"type": "RCT", "year": 2026, "language": "zh",
                "status": "reviewed", "grade": "moderate"}
    defaults.update(kwargs)
    defaults["id"] = id_
    path = tmp_path / subdir / f"{id_}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.format(**defaults), encoding="utf-8")


@pytest.mark.unit
def test_stats_empty_corpus(tmp_path):
    stats = compute_stats(evidence_root=tmp_path)
    assert isinstance(stats, CorpusStats)
    assert stats.total == 0


@pytest.mark.unit
def test_stats_counts_by_type(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", type="RCT")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", type="RCT")
    _write(tmp_path, "meta_analyses", "EV-META-2026-A-001", type="META")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.total == 3
    assert stats.by_type == {"RCT": 2, "META": 1}


@pytest.mark.unit
def test_stats_counts_by_status(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", status="draft")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", status="reviewed")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-003", status="published")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_status["draft"] == 1
    assert stats.by_status["reviewed"] == 1
    assert stats.by_status["published"] == 1


@pytest.mark.unit
def test_stats_counts_by_grade(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", grade="high")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", grade="moderate")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-003", grade="moderate")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_grade == {"high": 1, "moderate": 2}


@pytest.mark.unit
def test_stats_counts_by_year(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", year=2026)
    _write(tmp_path, "rcts", "EV-RCT-2025-A-001", year=2025)
    _write(tmp_path, "rcts", "EV-RCT-2024-A-001", year=2024)
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_year[2026] == 1
    assert stats.by_year[2024] == 1


@pytest.mark.unit
def test_stats_skips_quarantine(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001")
    bad_dir = tmp_path / "_quarantine"
    bad_dir.mkdir()
    (bad_dir / "anything.md").write_text("garbage", encoding="utf-8")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.total == 1


@pytest.mark.unit
def test_stats_draft_pile_alert_threshold(tmp_path):
    """Pile-up alert triggers when drafts > 20% of corpus."""
    # 4 drafts, 1 reviewed = 80% drafts
    for i in range(4):
        _write(tmp_path, "rcts", f"EV-RCT-2026-A-{i:03d}",
               id=f"EV-RCT-2026-A-{i:03d}", status="draft")
    _write(tmp_path, "rcts", "EV-RCT-2026-X-001", status="reviewed")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.draft_pileup_alert is True
