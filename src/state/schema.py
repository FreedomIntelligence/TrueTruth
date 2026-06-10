from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PICOQuery:
    """Structured clinical question in PICO format"""

    patient: str
    intervention: str
    comparison: str
    outcome: str
    keywords: List[str]


@dataclass
class EBMQuery:
    """Structured clinical question supporting multiple EBM query frameworks"""

    query_type: str  # "pico" | "pird" | "peo" | "prognosis" | "diagnostic_reasoning"
    patient: str
    primary_focus: str  # intervention / index_test / exposure / prognostic_factor
    outcome: str
    keywords: List[str]
    comparator: Optional[str] = None  # comparison / reference_standard (PICO/PIRD)
    reference_standard: Optional[str] = None  # gold standard for diagnostic questions
    time_horizon: Optional[str] = None  # relevant for prognosis questions


@dataclass
class Passage:
    """A supporting passage retrieved from a paper.

    Sourced from hypertensiondb /search chunk-level results.  Multiple
    passages from the same paper are grouped under one Evidence object.
    """

    section: str        # e.g. "结果/主要结局"
    snippet: str        # <= 800 chars
    score: float        # rerank_score from /search
    filter_label: Optional[str] = None    # RELEVANT / TANGENTIAL / IRRELEVANT (None = unfiltered)
    filter_reason: Optional[str] = None   # reason string when TANGENTIAL


@dataclass
class Evidence:
    """A paper of evidence with its supporting passages.

    Acquire fills evidence_id / title / year / language / tags /
    supporting_passages / relevance_score from the hypertensiondb /search
    response.

    Appraise fills study_type / grade_level / rob_overall after appraising
    the paper.
    """

    title: str
    source: str                                       # "hypertensiondb"
    relevance_score: float                            # = max(passage.score) within paper

    # Filled by Acquire from hypertensiondb /search response:
    evidence_id: Optional[str] = None                 # e.g. EV-RCT-2026-PENG-001
    supporting_passages: List[Passage] = field(default_factory=list)
    language: str = ""                                # zh | en | bilingual
    tags: List[str] = field(default_factory=list)
    year: Optional[int] = None

    # Bibliographic metadata (best-effort, fetched from /evidence/{id} detail
    # endpoint; empty when the detail lookup is unavailable). Used only to
    # render human-readable numbered references in the user-facing output.
    authors: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    # Filled by Appraise:
    study_type: Optional[str] = None
    grade_level: Optional[str] = None                 # very_low | low | moderate | high
    rob_overall: Optional[str] = None                 # low | some_concerns | high
    publication_date: Optional[str] = None            # legacy; safe to leave None
    evidence_role: Optional[str] = None               # core_direct | supportive_indirect | safety_only


@dataclass
class AppraisalResults:
    """Results from evidence appraisal"""

    evidence: List[Evidence]
    has_conflict: bool
    conflict_description: Optional[str]
    summary: str


@dataclass
class Recommendation:
    """Clinical recommendation"""

    text: str
    strength: str
    rationale: str
    caveats: List[str]
    evidence_quality: str
    has_core_direct: bool = False


@dataclass
class Assessment:
    """Quality assessment of recommendation"""

    quality_score: float
    gaps: List[str]
    needs_backtrack: bool
    backtrack_reason: Optional[str]


@dataclass
class OutcomeCoverage:
    """Coverage status for a single PICO outcome across retrieved evidence."""

    outcome: str
    status: str          # COVERED / PARTIAL / NOT_COVERED
    evidence_ids: List[str] = field(default_factory=list)
    note: Optional[str] = None


@dataclass
class GapSearch:
    """Suggested PubMed search strategy for an uncovered outcome."""

    outcome: str
    pubmed_query: str
    rationale: str


@dataclass
class Issue:
    """Single issue identified in evaluation"""

    severity: str  # "critical" | "major" | "minor"
    dimension: str
    description: str


@dataclass
class Evaluation:
    """Evaluation results from Judge LLM"""

    overall_score: float  # 0.0-1.0
    dimension_scores: Dict[str, float]  # dimension_name -> score (0.0-1.0)
    pass_threshold: bool
    issues: List[Issue]
    summary: str
    search_exhausted: bool = (
        False  # True when search is thorough but genuinely no relevant evidence exists
    )


@dataclass
class Observe:
    """Observation after stage execution"""

    stage: str
    output: Dict[str, Any]
    evaluation: Evaluation


@dataclass
class SchedulingDecision:
    """Decision made by scheduling LLM"""

    reasoning: str
    action: str  # "proceed" | "backtrack_to_X" | "retry_current" | "terminate" | "request_human_review"
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class HumanInterventionRequest:
    """Request for human review"""

    review_scope: str  # "numerical_data" | "bias_assessment" | "evidence_conflict" | "final_recommendation" | "ethical_consideration"
    reason: str
    context: Dict[str, Any]
    resume_after_review: bool
    timestamp: datetime


@dataclass
class GateTrigger:
    """Gate trigger information"""

    gate_name: str
    reason: str
    suggested_action: str
    output_message: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionNode:
    """Node in execution graph"""

    id: str
    agent_type: str
    timestamp: datetime
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    tools_used: List[str]
    gate_triggered: Optional[str]
    status: str
    observe: Optional[Observe] = None
    scheduling_decision: Optional[SchedulingDecision] = None


class WorkflowState(TypedDict):
    """Main state for the workflow"""

    original_question: str
    current_step: str
    iteration_count: int
    agent_call_counts: Dict[str, int]
    pico_query: Optional[PICOQuery]
    evidence_list: Optional[List[Evidence]]
    # Grounded DRUG_SAFETY label evidence (openFDA), retrieved by a separate
    # type=DRUGSAFETY sub-query. Kept distinct from evidence_list so Appraise/
    # GRADE never grades a regulatory label as a study; consumed by Apply to
    # fill the SmPC-structured safety section with cited facts.
    safety_evidence: Optional[List[Evidence]]
    appraisal_results: Optional[AppraisalResults]
    recommendation: Optional[Recommendation]
    assessment: Optional[Assessment]
    gate_triggered: Optional[str]
    backtrack_reason: Optional[str]
    should_terminate: bool
    execution_history: List[ExecutionNode]
    observe_history: List[Observe]
    decision_history: List[SchedulingDecision]
    backtrack_history: List[Dict[str, Any]]
    human_intervention_requests: List[HumanInterventionRequest]
    remaining_budget: int
    soft_gate_signals: List[str]
    question_type: Optional[str]
    route_type: Optional[str]
    route_confidence: Optional[float]
    direct_answer_output: Optional[Dict[str, Any]]
    ebm_query: Optional[EBMQuery]
    sub_pico_queries: Optional[List[EBMQuery]]
    sub_question_index: Optional[int]
    sub_question_total: Optional[int]
    # NEW: hypertension RAG refactor
    out_of_domain: Optional[bool]       # True when Ask soft-rejected non-hypertension question
    rag_degraded: Optional[List[str]]   # degradation tags from /search response
    # Evidence coverage analysis (Phase 2)
    outcome_coverage: Optional[List[Any]]   # List[OutcomeCoverage] from Apply
    gap_searches: Optional[List[Any]]       # List[GapSearch] from Apply
    passage_filter_stats: Optional[Dict[str, Any]]  # stats from LLM passage filter
