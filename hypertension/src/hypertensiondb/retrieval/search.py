import time
from collections import Counter
from typing import Optional

from hypertensiondb.index.embedder import BaseEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.retrieval.hybrid import HybridSearcher, Candidate
from hypertensiondb.retrieval.reranker import BaseReranker
from hypertensiondb.retrieval.filters import SearchFilters, build_qdrant_filter
from hypertensiondb.retrieval.models import (
    SearchResponse, SearchResultItem, EvidenceMeta, Facets,
)

_PREFETCH_LIMIT = 50
_RERANK_INPUT = 30
_SNIPPET_MAX_CHARS = 800
_CLINICAL_BOOST = 1.2


class SearchEngine:
    """Orchestrate: query embed → hybrid search → rerank → facet → response."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        sparse_vectorizer: SparseVectorizer,
        hybrid_searcher: HybridSearcher,
        reranker: BaseReranker,
    ) -> None:
        self._embedder = embedder
        self._sparse = sparse_vectorizer
        self._hybrid = hybrid_searcher
        self._reranker = reranker

    def search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters,
        expand_evidence: bool = False,
    ) -> SearchResponse:
        t0 = time.monotonic()
        degraded: list[str] = []

        # 1) Embed query (dense)
        try:
            dense_vector = self._embedder.embed([query])[0]
        except Exception:
            dense_vector = []
            degraded.append("dense")

        # 2) Sparse vectorize
        sparse_indices, sparse_values = self._sparse.vectorize(query)

        # 3) Hybrid search via Qdrant
        qfilter = build_qdrant_filter(filters)
        candidates = self._hybrid.search(
            dense_vector=dense_vector,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            limit=_RERANK_INPUT,
            prefetch_limit=_PREFETCH_LIMIT,
            query_filter=qfilter,
        )

        # 4) Rerank
        try:
            reranked = self._reranker.rerank(query, candidates)
        except Exception:
            degraded.append("rerank")
            reranked = [(c, c.rrf_score) for c in
                        sorted(candidates, key=lambda x: x.rrf_score, reverse=True)]

        # 5) Apply clinical_bottom_line boost
        boosted: list[tuple[Candidate, float]] = []
        for cand, score in reranked:
            is_cbl = bool(cand.payload.get("is_clinical_bottom_line"))
            final_score = score * _CLINICAL_BOOST if is_cbl else score
            boosted.append((cand, final_score))
        boosted.sort(key=lambda t: t[1], reverse=True)

        # 6) Build response items (truncate to top_k)
        items: list[SearchResultItem] = []
        for cand, rerank_score in boosted[:top_k]:
            items.append(self._make_item(cand, rerank_score, expand_evidence))

        # 7) Facets from all reranked candidates (distinct evidence_id)
        facets = self._build_facets([c for c, _ in boosted])

        took_ms = int((time.monotonic() - t0) * 1000)
        return SearchResponse(
            query=query,
            took_ms=took_ms,
            results=items,
            facets=facets,
            degraded=degraded,
        )

    def _make_item(
        self, cand: Candidate, rerank_score: float, expand_evidence: bool
    ) -> SearchResultItem:
        p = cand.payload
        snippet = (cand.text or "")[:_SNIPPET_MAX_CHARS]
        meta = EvidenceMeta(
            title={"zh": p.get("title_zh"), "en": p.get("title_en")},
            type=p.get("type", ""),
            year=int(p.get("year", 0)),
            language=p.get("language", ""),
            study_type=p.get("study_type"),
            grade_level=p.get("grade_level"),
            rob_overall=p.get("rob_overall"),
            tags=list(p.get("tags") or []),
        )
        return SearchResultItem(
            evidence_id=cand.evidence_id,
            section=cand.section_name,
            score=cand.rrf_score,
            rerank_score=float(rerank_score),
            snippet=snippet,
            is_clinical_bottom_line=bool(p.get("is_clinical_bottom_line")),
            evidence_meta=meta,
        )

    @staticmethod
    def _build_facets(candidates: list[Candidate]) -> Facets:
        type_counter: Counter[str] = Counter()
        year_counter: Counter[str] = Counter()
        grade_counter: Counter[str] = Counter()
        lang_counter: Counter[str] = Counter()
        seen_evidence: set[str] = set()
        for c in candidates:
            if c.evidence_id in seen_evidence:
                continue
            seen_evidence.add(c.evidence_id)
            p = c.payload
            if p.get("type"):
                type_counter[p["type"]] += 1
            if p.get("year"):
                year_counter[str(p["year"])] += 1
            if p.get("grade_level"):
                grade_counter[p["grade_level"]] += 1
            if p.get("language"):
                lang_counter[p["language"]] += 1
        return Facets(
            type=dict(type_counter),
            year=dict(year_counter),
            grade=dict(grade_counter),
            language=dict(lang_counter),
        )
