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
    "SYSTEMATIC_REVIEW": 4,  # Dynamic: overridden by _SR_INITIAL_POINTS when included_study_type is known
    "META_ANALYSIS": 4,
    "NMA": 4,
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CROSS_SECTIONAL": 2,  # Observational: starts Low
    "NARRATIVE_REVIEW": 1,
    "CASE_REPORT": 1,
    "GUIDELINE": 3,
    "EXPERT_OPINION": 1,
}

# For SR/MA/NMA: initial points depend on the type of included studies
_SR_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "OBSERVATIONAL": 2,
    "MIXED": 3,
    "UNKNOWN": 3,
}

# Study types that are SRs/MAs (use _SR_INITIAL_POINTS when included_study_type is set)
_SR_TYPES = {"SYSTEMATIC_REVIEW", "META_ANALYSIS", "NMA"}

# Only these observational study types are eligible for upgrade factors
_UPGRADE_STUDY_TYPES = {"COHORT", "CASE_CONTROL"}

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

_SAFETY_KEYWORDS = frozenset({
    "adverse", "安全", "不良反应", "side effect", "safety",
    "耐受", "tolerability", "咳嗽", "cough", "水肿",
})
_EFFICACY_KEYWORDS = frozenset({
    "efficacy", "有效", "疗效", "outcome", "mortality",
    "降压", "心血管事件", "blood pressure", "cardiovascular",
})


def _derive_evidence_role(indirectness: str, indirectness_source: str, rationale: str) -> str:
    """Derive evidence role from Appraise indirectness + source dimension.

    Roles:
      core_direct         — PICO fully matches (head-to-head, same population)
      core_direct_limited — drug comparison is direct but population differs
      supportive_indirect — intervention/comparator/outcome mismatch
      safety_only         — only addresses safety, not efficacy
    """
    rationale_l = rationale.lower()
    has_safety = any(k in rationale_l for k in _SAFETY_KEYWORDS)
    has_efficacy = any(k in rationale_l for k in _EFFICACY_KEYWORDS)
    if has_safety and not has_efficacy:
        return "safety_only"
    if indirectness in ("SERIOUS", "VERY_SERIOUS"):
        if indirectness == "SERIOUS" and indirectness_source == "population":
            return "core_direct_limited"
        return "supportive_indirect"
    return "core_direct"


