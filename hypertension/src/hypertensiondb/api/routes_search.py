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
