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


@dataclass(frozen=True)
class RAGConfig:
    base_url: str
    timeout_s: float
    top_k: int
    max_papers: int
    max_passages_per_paper: int

    @classmethod
    def from_env(cls) -> "RAGConfig":
        return cls(
            base_url=os.getenv("HYPERTENSION_API_URL", "http://localhost:8000"),
            timeout_s=float(os.getenv("HYPERTENSION_API_TIMEOUT", "10")),
            top_k=int(os.getenv("RAG_SEARCH_TOP_K", "15")),
            max_papers=int(os.getenv("RAG_MAX_PAPERS", "6")),
            max_passages_per_paper=int(os.getenv("RAG_MAX_PASSAGES_PER_PAPER", "3")),
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
    return evidence_list, degraded


def _request_with_retries(query: str, cfg: RAGConfig) -> dict[str, Any]:
    url = f"{cfg.base_url.rstrip('/')}/search"
    params = {"q": query, "top_k": cfg.top_k}
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
                # None means Appraise will infer from passage text instead.
                study_type=meta.get("type") or None,
                grade_level=meta.get("grade_level") or None,
                rob_overall=meta.get("rob_overall") or None,
            )
        )

    papers.sort(key=lambda e: e.relevance_score, reverse=True)
    return papers[: cfg.max_papers]
