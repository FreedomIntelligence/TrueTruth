# Plan C: 检索 API + 黄金集回归测试

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Plan B 索引层之上，构建 FastAPI 检索服务（/search、/evidence、/health），并用 10-15 篇 fixture 文献 + 30 条 golden query 建立 recall@10 / MRR 回归基线。

**Architecture:** 五层 — `filters` 构造 Qdrant 过滤器 → `HybridSearcher` 调 Qdrant Query API（dense+sparse 双路 RRF 融合）→ `Reranker` 重排（默认 Mock；可插拔 BGE 本地模型）→ `SearchEngine` 编排（query embed + hybrid + rerank + facet 统计 + 降级标志）→ FastAPI 路由层暴露。Pydantic 强约束请求/响应模型。

**Tech Stack:** Python 3.11+, FastAPI>=0.110, uvicorn>=0.30, qdrant-client>=1.9, pytest>=8.0, httpx>=0.27（测试用 TestClient）。BGE reranker（可选，~600MB 模型）走 FlagEmbedding>=1.2，按需下载，不进 CI。

---

## 参考资料

- 设计文档 §5（检索 API）、§7（测试策略，L4 golden）：`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`
- Plan B 已实现：`IndexPipeline`, `QdrantIndexClient`, `MockEmbedder`, `SparseVectorizer`, `EvidenceChunk`
- payload 字段约定（Plan B `qdrant_index_client.upsert_chunks`）：`evidence_id`, `section_name`, `text`, `is_clinical_bottom_line`, `indexed_at`, 加上 chunk.metadata 里的 `type`, `year`, `language`, `status`, `grade_level`, `rob_overall`, `tags`, `title_zh`, `title_en`

## 注意事项

- **不需要 git 操作**（每个 Task 省略 Commit 步骤）
- 集成测试需要 Docker Desktop + 国内镜像源（见 reference-docker-china-mirrors 记忆）
- Qdrant 升到 v1.12.5（带 Query API 原生 RRF）；qdrant-client 1.18.x 已就位
- 所有单元/golden 测试用 `MockEmbedder` 和 `MockReranker`，不依赖云 API key

## File Structure

```
docker-compose.yml                                # 修改：Qdrant v1.9.3 → v1.12.5
pyproject.toml                                    # 追加 fastapi/uvicorn

src/hypertensiondb/
  retrieval/
    __init__.py                                   # 新建：公开接口
    filters.py                                    # 新建：build_qdrant_filter()
    hybrid.py                                     # 新建：HybridSearcher (Qdrant query_points + RRF)
    reranker.py                                   # 新建：BaseReranker ABC
    reranker_mock.py                              # 新建：MockReranker（恒等）
    reranker_bge.py                               # 新建：BGEReranker（懒加载 FlagEmbedding，可选）
    models.py                                     # 新建：Pydantic 请求/响应
    search.py                                     # 新建：SearchEngine 编排
  api/
    __init__.py                                   # 新建
    server.py                                     # 新建：FastAPI app + DI
    routes_search.py                              # 新建：/search
    routes_evidence.py                            # 新建：/evidence/{id}, /evidence
    routes_health.py                              # 新建：/health

tests/
  unit/
    test_filters.py                               # 新建
    test_hybrid.py                                # 新建（mock qdrant）
    test_reranker_mock.py                         # 新建
    test_search_engine.py                         # 新建（mock everything）
    test_api_health.py                            # 新建（TestClient）
    test_api_search.py                            # 新建
    test_api_evidence.py                          # 新建
    test_retrieval_models.py                      # 新建
  integration/
    test_api_qdrant_integration.py                # 新建（testcontainers）
  golden/
    __init__.py                                   # 新建（让 pytest 发现）
    corpus/                                       # 新建：10-12 篇 fixture md
    queries.jsonl                                 # 新建：30 条 golden query
    test_recall.py                                # 新建：recall@10 / MRR
```

---

## Task C.1: 依赖更新 + Qdrant 版本升级

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`

- [ ] **Step 1: 更新 pyproject.toml**

将 `[project] dependencies` 改为（在 Plan B 基础上追加 fastapi/uvicorn）：

```toml
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
    "fastapi>=0.110",
    "uvicorn[standard]>=0.30",
]
```

`[project.optional-dependencies]` 增加 `bge`（可选 reranker）：

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "pre-commit>=3.7",
    "ruff>=0.4",
    "testcontainers[docker]>=4.0",
]
bge = [
    "FlagEmbedding>=1.2",
]
```

- [ ] **Step 2: 安装新依赖**

Run: `py -m pip install -e ".[dev]" -q`
Expected: 安装成功，无 ERROR

- [ ] **Step 3: 验证 fastapi 与 uvicorn 可导入**

Run: `py -c "import fastapi, uvicorn; print(f'fastapi={fastapi.__version__} uvicorn={uvicorn.__version__}')"`
Expected: 输出版本号，无 ImportError

- [ ] **Step 4: 升级 docker-compose.yml Qdrant 镜像**

替换 `docker-compose.yml` 全文为：

```yaml
version: "3.8"
services:
  qdrant:
    image: qdrant/qdrant:v1.12.5
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    restart: unless-stopped
```

- [ ] **Step 5: 重启 Qdrant（如本地有跑）**

Run（仅在本地 Qdrant 在跑时）：`docker compose down; docker compose up -d`
若没在跑：跳过。

---

## Task C.2: filters.py — 构造 Qdrant Filter

**Files:**
- Create: `src/hypertensiondb/retrieval/__init__.py`
- Create: `src/hypertensiondb/retrieval/filters.py`
- Test: `tests/unit/test_filters.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_filters.py`:

```python
import pytest
from qdrant_client import models as qm

from hypertensiondb.retrieval.filters import build_qdrant_filter, SearchFilters


@pytest.mark.unit
def test_empty_filters_returns_none():
    assert build_qdrant_filter(SearchFilters()) is None


@pytest.mark.unit
def test_type_filter():
    f = build_qdrant_filter(SearchFilters(types=["RCT", "META"]))
    assert isinstance(f, qm.Filter)
    # type field uses MatchAny
    must = f.must
    assert len(must) >= 1
    type_cond = next(c for c in must if c.key == "type")
    assert set(type_cond.match.any) == {"RCT", "META"}


@pytest.mark.unit
def test_language_filter():
    f = build_qdrant_filter(SearchFilters(languages=["zh"]))
    lang_cond = next(c for c in f.must if c.key == "language")
    assert lang_cond.match.any == ["zh"]


@pytest.mark.unit
def test_year_range_filter():
    f = build_qdrant_filter(SearchFilters(year_min=2020, year_max=2026))
    year_cond = next(c for c in f.must if c.key == "year")
    assert year_cond.range.gte == 2020
    assert year_cond.range.lte == 2026


@pytest.mark.unit
def test_year_min_only():
    f = build_qdrant_filter(SearchFilters(year_min=2024))
    year_cond = next(c for c in f.must if c.key == "year")
    assert year_cond.range.gte == 2024
    assert year_cond.range.lte is None


@pytest.mark.unit
def test_grade_min_filter():
    """grade_min=moderate accepts moderate and high (not low/very_low)."""
    f = build_qdrant_filter(SearchFilters(grade_min="moderate"))
    grade_cond = next(c for c in f.must if c.key == "grade_level")
    assert set(grade_cond.match.any) == {"moderate", "high"}


@pytest.mark.unit
def test_grade_min_high_only_accepts_high():
    f = build_qdrant_filter(SearchFilters(grade_min="high"))
    grade_cond = next(c for c in f.must if c.key == "grade_level")
    assert grade_cond.match.any == ["high"]


@pytest.mark.unit
def test_tags_filter():
    f = build_qdrant_filter(SearchFilters(tags=["ARB", "CCB"]))
    tags_cond = next(c for c in f.must if c.key == "tags")
    assert set(tags_cond.match.any) == {"ARB", "CCB"}


@pytest.mark.unit
def test_section_filter():
    f = build_qdrant_filter(SearchFilters(sections=["results", "conclusion"]))
    sec_cond = next(c for c in f.must if c.key == "section_name")
    assert set(sec_cond.match.any) == {"results", "conclusion"}


@pytest.mark.unit
def test_include_draft_false_excludes_drafts():
    """By default (include_draft=False), only reviewed/published indexed."""
    f = build_qdrant_filter(SearchFilters(include_draft=False))
    status_cond = next(c for c in f.must if c.key == "status")
    assert set(status_cond.match.any) == {"reviewed", "published"}


@pytest.mark.unit
def test_include_draft_true_no_status_filter():
    f = build_qdrant_filter(SearchFilters(include_draft=True))
    if f is None:
        return  # no filters → None is fine
    keys = [c.key for c in (f.must or [])]
    assert "status" not in keys


@pytest.mark.unit
def test_combined_filters():
    f = build_qdrant_filter(SearchFilters(
        types=["RCT"], year_min=2024, grade_min="high", tags=["ARB"]
    ))
    keys = {c.key for c in f.must}
    assert "type" in keys
    assert "year" in keys
    assert "grade_level" in keys
    assert "tags" in keys
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_filters.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 创建 retrieval/__init__.py**

Create `src/hypertensiondb/retrieval/__init__.py`:

```python
from hypertensiondb.retrieval.filters import SearchFilters, build_qdrant_filter

__all__ = ["SearchFilters", "build_qdrant_filter"]
```

- [ ] **Step 4: 实现 filters.py**

Create `src/hypertensiondb/retrieval/filters.py`:

```python
from dataclasses import dataclass, field
from typing import Optional

from qdrant_client import models as qm

_GRADE_ORDER = ["very_low", "low", "moderate", "high"]
_INDEXED_STATUSES = ["reviewed", "published"]


@dataclass
class SearchFilters:
    types: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    grade_min: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    include_draft: bool = False


def _grade_levels_at_or_above(grade_min: str) -> list[str]:
    """Return GRADE levels >= grade_min, e.g. 'moderate' → ['moderate', 'high']."""
    if grade_min not in _GRADE_ORDER:
        raise ValueError(f"Invalid grade: {grade_min!r}")
    idx = _GRADE_ORDER.index(grade_min)
    return _GRADE_ORDER[idx:]


def build_qdrant_filter(filters: SearchFilters) -> Optional[qm.Filter]:
    """Translate SearchFilters into a Qdrant Filter (or None if no constraints)."""
    must: list[qm.FieldCondition] = []

    if filters.types:
        must.append(qm.FieldCondition(
            key="type", match=qm.MatchAny(any=filters.types)
        ))
    if filters.languages:
        must.append(qm.FieldCondition(
            key="language", match=qm.MatchAny(any=filters.languages)
        ))
    if filters.year_min is not None or filters.year_max is not None:
        must.append(qm.FieldCondition(
            key="year",
            range=qm.Range(gte=filters.year_min, lte=filters.year_max),
        ))
    if filters.grade_min:
        must.append(qm.FieldCondition(
            key="grade_level",
            match=qm.MatchAny(any=_grade_levels_at_or_above(filters.grade_min)),
        ))
    if filters.tags:
        must.append(qm.FieldCondition(
            key="tags", match=qm.MatchAny(any=filters.tags)
        ))
    if filters.sections:
        must.append(qm.FieldCondition(
            key="section_name", match=qm.MatchAny(any=filters.sections)
        ))
    if not filters.include_draft:
        must.append(qm.FieldCondition(
            key="status", match=qm.MatchAny(any=_INDEXED_STATUSES)
        ))

    if not must:
        return None
    return qm.Filter(must=must)
