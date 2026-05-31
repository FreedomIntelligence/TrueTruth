import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypertensiondb.index.pipeline import IndexPipeline
from hypertensiondb.index.embedder_mock import MockEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.chunk import EvidenceChunk


def _make_mock_qdrant_client():
    client = MagicMock()
    client.get_evidence_indexed_at.return_value = None
    return client


@pytest.fixture
def pipeline():
    return IndexPipeline(
        embedder=MockEmbedder(dim=8),
        sparse_vectorizer=SparseVectorizer(),
        qdrant_client=_make_mock_qdrant_client(),
        collection_name="test",
    )


@pytest.mark.unit
def test_index_draft_file_returns_zero(pipeline, tmp_path):
    """Draft file: no chunks, nothing indexed."""
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
status: draft
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

有内容。
""", encoding="utf-8")
    count = pipeline.index_file(md)
    assert count == 0
    pipeline._qdrant.upsert_chunks.assert_not_called()


@pytest.mark.unit
def test_index_reviewed_file_returns_chunk_count(pipeline, tmp_path):
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

## 结论 / Conclusion

联合治疗显著有效。
""", encoding="utf-8")
    count = pipeline.index_file(md)
    assert count == 2
    pipeline._qdrant.upsert_chunks.assert_called_once()


@pytest.mark.unit
def test_ensure_collection_called_on_init(tmp_path):
    mock_qdrant = _make_mock_qdrant_client()
    IndexPipeline(
        embedder=MockEmbedder(dim=8),
        sparse_vectorizer=SparseVectorizer(),
        qdrant_client=mock_qdrant,
        collection_name="test",
    )
    mock_qdrant.ensure_collection.assert_called_once_with(dense_dim=8)