def _compute_grade(appraisal: Dict) -> str:
    """
    Deterministically compute GRADE level from LLM classification labels.

    Rules:
      1. Initial points:
         - SR/MA/NMA: use _SR_INITIAL_POINTS keyed by included_study_type
           (RCT→4, OBSERVATIONAL→2, MIXED→3, UNKNOWN→3); fall back to 4.
         - All other types: use _INITIAL_POINTS.
      2. Downgrade for each factor (risk_of_bias, inconsistency, indirectness,
         imprecision) and for suspected publication_bias.
      3. Upgrade (large_effect, dose_response) only when:
         - study_type is in _UPGRADE_STUDY_TYPES (COHORT or CASE_CONTROL), AND
         - risk_of_bias is NOT_SERIOUS (serious bias blocks upgrades).
         Upgraded points are capped at min(points, 3) — observational evidence
         cannot reach High (4) through upgrades alone.
      4. Clamp to [1, 4] and map to label.
    """
    study_type = appraisal.get("study_type", "CASE_REPORT")

    # Step 1: initial points
    if study_type in _SR_TYPES:
        included = appraisal.get("included_study_type", "UNKNOWN")
        points = _SR_INITIAL_POINTS.get(included, _SR_INITIAL_POINTS["UNKNOWN"])
    else:
        points = _INITIAL_POINTS.get(study_type, 1)

    # Step 2: downgrade factors
    for factor in ("risk_of_bias", "inconsistency", "indirectness", "imprecision"):
        points -= _DOWNGRADE_PENALTY.get(appraisal.get(factor, "NOT_SERIOUS"), 0)

    if appraisal.get("publication_bias") == "SUSPECTED":
        points -= 1

    # Step 3: upgrade factors — only for COHORT/CASE_CONTROL with no serious bias
    if (
        study_type in _UPGRADE_STUDY_TYPES
        and appraisal.get("risk_of_bias", "NOT_SERIOUS") == "NOT_SERIOUS"
    ):
        if appraisal.get("large_effect") == "YES":
            points += 1
        if appraisal.get("dose_response") == "YES":
            points += 1
        if appraisal.get("confounding_bias_mitigates") == "YES":
            points += 1
        # Observational evidence cannot reach High (4) through upgrades alone
        points = min(points, 3)

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
        prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "appraise_agent.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def _format_evidence_list(self, evidence_list) -> str:
        """Format evidence list for the prompt using supporting passages."""
        parts = []
        for i, e in enumerate(evidence_list):
            passages_text = "\n".join(
                f"  [{j+1}] Section: {p.section} (score: {p.score:.2f})\n      \"{p.snippet}\""
                for j, p in enumerate(e.supporting_passages)
            ) or "  （无 passages）"

            # Pre-computed metadata from frontmatter (authoritative when present)
            pre_computed = []
            if e.study_type:
                # Full-text Methods extraction is more reliable than passage snippets.
                # Pass as authoritative so the LLM does not re-classify from the
                # Evidence ID prefix (EV-META-*, EV-RCT-*, etc.).
                pre_computed.append(
                    f"study_type (pre-computed from full-text Methods extraction, "
                    f"authoritative — output this value exactly, do not re-classify "
                    f"from Evidence ID prefix or passage content): {e.study_type}"
                )
            if e.grade_level and e.grade_level != "not_assessed":
                pre_computed.append(f"grade_level (pre-computed, DO NOT re-derive): {e.grade_level}")
            if e.rob_overall and e.rob_overall != "not_assessed":
                pre_computed.append(f"rob_overall (pre-computed, DO NOT re-derive): {e.rob_overall}")
            pre_str = "\n".join(pre_computed) if pre_computed else "（无预计算字段，请从 passages 推断）"

            parts.append(
                f"Evidence {i + 1}:\n"
                f"Title: {e.title}\n"
                f"Source: {e.source}\n"
                f"Evidence ID: {e.evidence_id or 'unknown'}\n"
                f"Year: {e.year or 'unknown'} | Language: {e.language or 'unknown'}\n"
                f"Tags: {', '.join(e.tags) if e.tags else 'none'}\n"
                f"Pre-computed fields:\n{pre_str}\n"
                f"Supporting passages:\n{passages_text}"
            )
        return "\n\n".join(parts)

    def _appraise_batch(self, evidence_subset: list, backtrack_context: str, target_pico: str) -> dict:
        """Appraise a subset of evidence articles using the standard prompt."""
        evidence_text = self._format_evidence_list(evidence_subset)
        prompt = self.prompt_template.format(
            target_pico=target_pico,
            evidence_list=evidence_text,
            backtrack_context=backtrack_context,
        )
        response = self.llm.invoke(prompt)
        return self._parse_json(response.content)

    def _merge_appraisal_dicts(
        self, results: List[dict], batch_sizes: List[int]
    ) -> dict:
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
        merged_conflict = {
            "conflicts_exist": "NO",
            "conflict_type": "NA",
            "conflict_severity": "NA",
            "conflict_description": None,
        }
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
        summaries = [
            r.get("evidence_summary", "") for r in results if r.get("evidence_summary")
        ]
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
            # Graceful terminate — Coordinator should have caught this, but guard here too
            state["should_terminate"] = True
            state["backtrack_reason"] = "Appraise: evidence_list is empty, cannot proceed."
            return {
                "appraisal_results": None,
                "grade_rationales": [],
                "numerical_confidence": 0.0,
                "numerical_data": {"data_available": "NO", "confidence_level": "VERY_LOW", "note": "No evidence available"},
                "bias_inconsistency": False,
            }

        # Build target PICO string for indirectness assessment
        ebm_query = state.get("ebm_query")
        pico_query = state.get("pico_query")
        if ebm_query:
            target_pico = (
                f"P: {ebm_query.patient}; "
                f"I/E: {ebm_query.primary_focus}; "
                f"C: {ebm_query.comparator or 'N/A'}; "
                f"O: {ebm_query.outcome}"
            )
        elif pico_query:
            target_pico = (
                f"P: {pico_query.patient}; "
                f"I: {pico_query.intervention}; "
                f"C: {pico_query.comparison}; "
                f"O: {pico_query.outcome}"
            )
        else:
            target_pico = state.get("original_question", "未提供")

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
                    executor.submit(self._appraise_batch, batch, backtrack_context, target_pico)
                    for batch in batches
                ]
                batch_results = [f.result() for f in futures]
            print(
                f"[TIMING] Appraise parallel batches ({len(batches)}×{_BATCH_SIZE}): {time.time()-t0:.1f}s"
            )
            appraisal_dict = self._merge_appraisal_dicts(
                batch_results, [len(b) for b in batches]
            )
            print(f"[PARALLEL-APPRAISE] {len(batches)} batches completed in parallel.")
        else:
            # Single batch (≤5 articles): no need for parallel overhead
            appraisal_dict = self._appraise_batch(evidence_list, backtrack_context, target_pico)

        study_appraisals = appraisal_dict.get("study_appraisals", [])
        grade_rationales: List[Dict] = []
        graded_evidence = []

        for i, evidence in enumerate(evidence_list):
            appraisal = study_appraisals[i] if i < len(study_appraisals) else {}

            study_type = appraisal.get("study_type", "CASE_REPORT")
            # Pre-computed study_type (from full-text Methods extraction) is the
            # authoritative source. Override the LLM's output so GRADE calculation
            # uses the correct type even if the LLM was misled by the Evidence ID.
            if evidence.study_type:
                study_type = evidence.study_type
                appraisal["study_type"] = study_type

            # If pre-computed grade/rob are available from frontmatter metadata,
            # use them directly instead of LLM-derived values.
            if (evidence.grade_level and evidence.grade_level != "not_assessed"
                    and evidence.rob_overall and evidence.rob_overall != "not_assessed"):
                # Map pre-computed grade string to our internal label
                _GRADE_STR_MAP = {
                    "high": "High", "moderate": "Moderate",
                    "low": "Low", "very_low": "Very Low",
                }
                computed_grade = _GRADE_STR_MAP.get(
                    evidence.grade_level.lower(), evidence.grade_level
                )
                # GRADE standard: only "high" RoB (serious bias confirmed) warrants
                # downgrade.  "some_concerns" means possible bias but impact on
                # conclusion is uncertain — do NOT automatically downgrade.
                appraisal["risk_of_bias"] = {
                    "low": "NOT_SERIOUS",
                    "some_concerns": "NOT_SERIOUS",
                    "high": "SERIOUS",
                }.get(evidence.rob_overall.lower(), "NOT_SERIOUS")
            else:
                computed_grade = _compute_grade(appraisal)

            # Sync study_type from pre-computed field if available
            if evidence.study_type:
                # Already set from RAG client metadata
                pass
            else:
                evidence.study_type = _GRADE_CODE_TO_LABEL.get(study_type, study_type)

            evidence.grade_level = computed_grade
            graded_evidence.append(evidence)

            # Derive evidence role from indirectness classification + source dimension
            indirectness_val = appraisal.get("indirectness", "NOT_SERIOUS")
            indirectness_src = appraisal.get("indirectness_source", "NA")
            rationale_text = appraisal.get("rationale", "")
            evidence.evidence_role = _derive_evidence_role(indirectness_val, indirectness_src, rationale_text)

            # Build rich rationale record for downstream consumers (including Judge)
            initial_grade = _POINTS_TO_GRADE.get(
                _INITIAL_POINTS.get(study_type, 1), "Very Low"
            )
            grade_rationales.append(
                {
                    "evidence_id": i + 1,
                    "title": evidence.title,
                    "study_type": study_type,
                    "included_study_type": appraisal.get("included_study_type", "NA"),
                    "initial_grade": initial_grade,
                    "risk_of_bias": appraisal.get("risk_of_bias", "NOT_SERIOUS"),
                    "inconsistency": appraisal.get("inconsistency", "NA"),
                    "indirectness": appraisal.get("indirectness", "NOT_SERIOUS"),
                    "indirectness_source": appraisal.get("indirectness_source", "NA"),
                    "imprecision": appraisal.get("imprecision", "NOT_SERIOUS"),
                    "publication_bias": appraisal.get("publication_bias", "UNDETECTED"),
                    "large_effect": appraisal.get("large_effect", "NA"),
                    "dose_response": appraisal.get("dose_response", "NA"),
                    "confounding_bias_mitigates": appraisal.get("confounding_bias_mitigates", "NA"),
                    "upgrade_blocked_by_bias": (
                        study_type in _UPGRADE_STUDY_TYPES
                        and appraisal.get("risk_of_bias") in ("SERIOUS", "VERY_SERIOUS")
                    ),
                    "computed_grade": computed_grade,
                    "rationale": appraisal.get("rationale", ""),
                    "evidence_role": evidence.evidence_role,
                }
            )

        # --- Conflict assessment ---
        conflict = appraisal_dict.get("conflict_assessment", {})
        has_conflict = conflict.get("conflicts_exist") == "YES"
        conflict_description = (
            conflict.get("conflict_description") if has_conflict else None
        )

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
            "bias_inconsistency": has_conflict
            and conflict.get("conflict_severity") == "MAJOR",
        }
