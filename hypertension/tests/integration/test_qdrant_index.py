import pytest
from pathlib import Path

pytest.importorskip("testcontainers", reason="testcontainers not installed")

from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from qdrant_client import QdrantClient

from hypertensiondb.index.embedder_mock import MockEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.index.pipeline import IndexPipeline


REVIEWED_MD_CONTENT = """\
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 集成测试文献
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
  intervention:
    name: ARB联合CCB
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---

## 临床要点 / Clinical Bottom Line

ARB联合CCB显著降低血压。

## 结果 / Results

SBP 下降 8 mmHg (P<0.001)。

## 结论 / Conclusion

联合治疗优于单药。
"""


@pytest.fixture(scope="module")
def qdrant_client():
    """Start a Qdrant container and return a connected QdrantClient."""
    container = DockerContainer("qdrant/qdrant:v1.9.3")
    container.with_exposed_ports(6333)
    container.start()
    wait_for_logs(container, "Qdrant gRPC listening", timeout=30)
    port = container.get_exposed_port(6333)
    client = QdrantClient(host="localhost", port=int(port))
    yield client
    container.stop()


@pytest.mark.integration
def test_index_reviewed_file_and_verify_qdrant(qdrant_client, tmp_path):
    """Index a reviewed evidence file and verify chunks appear in Qdrant."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    md.write_text(REVIEWED_MD_CONTENT, encoding="utf-8")

    embedder = MockEmbedder(dim=8)
    sparse = SparseVectorizer()
    idx_client = QdrantIndexClient(qdrant=qdrant_client, collection_name="test_integration")
    pipeline = IndexPipeline(
        embedder=embedder,
        sparse_vectorizer=sparse,
        qdrant_client=idx_client,
        collection_name="test_integration",
    )

    count = pipeline.index_file(md)
    assert count == 3  # clinical_bottom_line + results + conclusion

    results, _ = qdrant_client.scroll(
        collection_name="test_integration",
        scroll_filter={"must": [{"key": "evidence_id", "match": {"value": "EV-RCT-2026-TEST-001"}}]},
        limit=10,
        with_payload=True,
    )
    assert len(results) == 3
    section_names = {r.payload["section_name"] for r in results}
    assert "clinical_bottom_line" in section_names
    assert "results" in section_names


@pytest.mark.integration
def test_rebuild_clears_and_reindexes(qdrant_client, tmp_path):
    """Rebuild deletes existing points and reindexes all reviewed files."""
    for i, ev_id in enumerate(["EV-RCT-2026-A-001", "EV-RCT-2026-B-001"]):
        content = REVIEWED_MD_CONTENT.replace("EV-RCT-2026-TEST-001", ev_id)
        (tmp_path / f"{ev_id}.md").write_text(content, encoding="utf-8")

    embedder = MockEmbedder(dim=8)
    sparse = SparseVectorizer()
    idx_client = QdrantIndexClient(qdrant=qdrant_client, collection_name="test_rebuild")
    pipeline = IndexPipeline(
        embedder=embedder,
        sparse_vectorizer=sparse,
        qdrant_client=idx_client,
        collection_name="test_rebuild",
    )

    total = pipeline.rebuild(tmp_path)
    assert total == 6  # 2 files × 3 chunks each

    info = qdrant_client.get_collection("test_rebuild")
    assert info.points_count == 6
