from fastapi import APIRouter, Request

from hypertensiondb.retrieval.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    deps = request.app.state.deps
    qdrant = deps.qdrant
    collection_points = None
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
