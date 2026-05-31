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
