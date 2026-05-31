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

RECALL_AT_10_THRESHOLD = 0.85
MRR_THRESHOLD = 0.45


@pytest.fixture(scope="module")
def qdrant_client():
    container = DockerContainer("qdrant/qdrant:v1.12.5")
    container.with_exposed_ports(6333)
    container.start()
    wait_for_logs(container, "Qdrant gRPC listening", timeout=120)
    port = container.get_exposed_port(6333)
    client = QdrantClient(host="localhost", port=int(port))
    yield client
    container.stop()


@pytest.fixture(scope="module")
def search_engine(qdrant_client):
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


def _build_filters(filters_dict: dict) -> SearchFilters:
    return SearchFilters(
        types=filters_dict.get("types", []),
        languages=filters_dict.get("languages", []),
        year_min=filters_dict.get("year_min"),
        year_max=filters_dict.get("year_max"),
        grade_min=filters_dict.get("grade_min"),
        tags=filters_dict.get("tags", []),
        include_draft=False,
    )


@pytest.mark.golden
def test_corpus_loads(search_engine):
    pass


@pytest.mark.golden
def test_recall_at_10(search_engine):
    queries = _load_queries()
    hits = 0
    misses: list[str] = []
    for q in queries:
        filters = _build_filters(q.get("filters", {}))
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
    queries = _load_queries()
    rr_sum = 0.0
    for q in queries:
        filters = _build_filters(q.get("filters", {}))
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
    queries = [q for q in _load_queries() if q.get("filters")]
    assert queries, "no filtered queries"
    for q in queries:
        fdict = q["filters"]
        filters = _build_filters(fdict)
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
