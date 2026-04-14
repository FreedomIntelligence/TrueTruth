import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, AppraisalResults

# ---------------------------------------------------------------------------
# GRADE computation tables
# ---------------------------------------------------------------------------

# Initial GRADE points by study type (4=High, 3=Moderate, 2=Low, 1=Very Low)
_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "SYSTEMATIC_REVIEW": 4,   # Starts High (synthesizes RCTs or best available evidence)
    "META_ANALYSIS": 4,        # Starts High
    "NMA": 4,                  # Network meta-analysis: starts High
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CROSS_SECTIONAL": 2,      # Observational: starts Low
    "NARRATIVE_REVIEW": 1,     # Expert synthesis without systematic search: Very Low
    "CASE_REPORT": 1,
    "GUIDELINE": 3,            # Typically based on SR: starts Moderate
    "EXPERT_OPINION": 1,       # No systematic search: Very Low
}

# Mapping from GRADE codes to human-readable study type labels
# (used to sync evidence.study_type with Appraise classification)
_GRADE_CODE_TO_LABEL: Dict[str, str] = {
    "RCT": "RCT",
    "SYSTEMATIC_REVIEW": "Systematic Review",
    "META_ANALYSIS": "Meta-Analysis",
    "NMA": "Network Meta-Analysis",
    "COHORT": "Cohort Study",
    "CASE_CONTROL": "Case-Control Study",
    "CROSS_SECTIONAL": "Cross-Sectional Study",
    "NARRATIVE_REVIEW": "Narrative Review",
    "CASE_REPORT": "Case Report",
    "GUIDELINE": "Clinical Practice Guideline",
    "EXPERT_OPINION": "Expert Opinion",
}

# Downgrade penalty for each factor level
_DOWNGRADE_PENALTY: Dict[str, int] = {
    "NOT_SERIOUS": 0,
    "SERIOUS": 1,
    "VERY_SERIOUS": 2,
    "NA": 0,
}

# Points → GRADE level label
_POINTS_TO_GRADE: Dict[int, str] = {
    4: "High",
    3: "Moderate",
    2: "Low",
    1: "Very Low",
}

# Numerical confidence level → float score
_CONFIDENCE_SCORES: Dict[str, float] = {
    "HIGH": 0.90,
    "MODERATE": 0.65,
    "LOW": 0.40,
    "VERY_LOW": 0.15,
}


def _compute_grade(appraisal: Dict) -> str:
    """
    Deterministically compute GRADE level from LLM classification labels.

    Rules:
      - Start from initial points based on study_type
      - Deduct for each downgrade factor (risk_of_bias, inconsistency,
        indirectness, imprecision, publication_bias)
      - Add for upgrade factors (large_effect, dose_response)
        only when study_type is observational (COHORT / CASE_CONTROL)
      - Clamp result to [1, 4] and map to label
    """
    study_type = appraisal.get("study_type", "CASE_REPORT")
    points = _INITIAL_POINTS.get(study_type, 1)

    # Downgrade factors
    for factor in ("risk_of_bias", "inconsistency", "indirectness", "imprecision"):
        points -= _DOWNGRADE_PENALTY.get(appraisal.get(factor, "NOT_SERIOUS"), 0)

    if appraisal.get("publication_bias") == "SUSPECTED":
        points -= 1

    # Upgrade factors (observational studies only)
    if study_type in ("COHORT", "CASE_CONTROL", "CROSS_SECTIONAL"):
        if appraisal.get("large_effect") == "YES":
            points += 1
        if appraisal.get("dose_response") == "YES":
            points += 1

    points = max(1, min(4, points))
    return _POINTS_TO_GRADE[points]


def _compute_numerical_confidence(numerical_assessment: Dict) -> float:
    """Convert numerical assessment classification to a float confidence score."""
    level = numerical_assessment.get("confidence_level", "MODERATE")
    return _CONFIDENCE_SCORES.get(level, 0.65)


