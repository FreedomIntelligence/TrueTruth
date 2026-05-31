# Plan B: 索引管线 + Qdrant Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 evidence/ 目录下的 Markdown 文件切块、向量化并写入本地 Qdrant，提供 `hdb index update`（增量）和 `hdb index rebuild`（全量重建）两条命令。

**Architecture:** 四层管线 — Chunker（按节区切块）→ Embedder（稠密向量，可插拔云 API）→ SparseVectorizer（jieba BM25 式稀疏向量）→ QdrantIndexClient（写入本地 Qdrant）。IndexPipeline 统一编排，IncrementalUpdater 对比文件 mtime 与 Qdrant payload 中的 indexed_at 决定哪些文件需重新索引。所有测试均使用 MockEmbedder，不依赖真实 API key。

**Tech Stack:** Python 3.12, qdrant-client>=1.9, jieba>=0.42, openai>=1.30, httpx>=0.27, testcontainers[docker]>=4.0, pytest-mock>=3.12

---

## 参考资料

- 设计文档 §4（数据流）、§6（错误处理）：`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`
- Plan A 已实现：`load_evidence(path)` → `(AnyFrontmatter, dict[str, str])`，`split_sections()` → section dict

## 注意事项

- **不需要 git 操作**（每个 Task 省略 Commit 步骤）
- Plan B 末尾的集成测试需要 Docker Desktop 已启动

## File Structure

```
docker-compose.yml                          # Qdrant 容器编排（新建）

pyproject.toml                              # 追加新依赖（修改）

src/hypertensiondb/
  index/
    __init__.py                             # 导出公开接口（新建）
    chunk.py                                # EvidenceChunk dataclass（新建）
    chunker.py                              # split_evidence_into_chunks(path) → list[EvidenceChunk]（新建）
    embedder.py                             # BaseEmbedder ABC（新建）
    embedder_mock.py                        # MockEmbedder — 测试用，不需要 API key（新建）
    embedder_openai.py                      # OpenAIEmbedder（新建）
    embedder_zhipu.py                       # ZhipuEmbedder（新建）
    sparse.py                               # SparseVectorizer: jieba → {indices, values}（新建）
    qdrant_index_client.py                  # QdrantIndexClient: 封装 qdrant-client（新建）
    pipeline.py                             # IndexPipeline: 编排 chunk+embed+sparse+upsert（新建）
    incremental.py                          # find_files_needing_reindex()（新建）

  cli.py                                    # 修改：实现 hdb index update / rebuild（修改）

tests/
  unit/
    test_chunker.py                         # 新建
    test_sparse.py                          # 新建
    test_embedder_mock.py                   # 新建
    test_pipeline.py                        # 新建（mock qdrant + mock embedder）
    test_incremental.py                     # 新建
  integration/
    test_qdrant_index.py                    # 新建（testcontainers 起真实 Qdrant）
```

---

## Task B.1: 依赖更新 + docker-compose.yml

**Files:**
- Modify: `pyproject.toml`
- Create: `docker-compose.yml`

- [ ] **Step 1: 更新 pyproject.toml — 追加新依赖**

将 `pyproject.toml` 的 `dependencies` 改为：

```toml
[project]
name = "hypertensiondb"
version = "0.1.0"
description = "Hypertension Evidence RAG Database"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "typer>=0.12",
    "pypinyin>=0.51",
    "python-frontmatter>=1.1",
    "qdrant-client>=1.9",
    "jieba>=0.42",
    "openai>=1.30",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "pre-commit>=3.7",
    "ruff>=0.4",
    "testcontainers[docker]>=4.0",
]
```

（其余 `[build-system]`、`[tool.setuptools]`、`[tool.pytest]`、`[tool.ruff]` 节保持不变。）

- [ ] **Step 2: 安装新依赖**

Run: `py -m pip install -e ".[dev]" -q`
Expected: 安装成功，最后无 ERROR 行

- [ ] **Step 3: 验证 qdrant-client 可导入**

Run: `py -c "from qdrant_client import QdrantClient; print('qdrant-client OK')"`
Expected: `qdrant-client OK`

- [ ] **Step 4: 创建 docker-compose.yml**

```yaml
version: "3.8"
services:
  qdrant:
    image: qdrant/qdrant:v1.9.3
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    restart: unless-stopped
```

- [ ] **Step 5: 验证 Docker Compose 可解析（不启动容器）**

Run: `docker compose config --quiet`
Expected: 无 ERROR，正常退出

---

## Task B.2: EvidenceChunk dataclass + Chunker