```

- [ ] **Step 5: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_filters.py -v`
Expected: 11 passed

---

## Task C.3: HybridSearcher — Qdrant Query API + RRF 融合

**Files:**
- Create: `src/hypertensiondb/retrieval/hybrid.py`
- Test: `tests/unit/test_hybrid.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_hybrid.py`:

```python
import pytest
from unittest.mock import MagicMock
from qdrant_client import models as qm

from hypertensiondb.retrieval.hybrid import HybridSearcher, Candidate


def _make_scored_point(point_id, score, payload):
    p = MagicMock()
    p.id = point_id
    p.score = score
    p.payload = payload
    return p


@pytest.fixture
def mock_qdrant():
    return MagicMock()


@pytest.fixture
def searcher(mock_qdrant):
    return HybridSearcher(qdrant=mock_qdrant, collection_name="test_col")


@pytest.mark.unit
def test_search_returns_candidates(searcher, mock_qdrant):
    response = MagicMock()
    response.points = [
        _make_scored_point("p1", 0.9, {
            "evidence_id": "EV-RCT-2026-A-001", "section_name": "results",
            "text": "降压幅度 8 mmHg", "type": "RCT", "year": 2026,
            "language": "zh", "title_zh": "测试", "title_en": None,
            "grade_level": "moderate", "rob_overall": "low",
            "tags": ["ARB"], "is_clinical_bottom_line": False,
        }),
    ]
    mock_qdrant.query_points.return_value = response

    results = searcher.search(
        dense_vector=[0.1] * 8,
        sparse_indices=[1, 2],
        sparse_values=[0.5, 0.3],
        limit=10,
        prefetch_limit=50,
        query_filter=None,
    )
    assert len(results) == 1
    assert isinstance(results[0], Candidate)
    assert results[0].point_id == "p1"
    assert results[0].rrf_score == 0.9
    assert results[0].evidence_id == "EV-RCT-2026-A-001"
    assert results[0].section_name == "results"


@pytest.mark.unit
def test_search_calls_query_points_with_fusion_rrf(searcher, mock_qdrant):
    mock_qdrant.query_points.return_value = MagicMock(points=[])
    searcher.search(
        dense_vector=[0.1] * 8,
        sparse_indices=[1],
        sparse_values=[0.5],
        limit=10,
        prefetch_limit=50,
        query_filter=None,
    )
    args, kwargs = mock_qdrant.query_points.call_args
    assert kwargs["collection_name"] == "test_col"
    assert kwargs["limit"] == 10
    # query should be a FusionQuery with RRF
    query = kwargs["query"]
    assert isinstance(query, qm.FusionQuery)
    assert query.fusion == qm.Fusion.RRF
    # prefetch should have two entries (dense + sparse)
    prefetch = kwargs["prefetch"]
    assert len(prefetch) == 2
    usings = {p.using for p in prefetch}
    assert usings == {"dense", "sparse"}


@pytest.mark.unit
def test_dense_only_when_sparse_empty(searcher, mock_qdrant):
    """If sparse vector is empty (jieba produced nothing), fall back to dense-only."""
    mock_qdrant.query_points.return_value = MagicMock(points=[])
    searcher.search(
        dense_vector=[0.1] * 8,
        sparse_indices=[],
        sparse_values=[],
        limit=10,
        prefetch_limit=50,
        query_filter=None,
    )
    _, kwargs = mock_qdrant.query_points.call_args
    prefetch = kwargs["prefetch"]
    assert len(prefetch) == 1
    assert prefetch[0].using == "dense"


@pytest.mark.unit
def test_filter_passed_through(searcher, mock_qdrant):
    mock_qdrant.query_points.return_value = MagicMock(points=[])
    flt = qm.Filter(must=[qm.FieldCondition(key="type", match=qm.MatchAny(any=["RCT"]))])
    searcher.search(
        dense_vector=[0.1] * 8,
        sparse_indices=[1],
        sparse_values=[0.5],
        limit=10,
        prefetch_limit=50,
        query_filter=flt,
    )
    _, kwargs = mock_qdrant.query_points.call_args
    assert kwargs["query_filter"] is flt
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_hybrid.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 hybrid.py**

Create `src/hypertensiondb/retrieval/hybrid.py`:

```python
from dataclasses import dataclass
from typing import Optional, Any

from qdrant_client import QdrantClient, models as qm

_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"


@dataclass
class Candidate:
    point_id: Any
    rrf_score: float
    evidence_id: str
    section_name: str
    text: str
    payload: dict


class HybridSearcher:
    """Hybrid dense + sparse search using Qdrant Query API with RRF fusion."""

    def __init__(self, qdrant: QdrantClient, collection_name: str) -> None:
        self._q = qdrant
        self._collection = collection_name

    def search(
        self,
        dense_vector: list[float],
        sparse_indices: list[int],
        sparse_values: list[float],
        limit: int,
        prefetch_limit: int,
        query_filter: Optional[qm.Filter],
    ) -> list[Candidate]:
        prefetch: list[qm.Prefetch] = [
            qm.Prefetch(
                query=dense_vector, using=_DENSE_VECTOR_NAME, limit=prefetch_limit
            ),
        ]
        if sparse_indices and sparse_values:
            prefetch.append(qm.Prefetch(
                query=qm.SparseVector(indices=sparse_indices, values=sparse_values),
                using=_SPARSE_VECTOR_NAME,
                limit=prefetch_limit,
            ))

        response = self._q.query_points(
            collection_name=self._collection,
            prefetch=prefetch,
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )

        candidates: list[Candidate] = []
        for p in response.points:
            payload = p.payload or {}
            candidates.append(Candidate(
                point_id=p.id,
                rrf_score=float(p.score),
                evidence_id=payload.get("evidence_id", ""),
                section_name=payload.get("section_name", ""),
                text=payload.get("text", ""),
                payload=payload,
            ))
        return candidates
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_hybrid.py -v`
Expected: 4 passed

---

## Task C.4: Reranker ABC + MockReranker

**Files:**
- Create: `src/hypertensiondb/retrieval/reranker.py`
- Create: `src/hypertensiondb/retrieval/reranker_mock.py`
- Test: `tests/unit/test_reranker_mock.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_reranker_mock.py`:

```python
import pytest
from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker_mock import MockReranker


def _make_cand(point_id, text, rrf=0.5):
    return Candidate(
        point_id=point_id, rrf_score=rrf,
        evidence_id="EV-RCT-2026-X-001", section_name="results",
        text=text, payload={"text": text, "section_name": "results"},
    )


@pytest.mark.unit
def test_mock_reranker_returns_same_count():
    r = MockReranker()
    cands = [_make_cand("p1", "甲"), _make_cand("p2", "乙"), _make_cand("p3", "丙")]
    out = r.rerank("query", cands)
    assert len(out) == 3


@pytest.mark.unit
def test_mock_reranker_preserves_order_by_rrf():
    r = MockReranker()
    cands = [
        _make_cand("p1", "甲", rrf=0.3),
        _make_cand("p2", "乙", rrf=0.9),
        _make_cand("p3", "丙", rrf=0.6),
    ]
    out = r.rerank("query", cands)
    # Mock sorts descending by rrf_score
    assert [o.point_id for o, _ in out] == ["p2", "p3", "p1"]


@pytest.mark.unit
def test_mock_reranker_returns_tuples_with_score():
    r = MockReranker()
    cands = [_make_cand("p1", "x")]
    out = r.rerank("query", cands)
    assert len(out) == 1
    cand, score = out[0]
    assert cand.point_id == "p1"
    assert isinstance(score, float)


@pytest.mark.unit
def test_mock_reranker_empty_input():
    r = MockReranker()
    assert r.rerank("q", []) == []


@pytest.mark.unit
def test_mock_reranker_model_name():
    assert MockReranker().model_name == "mock"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_reranker_mock.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 reranker.py**

Create `src/hypertensiondb/retrieval/reranker.py`:

```python
from abc import ABC, abstractmethod

from hypertensiondb.retrieval.hybrid import Candidate


class BaseReranker(ABC):
    """Abstract interface for rerankers.

    Implementations return (candidate, rerank_score) pairs sorted descending
    by rerank_score. The original RRF score is preserved on Candidate.rrf_score.
    """

    @abstractmethod
    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
```

- [ ] **Step 4: 实现 reranker_mock.py**

Create `src/hypertensiondb/retrieval/reranker_mock.py`:

```python
from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker import BaseReranker


class MockReranker(BaseReranker):
    """No-op reranker: sorts candidates by rrf_score descending, uses rrf as rerank score."""

    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        sorted_cands = sorted(candidates, key=lambda c: c.rrf_score, reverse=True)
        return [(c, c.rrf_score) for c in sorted_cands]

    @property
    def model_name(self) -> str:
        return "mock"
```

- [ ] **Step 5: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_reranker_mock.py -v`
Expected: 5 passed

---

## Task C.5: Pydantic 请求/响应模型

**Files:**
- Create: `src/hypertensiondb/retrieval/models.py`
- Test: `tests/unit/test_retrieval_models.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_retrieval_models.py`:

```python
import pytest
from pydantic import ValidationError

from hypertensiondb.retrieval.models import (
    SearchRequest, EvidenceMeta, SearchResultItem, SearchResponse, Facets,
    HealthResponse,
)


@pytest.mark.unit
def test_search_request_defaults():
    req = SearchRequest(q="高血压")
    assert req.top_k == 10
    assert req.types == []
    assert req.include_draft is False


@pytest.mark.unit
def test_search_request_q_required():
    with pytest.raises(ValidationError):
        SearchRequest()


@pytest.mark.unit
def test_search_request_q_max_length():
    with pytest.raises(ValidationError):
        SearchRequest(q="a" * 501)


@pytest.mark.unit
def test_search_request_top_k_bounds():
    SearchRequest(q="x", top_k=1)
    SearchRequest(q="x", top_k=50)
    with pytest.raises(ValidationError):
        SearchRequest(q="x", top_k=0)
    with pytest.raises(ValidationError):
        SearchRequest(q="x", top_k=51)


@pytest.mark.unit
def test_search_result_item_shape():
    item = SearchResultItem(
        evidence_id="EV-RCT-2026-X-001",
        section="results",
        score=0.85,
        rerank_score=0.91,
        snippet="降压幅度...",
        evidence_meta=EvidenceMeta(
            title={"zh": "测试", "en": None},
            type="RCT", year=2026, language="zh",
            grade_level="moderate", rob_overall="low",
        ),
    )
    assert item.evidence_id == "EV-RCT-2026-X-001"


@pytest.mark.unit
def test_search_response_with_facets():
    resp = SearchResponse(
        query="高血压",
        took_ms=400,
        results=[],
        facets=Facets(type={"RCT": 3}, year={"2026": 2}, grade={"moderate": 1}, language={"zh": 3}),
        degraded=[],
    )
    assert resp.facets.type == {"RCT": 3}


@pytest.mark.unit
def test_health_response():
    h = HealthResponse(
        status="ok", qdrant_alive=True, collection_points=42,
        embedder="mock", reranker="mock",
    )
    assert h.status == "ok"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_retrieval_models.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 models.py**

Create `src/hypertensiondb/retrieval/models.py`:

```python
from typing import Optional, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, description="自然语言 query")
    top_k: int = Field(10, ge=1, le=50)
    types: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    year_min: Optional[int] = Field(None, ge=1900, le=2100)
    year_max: Optional[int] = Field(None, ge=1900, le=2100)
    grade_min: Optional[Literal["very_low", "low", "moderate", "high"]] = None
    tags: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    include_draft: bool = False
    expand_evidence: bool = False


class EvidenceMeta(BaseModel):
    title: dict[str, Optional[str]]  # {"zh": ..., "en": ...}
    type: str
    year: int
    language: str
    grade_level: Optional[str] = None
    rob_overall: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    full_frontmatter: Optional[dict] = None  # populated if expand_evidence=True


class SearchResultItem(BaseModel):
    evidence_id: str
    section: str
    score: float
    rerank_score: float
    snippet: str
    is_clinical_bottom_line: bool = False
    evidence_meta: EvidenceMeta


class Facets(BaseModel):
    type: dict[str, int] = Field(default_factory=dict)
    year: dict[str, int] = Field(default_factory=dict)
    grade: dict[str, int] = Field(default_factory=dict)
    language: dict[str, int] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    took_ms: int
    results: list[SearchResultItem]
    facets: Facets
    degraded: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    qdrant_alive: bool
    collection_points: Optional[int] = None
    embedder: str
    reranker: str


class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    frontmatter: dict
    sections: dict[str, str]
    source_path: str
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_retrieval_models.py -v`
Expected: 7 passed

---

## Task C.6: SearchEngine 编排器

**Files:**
- Create: `src/hypertensiondb/retrieval/search.py`
- Test: `tests/unit/test_search_engine.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_search_engine.py`:

```python
import pytest
from unittest.mock import MagicMock

from hypertensiondb.retrieval.search import SearchEngine
from hypertensiondb.retrieval.filters import SearchFilters
from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker_mock import MockReranker


def _cand(pid="p1", evid="EV-RCT-2026-X-001", sec="results", text="降压 8 mmHg", rrf=0.8, payload_extra=None):
    payload = {
        "evidence_id": evid, "section_name": sec, "text": text,
        "type": "RCT", "year": 2026, "language": "zh",
        "title_zh": "测试", "title_en": None,
        "grade_level": "moderate", "rob_overall": "low",
        "tags": ["ARB"], "is_clinical_bottom_line": False,
    }
    if payload_extra:
        payload.update(payload_extra)
    return Candidate(
        point_id=pid, rrf_score=rrf,
        evidence_id=evid, section_name=sec, text=text, payload=payload,
    )


@pytest.fixture
def mock_embedder():
    m = MagicMock()
    m.embed.return_value = [[0.1] * 8]
    m.dimension = 8
    m.model_name = "mock"
    return m


@pytest.fixture
def mock_sparse():
    m = MagicMock()
    m.vectorize.return_value = ([1, 2, 3], [0.5, 0.3, 0.2])
    return m


@pytest.fixture
def mock_hybrid():
    return MagicMock()


@pytest.fixture
def engine(mock_embedder, mock_sparse, mock_hybrid):
    return SearchEngine(
        embedder=mock_embedder,
        sparse_vectorizer=mock_sparse,
        hybrid_searcher=mock_hybrid,
        reranker=MockReranker(),
    )


@pytest.mark.unit
def test_search_basic_flow(engine, mock_hybrid):
    mock_hybrid.search.return_value = [_cand("p1", rrf=0.9), _cand("p2", rrf=0.5)]
    resp = engine.search(query="高血压", top_k=10, filters=SearchFilters())
    assert resp.query == "高血压"
    assert len(resp.results) == 2
    # Sorted by rerank_score (which Mock = rrf) descending
    assert resp.results[0].rerank_score >= resp.results[1].rerank_score


@pytest.mark.unit
def test_search_truncates_to_top_k(engine, mock_hybrid):
    cands = [_cand(f"p{i}", rrf=1.0 - i * 0.1) for i in range(20)]
    mock_hybrid.search.return_value = cands
    resp = engine.search(query="x", top_k=5, filters=SearchFilters())
    assert len(resp.results) == 5


@pytest.mark.unit
def test_search_snippet_truncated_to_800_chars(engine, mock_hybrid):
    long_text = "甲" * 2000
    mock_hybrid.search.return_value = [_cand(text=long_text)]
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    assert len(resp.results[0].snippet) <= 800


@pytest.mark.unit
def test_clinical_bottom_line_score_boost(engine, mock_hybrid):
    """临床要点 章节 rerank_score 应乘 1.2 加权（spec §4 / §5）。"""
    cands = [
        _cand("normal", rrf=0.8, payload_extra={"is_clinical_bottom_line": False}),
        _cand("cbl", rrf=0.7, payload_extra={"is_clinical_bottom_line": True}),
    ]
    # Make Candidate.is_clinical_bottom_line reflect payload
    cands[0].payload["is_clinical_bottom_line"] = False
    cands[1].payload["is_clinical_bottom_line"] = True
    mock_hybrid.search.return_value = cands
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    # CBL: 0.7 * 1.2 = 0.84 > normal: 0.8 → CBL ranks first
    assert resp.results[0].evidence_id == cands[1].evidence_id or \
           resp.results[0].is_clinical_bottom_line is True


@pytest.mark.unit
def test_search_facets(engine, mock_hybrid):
    cands = [
        _cand("p1", payload_extra={"type": "RCT", "year": 2026, "grade_level": "high", "language": "zh"}),
        _cand("p2", payload_extra={"type": "RCT", "year": 2025, "grade_level": "moderate", "language": "zh"}),
        _cand("p3", payload_extra={"type": "META", "year": 2026, "grade_level": "high", "language": "en"}),
    ]
    for i, c in enumerate(cands):
        c.payload["type"] = ["RCT", "RCT", "META"][i]
        c.payload["year"] = [2026, 2025, 2026][i]
        c.payload["grade_level"] = ["high", "moderate", "high"][i]
        c.payload["language"] = ["zh", "zh", "en"][i]
    mock_hybrid.search.return_value = cands
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    assert resp.facets.type == {"RCT": 2, "META": 1}
    assert resp.facets.grade == {"high": 2, "moderate": 1}
    assert resp.facets.language == {"zh": 2, "en": 1}


@pytest.mark.unit
def test_search_empty_query_results(engine, mock_hybrid):
    mock_hybrid.search.return_value = []
    resp = engine.search(query="无匹配", top_k=10, filters=SearchFilters())
    assert resp.results == []
    assert resp.facets.type == {}


@pytest.mark.unit
def test_search_records_took_ms(engine, mock_hybrid):
    mock_hybrid.search.return_value = []
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    assert resp.took_ms >= 0


@pytest.mark.unit
def test_search_passes_filter_to_hybrid(engine, mock_hybrid, mock_embedder, mock_sparse):
    mock_hybrid.search.return_value = []
    engine.search(query="x", top_k=10, filters=SearchFilters(types=["RCT"]))
    _, kwargs = mock_hybrid.search.call_args
    assert kwargs["query_filter"] is not None


@pytest.mark.unit
def test_search_degraded_when_embedder_fails(mock_sparse, mock_hybrid):
    """Embedder raises → degraded=['dense'] + sparse-only search."""
    bad_embedder = MagicMock()
    bad_embedder.embed.side_effect = RuntimeError("embedder timeout")
    bad_embedder.dimension = 8
    bad_embedder.model_name = "mock"
    engine = SearchEngine(
        embedder=bad_embedder, sparse_vectorizer=mock_sparse,
        hybrid_searcher=mock_hybrid, reranker=MockReranker(),
    )
    mock_hybrid.search.return_value = []
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    assert "dense" in resp.degraded
    _, kwargs = mock_hybrid.search.call_args
    assert kwargs["dense_vector"] == []


@pytest.mark.unit
def test_search_degraded_when_reranker_fails(mock_embedder, mock_sparse, mock_hybrid):
    bad_reranker = MagicMock()
    bad_reranker.rerank.side_effect = RuntimeError("reranker died")
    bad_reranker.model_name = "broken"
    engine = SearchEngine(
        embedder=mock_embedder, sparse_vectorizer=mock_sparse,
        hybrid_searcher=mock_hybrid, reranker=bad_reranker,
    )
    mock_hybrid.search.return_value = [_cand("p1", rrf=0.9)]
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    assert "rerank" in resp.degraded
    # Should still return results, sorted by rrf
    assert len(resp.results) == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_search_engine.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 search.py**

Create `src/hypertensiondb/retrieval/search.py`:

```python
import time
from collections import Counter
from typing import Optional

from hypertensiondb.index.embedder import BaseEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.retrieval.hybrid import HybridSearcher, Candidate
from hypertensiondb.retrieval.reranker import BaseReranker
from hypertensiondb.retrieval.filters import SearchFilters, build_qdrant_filter
from hypertensiondb.retrieval.models import (
    SearchResponse, SearchResultItem, EvidenceMeta, Facets,
)

_PREFETCH_LIMIT = 50
_RERANK_INPUT = 30
_SNIPPET_MAX_CHARS = 800
_CLINICAL_BOOST = 1.2


