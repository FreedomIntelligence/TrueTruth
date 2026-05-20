from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import EBMQuery, WorkflowState, Evidence
from src.tools.pubmed_api import fetch_pmc_full_text, search_pubmed
from src.tools.local_evidence_db import search_local

# Cochrane Handbook Highly Sensitive Search Strategy (HSSS) —
# sensitive version for identifying RCTs and systematic reviews in MEDLINE.
# Used for Therapy and Prevention questions.
# Reference: Cochrane Handbook for Systematic Reviews, Section 4.4.
_HSSS_FILTER = (
    "(randomized controlled trial[pt] OR controlled clinical trial[pt] "
    "OR randomized[tiab] OR placebo[tiab] OR randomly[tiab] OR trial[ti] "
    "OR systematic[sb])"
)

# Diagnostic Test Accuracy (DTA) filter for Diagnosis questions.
# Targets sensitivity, specificity, ROC, likelihood ratio, and QUADAS studies.
_DTA_FILTER = (
    '(sensitivity[tiab] OR specificity[tiab] OR "diagnostic accuracy"[tiab] '
    'OR "likelihood ratio"[tiab] OR "ROC curve"[tiab] OR "area under the curve"[tiab] '
    'OR QUADAS[tiab] OR "diagnostic test"[tiab] OR "predictive value"[tiab] '
    "OR systematic[sb])"
)

# Observational filter for Prognosis and Harm questions.
# Allows cohort studies; keeps systematic reviews; drops RCT bias.
_OBSERVATIONAL_FILTER = (
    "(cohort[tiab] OR prospective[tiab] OR retrospective[tiab] "
    'OR "follow-up"[tiab] OR prognosis[tiab] OR survival[tiab] '
    'OR "risk factor"[tiab] OR incidence[tiab] OR mortality[tiab] '
    "OR systematic[sb])"
)

# Map question_type to the appropriate PubMed filter
_FILTER_BY_QUESTION_TYPE = {
    "Therapy": _HSSS_FILTER,
    "Prevention": _HSSS_FILTER,
    "Diagnosis": _DTA_FILTER,
    "Prognosis": _OBSERVATIONAL_FILTER,
    "Harm": _OBSERVATIONAL_FILTER,
}

# Map EBMQuery route_type to the appropriate PubMed filter
_FILTER_BY_ROUTE_TYPE = {
    "ebm_pico": _HSSS_FILTER,
    "ebm_peo": _OBSERVATIONAL_FILTER,
    "ebm_pird": _DTA_FILTER,
    "ebm_prognosis": _OBSERVATIONAL_FILTER,
    "full_pipeline": _HSSS_FILTER,  # default for generic full_pipeline
}

# Number of top-K articles to select via listwise ranking.
_TOP_K = 5

# ---------------------------------------------------------------------------
# Lazy-loaded sentence-transformer for RAG reranking
# ---------------------------------------------------------------------------
_embedding_model = None
_embedding_lock = threading.Lock()


def _get_embedding_model():
    """Return a shared SentenceTransformer instance (thread-safe lazy init)."""
    global _embedding_model  # noqa: PLW0603
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                try:
                    from sentence_transformers import SentenceTransformer  # noqa: PLC0415
                    try:
                        # Use cached model without network check (avoids HuggingFace timeouts)
                        _embedding_model = SentenceTransformer(
                            "all-MiniLM-L6-v2", local_files_only=True
                        )
                    except Exception:
                        # Model not cached yet — download it once
                        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                except Exception:
                    _embedding_model = None  # graceful degradation
    return _embedding_model


