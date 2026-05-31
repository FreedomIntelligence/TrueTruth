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
    """临床要点 章节 rerank_score 应乘 1.2 加权."""
    cands = [
        _cand("normal", evid="EV-RCT-2026-A-001", rrf=0.8, payload_extra={"is_clinical_bottom_line": False}),
        _cand("cbl", evid="EV-RCT-2026-B-001", rrf=0.7, payload_extra={"is_clinical_bottom_line": True}),
    ]
    cands[0].payload["is_clinical_bottom_line"] = False
    cands[1].payload["is_clinical_bottom_line"] = True
    mock_hybrid.search.return_value = cands
    resp = engine.search(query="x", top_k=10, filters=SearchFilters())
    # CBL: 0.7 * 1.2 = 0.84 > normal: 0.8 → CBL ranks first
    assert resp.results[0].is_clinical_bottom_line is True


@pytest.mark.unit
def test_search_facets(engine, mock_hybrid):
    cands = [
        _cand("p1", evid="EV-RCT-2026-A-001"),
        _cand("p2", evid="EV-RCT-2025-B-001"),
        _cand("p3", evid="EV-META-2026-C-001"),
    ]
    cands[0].payload["type"] = "RCT"; cands[0].payload["year"] = 2026; cands[0].payload["grade_level"] = "high"; cands[0].payload["language"] = "zh"
    cands[1].payload["type"] = "RCT"; cands[1].payload["year"] = 2025; cands[1].payload["grade_level"] = "moderate"; cands[1].payload["language"] = "zh"
    cands[2].payload["type"] = "META"; cands[2].payload["year"] = 2026; cands[2].payload["grade_level"] = "high"; cands[2].payload["language"] = "en"
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
    assert len(resp.results) == 1