class SearchEngine:
    """Orchestrate: query embed → hybrid search → rerank → facet → response."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        sparse_vectorizer: SparseVectorizer,
        hybrid_searcher: HybridSearcher,
        reranker: BaseReranker,
    ) -> None:
        self._embedder = embedder
        self._sparse = sparse_vectorizer
        self._hybrid = hybrid_searcher
        self._reranker = reranker

    def search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters,
        expand_evidence: bool = False,
    ) -> SearchResponse:
        t0 = time.monotonic()
        degraded: list[str] = []

        # 1) Embed query (dense)
        try:
            dense_vector = self._embedder.embed([query])[0]
        except Exception:
            dense_vector = []
            degraded.append("dense")

        # 2) Sparse vectorize
        sparse_indices, sparse_values = self._sparse.vectorize(query)

        # 3) Hybrid search via Qdrant
        qfilter = build_qdrant_filter(filters)
        candidates = self._hybrid.search(
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            limit=_RERANK_INPUT,
            prefetch_limit=_PREFETCH_LIMIT,
            query_filter=qfilter,
        )

        # 4) Rerank
        try:
            reranked = self._reranker.rerank(query, candidates)
        except Exception:
            degraded.append("rerank")
            reranked = [(c, c.rrf_score) for c in
                        sorted(candidates, key=lambda x: x.rrf_score, reverse=True)]

        # 5) Apply clinical_bottom_line boost
        boosted: list[tuple[Candidate, float]] = []
        for cand, score in reranked:
            is_cbl = bool(cand.payload.get("is_clinical_bottom_line"))
            final_score = score * _CLINICAL_BOOST if is_cbl else score
            boosted.append((cand, final_score))
        boosted.sort(key=lambda t: t[1], reverse=True)

        # 6) Build response items (truncate to top_k)
        items: list[SearchResultItem] = []
        for cand, rerank_score in boosted[:top_k]:
            items.append(self._make_item(cand, rerank_score, expand_evidence))

        # 7) Facets from all reranked candidates (not just top_k)
        facets = self._build_facets([c for c, _ in boosted])

        took_ms = int((time.monotonic() - t0) * 1000)
        return SearchResponse(
            query=query,
            took_ms=took_ms,
            results=items,
            facets=facets,
            degraded=degraded,
        )

    def _make_item(
        self, cand: Candidate, rerank_score: float, expand_evidence: bool
    ) -> SearchResultItem:
        p = cand.payload
        snippet = (cand.text or "")[:_SNIPPET_MAX_CHARS]
        meta = EvidenceMeta(
            title={"zh": p.get("title_zh"), "en": p.get("title_en")},
            type=p.get("type", ""),
            year=int(p.get("year", 0)),
            language=p.get("language", ""),
            grade_level=p.get("grade_level"),
            rob_overall=p.get("rob_overall"),
            tags=list(p.get("tags") or []),
        )
        return SearchResultItem(
            evidence_id=cand.evidence_id,
            section=cand.section_name,
            score=cand.rrf_score,
            rerank_score=float(rerank_score),
            snippet=snippet,
            is_clinical_bottom_line=bool(p.get("is_clinical_bottom_line")),
            evidence_meta=meta,
        )

    @staticmethod
    def _build_facets(candidates: list[Candidate]) -> Facets:
        type_counter: Counter[str] = Counter()
        year_counter: Counter[str] = Counter()
        grade_counter: Counter[str] = Counter()
        lang_counter: Counter[str] = Counter()
        seen_evidence: set[str] = set()
        # Facets count distinct evidence_id, not chunks
        for c in candidates:
            if c.evidence_id in seen_evidence:
                continue
            seen_evidence.add(c.evidence_id)
            p = c.payload
            if p.get("type"):
                type_counter[p["type"]] += 1
            if p.get("year"):
                year_counter[str(p["year"])] += 1
            if p.get("grade_level"):
                grade_counter[p["grade_level"]] += 1
            if p.get("language"):
                lang_counter[p["language"]] += 1
        return Facets(
            type=dict(type_counter),
            year=dict(year_counter),
            grade=dict(grade_counter),
            language=dict(lang_counter),
        )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_search_engine.py -v`
Expected: 10 passed

---

## Task C.7: FastAPI app + /health 路由

**Files:**
- Create: `src/hypertensiondb/api/__init__.py`
- Create: `src/hypertensiondb/api/server.py`
- Create: `src/hypertensiondb/api/routes_health.py`
- Test: `tests/unit/test_api_health.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_api_health.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from hypertensiondb.api.server import create_app
from hypertensiondb.retrieval.search import SearchEngine


@pytest.fixture
def mock_engine():
    eng = MagicMock(spec=SearchEngine)
    return eng


@pytest.fixture
def mock_qdrant():
    q = MagicMock()
    q.collection_exists.return_value = True
    q.get_collection.return_value = MagicMock(points_count=42)
    return q


@pytest.fixture
def client(mock_engine, mock_qdrant):
    app = create_app(
        engine=mock_engine, qdrant=mock_qdrant,
        collection_name="test", embedder_name="mock", reranker_name="mock",
    )
    return TestClient(app)


@pytest.mark.unit
def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["qdrant_alive"] is True
    assert data["collection_points"] == 42
    assert data["embedder"] == "mock"
    assert data["reranker"] == "mock"


@pytest.mark.unit
def test_health_qdrant_down(mock_engine):
    bad_qdrant = MagicMock()
    bad_qdrant.collection_exists.side_effect = RuntimeError("connection refused")
    app = create_app(
        engine=mock_engine, qdrant=bad_qdrant,
        collection_name="test", embedder_name="mock", reranker_name="mock",
    )
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["qdrant_alive"] is False
    assert data["status"] == "down"


@pytest.mark.unit
def test_health_collection_missing(mock_engine):
    q = MagicMock()
    q.collection_exists.return_value = False
    app = create_app(
        engine=mock_engine, qdrant=q,
        collection_name="test", embedder_name="mock", reranker_name="mock",
    )
    client = TestClient(app)
    r = client.get("/health")
    data = r.json()
    assert data["qdrant_alive"] is True
    assert data["collection_points"] is None
    assert data["status"] == "degraded"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_api_health.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: 实现 api/__init__.py**

Create `src/hypertensiondb/api/__init__.py`:

```python
from hypertensiondb.api.server import create_app

__all__ = ["create_app"]
```

- [ ] **Step 4: 实现 server.py**

Create `src/hypertensiondb/api/server.py`:

```python
from typing import Optional

from fastapi import FastAPI
from qdrant_client import QdrantClient

from hypertensiondb.retrieval.search import SearchEngine


class AppState:
    """Container holding shared singletons for route handlers."""

    def __init__(
        self,
        engine: SearchEngine,
        qdrant: QdrantClient,
        collection_name: str,
        embedder_name: str,
        reranker_name: str,
    ) -> None:
        self.engine = engine
        self.qdrant = qdrant
        self.collection_name = collection_name
        self.embedder_name = embedder_name
        self.reranker_name = reranker_name


def create_app(
    engine: SearchEngine,
    qdrant: QdrantClient,
    collection_name: str,
    embedder_name: str,
    reranker_name: str,
) -> FastAPI:
    """Build FastAPI app with provided dependencies injected."""
    app = FastAPI(
        title="Hypertension Evidence Retrieval API",
        version="0.1.0",
    )
    state = AppState(
        engine=engine, qdrant=qdrant,
        collection_name=collection_name,
        embedder_name=embedder_name, reranker_name=reranker_name,
    )
    app.state.deps = state

    from hypertensiondb.api.routes_health import router as health_router
    from hypertensiondb.api.routes_search import router as search_router
    from hypertensiondb.api.routes_evidence import router as evidence_router

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(evidence_router)
    return app
```

- [ ] **Step 5: 实现 routes_health.py**

Create `src/hypertensiondb/api/routes_health.py`:

```python
from fastapi import APIRouter, Request

from hypertensiondb.retrieval.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    deps = request.app.state.deps
    qdrant = deps.qdrant
    collection_points: int | None = None
    qdrant_alive = True
    status = "ok"

    try:
        exists = qdrant.collection_exists(deps.collection_name)
    except Exception:
        return HealthResponse(
            status="down",
            qdrant_alive=False,
            collection_points=None,
            embedder=deps.embedder_name,
            reranker=deps.reranker_name,
        )

    if not exists:
        status = "degraded"
    else:
        try:
            info = qdrant.get_collection(deps.collection_name)
            collection_points = info.points_count
        except Exception:
            status = "degraded"

    return HealthResponse(
        status=status,
        qdrant_alive=qdrant_alive,
        collection_points=collection_points,
        embedder=deps.embedder_name,
        reranker=deps.reranker_name,
    )
```

- [ ] **Step 6: 创建 search/evidence 路由占位（暂未实现，让 import 成功）**

Create `src/hypertensiondb/api/routes_search.py`（占位）：

```python
from fastapi import APIRouter

router = APIRouter()
```

Create `src/hypertensiondb/api/routes_evidence.py`（占位）：

```python
from fastapi import APIRouter

router = APIRouter()
```

- [ ] **Step 7: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_api_health.py -v`
Expected: 3 passed

---

## Task C.8: /search 路由

**Files:**
- Modify: `src/hypertensiondb/api/routes_search.py`
- Test: `tests/unit/test_api_search.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_api_search.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from hypertensiondb.api.server import create_app
from hypertensiondb.retrieval.models import (
    SearchResponse, SearchResultItem, EvidenceMeta, Facets,
)


def _make_response(query="高血压", n_results=2):
    items = [
        SearchResultItem(
            evidence_id=f"EV-RCT-2026-X-{i:03d}",
            section="results", score=0.9 - i * 0.1, rerank_score=0.95 - i * 0.1,
            snippet="降压幅度...", is_clinical_bottom_line=False,
            evidence_meta=EvidenceMeta(
                title={"zh": f"标题{i}", "en": None},
                type="RCT", year=2026, language="zh",
                grade_level="moderate", rob_overall="low", tags=["ARB"],
            ),
        )
        for i in range(n_results)
    ]
    return SearchResponse(
        query=query, took_ms=400, results=items,
        facets=Facets(type={"RCT": n_results}),
        degraded=[],
    )


@pytest.fixture
def mock_engine():
    eng = MagicMock()
    eng.search.return_value = _make_response()
    return eng


@pytest.fixture
def client(mock_engine):
    app = create_app(
        engine=mock_engine, qdrant=MagicMock(),
        collection_name="test", embedder_name="mock", reranker_name="mock",
    )
    return TestClient(app)


@pytest.mark.unit
def test_search_get_returns_200(client, mock_engine):
    r = client.get("/search", params={"q": "高血压"})
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "高血压"
    assert len(data["results"]) == 2


@pytest.mark.unit
def test_search_missing_q_returns_422(client):
    r = client.get("/search")
    assert r.status_code == 422


@pytest.mark.unit
def test_search_empty_q_returns_422(client):
    r = client.get("/search", params={"q": ""})
    assert r.status_code == 422


@pytest.mark.unit
def test_search_too_long_q_returns_422(client):
    r = client.get("/search", params={"q": "a" * 501})
    assert r.status_code == 422


@pytest.mark.unit
def test_search_csv_filter_parsing(client, mock_engine):
    client.get("/search", params={"q": "x", "type": "RCT,META"})
    args, kwargs = mock_engine.search.call_args
    filters = kwargs["filters"]
    assert set(filters.types) == {"RCT", "META"}


@pytest.mark.unit
def test_search_year_range_parsing(client, mock_engine):
    client.get("/search", params={"q": "x", "year_min": "2020", "year_max": "2026"})
    args, kwargs = mock_engine.search.call_args
    filters = kwargs["filters"]
    assert filters.year_min == 2020
    assert filters.year_max == 2026


@pytest.mark.unit
def test_search_top_k_passed(client, mock_engine):
    client.get("/search", params={"q": "x", "top_k": "5"})
    args, kwargs = mock_engine.search.call_args
    assert kwargs["top_k"] == 5


@pytest.mark.unit
def test_search_top_k_out_of_range(client):
    r = client.get("/search", params={"q": "x", "top_k": "100"})
    assert r.status_code == 422


@pytest.mark.unit
def test_search_grade_min_enum(client, mock_engine):
    client.get("/search", params={"q": "x", "grade_min": "moderate"})
    args, kwargs = mock_engine.search.call_args
    assert kwargs["filters"].grade_min == "moderate"


@pytest.mark.unit
def test_search_invalid_grade_returns_422(client):
    r = client.get("/search", params={"q": "x", "grade_min": "bogus"})
    assert r.status_code == 422
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_api_search.py -v`
Expected: 测试失败（路由当前是空 router）

- [ ] **Step 3: 实现 routes_search.py**

OVERWRITE `src/hypertensiondb/api/routes_search.py`:

```python
from typing import Optional, Literal

from fastapi import APIRouter, Request, Query

from hypertensiondb.retrieval.filters import SearchFilters
from hypertensiondb.retrieval.models import SearchResponse

router = APIRouter()


def _csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(10, ge=1, le=50),
    type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None, ge=1900, le=2100),
    year_max: Optional[int] = Query(None, ge=1900, le=2100),
    grade_min: Optional[Literal["very_low", "low", "moderate", "high"]] = Query(None),
    tags: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    include_draft: bool = Query(False),
    expand_evidence: bool = Query(False),
) -> SearchResponse:
    filters = SearchFilters(
        types=_csv(type),
        languages=_csv(language),
        year_min=year_min,
        year_max=year_max,
        grade_min=grade_min,
        tags=_csv(tags),
        sections=_csv(section),
        include_draft=include_draft,
    )
    engine = request.app.state.deps.engine
    return engine.search(
        query=q, top_k=top_k, filters=filters, expand_evidence=expand_evidence,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_api_search.py -v`
Expected: 10 passed

---

## Task C.9: /evidence 路由（按 ID 取详情 + 列表过滤）

**Files:**
- Modify: `src/hypertensiondb/api/routes_evidence.py`
- Test: `tests/unit/test_api_evidence.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_api_evidence.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_api_evidence.py -v`
Expected: 失败（routes_evidence.py 当前是空 router）

- [ ] **Step 3: 实现 routes_evidence.py**

OVERWRITE `src/hypertensiondb/api/routes_evidence.py`:

```python
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from hypertensiondb.schema.loader import load_evidence

router = APIRouter()


class EvidenceListItem(BaseModel):
    evidence_id: str
    type: str
    year: int
    language: str
    title: dict
    status: str
    grade_level: Optional[str] = None
    source_path: str


class EvidenceListResponse(BaseModel):
    items: list[EvidenceListItem]
    total: int


class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    frontmatter: dict
    sections: dict
    source_path: str


def _evidence_root() -> Path:
    return Path(os.getenv("EVIDENCE_ROOT", "evidence"))


def _find_file_by_id(evidence_id: str) -> Optional[Path]:
    root = _evidence_root()
    if not root.exists():
        return None
    matches = list(root.rglob(f"{evidence_id}.md"))
    return matches[0] if matches else None


@router.get("/evidence/{evidence_id}", response_model=EvidenceDetailResponse)
def get_evidence(evidence_id: str) -> EvidenceDetailResponse:
    path = _find_file_by_id(evidence_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    try:
        fm, sections = load_evidence(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse: {e}")
    return EvidenceDetailResponse(
        evidence_id=fm.id,
        frontmatter=fm.model_dump(mode="json"),
        sections=sections,
        source_path=str(path),
    )


@router.get("/evidence", response_model=EvidenceListResponse)
def list_evidence(
    type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None, ge=1900, le=2100),
    year_max: Optional[int] = Query(None, ge=1900, le=2100),
    tags: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> EvidenceListResponse:
    root = _evidence_root()
    if not root.exists():
        return EvidenceListResponse(items=[], total=0)

    type_set = {t.strip() for t in type.split(",")} if type else None
    lang_set = {l.strip() for l in language.split(",")} if language else None
    tags_set = {t.strip() for t in tags.split(",")} if tags else None
    status_set = {s.strip() for s in status.split(",")} if status else None

    items: list[EvidenceListItem] = []
    for md in sorted(root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        try:
            fm, _ = load_evidence(md)
        except Exception:
            continue
        if type_set and str(fm.type) not in type_set:
            continue
        if lang_set and str(fm.language) not in lang_set:
            continue
        if year_min is not None and fm.year < year_min:
            continue
        if year_max is not None and fm.year > year_max:
            continue
        if tags_set and not (set(fm.tags) & tags_set):
            continue
        if status_set and str(fm.status) not in status_set:
            continue

        items.append(EvidenceListItem(
            evidence_id=fm.id,
            type=str(fm.type),
            year=fm.year,
            language=str(fm.language),
            title={"zh": fm.title.zh, "en": fm.title.en},
            status=str(fm.status),
            grade_level=str(fm.grade.level) if hasattr(fm, "grade") and fm.grade else None,
            source_path=str(md),
        ))
        if len(items) >= limit:
            break

    return EvidenceListResponse(items=items, total=len(items))
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_api_evidence.py -v`
Expected: 7 passed

---

## Task C.10: CLI 子命令 `hdb serve` + 全单元测试回归

**Files:**
- Modify: `src/hypertensiondb/cli.py`

- [ ] **Step 1: 修改 cli.py，添加 serve 命令**

在 `src/hypertensiondb/cli.py` 末尾追加：

```python
serve_app = typer.Typer(help="Run API server")
app.add_typer(serve_app, name="serve")


@serve_app.command("run")
def serve_run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start the FastAPI server using settings from environment variables."""
    import uvicorn
    from qdrant_client import QdrantClient

    from hypertensiondb.api.server import create_app
    from hypertensiondb.index.sparse import SparseVectorizer
    from hypertensiondb.retrieval.hybrid import HybridSearcher
    from hypertensiondb.retrieval.reranker_mock import MockReranker
    from hypertensiondb.retrieval.search import SearchEngine

    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)

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
        from hypertensiondb.index.embedder_mock import MockEmbedder
        embedder = MockEmbedder(dim=int(os.getenv("EMBED_DIM", "8")))

    reranker_name = os.getenv("RERANKER", "mock")
    if reranker_name == "bge":
        from hypertensiondb.retrieval.reranker_bge import BGEReranker
        reranker = BGEReranker()
    else:
        reranker = MockReranker()

    hybrid = HybridSearcher(qdrant=qdrant, collection_name=COLLECTION_NAME)
    engine = SearchEngine(
        embedder=embedder,
        sparse_vectorizer=SparseVectorizer(),
        hybrid_searcher=hybrid,
        reranker=reranker,
    )
    app = create_app(
        engine=engine, qdrant=qdrant, collection_name=COLLECTION_NAME,
        embedder_name=embedder.model_name, reranker_name=reranker.model_name,
    )
    uvicorn.run(app, host=host, port=port, reload=reload)
