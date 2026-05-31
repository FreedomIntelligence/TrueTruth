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
    query = kwargs["query"]
    assert isinstance(query, qm.FusionQuery)
    assert query.fusion == qm.Fusion.RRF
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
