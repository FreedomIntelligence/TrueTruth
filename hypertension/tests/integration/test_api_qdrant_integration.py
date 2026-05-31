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


# Tests expect /evidence to find corpus files; EVIDENCE_ROOT must point at the dir
# that CONTAINS the .md files (rglob finds them).
CORPUS_DIR = Path(__file__).parent.parent / "golden" / "corpus"


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's built-in is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def qdrant(monkeypatch_module):
    container = DockerContainer("qdrant/qdrant:v1.12.5")
    container.with_exposed_ports(6333)
    container.start()
    wait_for_logs(container, "Qdrant gRPC listening", timeout=120)
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
    # Point /evidence routes at the corpus dir
    monkeypatch_module.setenv("EVIDENCE_ROOT", str(CORPUS_DIR))
    return TestClient(app)


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