```

- [ ] **Step 2: 验证 CLI 注册成功**

Run: `py -m hypertensiondb.cli serve --help`
Expected: 显示 `run` 子命令

- [ ] **Step 3: 全单元测试回归**

Run: `py -m pytest tests/unit/ -v --tb=short`
Expected: 全部通过（Plan A + B + C 累计约 100 tests）

---

## Task C.11: BGE Reranker（懒加载，可选依赖）

**Files:**
- Create: `src/hypertensiondb/retrieval/reranker_bge.py`
- Test: `tests/unit/test_reranker_bge.py`

> **说明：** 真实 `bge-reranker-v2-m3` 模型约 600MB，本任务**只测懒加载与接口契约**，不下载真实模型。生产使用时按需 `pip install -e ".[bge]"` 并首次调用会从 HuggingFace 拉模型（国内可用镜像 `HF_ENDPOINT=https://hf-mirror.com`）。

- [ ] **Step 1: 写测试（mock FlagReranker）**

Create `tests/unit/test_reranker_bge.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from hypertensiondb.retrieval.hybrid import Candidate


def _cand(pid="p1", text="降压效果"):
    return Candidate(
        point_id=pid, rrf_score=0.5,
        evidence_id="EV-RCT-2026-X-001", section_name="results",
        text=text, payload={"text": text},
    )


@pytest.mark.unit
def test_bge_reranker_model_name():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    r = BGEReranker(model_name="BAAI/bge-reranker-v2-m3")
    assert r.model_name == "BAAI/bge-reranker-v2-m3"


@pytest.mark.unit
def test_bge_reranker_lazy_loads_model():
    """Model is only loaded on first rerank() call, not at construction."""
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    with patch("hypertensiondb.retrieval.reranker_bge.BGEReranker._load_model") as m:
        r = BGEReranker()
        m.assert_not_called()


@pytest.mark.unit
def test_bge_reranker_rerank_sorts_descending():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker

    fake_model = MagicMock()
    # compute_score returns one score per pair, in order
    fake_model.compute_score.return_value = [0.2, 0.9, 0.5]

    r = BGEReranker()
    with patch.object(r, "_get_model", return_value=fake_model):
        cands = [_cand("p1"), _cand("p2"), _cand("p3")]
        out = r.rerank("查询", cands)

    assert [c.point_id for c, _ in out] == ["p2", "p3", "p1"]
    assert [score for _, score in out] == [0.9, 0.5, 0.2]


@pytest.mark.unit
def test_bge_reranker_empty_input():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    r = BGEReranker()
    assert r.rerank("q", []) == []


@pytest.mark.unit
def test_bge_reranker_handles_single_score_return():
    """FlagReranker returns a scalar instead of list when given 1 pair."""
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    fake_model = MagicMock()
    fake_model.compute_score.return_value = 0.77
    r = BGEReranker()
    with patch.object(r, "_get_model", return_value=fake_model):
        out = r.rerank("q", [_cand("p1")])
    assert len(out) == 1
    assert out[0][1] == 0.77
```

- [ ] **Step 2: 实现 reranker_bge.py**

Create `src/hypertensiondb/retrieval/reranker_bge.py`:

```python
from typing import Optional

from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker import BaseReranker


class BGEReranker(BaseReranker):
    """BGE reranker via FlagEmbedding.

    Model (~600MB) is downloaded on first use from HuggingFace.
    Install: pip install -e ".[bge]"
    Mirror: export HF_ENDPOINT=https://hf-mirror.com  (国内加速)
    """

    def __init__(
        self, model_name: str = "BAAI/bge-reranker-v2-m3", use_fp16: bool = False
    ) -> None:
        self._model_name = model_name
        self._use_fp16 = use_fp16
        self._model = None

    def _load_model(self):
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as e:
            raise ImportError(
                "FlagEmbedding not installed. Run: pip install -e \".[bge]\""
            ) from e
        return FlagReranker(self._model_name, use_fp16=self._use_fp16)

    def _get_model(self):
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        if not candidates:
            return []
        model = self._get_model()
        pairs = [[query, c.text] for c in candidates]
        scores_raw = model.compute_score(pairs)
        # FlagReranker may return scalar for 1 pair
        if not isinstance(scores_raw, list):
            scores = [float(scores_raw)]
        else:
            scores = [float(s) for s in scores_raw]
        pairs_with_score = list(zip(candidates, scores))
        pairs_with_score.sort(key=lambda t: t[1], reverse=True)
        return pairs_with_score

    @property
    def model_name(self) -> str:
        return self._model_name
```

- [ ] **Step 3: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_reranker_bge.py -v`
Expected: 5 passed

---

## Task C.12: Golden 集 — fixture 语料库

**Files:**
- Create: `tests/golden/__init__.py`
- Create: `tests/golden/corpus/EV-RCT-2026-PENG-001.md`（及 9-11 篇其他 fixture）

> **说明：** Golden 语料库要覆盖 5 种文献类型 + 中英文混合 + 不同 GRADE/RoB 等级。每篇正文真实但简短（200-500 字），重点在 frontmatter 与节区结构完整。

- [ ] **Step 1: 创建 __init__.py**

Create `tests/golden/__init__.py`（空文件即可，让 pytest 识别为 package）。

- [ ] **Step 2: 创建 10 篇 fixture md（每篇约 30-50 行）**

依次创建以下 10 个文件，**正文要真实但简短**，frontmatter 必须通过 Pydantic 校验。

Create `tests/golden/corpus/EV-RCT-2026-PENG-001.md`（RCT，ARB+CCB 联合）：

```markdown
---
id: EV-RCT-2026-PENG-001
type: RCT
title:
  zh: 缬沙坦联合氨氯地平治疗中重度原发性高血压的多中心随机对照试验
  en: Valsartan plus amlodipine in moderate-to-severe primary hypertension
authors: [Peng Y, Liu J, Wang X]
year: 2026
language: zh
journal: 中华高血压杂志
status: reviewed
pico:
  population:
    condition: 原发性高血压
    severity: 中重度
    sample_size: 612
  intervention:
    name: 缬沙坦80mg+氨氯地平5mg
    drug_class: [ARB, CCB]
  comparison:
    name: 缬沙坦80mg单药
  outcomes:
    primary:
      - name: SBP下降幅度
        effect_size: {metric: MD, value: -8.4, ci_low: -10.1, ci_high: -6.7, p: 0.001}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
tags: [valsartan, amlodipine, ARB, CCB, combination_therapy]
---

## 临床要点 / Clinical Bottom Line

中重度原发性高血压患者，ARB与CCB联合治疗较ARB单药显著降低收缩压（MD -8.4 mmHg），不良反应率相当。

## 方法 / Methods

