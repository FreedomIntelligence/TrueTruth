import pytest
from pathlib import Path

from hypertensiondb.quality.publish import publish_evidence, PublishError


_DRAFT_LLM = """---
id: EV-RCT-2026-PUB-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: draft
extracted_by: llm
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
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

_DRAFT_HUMAN_REVIEWED = _DRAFT_LLM.replace(
    "extracted_by: llm",
    "extracted_by: human",
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_publish_rejects_llm_draft_without_review(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_LLM)
    with pytest.raises(PublishError) as ei:
        publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                         target_status="reviewed")
    assert "human review" in str(ei.value).lower()


@pytest.mark.unit
def test_publish_accepts_human_extracted_to_reviewed(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_HUMAN_REVIEWED)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="reviewed")
    content = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: reviewed" in content
    assert "status: draft" not in content


@pytest.mark.unit
def test_publish_accepts_llm_draft_with_reviewer_set(tmp_path):
    content = _DRAFT_LLM.replace(
        "extracted_by: llm",
        "extracted_by: llm\nreviewed_by: alice@example.com",
    )
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", content)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="reviewed")
    new = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: reviewed" in new


@pytest.mark.unit
def test_publish_reviewed_to_published(tmp_path):
    reviewed = _DRAFT_HUMAN_REVIEWED.replace("status: draft", "status: reviewed")
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", reviewed)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="published")
    content = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: published" in content


@pytest.mark.unit
def test_publish_not_found(tmp_path):
    with pytest.raises(PublishError) as ei:
        publish_evidence("EV-RCT-2099-NOSUCH-001", evidence_root=tmp_path,
                         target_status="reviewed")
    assert "not found" in str(ei.value).lower()


@pytest.mark.unit
def test_publish_invalid_target_status(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_HUMAN_REVIEWED)
    with pytest.raises(PublishError):
        publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                         target_status="draft")  # can only go up the ladder