**Files:**
- Create: `src/hypertensiondb/index/chunk.py`
- Create: `src/hypertensiondb/index/chunker.py`
- Create: `src/hypertensiondb/index/__init__.py`
- Test: `tests/unit/test_chunker.py`

- [ ] **Step 1: 写 chunker 失败测试**

Create `tests/unit/test_chunker.py`:
```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_chunker.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 创建 chunk.py**

Create `src/hypertensiondb/index/chunk.py`:
```python
from dataclasses import dataclass, field


@dataclass
class EvidenceChunk:
    point_id: str               # UUID derived from sha1(evidence_id:section_name)
    evidence_id: str            # e.g. "EV-RCT-2026-PENG-001"
    section_name: str           # e.g. "results", "clinical_bottom_line"
    text: str                   # cleaned section text
    is_clinical_bottom_line: bool
    metadata: dict = field(default_factory=dict)  # full frontmatter fields
```

- [ ] **Step 4: 创建 chunker.py**

Create `src/hypertensiondb/index/chunker.py`:
```python
import hashlib
import uuid
from pathlib import Path

from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.schema.base import Status
from hypertensiondb.index.chunk import EvidenceChunk

_INDEXABLE_STATUSES = {Status.REVIEWED, Status.PUBLISHED}
_CLINICAL_BOTTOM_LINE_KEY = "clinical_bottom_line"
_MAX_SECTION_CHARS = 1500


def _make_point_id(evidence_id: str, section_name: str) -> str:
    """Derive a stable UUID from evidence_id + section_name."""
    sha1_bytes = hashlib.sha1(f"{evidence_id}:{section_name}".encode()).digest()
    return str(uuid.UUID(bytes=sha1_bytes[:16]))


def _frontmatter_to_metadata(fm) -> dict:
    """Extract key metadata fields from frontmatter model for Qdrant payload."""
    return {
        "evidence_id": fm.id,
        "type": str(fm.type),
        "year": fm.year,
        "language": str(fm.language),
        "status": str(fm.status),
        "grade_level": str(fm.grade.level) if hasattr(fm, "grade") else None,
        "rob_overall": str(fm.risk_of_bias.overall) if hasattr(fm, "risk_of_bias") else None,
        "tags": fm.tags,
        "title_zh": fm.title.zh,
        "title_en": fm.title.en,
    }


def split_evidence_into_chunks(path: Path) -> list[EvidenceChunk]:
    """Parse one evidence .md file and return its chunks.

    Returns [] if the file has status=draft or is invalid.
    """
    try:
        fm, sections = load_evidence(path)
    except Exception:
        return []

    if fm.status not in _INDEXABLE_STATUSES:
        return []

    metadata = _frontmatter_to_metadata(fm)
    chunks: list[EvidenceChunk] = []

    for section_key, text in sections.items():
        text = text.strip()
        if not text:
            continue

        if len(text) <= _MAX_SECTION_CHARS:
            # Single chunk for this section
            chunks.append(EvidenceChunk(
                point_id=_make_point_id(fm.id, section_key),
                evidence_id=fm.id,
                section_name=section_key,
                text=text,
                is_clinical_bottom_line=(section_key == _CLINICAL_BOTTOM_LINE_KEY),
                metadata=metadata,
            ))
        else:
            # Split long section by ### sub-headings
            sub_parts = _split_by_subheadings(text)
            for i, part in enumerate(sub_parts):
                part = part.strip()
                if not part:
                    continue
                sub_key = f"{section_key}_{i}"
                chunks.append(EvidenceChunk(
                    point_id=_make_point_id(fm.id, sub_key),
                    evidence_id=fm.id,
                    section_name=sub_key,
                    text=part,
                    is_clinical_bottom_line=False,
                    metadata=metadata,
                ))

    return chunks