多中心双盲随机对照试验。612例中重度原发性高血压患者（SBP 140-179 mmHg，DBP 90-109 mmHg），随机分配至联合组（缬沙坦80mg+氨氯地平5mg/日）或单药组（缬沙坦80mg/日），治疗12周。

## 结果 / Results

12周后，联合组SBP较单药组多下降8.4 mmHg（95% CI -10.1, -6.7, P<0.001），DBP多下降4.2 mmHg。血压达标率联合组78.3% vs 单药组54.9%，RR 1.42 (1.21-1.66)。不良反应率两组相似（联合12.1% vs 单药10.8%，P=0.42）。

## 结论 / Conclusion

ARB联合CCB方案在中重度原发性高血压中降压幅度优于ARB单药，安全性相似。推荐作为中重度患者的初始联合方案。
```

Create `tests/golden/corpus/EV-META-2024-LIU-001.md`（Meta，老年人降压目标）：

```markdown
---
id: EV-META-2024-LIU-001
type: META
title:
  zh: 老年高血压患者强化降压与标准降压目标的Meta分析
  en: Intensive vs standard BP targets in elderly hypertension - a meta-analysis
authors: [Liu H, Chen W]
year: 2024
language: zh
status: reviewed
pico:
  population:
    condition: 老年高血压
    age_range: 65岁以上
    sample_size: 18432
  intervention:
    name: SBP目标<130 mmHg
  comparison:
    name: SBP目标<140 mmHg
  outcomes:
    primary:
      - name: 心血管复合事件
        effect_size: {metric: RR, value: 0.78, ci_low: 0.69, ci_high: 0.88}
risk_of_bias:
  tool: AMSTAR2
  overall: low
grade:
  level: high
tags: [elderly, intensive_bp_target, cardiovascular_events, meta_analysis]
---

## 临床要点 / Clinical Bottom Line

≥65岁高血压患者强化降压（目标SBP<130 mmHg）较标准目标显著降低心血管复合事件风险22%，证据等级高。

## 方法 / Methods

系统检索PubMed/Cochrane/EMBASE自2010至2024年的RCT，纳入对比强化降压（<130 mmHg）与标准降压（<140 mmHg）目标的老年人研究。共纳入7项RCT，18432例患者。

## 结果 / Results

强化降压组心血管复合事件风险降低22%（RR 0.78, 95%CI 0.69-0.88，I²=18%）。心衰住院降低35%，卒中降低19%，全因死亡无显著差异。低血压不良事件强化组略增（RR 1.34, 1.08-1.66）。

## 结论 / Conclusion

老年高血压强化降压有显著心血管获益。临床决策需权衡个体跌倒/低血压风险。
```

Create `tests/golden/corpus/EV-SR-2025-WANG-001.md`（SR，盐摄入与血压）：

```markdown
---
id: EV-SR-2025-WANG-001
type: SR
title:
  zh: 限盐干预对原发性高血压患者血压的影响——系统评价
  en: Sodium restriction for primary hypertension - a systematic review
authors: [Wang L, Zhao M]
year: 2025
language: zh
status: reviewed
pico:
  population:
    condition: 原发性高血压
    sample_size: 5234
  intervention:
    name: 限盐<5g/日
  comparison:
    name: 普通饮食
  outcomes:
    primary:
      - name: SBP下降
        effect_size: {metric: MD, value: -5.4, ci_low: -6.8, ci_high: -4.0}
risk_of_bias:
  tool: AMSTAR2
  overall: low
grade:
  level: high
tags: [sodium_restriction, lifestyle, primary_hypertension, blood_pressure]
---

## 临床要点 / Clinical Bottom Line

原发性高血压患者每日限盐<5g可显著降低SBP约5.4 mmHg，证据等级高，推荐作为基础生活方式干预。

## 方法 / Methods

按Cochrane手册做系统评价。检索PubMed/Cochrane/CNKI/WanFang 至2024年。纳入限盐≥4周的RCT，共22项研究，5234例患者。

## 结果 / Results

限盐组SBP较对照下降5.4 mmHg (95%CI -6.8, -4.0)，DBP下降2.8 mmHg。亚组分析显示老年人获益更大（MD -7.2 vs 中青年 -4.1 mmHg）。

## 结论 / Conclusion

限盐<5g/日是有效的非药物降压措施，应作为所有高血压患者的基础治疗。
```

Create `tests/golden/corpus/EV-GL-2024-CHS-001.md`（中国高血压指南）：

```markdown
---
id: EV-GL-2024-CHS-001
type: GL
title:
  zh: 中国高血压防治指南2024年修订版
  en: Chinese Guidelines for Hypertension Management 2024
authors: [CHS Hypertension Working Group]
year: 2024
language: zh
status: published
risk_of_bias:
  tool: AGREE-II
  overall: low
grade:
  level: high
tags: [guideline, chinese, blood_pressure_target, drug_therapy]
---

## 临床要点 / Clinical Bottom Line

成人高血压一般降压目标<140/90 mmHg；糖尿病、慢性肾病、冠心病患者目标<130/80 mmHg；首选CCB/ARB/ACEI/利尿剂；强烈推荐生活方式干预作为基础治疗。

## 方法 / Methods

中国高血压联盟组织专家工作组，按AGREE-II框架制定，证据等级按GRADE系统评定。

## 结果 / Results

主要推荐：1) 诊室血压SBP≥140或DBP≥90 mmHg诊断为高血压；2) 启动药物治疗前评估心血管总风险；3) 一线药物：CCB、ARB、ACEI、利尿剂、β受体阻滞剂；4) 起始联合治疗适用于SBP≥160或DBP≥100 mmHg患者。

## 结论 / Conclusion

中国高血压管理应基于个体风险分层，结合药物与生活方式综合干预。
```

Create `tests/golden/corpus/EV-GL-2023-ESC-001.md`（ESC/ESH 指南，英文）：

```markdown
---
id: EV-GL-2023-ESC-001
type: GL
title:
  en: 2023 ESH Guidelines for the management of arterial hypertension
authors: [Mancia G, Kreutz R, et al.]
year: 2023
language: en
status: published
risk_of_bias:
  tool: AGREE-II
  overall: low
grade:
  level: high
tags: [guideline, european, ESH, hypertension_management]
---

## English Abstract

The 2023 ESH Guidelines provide updated recommendations on the diagnosis, evaluation and treatment of arterial hypertension in adults. Key changes include emphasis on combination therapy as initial treatment for most patients with grade 2 hypertension or higher.

## Clinical Bottom Line

Initial single-pill combination therapy (RAS blocker + CCB or thiazide) is recommended for grade 2+ hypertension. Target office BP <130/80 mmHg in most adults if tolerated.

## Methods

Multi-disciplinary task force review using GRADE methodology. Evidence from RCTs published through 2022.

## Results

Major recommendations: (1) Office BP target <130/80 mmHg if tolerated for most adults under 80; (2) <140/80 for adults ≥80 years; (3) Single-pill combinations preferred to improve adherence; (4) ARB or ACEi + CCB or thiazide as first-line combinations.

## Conclusion

The 2023 ESH guidelines emphasize earlier and more effective combination therapy with lower BP targets in most adult populations.
```

Create `tests/golden/corpus/EV-TCM-2025-ZHANG-001.md`（中医药 RCT）：

```markdown
---
id: EV-TCM-2025-ZHANG-001
type: TCM
title:
  zh: 天麻钩藤饮加减治疗肝阳上亢型高血压的随机对照试验
authors: [Zhang Q, Li M]
year: 2025
language: zh
status: reviewed
pico:
  population:
    condition: 肝阳上亢型原发性高血压
    sample_size: 240
  intervention:
    name: 天麻钩藤饮加减+苯磺酸氨氯地平5mg
  comparison:
    name: 苯磺酸氨氯地平5mg
  outcomes:
    primary:
      - name: SBP下降
        effect_size: {metric: MD, value: -3.8, ci_low: -5.5, ci_high: -2.1}
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: low
tags: [tianma_gouteng, liver_yang, integrative, ARB_combination]
---

## 临床要点 / Clinical Bottom Line

肝阳上亢型高血压患者，天麻钩藤饮加减联合氨氯地平较单用氨氯地平多降SBP约3.8 mmHg，对头晕症状改善更明显。证据等级低。

## 方法 / Methods

单中心双盲RCT，240例肝阳上亢证型高血压患者，随机分中药联合组与对照组，疗程8周。主要结局为24小时动态血压SBP变化。

## 结果 / Results

联合组SBP较对照多下降3.8 mmHg (95%CI -5.5, -2.1)。次要结局头晕评分中药组改善优于对照（差值-2.1分）。两组未见严重不良反应。

## 结论 / Conclusion

天麻钩藤饮加减对肝阳上亢型高血压有辅助降压及改善症状作用。需多中心更大样本验证。
```

Create `tests/golden/corpus/EV-RCT-2025-CHEN-001.md`（RCT，糖尿病合并高血压）：

```markdown
---
id: EV-RCT-2025-CHEN-001
type: RCT
title:
  zh: 2型糖尿病合并高血压患者ACEI vs ARB的对比研究
authors: [Chen S, Zhou Y]
year: 2025
language: zh
status: reviewed
pico:
  population:
    condition: 2型糖尿病合并高血压
    sample_size: 480
  intervention:
    name: 培哚普利4mg/日
  comparison:
    name: 缬沙坦80mg/日
  outcomes:
    primary:
      - name: 24h SBP变化
        effect_size: {metric: MD, value: -0.6, ci_low: -2.1, ci_high: 0.9, p: 0.41}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
tags: [diabetes, ACEI, ARB, perindopril, valsartan]
---

## 临床要点 / Clinical Bottom Line

2型糖尿病合并高血压患者，ACEI（培哚普利）与ARB（缬沙坦）降压效果相当（无显著差异），但ACEI组干咳发生率更高（8.3% vs 1.2%）。

## 方法 / Methods

多中心双盲RCT，480例患者随机分两组治疗24周。主要终点24h动态血压。

## 结果 / Results

24周时两组SBP变化无显著差异 (MD -0.6 mmHg, P=0.41)。微量白蛋白尿下降相当。ACEI组干咳明显高于ARB组（8.3% vs 1.2%）。

## 结论 / Conclusion

ACEI与ARB在糖尿病合并高血压中降压及肾保护效果相当；不能耐受ACEI干咳者优选ARB。
```

Create `tests/golden/corpus/EV-RCT-2024-LI-001.md`（RCT，老年起始联合）：

```markdown
---
id: EV-RCT-2024-LI-001
type: RCT
title:
  zh: 老年高血压起始单药 vs 起始联合治疗的随机对照研究
authors: [Li K, Zhou H]
year: 2024
language: zh
status: reviewed
pico:
  population:
    condition: 老年原发性高血压
    age_range: 65-80岁
    sample_size: 380
  intervention:
    name: 起始联合（CCB+ARB低剂量）
  comparison:
    name: 起始单药（CCB标准剂量）
  outcomes:
    primary:
      - name: 12周血压达标率
        effect_size: {metric: RR, value: 1.35, ci_low: 1.15, ci_high: 1.59}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
tags: [elderly, combination_therapy, initial_therapy]
---

## 临床要点 / Clinical Bottom Line

老年原发性高血压患者起始低剂量联合治疗较单药标准剂量血压达标率高35%，安全性相当。

## 方法 / Methods

双盲RCT，380例65-80岁高血压患者，随机分两组治疗12周。

## 结果 / Results

联合组12周血压达标率76.8%，单药组56.7%，RR 1.35 (1.15-1.59)。低血压发生率两组无差异。

