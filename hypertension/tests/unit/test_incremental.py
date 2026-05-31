import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock

from hypertensiondb.index.incremental import find_files_needing_reindex


def _write_reviewed_md(path: Path, ev_id: str) -> None:
    path.write_text(f"""\
---
id: {ev_id}
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
    name: 测试
  outcomes: {{}}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 结果 / Results

有内容。
""", encoding="utf-8")


@pytest.mark.unit
def test_new_file_needs_reindex(tmp_path):
    """A file not yet in Qdrant needs indexing."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    _write_reviewed_md(md, "EV-RCT-2026-TEST-001")

    mock_qdrant = MagicMock()
    mock_qdrant.get_evidence_indexed_at.return_value = None

    result = find_files_needing_reindex(tmp_path, mock_qdrant)
    assert md in result


@pytest.mark.unit
def test_up_to_date_file_skipped(tmp_path):
    """A file indexed after its mtime is NOT returned."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    _write_reviewed_md(md, "EV-RCT-2026-TEST-001")

    from datetime import datetime, timezone
    future = datetime.now(timezone.utc).isoformat()

    mock_qdrant = MagicMock()
    mock_qdrant.get_evidence_indexed_at.return_value = future

    result = find_files_needing_reindex(tmp_path, mock_qdrant)
    assert md not in result


@pytest.mark.unit
def test_draft_file_excluded(tmp_path):
    """Draft files are never returned even if not indexed."""
    md = tmp_path / "EV-RCT-2026-DRAFT-001.md"
    md.write_text("""\
---
id: EV-RCT-2026-DRAFT-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: draft
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 结果 / Results

内容。
""", encoding="utf-8")
    mock_qdrant = MagicMock()
    mock_qdrant.get_evidence_indexed_at.return_value = None
    result = find_files_needing_reindex(tmp_path, mock_qdrant)
    assert md not in result
