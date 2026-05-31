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