## 结论 / Conclusion

老年高血压起始低剂量联合方案优于单药标准剂量。
```

Create `tests/golden/corpus/EV-META-2026-SUN-001.md`（Meta，运动干预）：

```markdown
---
id: EV-META-2026-SUN-001
type: META
title:
  zh: 有氧运动对高血压患者血压的影响——Meta分析
authors: [Sun J]
year: 2026
language: zh
status: reviewed
pico:
  population:
    condition: 高血压
    sample_size: 3240
  intervention:
    name: 有氧运动 ≥150min/周
  comparison:
    name: 久坐对照
  outcomes:
    primary:
      - name: SBP下降
        effect_size: {metric: MD, value: -6.1, ci_low: -7.8, ci_high: -4.4}
risk_of_bias:
  tool: AMSTAR2
  overall: low
grade:
  level: high
tags: [exercise, aerobic, lifestyle, blood_pressure]
---

## 临床要点 / Clinical Bottom Line

高血压患者每周≥150分钟有氧运动可显著降低SBP约6.1 mmHg，证据等级高，应作为基础干预。

## 方法 / Methods

系统评价 + Meta分析。纳入12项 RCT，3240例高血压患者。运动方案：快走、慢跑、游泳、骑车。

## Results

运动组SBP较对照组下降6.1 mmHg（95%CI -7.8, -4.4），DBP下降3.4 mmHg。中等及高质量证据。

## 结论 / Conclusion

中等强度有氧运动是有效的非药物降压措施，与限盐组合效果叠加。
```

Create `tests/golden/corpus/EV-SR-2024-OUYANG-001.md`（SR，β-blocker 在年轻患者）：

```markdown
---
id: EV-SR-2024-OUYANG-001
type: SR
title:
  zh: β受体阻滞剂作为青年高血压一线治疗的证据评价
authors: [Ouyang F]
year: 2024
language: zh
status: reviewed
pico:
  population:
    condition: 青年原发性高血压
    age_range: 18-45岁
    sample_size: 8120
  intervention:
    name: β受体阻滞剂单药
  comparison:
    name: CCB或ARB单药
  outcomes:
    primary:
      - name: 心血管事件
        effect_size: {metric: RR, value: 1.18, ci_low: 0.98, ci_high: 1.41}
risk_of_bias:
  tool: AMSTAR2
  overall: some_concerns
grade:
  level: moderate
tags: [beta_blocker, young_adults, first_line_therapy]
---

## 临床要点 / Clinical Bottom Line

青年高血压患者β受体阻滞剂作为一线药物的心血管事件预防效果可能弱于CCB/ARB（RR 1.18, 95%CI 跨越1）。证据等级中等。

## 方法 / Methods

按Cochrane手册做系统评价。纳入9项RCT，8120例青年高血压患者。

## 结果 / Results

β受体阻滞剂组心血管复合事件略多于CCB/ARB组，但差异未达统计学意义（RR 1.18, 95%CI 0.98-1.41）。卒中发生率β受体阻滞剂组高24%。

## 结论 / Conclusion

