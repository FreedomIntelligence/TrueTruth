from typing import Optional, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, description="自然语言 query")
    top_k: int = Field(10, ge=1, le=50)
    types: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    year_min: Optional[int] = Field(None, ge=1900, le=2100)
    year_max: Optional[int] = Field(None, ge=1900, le=2100)
    grade_min: Optional[Literal["very_low", "low", "moderate", "high"]] = None
    tags: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    include_draft: bool = False
    expand_evidence: bool = False


class EvidenceMeta(BaseModel):
    title: dict[str, Optional[str]]
    type: str
    year: int
    language: str
    study_type: Optional[str] = None
    grade_level: Optional[str] = None
    rob_overall: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    full_frontmatter: Optional[dict] = None


class SearchResultItem(BaseModel):
    evidence_id: str
    section: str
    score: float
    rerank_score: float
    snippet: str
    is_clinical_bottom_line: bool = False
    evidence_meta: EvidenceMeta


class Facets(BaseModel):
    type: dict[str, int] = Field(default_factory=dict)
    year: dict[str, int] = Field(default_factory=dict)
    grade: dict[str, int] = Field(default_factory=dict)
    language: dict[str, int] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    took_ms: int
    results: list[SearchResultItem]
    facets: Facets
    degraded: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    qdrant_alive: bool
    collection_points: Optional[int] = None
    embedder: str
    reranker: str


class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    frontmatter: dict
    sections: dict[str, str]
    source_path: str
