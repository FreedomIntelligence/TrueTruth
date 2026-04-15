from typing import List, Dict, Any
import time
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, Evidence
from src.tools.pubmed_api import search_pubmed
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

# Number of top-K articles to select via listwise ranking.
_TOP_K = 10


class AcquireAgent(BaseAgent):
    """
    Agent for acquiring evidence from PubMed.

    Evidence selection pipeline:
      1. LLM builds a PubMed Boolean search query (acquire_agent.txt).
      2. PubMed API returns up to 20 candidates (HSSS filter applied first).
      3. Keyword-based study type inference runs on all candidates.
      4. LLM performs Listwise ranking: given the full candidate list, it
         selects and ranks the Top-K most relevant articles in one pass.
      5. Rank-normalised relevance scores are assigned (rank 1 → 1.0).
    """

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Acquire")
        self.prompt_template = self._load_prompt("acquire_agent.txt")
        self.ranking_prompt_template = self._load_prompt("acquire_ranking.txt")

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
        """Return True to route retrieval through the local obstetrics evidence DB.

        Demo phase: always True.  Later this can be switched per question_type
        or via an environment variable / config flag.
        """
        return True

    def _apply_search_filter(self, query: str, question_type: str = "Therapy") -> str:
        """Wrap query with an appropriate filter based on question type."""
        search_filter = _FILTER_BY_QUESTION_TYPE.get(question_type, _HSSS_FILTER)
        return f"({query}) AND {search_filter}"

    def _infer_study_type(self, evidence: Evidence) -> str:
        """Infer study type from title and abstract using keyword rules."""
        text = f"{evidence.title} {evidence.abstract or ''}".lower()
        if "systematic review" in text or "meta-analysis" in text:
            return "Systematic Review"
        if (
            "randomized controlled trial" in text
            or "randomised controlled trial" in text
            or "randomized clinical trial" in text
            or "randomised clinical trial" in text
            or "rct" in text
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

        response = self.llm.invoke(prompt)
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
        """Execute Acquire agent: build query → search PubMed → listwise rank."""
        pico = state.get("pico_query")
        if not pico:
            raise ValueError("No PICO query found in state")

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = (
                f"Previous search failed: {state['backtrack_reason']}\n"
                "Please adjust your search strategy accordingly."
            )

        # Step 1: LLM builds Boolean search query
        prompt = self.prompt_template.format(
            patient=pico.patient,
            intervention=pico.intervention,
            comparison=pico.comparison,
            outcome=pico.outcome,
            keywords=", ".join(pico.keywords),
            backtrack_context=backtrack_context,
        )
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
                filtered_query = self._apply_search_filter(base_query, question_type)
                print(
                    f"[DEBUG] question_type={question_type}, filtered query: {filtered_query}"
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

        # Step 3: Infer study type for all candidates (used as hint in ranking prompt)
        for evidence in raw_results:
            evidence.study_type = self._infer_study_type(evidence)

        print(f"[DEBUG] Study types inferred for {len(raw_results)} candidates")

        # Step 4: LLM Listwise ranking → Top-K selection
        pico_dict = {
            "patient": pico.patient,
            "intervention": pico.intervention,
            "comparison": pico.comparison,
            "outcome": pico.outcome,
        }

        t0 = time.time()
        selected = self._listwise_rank(raw_results, pico_dict, top_k=_TOP_K)
        print(f"[TIMING] Listwise ranking LLM: {time.time()-t0:.1f}s")

        for i, e in enumerate(selected):
            print(
                f"[DEBUG] Rank {i + 1}: score={e.relevance_score:.3f}, "
                f"type={e.study_type}, title={e.title[:80]}..."
            )
        print(f"[DEBUG] Listwise selected {len(selected)}/{len(raw_results)} articles")

        study_type_distribution: Dict[str, int] = {}
        for e in selected:
            t = e.study_type or "Unknown"
            study_type_distribution[t] = study_type_distribution.get(t, 0) + 1

        return {
            "evidence_list": selected,
            "search_query": search_query_used,
            "total_results": len(raw_results),
            "selected_count": len(selected),
            "study_type_distribution": study_type_distribution,
        }
