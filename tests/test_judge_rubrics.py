"""
Tests for judge_llm.py Gate + Rubrics scoring system.

Covers:
  1. Gate failure → _score_ask returns score 0.0 and critical issue
  2. Gate pass + all YES rubrics → score 1.0
  3. _check_gates("Ask", intent_distorted) → returns failure
  4. _check_gates("Apply", recommendation_not_grounded) → returns failure
  5. All YES rubric_results → _score_rubrics returns overall 1.0
"""

import pytest
from src.judge.judge_llm import _check_gates, _score_rubrics, _score_ask, RUBRIC_WEIGHTS


# ---------------------------------------------------------------------------
# 1. Gate failure → _score_ask returns 0.0 with critical issue
# ---------------------------------------------------------------------------

def test_score_ask_gate_failure_returns_zero():
    """When intent_not_distorted gate fails, _score_ask returns 0.0 score."""
    audit = {
        "gate_results": {
            "intent_not_distorted": "NO",   # gate failure
            "route_correct": "YES",
            "nonresearch_classification_correct": "NA",
        },
        "rubric_results": {
            "core_dimensions_present": "YES",
            "secondary_dimensions_present": "YES",
            "statement_unambiguous": "YES",
        },
        "failures": ["intent_not_distorted"],
        "overall_quality": "gate_fail",
    }
    dim_scores, issues, search_exhausted, hint = _score_ask(audit)

    # At least one critical issue must be present
    assert any(i["severity"] == "critical" for i in issues), "Expected critical issue on gate failure"
    # The dimension score for the failed gate should be 0.0
    assert list(dim_scores.values())[0] == 0.0, "Expected 0.0 score on gate failure"


# ---------------------------------------------------------------------------
# 2. Gate pass + all YES rubrics → score 1.0
# ---------------------------------------------------------------------------

def test_score_ask_all_yes_returns_one():
    """When all gates pass and all rubrics are YES, _score_ask returns overall 1.0."""
    audit = {
        "gate_results": {
            "intent_not_distorted": "YES",
            "route_correct": "YES",
            "nonresearch_classification_correct": "NA",
        },
        "rubric_results": {
            "core_dimensions_present": "YES",
            "secondary_dimensions_present": "YES",
            "statement_unambiguous": "YES",
        },
        "failures": [],
        "overall_quality": "pass",
    }
    dim_scores, issues, search_exhausted, hint = _score_ask(audit)

    assert issues == [], f"Expected no issues, got: {issues}"
    # All dimension scores should be 1.0
    for k, v in dim_scores.items():
        if v is not None:
            assert v == 1.0, f"Expected 1.0 for {k}, got {v}"


# ---------------------------------------------------------------------------
# 3. _check_gates("Ask", intent_distorted=YES) → returns failure list
# ---------------------------------------------------------------------------

def test_check_gates_ask_intent_distorted():
    """_check_gates returns 'intent_not_distorted' when that gate is NO."""
    audit = {
        "gate_results": {
            "intent_not_distorted": "NO",
            "route_correct": "YES",
            "nonresearch_classification_correct": "NA",
        }
    }
    failures = _check_gates("Ask", audit)
    assert "intent_not_distorted" in failures


# ---------------------------------------------------------------------------
# 4. _check_gates("Apply", recommendation_not_grounded) → returns failure
# ---------------------------------------------------------------------------

def test_check_gates_apply_not_grounded():
    """_check_gates returns 'recommendation_grounded_in_evidence' when that gate is NO."""
    audit = {
        "gate_results": {
            "recommendation_grounded_in_evidence": "NO",
            "route_dimension_consistent": "YES",
            "strength_not_grossly_inflated": "YES",
        }
    }
    failures = _check_gates("Apply", audit)
    assert "recommendation_grounded_in_evidence" in failures


# ---------------------------------------------------------------------------
# 5. All YES rubric_results → _score_rubrics returns overall 1.0
# ---------------------------------------------------------------------------

def test_score_rubrics_all_yes_returns_one():
    """_score_rubrics returns overall score 1.0 when all rubrics are YES."""
    # Build an audit with all Ask rubrics set to YES
    rubric_results = {k: "YES" for k in RUBRIC_WEIGHTS["Ask"]}
    audit = {"rubric_results": rubric_results}

    dim_scores, issues, overall = _score_rubrics("Ask", audit)

    assert overall == pytest.approx(1.0), f"Expected 1.0, got {overall}"
    assert issues == [], f"Expected no issues, got: {issues}"


# ---------------------------------------------------------------------------
# Bonus: PARTIAL rubric gives 0.5 weight
# ---------------------------------------------------------------------------

def test_score_rubrics_partial_gives_half():
    """A PARTIAL rubric result contributes 0.5 × weight to the score."""
    # Only one rubric, set to PARTIAL
    audit = {
        "rubric_results": {
            "core_dimensions_present": "PARTIAL",   # weight=3, allows_partial=True
            "secondary_dimensions_present": "NA",
            "statement_unambiguous": "NA",
        }
    }
    dim_scores, issues, overall = _score_rubrics("Ask", audit)

    # score = 3*0.5 / 3 = 0.5
    assert overall == pytest.approx(0.5), f"Expected 0.5, got {overall}"
    assert dim_scores["core_dimensions_present"] == pytest.approx(0.5)
