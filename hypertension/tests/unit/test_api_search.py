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