class AcquireAgent(BaseAgent):
    """
    Agent for acquiring evidence from PubMed.

    Evidence selection pipeline:
      1. LLM builds a PubMed Boolean search query (acquire_agent.txt).
      2. PubMed API returns up to 20 candidates (filter chosen by route_type).
      3. PMC full-text is fetched in parallel for open-access articles.
      4. BM25 + Embedding RAG extracts key sentences from full-text articles.
      5. Keyword-based study type inference runs on all candidates.
      6. LLM performs Listwise ranking → Top-K selection.
      7. Full-text articles are promoted to the front of the ranked list.
    """

    def __init__(self, llm, ranking_llm=None, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Acquire")
        self.prompt_template = self._load_prompt("acquire_agent.txt")
        self.ranking_prompt_template = self._load_prompt("acquire_ranking.txt")
        # Listwise ranking is a classification/sorting task — fast model is sufficient.
        self.ranking_llm = ranking_llm or llm

    def _load_prompt(self, filename: str) -> str:
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / filename
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def _extract_query(self, content: str) -> str:
        """Extract search query from LLM response."""
        if "```pubmed" in content:
            start = content.find("```pubmed") + 9
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        if "**Query:**" in content:
            query_start = content.find("**Query:**") + 10
            remainder = content[query_start:].strip()
            if "```" in remainder:
                cb_start = remainder.find("```")
                after_backticks = remainder[cb_start + 3 :]
                newline = after_backticks.find("\n")
                if newline >= 0:
                    after_backticks = after_backticks[newline + 1 :]
                cb_end = after_backticks.find("```")
                if cb_end >= 0:
                    return after_backticks[:cb_end].strip()
            return remainder.strip()
        return content.strip()

    def _use_local_db(self, question_type: str = "Therapy") -> bool:
        """Return True to route retrieval through the local obstetrics evidence DB."""
        import os
        return os.getenv("USE_LOCAL_DB", "false").lower() == "true"

    def _apply_search_filter(self, query: str, question_type: str = "Therapy", route_type: str = "") -> str:
        """Wrap query with an appropriate filter based on route_type (preferred) or question_type."""
        if route_type and route_type in _FILTER_BY_ROUTE_TYPE:
            search_filter = _FILTER_BY_ROUTE_TYPE[route_type]
        else:
            search_filter = _FILTER_BY_QUESTION_TYPE.get(question_type, _HSSS_FILTER)
        return f"({query}) AND {search_filter}"

    def _fetch_full_texts(self, candidates: List[Evidence]) -> None:
        """Fetch PMC full text for open-access articles in parallel (in-place).

        Only articles with a pmcid are attempted.  Results are written directly
        to evidence.full_text and evidence.has_full_text.
        """
        pmc_candidates = [e for e in candidates if e.pmcid]
        if not pmc_candidates:
            return

        def _fetch_one(ev: Evidence) -> None:
            try:
                text = fetch_pmc_full_text(ev.pmid)
                if text:
                    ev.full_text = text
                    ev.has_full_text = True
            except Exception:
                pass  # non-fatal — abstract-only fallback is fine

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_fetch_one, pmc_candidates))

        n_fetched = sum(1 for e in pmc_candidates if e.has_full_text)
        print(f"[DEBUG] PMC full-text fetched: {n_fetched}/{len(pmc_candidates)}")

    def _rag_extract(
        self, evidence: Evidence, query_terms: List[str]
    ) -> Tuple[str, float]:
        """Extract key sentences from full text using BM25 → Embedding rerank.

        Pipeline:
          1. Split full_text into sentences.
          2. BM25 retrieves top-8 candidate sentences.
          3. Embedding model reranks to top-3 by cosine similarity to query.

        Returns (key_sentences_str, relevance_boost) where relevance_boost is
        the mean cosine similarity of the top-3 sentences (0.0 if unavailable).
        Falls back to abstract if full_text is absent.
        """
        text = evidence.full_text or evidence.abstract or ""
        if not text:
            return "", 0.0

        # Split into sentences (simple heuristic — good enough for abstracts/paragraphs)
        import re
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
        if not sentences:
            return text[:500], 0.0

        query_str = " ".join(query_terms)

        # BM25 retrieval
        try:
            from rank_bm25 import BM25Okapi
            tokenised = [s.lower().split() for s in sentences]
            bm25 = BM25Okapi(tokenised)
            scores = bm25.get_scores(query_str.lower().split())
            top8_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:8]
            top8 = [sentences[i] for i in top8_idx]
        except Exception:
            top8 = sentences[:8]

        # Embedding rerank to top-3
        model = _get_embedding_model()
        if model is not None and len(top8) > 1:
            try:
                import numpy as np
                query_emb = model.encode([query_str], normalize_embeddings=True)[0]
                sent_embs = model.encode(top8, normalize_embeddings=True)
                sims = sent_embs @ query_emb
                top3_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:3]
                top3 = [top8[i] for i in top3_idx]
                boost = float(np.mean([sims[i] for i in top3_idx]))
            except Exception:
                top3 = top8[:3]
                boost = 0.0
        else:
            top3 = top8[:3]
            boost = 0.0

        return " … ".join(top3), boost

    def _infer_study_type(self, evidence: Evidence) -> str:
        """Infer study type from PubMed publication types (primary) then title/abstract keywords (fallback)."""
        # --- Primary: PubMed pubtype metadata (authoritative, index-assigned) ---
        pub_types = getattr(evidence, "pub_types", None) or []
        pt_lower = {pt.lower() for pt in pub_types}
        if "meta-analysis" in pt_lower:
            return "Systematic Review"
        if "systematic review" in pt_lower:
            return "Systematic Review"
        if "randomized controlled trial" in pt_lower or "controlled clinical trial" in pt_lower:
            return "RCT"
        if "clinical trial" in pt_lower:
            return "RCT"
        if "observational study" in pt_lower or "cohort study" in pt_lower:
            return "Cohort Study"
        if "case-control study" in pt_lower or "case control study" in pt_lower:
            return "Case-Control Study"
        if "case reports" in pt_lower:
            return "Case Report"
        if "review" in pt_lower:
            # "Review" pubtype without "Systematic Review" → narrative review
            return "Narrative Review"

        # --- Fallback: keyword scan of title + abstract ---
        text = f"{evidence.title} {evidence.abstract or ''}".lower()
        if "systematic review" in text or "meta-analysis" in text:
            return "Systematic Review"
        if (
            "randomized controlled trial" in text
            or "randomised controlled trial" in text
            or "randomized clinical trial" in text
            or "randomised clinical trial" in text
            or " randomized " in text
            or " randomised " in text
        ):
            return "RCT"
        if "cohort study" in text or "cohort" in text:
            return "Cohort Study"
        if "case-control" in text:
            return "Case-Control Study"
        if "cross-sectional" in text:
            return "Cross-Sectional Study"
        if "case report" in text or "case series" in text:
            return "Case Report"
        return "Other"

    def _listwise_rank(
        self,
        candidates: List[Evidence],
        pico: Dict,
        top_k: int = _TOP_K,
    ) -> List[Evidence]:
        """
        Select and rank Top-K evidence using LLM Listwise strategy.

        The LLM receives all candidates at once and reasons comparatively to
        produce a ranked selection — superior to pointwise scoring because it
        considers the relative value of each article against the others.

        Returns the selected Evidence objects with rank-normalised
        relevance_score (rank 1 → 1.0, rank K → ~0.1, linear decay).
        """
        if not candidates:
            return []

        actual_k = min(top_k, len(candidates))

        # Build candidate block for prompt
        lines = []
        for i, e in enumerate(candidates):
            study_hint = f"[{e.study_type}] " if e.study_type else ""
            abstract_preview = (
                e.key_sentences if e.key_sentences else (e.abstract or "")[:150]
            )
            lines.append(
                f"[{i + 1}] {study_hint}{e.title}\n"
                f"     Abstract: {abstract_preview}"
            )
        candidate_text = "\n\n".join(lines)

        prompt = self.ranking_prompt_template.format(
            patient=pico["patient"],
            intervention=pico["intervention"],
            comparison=pico["comparison"],
            outcome=pico["outcome"],
            total=len(candidates),
            k=actual_k,
            candidates=candidate_text,
        )

        response = self.ranking_llm.invoke(prompt)
        print(
            f"[DEBUG] Listwise ranking response (first 300 chars): {response.content[:300]}"
        )

        # Parse ranked IDs, validate, deduplicate
        try:
            ranking_dict = self._parse_json(response.content)
            raw_ids = [
                item["id"]
                for item in ranking_dict.get("ranked_selection", [])
                if isinstance(item.get("id"), int)
            ]
        except Exception as e:
            print(f"[DEBUG] Listwise ranking parse failed ({e}), using original order")
            raw_ids = list(range(1, len(candidates) + 1))

        seen: set = set()
        ranked_ids: List[int] = []
        for rid in raw_ids:
            if rid not in seen and 1 <= rid <= len(candidates):
                seen.add(rid)
                ranked_ids.append(rid)

        selected = ranked_ids[:top_k]
        n = len(selected)

        result: List[Evidence] = []
        for rank, article_id in enumerate(selected):
            evidence = candidates[article_id - 1]  # prompt uses 1-based IDs
            # Linear rank-normalised score: rank 0 → 1.0, rank n-1 → 0.1
            evidence.relevance_score = round(1.0 - (rank / max(n, 1)) * 0.9, 3)
            result.append(evidence)

        return result

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Acquire agent: build query → search → full-text → RAG → listwise rank."""
        # Prefer EBMQuery (new routing); fall back to legacy PICOQuery
        ebm_query: Optional[EBMQuery] = state.get("ebm_query")
        pico = state.get("pico_query")

        if ebm_query is None and pico is None:
            raise ValueError("No EBMQuery or PICOQuery found in state")

        # Derive a unified pico_dict for the ranking prompt (always needed)
        if ebm_query is not None:
            pico_dict = {
                "patient": ebm_query.patient,
                "intervention": ebm_query.primary_focus,
                "comparison": ebm_query.comparator or "",
                "outcome": ebm_query.outcome,
            }
            query_keywords = ebm_query.keywords
            route_type = f"ebm_{ebm_query.query_type}"  # e.g. "ebm_pico", "ebm_pird"
        else:
            pico_dict = {
                "patient": pico.patient,
                "intervention": pico.intervention,
                "comparison": pico.comparison,
                "outcome": pico.outcome,
            }
            query_keywords = pico.keywords
            route_type = state.get("route_type") or ""

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = (
                f"Previous search failed: {state['backtrack_reason']}\n"
                "Please adjust your search strategy accordingly."
            )

        # Step 1: LLM builds Boolean search query
        prompt = self.prompt_template.format(
            patient=pico_dict["patient"],
            intervention=pico_dict["intervention"],
            comparison=pico_dict["comparison"],
            outcome=pico_dict["outcome"],
            keywords=", ".join(query_keywords),
            backtrack_context=backtrack_context,
        )
        # Split into system + user messages so the static prefix (role, worked
        # example, instructions) gets prefix-cached by the gateway. See
        # base.split_prompt_for_caching.
        from src.agents.base import split_prompt_for_caching
        prompt = split_prompt_for_caching(prompt)
        t0 = time.time()
        response = self.llm.invoke(prompt)
        print(f"[TIMING] Acquire query LLM: {time.time()-t0:.1f}s")
        base_query = self._extract_query(response.content)
        print(f"[DEBUG] Base query: {base_query}")

        # Step 2: Search — local obstetrics DB (full-text) or PubMed fallback
        question_type = state.get("question_type") or "Therapy"
        search_query_used = ""

        try:
            t0 = time.time()
            if self._use_local_db(question_type):
                print(
                    f"[DEBUG] question_type={question_type}, routing to local obstetrics DB"
                )
                raw_results = search_local(query=base_query, top_k=20)
                search_query_used = base_query
                print(f"[DEBUG] Local DB returned {len(raw_results)} articles")
                print(f"[TIMING] Local DB search: {time.time()-t0:.1f}s")
            else:
                filtered_query = self._apply_search_filter(
                    base_query, question_type=question_type, route_type=route_type
                )
                print(
                    f"[DEBUG] route_type={route_type}, question_type={question_type}, "
                    f"filtered query: {filtered_query}"
                )
                raw_results = search_pubmed(query=filtered_query, max_results=20)
                print(f"[DEBUG] PubMed (filtered) returned {len(raw_results)} articles")
                if len(raw_results) == 0:
                    print(
                        "[DEBUG] Filtered query returned 0 results — falling back to base query"
                    )
                    raw_results = search_pubmed(query=base_query, max_results=20)
                    print(f"[DEBUG] PubMed (base) returned {len(raw_results)} articles")
                    search_query_used = base_query
                else:
                    search_query_used = filtered_query
                print(f"[TIMING] PubMed search (parallel fetch): {time.time()-t0:.1f}s")
        except Exception as e:
            return {
                "evidence_list": [],
                "search_query": search_query_used,
                "total_results": 0,
                "selected_count": 0,
                "error": str(e),
            }

        # Step 3: Fetch PMC full texts in parallel for open-access articles
        t0 = time.time()
        self._fetch_full_texts(raw_results)
        print(f"[TIMING] PMC full-text fetch: {time.time()-t0:.1f}s")

        # Step 4: RAG extract key sentences for full-text articles
        rag_query_terms = query_keywords or base_query.split()[:10]
        for ev in raw_results:
            if ev.has_full_text and ev.full_text:
                key_sents, boost = self._rag_extract(ev, rag_query_terms)
                ev.key_sentences = key_sents
                # Slightly boost relevance score for full-text articles (applied after ranking)
                ev._rag_boost = boost  # type: ignore[attr-defined]

        # Step 5: Infer study type for all candidates (used as hint in ranking prompt)
        for evidence in raw_results:
            evidence.study_type = self._infer_study_type(evidence)

        print(f"[DEBUG] Study types inferred for {len(raw_results)} candidates")

        # Step 6: LLM Listwise ranking → Top-K selection
        t0 = time.time()
        selected = self._listwise_rank(raw_results, pico_dict, top_k=_TOP_K)
        print(f"[TIMING] Listwise ranking LLM: {time.time()-t0:.1f}s")

        # Step 7: Promote full-text articles to the front (stable sort)
        full_text_first = sorted(selected, key=lambda e: 0 if e.has_full_text else 1)

        for i, e in enumerate(full_text_first):
            ft_flag = "[FT]" if e.has_full_text else ""
            print(
                f"[DEBUG] Rank {i + 1}{ft_flag}: score={e.relevance_score:.3f}, "
                f"type={e.study_type}, title={e.title[:80]}..."
            )
        print(
            f"[DEBUG] Listwise selected {len(full_text_first)}/{len(raw_results)} articles "
            f"({sum(1 for e in full_text_first if e.has_full_text)} with full text)"
        )

        study_type_distribution: Dict[str, int] = {}
        for e in full_text_first:
            t = e.study_type or "Unknown"
            study_type_distribution[t] = study_type_distribution.get(t, 0) + 1

        return {
            "evidence_list": full_text_first,
            "search_query": search_query_used,
            "total_results": len(raw_results),
            "selected_count": len(full_text_first),
            "study_type_distribution": study_type_distribution,
        }
