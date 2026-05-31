import pytest
from pathlib import Path

from hypertensiondb.quality.lint import run_lint, LintReport, LintIssue


_VALID_FM = """---
id: EV-RCT-2026-VALID-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
---

## 方法 / Methods

x x x

## 结果 / Results

y y y

## 结论 / Conclusion

z z z

## 中文摘要

abstract.
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_lint_clean_corpus_returns_no_issues(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert isinstance(report, LintReport)
    assert report.total_files == 1
    assert report.issues == []


@pytest.mark.unit
def test_lint_detects_filename_id_mismatch(tmp_path):
    _write(tmp_path / "rcts" / "WRONG-NAME.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "filename_mismatch" for i in report.issues)


@pytest.mark.unit
def test_lint_detects_duplicate_doi(tmp_path):
    fm_with_doi = _VALID_FM.replace(
        "language: zh",
        "language: zh\ndoi: 10.1234/dup",
    )
    second = fm_with_doi.replace("EV-RCT-2026-VALID-001", "EV-RCT-2026-VALID-002")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", fm_with_doi)
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-002.md", second)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "duplicate_doi" for i in report.issues)


@pytest.mark.unit
def test_lint_detects_pydantic_failure(tmp_path):
    bad = _VALID_FM.replace("year: 2026", "year: 1850")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", bad)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "schema_error" for i in report.issues)


@pytest.mark.unit
def test_lint_counts_drafts_in_summary(tmp_path):
    draft_fm = _VALID_FM.replace("status: reviewed", "status: draft")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", draft_fm)
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-002.md",
           draft_fm.replace("VALID-001", "VALID-002"))
    report = run_lint(evidence_root=tmp_path)
    assert report.draft_count == 2


@pytest.mark.unit
def test_lint_skips_quarantine_directory(tmp_path):
    _write(tmp_path / "_quarantine" / "bad.md", "garbage content not valid")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert report.total_files == 1
