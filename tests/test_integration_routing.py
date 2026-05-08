"""
Integration tests for AskAgent routing logic using mock LLM.

Tests:
  1. direct_answer route → should_terminate=True, direct_answer_output non-empty
  2. ebm_pico route → ebm_query.query_type == "pico", pico_query compat fields present
  3. ebm_pird route → ebm_query.query_type == "pird"
  4. Legacy pico_query compat → pico_query fields accessible after full_pipeline
"""

import json
import pytest
from unittest.mock import MagicMock
from src.agents.ask_agent import AskAgent
from src.state.schema import WorkflowState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm(*responses: str) -> MagicMock:
    """Return a mock LLM that yields responses in order."""
    llm = MagicMock()
    side_effects = [MagicMock(content=r) for r in responses]
    llm.invoke.side_effect = side_effects
    return llm


def _base_state(question: str) -> WorkflowState:
    return WorkflowState(
        original_question=question,
        current_step="Ask",
        iteration_count=0,
        agent_call_counts={},
        pico_query=None,
        evidence_list=None,
        appraisal_results=None,
        recommendation=None,
        assessment=None,
        gate_triggered=None,
        backtrack_reason=None,
        should_terminate=False,
        execution_history=[],
        observe_history=[],
        decision_history=[],
        backtrack_history=[],
        human_intervention_requests=[],
        remaining_budget=20,
        soft_gate_signals=[],
        question_type=None,
        route_type=None,
        route_confidence=None,
        direct_answer_output=None,
        ebm_query=None,
        sub_pico_queries=None,
        sub_question_index=None,
        sub_question_total=None,
    )


# ---------------------------------------------------------------------------
# 1. direct_answer route
# ---------------------------------------------------------------------------

def test_direct_answer_route_sets_terminate():
    """direct_answer route → should_terminate=True, direct_answer_output non-empty."""
    router_json = json.dumps({
        "route_type": "direct_answer",
        "route_confidence": 0.95,
        "question_type": "Therapy",
        "ebm_framework": "pico",
        "routing_rationale": "Immediate life-threatening situation",
    })
    direct_answer_json = json.dumps({
        "answer": "Call 911 immediately and start CPR.",
        "requires_pipeline": False,
    })

    llm = _make_llm(router_json, direct_answer_json)
    agent = AskAgent(llm=llm)
    state = _base_state("Patient is in cardiac arrest, what do I do?")

    result = agent.execute(state)

    assert result["route_type"] == "direct_answer"
    assert result["should_terminate"] is True
    assert result["direct_answer_output"] is not None
    assert result["direct_answer_output"].get("answer")


# ---------------------------------------------------------------------------
# 2. ebm_pico route → ebm_query.query_type == "pico"
# ---------------------------------------------------------------------------

def test_full_pipeline_pico_route():
    """full_pipeline with ebm_pico framework → ebm_query.query_type == 'pico'."""
    router_json = json.dumps({
        "route_type": "full_pipeline",
        "route_confidence": 0.9,
        "question_type": "Therapy",
        "ebm_framework": "pico",
        "routing_rationale": "Standard therapy question",
    })
    pico_json = json.dumps({
        "query_type": "pico",
        "patient": "Adults with type 2 diabetes",
        "primary_focus": "SGLT2 inhibitors",
        "outcome": "HbA1c reduction",
        "keywords": ["SGLT2", "diabetes", "HbA1c"],
        "comparator": "placebo",
    })

    llm = _make_llm(router_json, pico_json)
    agent = AskAgent(llm=llm)
    state = _base_state("Do SGLT2 inhibitors reduce HbA1c in type 2 diabetes?")

    result = agent.execute(state)

    assert result["route_type"] == "full_pipeline"
    assert result["should_terminate"] is False
    assert result["ebm_query"] is not None
    assert result["ebm_query"].query_type == "pico"
    # Legacy compat: pico_query must be present with required fields
    assert result["pico_query"] is not None
    assert result["pico_query"].patient == "Adults with type 2 diabetes"
    assert result["pico_query"].intervention == "SGLT2 inhibitors"


# ---------------------------------------------------------------------------
# 3. ebm_pird route → ebm_query.query_type == "pird"
# ---------------------------------------------------------------------------

def test_full_pipeline_pird_route():
    """full_pipeline with ebm_pird framework → ebm_query.query_type == 'pird'.

    Diagnosis questions run diag_step1 before the PIRD prompt, so we need
    three LLM responses: router → diag_step1 → pird.
    """
    router_json = json.dumps({
        "route_type": "full_pipeline",
        "route_confidence": 0.85,
        "question_type": "Diagnosis",
        "ebm_framework": "pird",
        "routing_rationale": "Diagnostic accuracy question",
    })
    diag_step1_json = json.dumps({
        "diagnostic_type": "accuracy",
        "index_test": "CT pulmonary angiography",
        "reference_standard": "V/Q scan",
    })
    pird_json = json.dumps({
        "query_type": "pird",
        "patient": "Adults with suspected PE",
        "primary_focus": "CT pulmonary angiography",
        "outcome": "PE diagnosis confirmed",
        "keywords": ["CTPA", "pulmonary embolism", "diagnosis"],
        "reference_standard": "V/Q scan",
    })

    llm = _make_llm(router_json, diag_step1_json, pird_json)
    agent = AskAgent(llm=llm)
    state = _base_state("How accurate is CTPA for diagnosing pulmonary embolism?")

    result = agent.execute(state)

    assert result["route_type"] == "full_pipeline"
    assert result["ebm_query"] is not None
    assert result["ebm_query"].query_type == "pird"
    assert result["ebm_query"].reference_standard == "V/Q scan"


# ---------------------------------------------------------------------------
# 4. Legacy pico_query compat — pico_query fields accessible after full_pipeline
# ---------------------------------------------------------------------------

def test_pico_query_compat_fields_present():
    """After full_pipeline, pico_query has all legacy fields (patient, intervention, comparison, outcome, keywords)."""
    router_json = json.dumps({
        "route_type": "full_pipeline",
        "route_confidence": 0.88,
        "question_type": "Therapy",
        "ebm_framework": "pico",
    })
    pico_json = json.dumps({
        "query_type": "pico",
        "patient": "Children with asthma",
        "primary_focus": "Inhaled corticosteroids",
        "outcome": "Exacerbation rate",
        "keywords": ["ICS", "asthma", "children"],
        "comparator": "LABA",
    })

    llm = _make_llm(router_json, pico_json)
    agent = AskAgent(llm=llm)
    state = _base_state("Are inhaled corticosteroids effective in children with asthma?")

    result = agent.execute(state)

    pq = result["pico_query"]
    assert pq is not None
    assert pq.patient == "Children with asthma"
    assert pq.intervention == "Inhaled corticosteroids"
    assert pq.comparison == "LABA"
    assert pq.outcome == "Exacerbation rate"
    assert "ICS" in pq.keywords
