from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass
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
class Evidence:
    """Single piece of evidence"""

    title: str
    source: str
    pmid: Optional[str]
    abstract: str
    relevance_score: float
    study_type: Optional[str] = None
    publication_date: Optional[str] = None
    grade_level: Optional[str] = None
    pmcid: Optional[str] = None  # PMC article ID (local DB only)
    full_text: Optional[str] = None  # Full text (local DB only, not passed to prompts)
    key_sentences: Optional[str] = None  # Extracted span(s) relevant to query keywords
    has_full_text: bool = False  # True when full_text field is populated
    pub_types: Optional[List[str]] = None  # PubMed publication types (e.g. ["Randomized Controlled Trial"])


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


@dataclass
class Assessment:
    """Quality assessment of recommendation"""

    quality_score: float
    gaps: List[str]
    needs_backtrack: bool
    backtrack_reason: Optional[str]


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
    route_type: Optional[str]  # "direct_answer" | "full_pipeline" | "sub_questions"
    route_confidence: Optional[float]  # 0.0-1.0 confidence in routing decision
    direct_answer_output: Optional[Dict[str, Any]]  # populated when route_type == "direct_answer"
    ebm_query: Optional[EBMQuery]  # structured query replacing/extending pico_query
    sub_pico_queries: Optional[List[EBMQuery]]  # decomposed sub-questions
    sub_question_index: Optional[int]  # current sub-question being processed (0-based)
    sub_question_total: Optional[int]  # total number of sub-questions