class AppraiseAgent(BaseAgent):
    """
    Agent for appraising evidence quality using the GRADE framework.

    Architecture:
      1. LLM classifies each study's GRADE factors (study type, risk of bias,
         inconsistency, indirectness, imprecision, publication bias, etc.)
         as categorical labels — it does NOT assign final grades directly.
      2. Python applies deterministic GRADE rules to compute the final grade
         for each study from the classifications.
      3. Python also converts conflict and numerical assessments to structured
         output (has_conflict, numerical_confidence).
    """

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Appraise")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "appraise_agent.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def _format_evidence_list(self, evidence_list) -> str:
        """Format evidence list for the prompt, including abstract preview."""
        parts = []
        for i, e in enumerate(evidence_list):
            abstract_preview = (getattr(e, "abstract", "") or "")[:200]
            study_type_hint = getattr(e, "study_type", "") or ""
            hint_str = f"\nSource DB study_type hint: {study_type_hint}" if study_type_hint else ""
            parts.append(
                f"Evidence {i + 1}:\n"
                f"Title: {e.title}\n"
                f"Source: {e.source}\n"
                f"PMID: {e.pmid}{hint_str}\n"
                f"Abstract (preview): {abstract_preview}"
            )
        return "\n\n".join(parts)

    def _appraise_batch(self, evidence_subset: list, backtrack_context: str) -> dict:
        """Appraise a subset of evidence articles using the standard prompt."""
        evidence_text = self._format_evidence_list(evidence_subset)
        prompt = self.prompt_template.format(
            evidence_list=evidence_text,
            backtrack_context=backtrack_context,
        )
        response = self.llm.invoke(prompt)
        return self._parse_json(response.content)

    def _merge_appraisal_dicts(self, results: List[dict], batch_sizes: List[int]) -> dict:
        """
        Merge multiple batch appraisal results into a single appraisal dict.

        - study_appraisals: concatenated and re-indexed so evidence_id is global (1-based)
        - conflict_assessment: pessimistic merge (YES if any batch reports YES)
        - numerical_assessment: highest-confidence merge
        - evidence_summary: all summaries joined
        """
        merged_appraisals: List[dict] = []
        global_id = 1
        for result in results:
            for appraisal in result.get("study_appraisals", []):
                appraisal["evidence_id"] = global_id
                merged_appraisals.append(appraisal)
                global_id += 1

        # Conflict: pessimistic — YES wins
        merged_conflict = {"conflicts_exist": "NO", "conflict_type": "NA",
                           "conflict_severity": "NA", "conflict_description": None}
        for result in results:
            c = result.get("conflict_assessment", {})
            if c.get("conflicts_exist") == "YES":
                merged_conflict = c
                break

        # Numerical: pick the result with the highest data_available
        _data_rank = {"YES": 2, "PARTIAL": 1, "NO": 0}
        best_numerical = results[0].get("numerical_assessment", {})
        for result in results[1:]:
            n = result.get("numerical_assessment", {})
            if _data_rank.get(n.get("data_available", "NO"), 0) > _data_rank.get(
                best_numerical.get("data_available", "NO"), 0
            ):
                best_numerical = n

        # Summary: join all
        summaries = [r.get("evidence_summary", "") for r in results if r.get("evidence_summary")]
        merged_summary = " | ".join(summaries)

        return {
            "study_appraisals": merged_appraisals,
            "conflict_assessment": merged_conflict,
            "numerical_assessment": best_numerical,
            "evidence_summary": merged_summary,
        }

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Appraise agent to classify GRADE factors and compute final grades."""
        evidence_list = state.get("evidence_list")
        if not evidence_list:
            raise ValueError("No evidence found in state")

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = (
                f"Previous attempt feedback: {state['backtrack_reason']}\n"
                "Please address these issues in your classifications."
            )

        # Split evidence into batches for parallel processing.
        # Each batch produces per-study appraisals + local conflict/numerical assessments.
        # Results are merged afterwards.  Batching halves the token count per call and
        # lets both calls run simultaneously, cutting Appraise stage time by ~50%.
        _BATCH_SIZE = 5
        batches = [
            evidence_list[i : i + _BATCH_SIZE]
            for i in range(0, len(evidence_list), _BATCH_SIZE)
        ]

        if len(batches) > 1:
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=len(batches)) as executor:
                futures = [
                    executor.submit(self._appraise_batch, batch, backtrack_context)
                    for batch in batches
                ]
                batch_results = [f.result() for f in futures]
            print(f"[TIMING] Appraise parallel batches ({len(batches)}×{_BATCH_SIZE}): {time.time()-t0:.1f}s")
            appraisal_dict = self._merge_appraisal_dicts(batch_results, [len(b) for b in batches])
            print(f"[PARALLEL-APPRAISE] {len(batches)} batches completed in parallel.")
        else:
            # Single batch (≤5 articles): no need for parallel overhead
            appraisal_dict = self._appraise_batch(evidence_list, backtrack_context)

        study_appraisals = appraisal_dict.get("study_appraisals", [])
        grade_rationales: List[Dict] = []
        graded_evidence = []

        for i, evidence in enumerate(evidence_list):
            # Match by index (LLM outputs in same order as input)
            appraisal = study_appraisals[i] if i < len(study_appraisals) else {}

            study_type = appraisal.get("study_type", "CASE_REPORT")
            computed_grade = _compute_grade(appraisal)

            # Set grade and sync study_type on the Evidence object
            # (overrides acquire_agent keyword-inferred label with Appraise LLM classification)
            evidence.grade_level = computed_grade
            evidence.study_type = _GRADE_CODE_TO_LABEL.get(study_type, study_type)
            graded_evidence.append(evidence)

            # Build rich rationale record for downstream consumers (including Judge)
            initial_grade = _POINTS_TO_GRADE.get(_INITIAL_POINTS.get(study_type, 1), "Very Low")
            grade_rationales.append({
                "evidence_id": i + 1,
                "title": evidence.title,
                "study_type": study_type,
                "initial_grade": initial_grade,
                "risk_of_bias": appraisal.get("risk_of_bias", "NOT_SERIOUS"),
                "inconsistency": appraisal.get("inconsistency", "NA"),
                "indirectness": appraisal.get("indirectness", "NOT_SERIOUS"),
                "imprecision": appraisal.get("imprecision", "NOT_SERIOUS"),
                "publication_bias": appraisal.get("publication_bias", "UNDETECTED"),
                "large_effect": appraisal.get("large_effect", "NA"),
                "dose_response": appraisal.get("dose_response", "NA"),
                "computed_grade": computed_grade,
                "rationale": appraisal.get("rationale", ""),
            })

        # --- Conflict assessment ---
        conflict = appraisal_dict.get("conflict_assessment", {})
        has_conflict = conflict.get("conflicts_exist") == "YES"
        conflict_description = conflict.get("conflict_description") if has_conflict else None

        # --- Numerical assessment ---
        numerical = appraisal_dict.get("numerical_assessment", {})
        numerical_confidence = _compute_numerical_confidence(numerical)

        # --- Build AppraisalResults ---
        appraisal_results = AppraisalResults(
            evidence=graded_evidence,
            has_conflict=has_conflict,
            conflict_description=conflict_description,
            summary=appraisal_dict.get("evidence_summary", ""),
        )

        return {
            "appraisal_results": appraisal_results,
            "grade_rationales": grade_rationales,
            "numerical_confidence": numerical_confidence,
            "numerical_data": {
                "data_available": numerical.get("data_available", "NO"),
                "confidence_level": numerical.get("confidence_level", "MODERATE"),
                "note": numerical.get("note", ""),
            },
            # True only when there is a MAJOR conflict (influences scheduling)
            "bias_inconsistency": has_conflict and conflict.get("conflict_severity") == "MAJOR",
        }
