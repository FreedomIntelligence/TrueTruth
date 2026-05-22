"""AcquireAgent — retrieves evidence from the hypertensiondb RAG service.

Flow:
  1. LLM converts the structured PICO/EBMQuery into a single Chinese
     natural-language query string.
  2. HTTP GET /search?q=<query>&top_k=N against hypertensiondb FastAPI.
  3. Aggregate chunk-level results into paper+passages Evidence list.

PubMed, PMC full-text fetch, BM25 RAG, listwise ranking — all removed.
Domain filtering is handled upstream in AskAgent.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, split_prompt_for_caching
from src.state.schema import EBMQuery, WorkflowState
from src.tools.hypertension_rag_client import RAGConfig, RAGUnavailable, search


class AcquireAgent(BaseAgent):
    """Build a natural-language query from PICO and retrieve from hypertensiondb."""

    def __init__(self, llm, tools: Optional[List[Any]] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Acquire")
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "acquire_agent.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def _extract_query(self, content: str) -> str:
        """Extract the natural-language query from the LLM response.

        Expected format:  **Query:** ```query <text> ```
        Fallback: first non-empty line after **Query:** marker.
        """
        if "```query" in content:
            start = content.find("```query") + len("```query")
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        if "**Query:**" in content:
            tail = content.split("**Query:**", 1)[1]
            for line in tail.splitlines():
                stripped = line.strip().strip("`")
                if stripped:
                    return stripped
        return content.strip().splitlines()[0] if content.strip() else ""

    def _build_pico_dict(self, state: WorkflowState) -> Dict[str, Any]:
        ebm_query: Optional[EBMQuery] = state.get("ebm_query")
        pico = state.get("pico_query")
        if ebm_query is not None:
            return {
                "patient": ebm_query.patient,
                "intervention": ebm_query.primary_focus,
                "comparison": ebm_query.comparator or "",
                "outcome": ebm_query.outcome,
                "keywords": ebm_query.keywords,
            }
        if pico is not None:
            return {
                "patient": pico.patient,
                "intervention": pico.intervention,
                "comparison": pico.comparison,
                "outcome": pico.outcome,
                "keywords": pico.keywords,
            }
        raise ValueError("AcquireAgent: state has neither ebm_query nor pico_query")

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        pico_dict = self._build_pico_dict(state)

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = (
                f"Previous search returned unsatisfactory results: "
                f"{state['backtrack_reason']}\nAdjust the query accordingly."
            )

        # Step 1: LLM builds natural-language Chinese query
        prompt = self.prompt_template.format(
            patient=pico_dict["patient"],
            intervention=pico_dict["intervention"],
            comparison=pico_dict["comparison"],
            outcome=pico_dict["outcome"],
            keywords=", ".join(pico_dict["keywords"]),
            backtrack_context=backtrack_context,
        )
        prompt = split_prompt_for_caching(prompt)

        t0 = time.time()
        response = self.llm.invoke(prompt)
        print(f"[TIMING] Acquire query LLM: {time.time()-t0:.1f}s")
        query = self._extract_query(response.content)
        print(f"[DEBUG] Acquire NL query: {query}")

        # Step 2: HTTP /search against hypertensiondb
        t0 = time.time()
        try:
            evidence_list, degraded = search(query)
            print(f"[TIMING] hypertensiondb /search: {time.time()-t0:.1f}s")
            if degraded:
                print(f"[WARN] RAG degraded: {degraded}")
        except RAGUnavailable as exc:
            print(f"[ERROR] RAG unavailable: {exc}")
            return {
                "evidence_list": [],
                "search_query": query,
                "total_results": 0,
                "selected_count": 0,
                "error": f"hypertension_api_unavailable: {exc}",
                "rag_degraded": None,
            }

        for i, e in enumerate(evidence_list):
            print(
                f"[DEBUG] Rank {i+1}: score={e.relevance_score:.3f} "
                f"id={e.evidence_id} title={(e.title or '')[:60]}... "
                f"passages={len(e.supporting_passages)}"
            )

        return {
            "evidence_list": evidence_list,
            "search_query": query,
            "total_results": len(evidence_list),
            "selected_count": len(evidence_list),
            "rag_degraded": degraded or None,
        }
