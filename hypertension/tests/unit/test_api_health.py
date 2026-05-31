import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from hypertensiondb.api.server import create_app
from hypertensiondb.retrieval.search import SearchEngine


@pytest.fixture
def mock_engine():
    return MagicMock(spec=SearchEngine)


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
