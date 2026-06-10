"""HTTP client for the hypertensiondb FastAPI /search endpoint.

Responsibilities:
- Issue GET /search with query + top_k
- Retry on transient failures (2 retries with exponential backoff)
- Aggregate chunk-level results into paper-level Evidence objects with
  supporting_passages
- Raise RAGUnavailable on persistent failure
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import httpx

from src.state.schema import Evidence, Passage


class RAGUnavailable(Exception):
    """Raised when hypertensiondb /search is unreachable after retries."""


_MIN_EXPECTED_POINTS = 10000


def check_index_health(config: RAGConfig | None = None) -> None:
    """Warn loudly if Qdrant index looks incomplete. Called once at pipeline startup.

    After a fresh rebuild Qdrant's background optimizer may still be ingesting
    WAL entries, so we poll briefly before declaring the index incomplete.
    """
    import time as _time

    cfg = config or RAGConfig.from_env()
    url = f"{cfg.base_url.rstrip('/')}/health"
    pts = None
    try:
        for _ in range(6):
            resp = httpx.get(url, timeout=cfg.timeout_s)
            data = resp.json()
            pts = data.get("collection_points")
            if pts is not None and pts >= _MIN_EXPECTED_POINTS:
                return
            _time.sleep(5)
    except Exception:
        pass
    if pts is not None and pts < _MIN_EXPECTED_POINTS:
        print(
            f"[CRITICAL] hypertensiondb index has only {pts} chunks "
            f"(expected >= {_MIN_EXPECTED_POINTS}). "
            f"Run: cd hypertension && hdb index rebuild --confirm"
        )


@dataclass(frozen=True)
class RAGConfig:
    base_url: str
    timeout_s: float
    top_k: int
    max_papers: int
    max_passages_per_paper: int
    min_score: float

    @classmethod
    def from_env(cls) -> "RAGConfig":
        return cls(
            base_url=os.getenv("HYPERTENSION_API_URL", "http://localhost:8000"),
            timeout_s=float(os.getenv("HYPERTENSION_API_TIMEOUT", "10")),
            top_k=int(os.getenv("RAG_SEARCH_TOP_K", "15")),
            max_papers=int(os.getenv("RAG_MAX_PAPERS", "6")),
            max_passages_per_paper=int(os.getenv("RAG_MAX_PASSAGES_PER_PAPER", "3")),
            min_score=float(os.getenv("RAG_MIN_SCORE", "0.80")),
        )


def search(query: str, config: RAGConfig | None = None) -> tuple[list[Evidence], list[str]]:
    """Search hypertensiondb and return (evidence_list, degraded_flags).

    Args:
        query: natural-language Chinese (or English) query string
        config: RAGConfig; defaults to RAGConfig.from_env()

    Returns:
        evidence_list: up to config.max_papers Evidence objects, each with up to
            config.max_passages_per_paper supporting_passages, sorted by max
            passage score descending.
        degraded_flags: list of degradation tags from the /search response
            (e.g. ["dense"], ["rerank"]).  Empty list when fully healthy.

    Raises:
        RAGUnavailable: after 2 retries + initial attempt all fail.
    """
    cfg = config or RAGConfig.from_env()
    payload = _request_with_retries(query, cfg)
    raw_results: list[dict] = payload.get("results") or []
    degraded: list[str] = payload.get("degraded") or []
    evidence_list = _aggregate(raw_results, cfg)
    _enrich_bibliography(evidence_list, cfg)
    return evidence_list, degraded


@dataclass(frozen=True)
class SafetyRAGConfig:
    """Config for the DRUG_SAFETY sub-retrieval.

    Separate from RAGConfig because drug-label safety chunks are English and
    queried cross-lingually (Chinese question), so rerank scores run lower than
    the study-evidence min_score=0.80 gate would allow — we relax min_score and
    surface more papers so multiple drugs/classes in the question are covered.
    """
    base_url: str
    timeout_s: float
    top_k: int
    max_papers: int
    max_passages_per_paper: int
    min_score: float

    @classmethod
    def from_env(cls) -> "SafetyRAGConfig":
        return cls(
            base_url=os.getenv("HYPERTENSION_API_URL", "http://localhost:8000"),
            timeout_s=float(os.getenv("HYPERTENSION_API_TIMEOUT", "10")),
            top_k=int(os.getenv("RAG_SAFETY_TOP_K", "20")),
            max_papers=int(os.getenv("RAG_SAFETY_MAX_PAPERS", "6")),
            max_passages_per_paper=int(os.getenv("RAG_SAFETY_MAX_PASSAGES", "4")),
            min_score=float(os.getenv("RAG_SAFETY_MIN_SCORE", "0.0")),
        )


def search_safety(query: str, config: SafetyRAGConfig | None = None) -> list[Evidence]:
    """Retrieve grounded DRUG_SAFETY label chunks for the drugs/classes in `query`.

    A separate sub-query (type=DRUGSAFETY) so the Apply agent can fill an
    SmPC-structured safety section from authoritative, citable drug labels rather
    than free LLM recall. Returns Evidence objects with evidence_role="safety_only";
    these are intentionally kept OUT of the main evidence_list (Appraise/GRADE must
    not grade a regulatory label as if it were a study).

    Never raises: on any failure returns [] (safety section then degrades to a
    "no grounded label retrieved" gap rather than blocking the answer).
    """
    cfg = config or SafetyRAGConfig.from_env()
    # Reuse RAGConfig's aggregation by mirroring fields.
    agg_cfg = RAGConfig(
        base_url=cfg.base_url, timeout_s=cfg.timeout_s, top_k=cfg.top_k,
        max_papers=cfg.max_papers, max_passages_per_paper=cfg.max_passages_per_paper,
        min_score=cfg.min_score,
    )
    try:
        payload = _request_with_retries(query, agg_cfg, extra_params={"type": "DRUGSAFETY"})
    except RAGUnavailable:
        return []
    raw_results: list[dict] = payload.get("results") or []
    evidence_list = _aggregate(raw_results, agg_cfg)
    for ev in evidence_list:
        ev.evidence_role = "safety_only"
    _enrich_bibliography(evidence_list, agg_cfg)
    return evidence_list


def _enrich_bibliography(evidence_list: list[Evidence], cfg: RAGConfig) -> None:
    """Best-effort: fill authors/journal/doi/pmid/url from the /evidence/{id}
    detail endpoint.

    The /search payload only carries indexed fields (title/year/type/grade);
    full bibliographic metadata lives in the source frontmatter, exposed via
    GET /evidence/{id}. We fetch it per paper so the user-facing output can
    render real numbered references instead of internal EV-ids.

    This is non-critical: any failure (endpoint down, 404, timeout) leaves the
    bib fields empty and the renderer degrades to an author-from-id label. We
    therefore never raise from here.
    """
    base = cfg.base_url.rstrip("/")
    for ev in evidence_list:
        if not ev.evidence_id:
            continue
        try:
            resp = httpx.get(f"{base}/evidence/{ev.evidence_id}", timeout=cfg.timeout_s)
            if resp.status_code != 200:
                continue
            fm = (resp.json() or {}).get("frontmatter") or {}
        except Exception:
            continue
        authors = fm.get("authors")
        if isinstance(authors, list):
            ev.authors = [str(a) for a in authors if a]
        ev.journal = fm.get("journal") or None
        ev.doi = fm.get("doi") or None
        ev.pmid = fm.get("pmid") or None
        ev.url = fm.get("url") or None


def _request_with_retries(
    query: str, cfg: RAGConfig, extra_params: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = f"{cfg.base_url.rstrip('/')}/search"
    params = {"q": query, "top_k": cfg.top_k}
    if extra_params:
        params.update(extra_params)
    backoffs = [0.5, 2.0]  # 2 retries; total max wait ~2.5s on top of timeouts

    last_exc: Exception | None = None
    for attempt in range(len(backoffs) + 1):  # 1 initial + 2 retries = 3 attempts
        try:
            resp = httpx.get(url, params=params, timeout=cfg.timeout_s)
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()  # 4xx -> raises immediately, will NOT retry
            return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise RAGUnavailable(f"hypertensiondb 4xx: {exc}") from exc
            last_exc = exc
            if attempt < len(backoffs):
                time.sleep(backoffs[attempt])
    raise RAGUnavailable(f"hypertensiondb unreachable after retries: {last_exc}")


def _aggregate(raw_results: list[dict], cfg: RAGConfig) -> list[Evidence]:
    """Aggregate chunk-level /search results into paper-level Evidence objects.

    - Groups chunks by evidence_id.
    - Within each group: sorts passages by rerank_score desc, keeps top N.
    - Group order: max(rerank_score) within group, desc.
    - Truncates to cfg.max_papers.
    """
    by_paper: dict[str, list[dict]] = defaultdict(list)
    paper_meta: dict[str, dict] = {}
    for item in raw_results:
        ev_id = item.get("evidence_id")
        if not ev_id:
            continue
        by_paper[ev_id].append(item)
        if ev_id not in paper_meta:
            paper_meta[ev_id] = item.get("evidence_meta") or {}

    papers: list[Evidence] = []
    for ev_id, chunks in by_paper.items():
        chunks.sort(key=lambda c: c.get("rerank_score", 0.0), reverse=True)
        top_chunks = chunks[: cfg.max_passages_per_paper]
        passages = [
            Passage(
                section=c.get("section") or "",
                snippet=c.get("snippet") or "",
                score=float(c.get("rerank_score", 0.0)),
            )
            for c in top_chunks
        ]
        meta = paper_meta[ev_id]
        title_field = meta.get("title") or {}
        title = title_field.get("zh") or title_field.get("en") or ""
        max_score = passages[0].score if passages else 0.0
        papers.append(
            Evidence(
                evidence_id=ev_id,
                title=title,
                source="hypertensiondb",
                year=meta.get("year"),
                language=meta.get("language") or "",
                tags=list(meta.get("tags") or []),
                supporting_passages=passages,
                relevance_score=max_score,
                # Pre-filled from frontmatter metadata when available;
                # Prefer explicit study_type (GRADE code) over the filing type field.
                # None means Appraise will infer from passage text instead.
                study_type=meta.get("study_type") or meta.get("type") or None,
                grade_level=meta.get("grade_level") or None,
                rob_overall=meta.get("rob_overall") or None,
            )
        )

    papers.sort(key=lambda e: e.relevance_score, reverse=True)

    if cfg.min_score > 0:
        before = len(papers)
        papers = [p for p in papers if p.relevance_score >= cfg.min_score]
        dropped = before - len(papers)
        if dropped:
            print(
                f"[RAG-FILTER] Dropped {dropped} paper(s) below "
                f"min_score={cfg.min_score:.2f}"
            )

    return papers[: cfg.max_papers]
