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

from src.agents.base import BaseAgent, split_prompt_for_caching, robust_parse_json
from src.state.schema import EBMQuery, Evidence, WorkflowState
from src.tools.hypertension_rag_client import RAGConfig, RAGUnavailable, search


class AcquireAgent(BaseAgent):
    """Build a natural-language query from PICO and retrieve from hypertensiondb."""

    def __init__(self, llm, tools: Optional[List[Any]] = None, fast_llm=None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Acquire")
        self.fast_llm = fast_llm
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "acquire_agent.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()
        filter_path = Path(__file__).parent.parent / "config" / "prompts" / "passage_filter.txt"
        with open(filter_path, "r", encoding="utf-8") as f:
            self._filter_prompt_template = f.read()

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

    def _filter_passages(
        self, evidence_list: List[Evidence], pico_dict: Dict[str, Any]
    ) -> tuple:
        """Batch-judge all passages against PICO using fast_llm.

        Returns (filtered_evidence_list, stats_dict).
        """
        passage_items = []
        passage_map = []
        for ev_idx, ev in enumerate(evidence_list):
            for p_idx, p in enumerate(ev.supporting_passages):
                seq = len(passage_items) + 1
                passage_items.append(
                    f"[{seq}] Evidence={ev.evidence_id} Section={p.section}\n"
                    f"    \"{p.snippet[:400]}\""
                )
                passage_map.append((ev_idx, p_idx))

        if not passage_items:
            return evidence_list, {"total": 0, "relevant": 0, "tangential": 0, "irrelevant": 0, "dropped_papers": 0}

        passage_list_str = "\n".join(passage_items)
        prompt = self._filter_prompt_template.format(
            patient=pico_dict["patient"],
            intervention=pico_dict["intervention"],
            comparison=pico_dict["comparison"],
            outcome=pico_dict["outcome"],
            passage_list=passage_list_str,
        )

        response = self.fast_llm.invoke(prompt)
        result = robust_parse_json(response.content)
        verdicts = result.get("verdicts", [])

        verdict_by_id: Dict[int, Dict] = {}
        for v in verdicts:
            verdict_by_id[v.get("id", 0)] = v

        counts = {"total": len(passage_items), "relevant": 0, "tangential": 0, "irrelevant": 0}
        for seq_id in range(1, len(passage_items) + 1):
            v = verdict_by_id.get(seq_id, {})
            label = v.get("label", "RELEVANT").upper()
            ev_idx, p_idx = passage_map[seq_id - 1]
            passage = evidence_list[ev_idx].supporting_passages[p_idx]
            passage.filter_label = label
            if label == "TANGENTIAL":
                passage.filter_reason = v.get("reason")
                counts["tangential"] += 1
            elif label == "IRRELEVANT":
                counts["irrelevant"] += 1
            else:
                counts["relevant"] += 1

        dropped_papers = 0
        filtered = []
        for ev in evidence_list:
            kept = [p for p in ev.supporting_passages if p.filter_label != "IRRELEVANT"]
            if kept:
                ev.supporting_passages = kept
                ev.relevance_score = max(p.score for p in kept)
                filtered.append(ev)
            else:
                dropped_papers += 1
                print(f"[PASSAGE-FILTER] Dropped entire paper {ev.evidence_id}: all passages IRRELEVANT")

        counts["dropped_papers"] = dropped_papers
        if counts["irrelevant"] or counts["tangential"]:
            print(
                f"[PASSAGE-FILTER] {counts['relevant']} relevant, "
                f"{counts['tangential']} tangential, "
                f"{counts['irrelevant']} irrelevant, "
                f"{counts['dropped_papers']} paper(s) dropped"
            )

        return filtered, counts

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        pico_dict = self._build_pico_dict(state)

        has_backtrack = bool(state.get("backtrack_reason"))
        backtrack_context = ""
        if has_backtrack:
            backtrack_context = (
                f"Previous search returned unsatisfactory results: "
                f"{state['backtrack_reason']}\nAdjust the query accordingly."
            )

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

        # Step 3: LLM passage filter (semantic relevance check)
        filter_stats = None
        if self.fast_llm and evidence_list:
            t0 = time.time()
            try:
                evidence_list, filter_stats = self._filter_passages(evidence_list, pico_dict)
                print(f"[TIMING] Acquire passage filter: {time.time()-t0:.1f}s")
            except Exception as exc:
                print(f"[WARN] Passage filter failed, proceeding unfiltered: {exc}")

        return {
            "evidence_list": evidence_list,
            "search_query": query,
            "total_results": len(evidence_list),
            "selected_count": len(evidence_list),
            "rag_degraded": degraded or None,
            "passage_filter_stats": filter_stats,
        }