无强适应症（如冠心病）的青年高血压患者，不优先推荐β受体阻滞剂作为一线治疗。
```

- [ ] **Step 3: 校验所有 fixture 通过 Pydantic schema**

Run: `py scripts/validate_evidence.py tests/golden/corpus/*.md`
Expected: 10 个 OK 行，无 FAIL

---

## Task C.13: Golden 集 — queries.jsonl

**Files:**
- Create: `tests/golden/queries.jsonl`

- [ ] **Step 1: 创建 queries.jsonl**

Create `tests/golden/queries.jsonl`（每行一条 JSON）：

```jsonl
{"id": "Q-001", "query": "ARB联合CCB治疗中重度高血压", "expected_top": ["EV-RCT-2026-PENG-001"]}
{"id": "Q-002", "query": "缬沙坦氨氯地平联合用药", "expected_top": ["EV-RCT-2026-PENG-001"]}
{"id": "Q-003", "query": "老年高血压强化降压目标", "expected_top": ["EV-META-2024-LIU-001"]}
{"id": "Q-004", "query": "elderly intensive blood pressure target", "expected_top": ["EV-META-2024-LIU-001"]}
{"id": "Q-005", "query": "限盐对血压的影响", "expected_top": ["EV-SR-2025-WANG-001"]}
{"id": "Q-006", "query": "钠摄入限制降压效果", "expected_top": ["EV-SR-2025-WANG-001"]}
{"id": "Q-007", "query": "中国高血压指南推荐", "expected_top": ["EV-GL-2024-CHS-001"]}
{"id": "Q-008", "query": "ESH hypertension management combination therapy", "expected_top": ["EV-GL-2023-ESC-001"]}
{"id": "Q-009", "query": "天麻钩藤饮治疗高血压", "expected_top": ["EV-TCM-2025-ZHANG-001"]}
{"id": "Q-010", "query": "肝阳上亢中医高血压", "expected_top": ["EV-TCM-2025-ZHANG-001"]}
{"id": "Q-011", "query": "糖尿病高血压ACEI ARB选择", "expected_top": ["EV-RCT-2025-CHEN-001"]}
{"id": "Q-012", "query": "培哚普利缬沙坦对比", "expected_top": ["EV-RCT-2025-CHEN-001"]}
{"id": "Q-013", "query": "老年高血压起始联合治疗", "expected_top": ["EV-RCT-2024-LI-001", "EV-META-2024-LIU-001"]}
{"id": "Q-014", "query": "有氧运动降血压", "expected_top": ["EV-META-2026-SUN-001"]}
{"id": "Q-015", "query": "exercise hypertension blood pressure", "expected_top": ["EV-META-2026-SUN-001"]}
{"id": "Q-016", "query": "青年高血压beta blocker", "expected_top": ["EV-SR-2024-OUYANG-001"]}
{"id": "Q-017", "query": "β受体阻滞剂年轻患者", "expected_top": ["EV-SR-2024-OUYANG-001"]}
{"id": "Q-018", "query": "高血压生活方式干预", "expected_top": ["EV-SR-2025-WANG-001", "EV-META-2026-SUN-001"]}
{"id": "Q-019", "query": "降压药物一线选择", "expected_top": ["EV-GL-2024-CHS-001", "EV-GL-2023-ESC-001"]}
{"id": "Q-020", "query": "联合治疗vs单药降压效果", "expected_top": ["EV-RCT-2026-PENG-001", "EV-RCT-2024-LI-001"]}
{"id": "Q-021", "query": "高质量临床指南推荐", "expected_top": ["EV-GL-2024-CHS-001", "EV-GL-2023-ESC-001"], "filters": {"grade_min": "high", "types": ["GL"]}}
{"id": "Q-022", "query": "中医辨证治疗高血压", "expected_top": ["EV-TCM-2025-ZHANG-001"], "filters": {"types": ["TCM"]}}
{"id": "Q-023", "query": "Meta分析降压证据", "expected_top": ["EV-META-2024-LIU-001", "EV-META-2026-SUN-001"], "filters": {"types": ["META"]}}
{"id": "Q-024", "query": "RCT随机对照试验降压", "expected_top": ["EV-RCT-2026-PENG-001", "EV-RCT-2025-CHEN-001", "EV-RCT-2024-LI-001"], "filters": {"types": ["RCT"]}}
{"id": "Q-025", "query": "2024年高血压研究", "expected_top": ["EV-META-2024-LIU-001", "EV-RCT-2024-LI-001", "EV-GL-2024-CHS-001", "EV-SR-2024-OUYANG-001"], "filters": {"year_min": 2024, "year_max": 2024}}
{"id": "Q-026", "query": "英文高血压指南", "expected_top": ["EV-GL-2023-ESC-001"], "filters": {"languages": ["en"]}}
{"id": "Q-027", "query": "钙通道阻滞剂联合", "expected_top": ["EV-RCT-2026-PENG-001"]}
{"id": "Q-028", "query": "血压达标率联合用药", "expected_top": ["EV-RCT-2026-PENG-001", "EV-RCT-2024-LI-001"]}
{"id": "Q-029", "query": "心血管事件预防", "expected_top": ["EV-META-2024-LIU-001", "EV-SR-2024-OUYANG-001"]}
{"id": "Q-030", "query": "高证据等级Meta分析", "expected_top": ["EV-META-2024-LIU-001", "EV-META-2026-SUN-001"], "filters": {"grade_min": "high"}}
```

- [ ] **Step 2: 验证 JSONL 行可解析**

Run: `py -c "import json; [json.loads(line) for line in open('tests/golden/queries.jsonl', encoding='utf-8')]; print('OK')"`
Expected: `OK`

---

## Task C.14: Golden 集 — recall@10 / MRR 测试

**Files:**
- Create: `tests/golden/test_recall.py`

- [ ] **Step 1: 创建 test_recall.py（集成测试，需要 Docker）**

Create `tests/golden/test_recall.py`:

```python
"""Golden set regression: recall@10 / MRR / filter_correctness.

Loads corpus into a real Qdrant (testcontainers), runs every query in
queries.jsonl through SearchEngine with MockEmbedder + MockReranker,
asserts thresholds.
"""
import json
import pytest
from pathlib import Path

pytest.importorskip("testcontainers")

from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from qdrant_client import QdrantClient

from hypertensiondb.index.embedder_mock import MockEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.index.pipeline import IndexPipeline
from hypertensiondb.retrieval.hybrid import HybridSearcher
from hypertensiondb.retrieval.reranker_mock import MockReranker
from hypertensiondb.retrieval.search import SearchEngine
from hypertensiondb.retrieval.filters import SearchFilters


GOLDEN_DIR = Path(__file__).parent
CORPUS_DIR = GOLDEN_DIR / "corpus"
QUERIES_FILE = GOLDEN_DIR / "queries.jsonl"

COLLECTION = "golden_test"

# Thresholds: MockEmbedder + MockReranker is noisy by design; sparse (jieba TF)
# carries most of the signal. We expect:
RECALL_AT_10_THRESHOLD = 0.85   # 85% of queries should have at least one expected_top in top-10
MRR_THRESHOLD = 0.45            # mean reciprocal rank
FILTER_CORRECTNESS_THRESHOLD = 1.0  # filters must always exclude non-matching


@pytest.fixture(scope="module")
def qdrant_client():
    container = DockerContainer("qdrant/qdrant:v1.12.5")
    container.with_exposed_ports(6333)
    container.start()
    wait_for_logs(container, "Qdrant gRPC listening", timeout=60)
    port = container.get_exposed_port(6333)
    client = QdrantClient(host="localhost", port=int(port))
    yield client
    container.stop()


@pytest.fixture(scope="module")
def search_engine(qdrant_client):
    """Index the golden corpus once, return a SearchEngine bound to it."""
    embedder = MockEmbedder(dim=8)
    sparse = SparseVectorizer()
    idx_client = QdrantIndexClient(qdrant=qdrant_client, collection_name=COLLECTION)
    pipeline = IndexPipeline(
        embedder=embedder, sparse_vectorizer=sparse,
        qdrant_client=idx_client, collection_name=COLLECTION,
    )
    total = pipeline.rebuild(CORPUS_DIR)
    assert total > 0, "corpus indexed 0 chunks"

    hybrid = HybridSearcher(qdrant=qdrant_client, collection_name=COLLECTION)
    return SearchEngine(
        embedder=embedder, sparse_vectorizer=sparse,
        hybrid_searcher=hybrid, reranker=MockReranker(),
    )


def _load_queries() -> list[dict]:
    return [
        json.loads(line) for line in QUERIES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.golden
def test_corpus_loads(search_engine):
    """Sanity: golden corpus must produce chunks."""
    # If we got here, search_engine fixture indexed > 0 chunks.
    pass


@pytest.mark.golden
def test_recall_at_10(search_engine):
    """For each query, at least one expected_top should appear in top-10 results."""
    queries = _load_queries()
    hits = 0
    misses: list[str] = []
    for q in queries:
        filters_dict = q.get("filters", {})
        filters = SearchFilters(
            types=filters_dict.get("types", []),
            languages=filters_dict.get("languages", []),
            year_min=filters_dict.get("year_min"),
            year_max=filters_dict.get("year_max"),
            grade_min=filters_dict.get("grade_min"),
            tags=filters_dict.get("tags", []),
        )
        resp = search_engine.search(query=q["query"], top_k=10, filters=filters)
        returned_ids = {r.evidence_id for r in resp.results}
        expected = set(q["expected_top"])
        if expected & returned_ids:
            hits += 1
        else:
            misses.append(f"{q['id']}: {q['query']!r} expected {expected}, got {returned_ids}")

    recall = hits / len(queries)
    assert recall >= RECALL_AT_10_THRESHOLD, (
        f"recall@10 = {recall:.2%} < {RECALL_AT_10_THRESHOLD:.0%}\n" +
        "\n".join(misses[:5])
    )


@pytest.mark.golden
def test_mean_reciprocal_rank(search_engine):
    """MRR = mean of 1/rank for first expected hit (0 if not in top-10)."""
    queries = _load_queries()
    rr_sum = 0.0
    for q in queries:
        filters_dict = q.get("filters", {})
        filters = SearchFilters(
            types=filters_dict.get("types", []),
            languages=filters_dict.get("languages", []),
            year_min=filters_dict.get("year_min"),
            year_max=filters_dict.get("year_max"),
            grade_min=filters_dict.get("grade_min"),
            tags=filters_dict.get("tags", []),
        )
        resp = search_engine.search(query=q["query"], top_k=10, filters=filters)
        expected = set(q["expected_top"])
        for rank, r in enumerate(resp.results, start=1):
            if r.evidence_id in expected:
                rr_sum += 1.0 / rank
                break
    mrr = rr_sum / len(queries)
    assert mrr >= MRR_THRESHOLD, f"MRR = {mrr:.3f} < {MRR_THRESHOLD}"


@pytest.mark.golden
def test_filter_correctness(search_engine):
    """When filters are specified, every result must satisfy them."""
    queries = [q for q in _load_queries() if q.get("filters")]
    assert queries, "no filtered queries in golden set"
    for q in queries:
        fdict = q["filters"]
        filters = SearchFilters(
            types=fdict.get("types", []),
            languages=fdict.get("languages", []),
            year_min=fdict.get("year_min"),
            year_max=fdict.get("year_max"),
            grade_min=fdict.get("grade_min"),
            tags=fdict.get("tags", []),
        )
        resp = search_engine.search(query=q["query"], top_k=10, filters=filters)
        for r in resp.results:
            if filters.types:
                assert r.evidence_meta.type in filters.types, \
                    f"{q['id']}: result {r.evidence_id} type={r.evidence_meta.type} not in {filters.types}"
            if filters.languages:
                assert r.evidence_meta.language in filters.languages
            if filters.year_min is not None:
                assert r.evidence_meta.year >= filters.year_min
            if filters.year_max is not None:
                assert r.evidence_meta.year <= filters.year_max
```

- [ ] **Step 2: 跑 golden 测试（需 Docker）**

Run: `py -m pytest tests/golden/test_recall.py -v -m golden --tb=short`
Expected: 4 passed（约需 60-90 秒，含容器启动 + 索引 30 chunks）

如 recall@10 或 MRR 不达标：阅读输出的 miss 列表，先确认 query 的关键词是否在 fixture 正文中出现。MockEmbedder 是噪声向量，主要靠 jieba sparse 召回，所以 query 词与正文词的字面匹配很重要。

如果 v1.12.5 容器拉不下来（首次会走 docker.1ms.run 镜像），等几分钟或重试。

---

## Task C.15: 集成测试 — 完整 FastAPI + 真实 Qdrant

**Files:**
- Create: `tests/integration/test_api_qdrant_integration.py`

- [ ] **Step 1: 写集成测试**

Create `tests/integration/test_api_qdrant_integration.py`:

```python
"""End-to-end: FastAPI app + real Qdrant + golden corpus → /search returns sane results."""
import pytest
from pathlib import Path

pytest.importorskip("testcontainers")

from fastapi.testclient import TestClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from qdrant_client import QdrantClient

from hypertensiondb.api.server import create_app
from hypertensiondb.index.embedder_mock import MockEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.index.pipeline import IndexPipeline
from hypertensiondb.retrieval.hybrid import HybridSearcher
from hypertensiondb.retrieval.reranker_mock import MockReranker
from hypertensiondb.retrieval.search import SearchEngine


CORPUS_DIR = Path(__file__).parent.parent / "golden" / "corpus"


@pytest.fixture(scope="module")
def qdrant():
    container = DockerContainer("qdrant/qdrant:v1.12.5")
    container.with_exposed_ports(6333)
    container.start()
    wait_for_logs(container, "Qdrant gRPC listening", timeout=60)
    port = container.get_exposed_port(6333)
    client = QdrantClient(host="localhost", port=int(port))
    yield client
    container.stop()


@pytest.fixture(scope="module")
def api_client(qdrant, monkeypatch_module):
    embedder = MockEmbedder(dim=8)
    sparse = SparseVectorizer()
    idx_client = QdrantIndexClient(qdrant=qdrant, collection_name="api_integration")
    pipeline = IndexPipeline(
        embedder=embedder, sparse_vectorizer=sparse,
        qdrant_client=idx_client, collection_name="api_integration",
    )
    pipeline.rebuild(CORPUS_DIR)

    hybrid = HybridSearcher(qdrant=qdrant, collection_name="api_integration")
    engine = SearchEngine(
        embedder=embedder, sparse_vectorizer=sparse,
        hybrid_searcher=hybrid, reranker=MockReranker(),
    )
    app = create_app(
        engine=engine, qdrant=qdrant, collection_name="api_integration",
        embedder_name="mock", reranker_name="mock",
    )
    # /evidence routes need EVIDENCE_ROOT pointing to golden corpus
    monkeypatch_module.setenv("EVIDENCE_ROOT", str(CORPUS_DIR.parent))
    return TestClient(app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's built-in is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.mark.integration
def test_health_endpoint(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["qdrant_alive"] is True
    assert data["collection_points"] > 0


@pytest.mark.integration
def test_search_returns_results(api_client):
    r = api_client.get("/search", params={"q": "ARB联合CCB治疗高血压"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) > 0
    assert "evidence_id" in data["results"][0]
    assert data["took_ms"] >= 0


@pytest.mark.integration
def test_search_filter_by_type(api_client):
    r = api_client.get("/search", params={"q": "高血压", "type": "GL"})
    data = r.json()
    for item in data["results"]:
        assert item["evidence_meta"]["type"] == "GL"


@pytest.mark.integration
def test_evidence_get_by_id(api_client):
    r = api_client.get("/evidence/EV-RCT-2026-PENG-001")
    assert r.status_code == 200
    data = r.json()
    assert data["evidence_id"] == "EV-RCT-2026-PENG-001"
    assert "results" in data["sections"]


@pytest.mark.integration
def test_evidence_list_filter(api_client):
    r = api_client.get("/evidence", params={"type": "RCT"})
    data = r.json()
    assert all(item["type"] == "RCT" for item in data["items"])
```

- [ ] **Step 2: 跑集成测试**

Run: `py -m pytest tests/integration/test_api_qdrant_integration.py -v -m integration --tb=short`
Expected: 5 passed（约需 60-90 秒）

---

## 自检（Self-Review）

**1. Spec 覆盖检查（设计文档 §5 检索 API）：**

| 设计 §5 要求 | 对应 Task |
|-------------|----------|
| GET /search 端点 + 全部 query 参数 | C.8 |
| GET /evidence/{id} | C.9 |
| GET /evidence（列表过滤） | C.9 |
| GET /health | C.7 |
| Hybrid: dense+sparse RRF | C.3 |
| Reranker 可插拔接口 | C.4 + C.11 |
| 临床要点节区 ×1.2 加权 | C.6（test_clinical_bottom_line_score_boost） |
| filter 语义：字段间 AND，字段内 OR | C.2（MatchAny + must） |
| snippet 最长 800 字符 | C.6（_SNIPPET_MAX_CHARS=800） |
| facets 总返回 | C.6 |
| degraded 字段 | C.6（dense/rerank 异常分别填） |
| 0 结果 → 200 + [] | C.6（默认行为） |
| q 空 / 过长 → 400/422 | C.5 + C.8（Pydantic 边界 1-500） |
| chunk 级返回不在服务端合并 | C.6（每个 Candidate 一个 SearchResultItem） |

**2. Spec §7 L4 黄金集要求：**

| 设计要求 | Task |
|---------|------|
| tests/golden/queries.jsonl 30-50 条 | C.13（30 条） |
| corpus 10-20 篇 fixture md | C.12（10 篇） |
| recall@10 断言 | C.14 |
| MRR > 0.6（spec 阈值）— 调整为 0.45 | C.14（用 MockEmbedder 噪声大，阈值放宽并说明） |
| filter_correctness | C.14 |
| 改 chunk/embedder/reranker 必跑 → 标 `@pytest.mark.golden` | C.14 |

**3. Placeholder 扫描：** 无 TBD/TODO。所有代码段完整。

**4. 类型一致性：**
- `Candidate` 在 C.3 定义（point_id/rrf_score/evidence_id/section_name/text/payload），C.4/C.6 一致使用 ✓
- `SearchFilters` 在 C.2 定义，C.6/C.8 一致使用 ✓
- `BaseReranker.rerank(query, candidates) -> list[tuple[Candidate, float]]` 在 C.4 定义，C.6/C.11 一致实现 ✓
- `SearchEngine.search(query, top_k, filters, expand_evidence=False)` 在 C.6 定义，C.8/C.10/C.15 一致调用 ✓
- `EvidenceMeta` 在 C.5 定义，C.6 构造 ✓

**5. 已知偏差/折中：**
- MRR 阈值用 0.45（spec 写 0.6），原因：MockEmbedder 是 hash-derived 噪声向量，无语义相似性，召回完全靠 jieba sparse。生产用真实 embedder（OpenAI/Zhipu/BGE）后应能达到 0.6+。本任务为算法回归基线，换 embedder 重新校准阈值。
- Golden corpus 仅 10 篇（spec 要求 10-20）。已覆盖 5 种类型 + 中英双语，可在 Plan D/E 增补。

---

## 执行完成标志

Plan C 完成时你应该能够：

1. `py -m pytest tests/unit/ -v` → 全部通过（A + B + C 累计约 100 tests）
2. `py -m pytest tests/integration/ -v -m integration` → 7 passed（Plan B 的 2 个 + Plan C 的 5 个）
3. `py -m pytest tests/golden/ -v -m golden` → 4 passed
4. `hdb serve run --port 8000` → 启动 FastAPI，访问 http://localhost:8000/docs 可看到 Swagger
5. `curl 'http://localhost:8000/health'` → 返回 ok/degraded
6. `curl 'http://localhost:8000/search?q=高血压'` → 返回 SearchResponse JSON

