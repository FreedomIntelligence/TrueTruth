import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from hypertensiondb.api.server import create_app


VALID_MD = """\
---
id: EV-RCT-2026-XYZ-001
type: RCT
title:
  zh: 测试文献
authors: [Test A]
year: 2026
language: zh
status: reviewed
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

降压 8 mmHg。

## 结论 / Conclusion

有效。
"""


@pytest.fixture
def evidence_dir(tmp_path, monkeypatch):
    """Create an evidence/rcts/ dir with one valid file, point EVIDENCE_ROOT to it."""
    root = tmp_path / "evidence"
    rcts = root / "rcts"
    rcts.mkdir(parents=True)
    (rcts / "EV-RCT-2026-XYZ-001.md").write_text(VALID_MD, encoding="utf-8")
    monkeypatch.setenv("EVIDENCE_ROOT", str(root))
    return root


@pytest.fixture
def client(evidence_dir):
    app = create_app(
        engine=MagicMock(), qdrant=MagicMock(),
        collection_name="test", embedder_name="mock", reranker_name="mock",
    )
    return TestClient(app)


@pytest.mark.unit
def test_get_evidence_by_id(client):
    r = client.get("/evidence/EV-RCT-2026-XYZ-001")
    assert r.status_code == 200
    data = r.json()
    assert data["evidence_id"] == "EV-RCT-2026-XYZ-001"
    assert data["frontmatter"]["type"] == "RCT"
    assert "results" in data["sections"]
    assert "降压" in data["sections"]["results"]


@pytest.mark.unit
def test_get_evidence_not_found(client):
    r = client.get("/evidence/EV-RCT-2099-NOSUCH-999")
    assert r.status_code == 404


@pytest.mark.unit
def test_get_evidence_invalid_id_format(client):
    r = client.get("/evidence/not-a-valid-id")
    assert r.status_code == 404


@pytest.mark.unit
def test_evidence_list_by_type(client):
    r = client.get("/evidence", params={"type": "RCT"})
    assert r.status_code == 200
    data = r.json()
    assert any(e["evidence_id"] == "EV-RCT-2026-XYZ-001" for e in data["items"])


@pytest.mark.unit
def test_evidence_list_filter_excludes_non_matching(client):
    r = client.get("/evidence", params={"type": "META"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 0


@pytest.mark.unit
def test_evidence_list_year_filter(client):
    r = client.get("/evidence", params={"year_min": 2020, "year_max": 2026})
    data = r.json()
    assert len(data["items"]) >= 1


@pytest.mark.unit
def test_evidence_list_year_filter_excludes(client):
    r = client.get("/evidence", params={"year_min": 2027})
    data = r.json()
    assert len(data["items"]) == 0