def _split_by_subheadings(text: str) -> list[str]:
    """Split text on ### lines."""
    import re
    parts = re.split(r"(?=^###\s)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]
```

- [ ] **Step 5: 创建 index/__init__.py**

Create `src/hypertensiondb/index/__init__.py`:
```python
from hypertensiondb.index.chunk import EvidenceChunk
from hypertensiondb.index.chunker import split_evidence_into_chunks

__all__ = ["EvidenceChunk", "split_evidence_into_chunks"]
```

- [ ] **Step 6: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_chunker.py -v`
Expected: 5 passed

---

## Task B.3: SparseVectorizer (jieba TF 稀疏向量)

**Files:**
- Create: `src/hypertensiondb/index/sparse.py`
- Test: `tests/unit/test_sparse.py`

- [ ] **Step 1: 写 sparse 失败测试**

Create `tests/unit/test_sparse.py`:
```python
import pytest
from hypertensiondb.index.sparse import SparseVectorizer


@pytest.fixture
def vectorizer():
    return SparseVectorizer()


@pytest.mark.unit
def test_chinese_text_produces_nonempty_vector(vectorizer):
    indices, values = vectorizer.vectorize("原发性高血压是心血管疾病的主要危险因素")
    assert len(indices) > 0
    assert len(indices) == len(values)


@pytest.mark.unit
def test_english_text_produces_nonempty_vector(vectorizer):
    indices, values = vectorizer.vectorize("primary hypertension cardiovascular risk")
    assert len(indices) > 0
    assert len(indices) == len(values)


@pytest.mark.unit
def test_mixed_text(vectorizer):
    indices, values = vectorizer.vectorize("ARB联合CCB treatment of hypertension")
    assert len(indices) > 0


@pytest.mark.unit
def test_all_values_positive(vectorizer):
    _, values = vectorizer.vectorize("缬沙坦联合氨氯地平治疗高血压")
    assert all(v > 0 for v in values)


@pytest.mark.unit
def test_all_indices_nonnegative(vectorizer):
    indices, _ = vectorizer.vectorize("hypertension ARB CCB combination therapy")
    assert all(idx >= 0 for idx in indices)


@pytest.mark.unit
def test_no_duplicate_indices(vectorizer):
    indices, _ = vectorizer.vectorize("high blood pressure hypertension blood")
    assert len(indices) == len(set(indices))


@pytest.mark.unit
def test_empty_text_returns_empty(vectorizer):
    indices, values = vectorizer.vectorize("")
    assert indices == []
    assert values == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_sparse.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 sparse.py**

Create `src/hypertensiondb/index/sparse.py`:
```python
import math
import re
from collections import Counter

import jieba

_VOCAB_SIZE = 2**16  # 65536 — hash space for term indices
_MIN_TOKEN_LEN = 1
_STOPWORDS = {"的", "了", "是", "在", "和", "与", "或", "也", "都", "把", "被", "对"}


def _tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text using jieba."""
    tokens = []
    for token in jieba.cut(text):
        token = token.strip().lower()
        if (
            len(token) >= _MIN_TOKEN_LEN
            and not token.isspace()
            and not re.fullmatch(r"[\s\W]+", token)
            and token not in _STOPWORDS
        ):
            tokens.append(token)
    return tokens


def _term_to_index(term: str) -> int:
    """Map term string to a non-negative index via hash."""
    h = hash(term) % _VOCAB_SIZE
    return h if h >= 0 else h + _VOCAB_SIZE


class SparseVectorizer:
    """Convert text into sparse TF-weighted vectors for Qdrant hybrid search."""

    def vectorize(self, text: str) -> tuple[list[int], list[float]]:
        """Return (indices, values) for the given text.

        Uses normalized term frequency as weights.
        Handles hash collisions by summing weights.
        """
        if not text or not text.strip():
            return [], []

        tokens = _tokenize(text)
        if not tokens:
            return [], []

        tf = Counter(tokens)
        doc_len = len(tokens)
        norm = math.sqrt(doc_len)

        # Aggregate by index (handle hash collisions)
        index_weights: dict[int, float] = {}
        for term, count in tf.items():
            idx = _term_to_index(term)
            weight = count / norm
            index_weights[idx] = index_weights.get(idx, 0.0) + weight

        indices = list(index_weights.keys())
        values = list(index_weights.values())
        return indices, values
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_sparse.py -v`
Expected: 7 passed

---

## Task B.4: BaseEmbedder ABC + MockEmbedder

**Files:**
- Create: `src/hypertensiondb/index/embedder.py`
- Create: `src/hypertensiondb/index/embedder_mock.py`
- Test: `tests/unit/test_embedder_mock.py`

- [ ] **Step 1: 写 MockEmbedder 失败测试**

Create `tests/unit/test_embedder_mock.py`:
```python
import pytest
from hypertensiondb.index.embedder_mock import MockEmbedder


@pytest.fixture
def embedder():
    return MockEmbedder(dim=8)


@pytest.mark.unit
def test_embed_returns_correct_shape(embedder):
    texts = ["高血压治疗", "combination therapy", "ARB联合CCB"]
    result = embedder.embed(texts)
    assert len(result) == 3
    assert all(len(v) == 8 for v in result)


@pytest.mark.unit
def test_embed_returns_float_vectors(embedder):
    result = embedder.embed(["test"])
    assert all(isinstance(x, float) for x in result[0])


@pytest.mark.unit
def test_embed_same_text_same_vector(embedder):
    """Deterministic: same text → same vector."""
    v1 = embedder.embed(["高血压"])[0]
    v2 = embedder.embed(["高血压"])[0]
    assert v1 == v2


@pytest.mark.unit
def test_embed_different_text_different_vector(embedder):
    v1 = embedder.embed(["高血压"])[0]
    v2 = embedder.embed(["低血压"])[0]
    assert v1 != v2


@pytest.mark.unit
def test_dimension_property(embedder):
    assert embedder.dimension == 8


@pytest.mark.unit
def test_model_name_property(embedder):
    assert embedder.model_name == "mock"


@pytest.mark.unit
def test_embed_empty_list_returns_empty(embedder):
    assert embedder.embed([]) == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_embedder_mock.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 embedder.py**

Create `src/hypertensiondb/index/embedder.py`:
```python
from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of float vectors."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""
```

- [ ] **Step 4: 实现 embedder_mock.py**

Create `src/hypertensiondb/index/embedder_mock.py`:
```python
import hashlib
import struct
from hypertensiondb.index.embedder import BaseEmbedder


class MockEmbedder(BaseEmbedder):
    """Deterministic mock embedder for tests. No API calls."""

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(t) for t in texts]

    def _text_to_vector(self, text: str) -> list[float]:
        """Derive a deterministic float vector from text via SHA-256."""
        digest = hashlib.sha256(text.encode()).digest()
        # Unpack `dim` floats from the digest (repeat if needed)
        floats = []
        for i in range(self._dim):
            byte_offset = (i * 4) % len(digest)
            chunk = digest[byte_offset:byte_offset + 4]
            if len(chunk) < 4:
                chunk = chunk + digest[:4 - len(chunk)]
            (value,) = struct.unpack(">I", chunk)
            floats.append(value / 0xFFFFFFFF)  # normalize to [0, 1]
        return floats

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "mock"
```

- [ ] **Step 5: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_embedder_mock.py -v`
Expected: 7 passed

---

## Task B.5: QdrantIndexClient

**Files:**
- Create: `src/hypertensiondb/index/qdrant_index_client.py`
- Test: `tests/unit/test_qdrant_index_client.py`

- [ ] **Step 1: 写 QdrantIndexClient 失败测试**

Create `tests/unit/test_qdrant_index_client.py`:
```python
import pytest
from unittest.mock import MagicMock, patch, call
from qdrant_client.models import Distance

from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.index.chunk import EvidenceChunk


def _make_chunk(evidence_id="EV-RCT-2026-PENG-001", section="results") -> EvidenceChunk:
    return EvidenceChunk(
        point_id="00000000-0000-0000-0000-000000000001",
        evidence_id=evidence_id,
        section_name=section,
        text="SBP 下降 8 mmHg",
        is_clinical_bottom_line=False,
        metadata={"type": "RCT", "year": 2026},
    )


@pytest.fixture
def mock_qdrant():
    return MagicMock()


@pytest.fixture
def client(mock_qdrant):
    return QdrantIndexClient(qdrant=mock_qdrant, collection_name="test_col")


@pytest.mark.unit
def test_ensure_collection_creates_when_missing(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = False
    client.ensure_collection(dense_dim=8)
    mock_qdrant.create_collection.assert_called_once()
    args, kwargs = mock_qdrant.create_collection.call_args
    assert kwargs.get("collection_name") == "test_col" or args[0] == "test_col"


@pytest.mark.unit
def test_ensure_collection_skips_if_exists(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = True
    client.ensure_collection(dense_dim=8)
    mock_qdrant.create_collection.assert_not_called()


@pytest.mark.unit
def test_upsert_chunks_calls_upsert(client, mock_qdrant):
    chunk = _make_chunk()
    dense = [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]]
    sparse = [([1, 2, 3], [0.5, 0.3, 0.2])]
    client.upsert_chunks([chunk], dense, sparse)
    mock_qdrant.upsert.assert_called_once()


@pytest.mark.unit
def test_delete_collection_calls_delete(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = True
    client.delete_collection()
    mock_qdrant.delete_collection.assert_called_once_with(collection_name="test_col")


@pytest.mark.unit
def test_delete_collection_skips_if_not_exists(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = False
    client.delete_collection()
    mock_qdrant.delete_collection.assert_not_called()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_qdrant_index_client.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 qdrant_index_client.py**

Create `src/hypertensiondb/index/qdrant_index_client.py`:
```python
from datetime import datetime, timezone
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseIndexParams,
    PointStruct, SparseVector, NamedSparseVector, NamedVector,
)

from hypertensiondb.index.chunk import EvidenceChunk

_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"
_BATCH_SIZE = 64


class QdrantIndexClient:
    """Thin wrapper around QdrantClient focused on evidence indexing operations."""

    def __init__(self, qdrant: QdrantClient, collection_name: str) -> None:
        self._q = qdrant
        self._collection = collection_name

    def ensure_collection(self, dense_dim: int) -> None:
        """Create collection if it doesn't exist."""
        if self._q.collection_exists(self._collection):
            return
        self._q.create_collection(
            collection_name=self._collection,
            vectors_config={
                _DENSE_VECTOR_NAME: VectorParams(
                    size=dense_dim, distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                _SPARSE_VECTOR_NAME: SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            },
        )

    def upsert_chunks(
        self,
        chunks: list[EvidenceChunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[tuple[list[int], list[float]]],
    ) -> None:
        """Upsert chunks with both dense and sparse vectors in batches."""
        now = datetime.now(timezone.utc).isoformat()
        points = []
        for chunk, dense, (sp_indices, sp_values) in zip(chunks, dense_vectors, sparse_vectors):
            payload = {
                **chunk.metadata,
                "evidence_id": chunk.evidence_id,
                "section_name": chunk.section_name,
                "text": chunk.text,
                "is_clinical_bottom_line": chunk.is_clinical_bottom_line,
                "indexed_at": now,
            }
            points.append(PointStruct(
                id=chunk.point_id,
                vector={
                    _DENSE_VECTOR_NAME: dense,
                    _SPARSE_VECTOR_NAME: SparseVector(
                        indices=sp_indices, values=sp_values
                    ),
                },
                payload=payload,
            ))

        for i in range(0, len(points), _BATCH_SIZE):
            self._q.upsert(
                collection_name=self._collection,
                points=points[i:i + _BATCH_SIZE],
            )

    def get_evidence_indexed_at(self, evidence_id: str) -> Optional[str]:
        """Return the indexed_at ISO string for the given evidence_id, or None."""
        results, _ = self._q.scroll(
            collection_name=self._collection,
            scroll_filter={"must": [{"key": "evidence_id", "match": {"value": evidence_id}}]},
            limit=1,
            with_payload=["indexed_at"],
        )
        if results:
            return results[0].payload.get("indexed_at")
        return None

    def delete_collection(self) -> None:
        """Delete the collection if it exists."""
        if self._q.collection_exists(self._collection):
            self._q.delete_collection(collection_name=self._collection)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_qdrant_index_client.py -v`
Expected: 5 passed

---

## Task B.6: IndexPipeline

**Files:**
- Create: `src/hypertensiondb/index/pipeline.py`
- Test: `tests/unit/test_pipeline.py`

- [ ] **Step 1: 写 pipeline 失败测试**

Create `tests/unit/test_pipeline.py`:
```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 pipeline.py**

Create `src/hypertensiondb/index/pipeline.py`:
```python
from pathlib import Path

from hypertensiondb.index.chunker import split_evidence_into_chunks
from hypertensiondb.index.embedder import BaseEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.schema.base import Status

_INDEXABLE_STATUSES = {Status.REVIEWED, Status.PUBLISHED}


class IndexPipeline:
    """Orchestrate: chunk → embed → sparse → upsert."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        sparse_vectorizer: SparseVectorizer,
        qdrant_client: QdrantIndexClient,
        collection_name: str,
    ) -> None:
        self._embedder = embedder
        self._sparse = sparse_vectorizer
        self._qdrant = qdrant_client
        self._collection = collection_name
        self._qdrant.ensure_collection(dense_dim=self._embedder.dimension)

    def index_file(self, path: Path) -> int:
        """Index all chunks from one evidence file. Returns chunk count (0 if skipped)."""
        chunks = split_evidence_into_chunks(path)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        dense_vectors = self._embedder.embed(texts)
        sparse_vectors = [self._sparse.vectorize(t) for t in texts]
        self._qdrant.upsert_chunks(chunks, dense_vectors, sparse_vectors)
        return len(chunks)

    def rebuild(self, evidence_root: Path) -> int:
        """Delete + recreate collection, then index all reviewed/published files."""
        self._qdrant.delete_collection()
        self._qdrant.ensure_collection(dense_dim=self._embedder.dimension)
        total = 0
        for md in sorted(evidence_root.rglob("*.md")):
            if "_quarantine" in md.parts:
                continue
            total += self.index_file(md)
        return total
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_pipeline.py -v`
Expected: 3 passed

---

## Task B.7: IncrementalUpdater

**Files:**
- Create: `src/hypertensiondb/index/incremental.py`
- Test: `tests/unit/test_incremental.py`

- [ ] **Step 1: 写 incremental 失败测试**

Create `tests/unit/test_incremental.py`:
```python
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
    mock_qdrant.get_evidence_indexed_at.return_value = None  # not in Qdrant

    result = find_files_needing_reindex(tmp_path, mock_qdrant)
    assert md in result


@pytest.mark.unit
def test_up_to_date_file_skipped(tmp_path):
    """A file indexed after its mtime is NOT returned."""
    md = tmp_path / "EV-RCT-2026-TEST-001.md"
    _write_reviewed_md(md, "EV-RCT-2026-TEST-001")

    from datetime import datetime, timezone
    # indexed_at is in the future relative to file mtime
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_incremental.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 incremental.py**

Create `src/hypertensiondb/index/incremental.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.schema.base import Status
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient

_INDEXABLE_STATUSES = {Status.REVIEWED, Status.PUBLISHED}


def find_files_needing_reindex(
    evidence_root: Path,
    qdrant_client: QdrantIndexClient,
) -> list[Path]:
    """Return .md files that are new or modified since they were last indexed.

    Only considers files with status ∈ {reviewed, published}.
    """
    needs_reindex: list[Path] = []

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue

        try:
            fm, _ = load_evidence(md)
        except Exception:
            continue

        if fm.status not in _INDEXABLE_STATUSES:
            continue

        indexed_at_str = qdrant_client.get_evidence_indexed_at(fm.id)
        if indexed_at_str is None:
            needs_reindex.append(md)
            continue

        file_mtime = datetime.fromtimestamp(md.stat().st_mtime, tz=timezone.utc)
        indexed_at = datetime.fromisoformat(indexed_at_str)
        if indexed_at.tzinfo is None:
            indexed_at = indexed_at.replace(tzinfo=timezone.utc)

        if file_mtime > indexed_at:
            needs_reindex.append(md)

    return needs_reindex
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_incremental.py -v`
Expected: 3 passed

---

## Task B.8: 具体 Embedder 实现 — OpenAI + Zhipu

**Files:**
- Create: `src/hypertensiondb/index/embedder_openai.py`
- Create: `src/hypertensiondb/index/embedder_zhipu.py`
- Test: `tests/unit/test_embedder_openai.py`
- Test: `tests/unit/test_embedder_zhipu.py`

- [ ] **Step 1: 写 OpenAI embedder 失败测试**

Create `tests/unit/test_embedder_openai.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_openai_embedder_calls_api(monkeypatch):
    """embed() calls openai.embeddings.create and returns float vectors."""
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder

    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 1536),
        MagicMock(embedding=[0.2] * 1536),
    ]

    with patch("hypertensiondb.index.embedder_openai.openai.embeddings.create",
               return_value=mock_response) as mock_create:
        embedder = OpenAIEmbedder(api_key="test-key", model="text-embedding-3-small", dim=1536)
        result = embedder.embed(["text1", "text2"])

    mock_create.assert_called_once()
    assert len(result) == 2
    assert len(result[0]) == 1536


@pytest.mark.unit
def test_openai_embedder_dimension():
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder
    e = OpenAIEmbedder(api_key="x", model="text-embedding-3-small", dim=1536)
    assert e.dimension == 1536


@pytest.mark.unit
def test_openai_embedder_model_name():
    from hypertensiondb.index.embedder_openai import OpenAIEmbedder
    e = OpenAIEmbedder(api_key="x", model="text-embedding-3-small", dim=1536)
    assert e.model_name == "text-embedding-3-small"
```

- [ ] **Step 2: 实现 embedder_openai.py**

Create `src/hypertensiondb/index/embedder_openai.py`:
```python
import openai
from hypertensiondb.index.embedder import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """Embedder backed by OpenAI Embeddings API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-large", dim: int = 3072) -> None:
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = openai.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 3: 跑 OpenAI embedder 测试**

Run: `py -m pytest tests/unit/test_embedder_openai.py -v`
Expected: 3 passed

- [ ] **Step 4: 写 Zhipu embedder 失败测试**

Create `tests/unit/test_embedder_zhipu.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_zhipu_embedder_calls_api(monkeypatch):
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder

    fake_result = [[0.1] * 2048, [0.2] * 2048]

    with patch("hypertensiondb.index.embedder_zhipu.ZhipuEmbedder._call_api",
               return_value=fake_result) as mock_call:
        embedder = ZhipuEmbedder(api_key="test-key")
        result = embedder.embed(["text1", "text2"])

    mock_call.assert_called_once_with(["text1", "text2"])
    assert len(result) == 2
    assert len(result[0]) == 2048


@pytest.mark.unit
def test_zhipu_embedder_dimension():
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
    e = ZhipuEmbedder(api_key="x")
    assert e.dimension == 2048


@pytest.mark.unit
def test_zhipu_embedder_model_name():
    from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
    e = ZhipuEmbedder(api_key="x")
    assert e.model_name == "embedding-3"
```

- [ ] **Step 5: 实现 embedder_zhipu.py**

Create `src/hypertensiondb/index/embedder_zhipu.py`:
```python
import httpx
from hypertensiondb.index.embedder import BaseEmbedder

_ZHIPU_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/embeddings"
_DEFAULT_MODEL = "embedding-3"
_DEFAULT_DIM = 2048


class ZhipuEmbedder(BaseEmbedder):
    """Embedder backed by Zhipu AI Embeddings API (国内可直接访问，无需代理)."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        dim: int = _DEFAULT_DIM,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dim = dim
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._call_api(texts)

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "input": texts}
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(_ZHIPU_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        # Sort by index to preserve order
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 6: 跑 Zhipu embedder 测试**

Run: `py -m pytest tests/unit/test_embedder_zhipu.py -v`
Expected: 3 passed

---

## Task B.9: Wire CLI + 集成测试

**Files:**
- Modify: `src/hypertensiondb/cli.py`
- Create: `tests/integration/test_qdrant_index.py`

- [ ] **Step 1: 写集成测试 (testcontainers + 真实 Qdrant)**

Create `tests/integration/test_qdrant_index.py`:
```python
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

    # Verify Qdrant has the points
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
    # Write two reviewed files
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
```

- [ ] **Step 2: 修改 cli.py — 实现 hdb index update / rebuild**

Replace the placeholder commands in `src/hypertensiondb/cli.py`:
```python
import os
from pathlib import Path

import typer
from hypertensiondb import __version__

app = typer.Typer(help="Hypertension Evidence DB CLI")

EVIDENCE_ROOT = Path("evidence")
COLLECTION_NAME = "hypertension_evidence"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    """hdb: Hypertension Evidence DB command line."""


ingest_app = typer.Typer(help="Ingest evidence from PDF / API / manual")
index_app = typer.Typer(help="Manage Qdrant index")
lint_app = typer.Typer(help="Data quality checks")

app.add_typer(ingest_app, name="ingest")
app.add_typer(index_app, name="index")
app.add_typer(lint_app, name="lint")


@ingest_app.command("dry-run")
def ingest_dry_run() -> None:
    """Placeholder — implemented in Plan D."""
    typer.echo("Not yet implemented (Plan D)")


@lint_app.command("run")
def lint_run() -> None:
    """Placeholder — implemented in Plan E."""
    typer.echo("Not yet implemented (Plan E)")


def _build_pipeline(dense_dim: int = 2048):
    """Build IndexPipeline from environment variables."""
    from qdrant_client import QdrantClient
    from hypertensiondb.index.embedder_mock import MockEmbedder
    from hypertensiondb.index.sparse import SparseVectorizer
    from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
    from hypertensiondb.index.pipeline import IndexPipeline

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant = QdrantClient(host=host, port=port)

    # Embedder selection: default to MockEmbedder for local dev
    # Set EMBEDDER=openai|zhipu to use real embedders
    embedder_name = os.getenv("EMBEDDER", "mock")
    if embedder_name == "openai":
        from hypertensiondb.index.embedder_openai import OpenAIEmbedder
        embedder = OpenAIEmbedder(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"),
            dim=int(os.getenv("EMBED_DIM", "3072")),
        )
    elif embedder_name == "zhipu":
        from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
        embedder = ZhipuEmbedder(
            api_key=os.environ["ZHIPU_API_KEY"],
            dim=int(os.getenv("EMBED_DIM", "2048")),
        )
    else:
        embedder = MockEmbedder(dim=int(os.getenv("EMBED_DIM", "8")))

    idx_client = QdrantIndexClient(qdrant=qdrant, collection_name=COLLECTION_NAME)
    return IndexPipeline(
        embedder=embedder,
        sparse_vectorizer=SparseVectorizer(),
        qdrant_client=idx_client,
        collection_name=COLLECTION_NAME,
    )


@index_app.command("update")
def index_update() -> None:
    """Incrementally index new or modified reviewed/published evidence files."""
    from hypertensiondb.index.incremental import find_files_needing_reindex

    pipeline = _build_pipeline()
    files = find_files_needing_reindex(EVIDENCE_ROOT, pipeline._qdrant)
    if not files:
        typer.echo("Nothing to update — all files are up to date.")
        return
    typer.echo(f"Indexing {len(files)} file(s)…")
    total = 0
    for path in files:
        count = pipeline.index_file(path)
        typer.echo(f"  {path.name}: {count} chunk(s)")
        total += count
    typer.echo(f"Done. {total} chunk(s) indexed.")


@index_app.command("rebuild")
def index_rebuild(
    confirm: bool = typer.Option(False, "--confirm", help="Required to proceed with rebuild"),
) -> None:
    """Delete and rebuild the entire Qdrant collection from scratch."""
    if not confirm:
        typer.echo("This will DELETE and rebuild the entire collection.")
        typer.echo("Add --confirm to proceed.")
        raise typer.Exit(1)
    pipeline = _build_pipeline()
    typer.echo("Rebuilding collection…")
    total = pipeline.rebuild(EVIDENCE_ROOT)
    typer.echo(f"Done. {total} chunk(s) indexed.")
```

- [ ] **Step 3: 跑所有单元测试确认不破坏 Plan A**

Run: `py -m pytest tests/unit/ -v --tb=short`
Expected: 全部通过（Plan A 的 34 tests + Plan B 新增约 26 tests = 约 60 passed）

- [ ] **Step 4: 启动 Qdrant 并跑集成测试（需要 Docker Desktop 已运行）**

先确认 Docker 已运行：
Run: `docker info --format "{{.ServerVersion}}"` 
Expected: 返回版本号，如 `27.x.x`

然后跑集成测试（testcontainers 会自动拉取并启动 qdrant 容器）：
Run: `py -m pytest tests/integration/test_qdrant_index.py -v -m integration --tb=short`
Expected: 2 passed（约需 30-60 秒，首次运行需拉取 qdrant 镜像）

- [ ] **Step 5: 验证 `hdb index update` 命令存在**

Run: `hdb index --help`
Expected: 显示 `update` 和 `rebuild` 两个子命令

---

## 自检（Self-Review）

**1. Spec 覆盖检查：**

| 设计 §4 要求 | 对应 Task |
|-------------|----------|
| chunk by ## 节区（超长按 ### 切） | Task B.2 (chunker.py) |
| dense + sparse 双索引 | Task B.4 + B.3 |
| point_id = sha1(evidence_id+section) | Task B.2 (_make_point_id) |
| draft 不入索引 | Task B.2 + B.6 |
| 临床要点节区打 boost 标志 | Task B.2 (is_clinical_bottom_line 字段，Plan C 在检索时用) |
| Embedding 可插拔接口 | Task B.4 (BaseEmbedder) + B.8 |
| BM25 sparse | Task B.3 (SparseVectorizer, jieba TF) |
| `hdb index update`（增量） | Task B.9 (cli.py) + B.7 (incremental.py) |
| `hdb index rebuild`（全量） | Task B.9 (cli.py) + B.6 (pipeline.rebuild) |
| Qdrant upsert 分批（每批 64） | Task B.5 (qdrant_index_client.py _BATCH_SIZE) |
| indexed_at payload 字段 | Task B.5 (upsert_chunks payload) |
| 索引失败写日志 | 未覆盖 — 当前 index_file 失败会抛异常。Plan B 暂不实现结构化日志（Plan E 补充） |
| 集成测试（真实 Qdrant） | Task B.9 (testcontainers) |

**2. Placeholder 扫描：** 无 TBD/TODO 表达。

**3. 类型一致性：**
- `split_evidence_into_chunks(path: Path) → list[EvidenceChunk]` — 在 B.2 定义，B.6 pipeline.index_file 中调用 ✓
- `QdrantIndexClient.upsert_chunks(chunks, dense_vectors, sparse_vectors)` — B.5 定义，B.6 调用 ✓
- `QdrantIndexClient.ensure_collection(dense_dim: int)` — B.5 定义，B.6 __init__ 调用 ✓
- `find_files_needing_reindex(evidence_root, qdrant_client)` — B.7 定义，B.9 cli.py 调用 ✓
- `MockEmbedder(dim=8)` — B.4 定义，B.5/B.6/B.9 测试中使用 ✓

---

## 执行完成标志

Plan B 完成时你应该能够：

1. `py -m pytest tests/unit/ -v` → 全部通过（约 60 tests）
2. `py -m pytest tests/integration/test_qdrant_index.py -v -m integration` → 2 passed（需 Docker）
3. `hdb index --help` → 显示 update / rebuild
4. 启动 `docker compose up -d`，运行 `hdb index update` → "Nothing to update"（evidence/ 无 reviewed 文件时）
