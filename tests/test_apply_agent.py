"""Tests for apply_agent helper functions."""
from src.agents.apply_agent import _format_ebm_query, _summarize_downgrade_factors
from src.state.schema import EBMQuery


def test_format_ebm_query_pico():
    q = EBMQuery(query_type="pico", patient="adults with HF",
                 primary_focus="SGLT2i", outcome="mortality",
                 keywords=[], comparator="placebo")
    result = _format_ebm_query(q)
    assert "Patient: adults with HF" in result
    assert "Intervention: SGLT2i" in result
    assert "Comparator: placebo" in result


def test_format_ebm_query_pird():
    q = EBMQuery(query_type="pird", patient="chest pain patients",
                 primary_focus="troponin", outcome="ACS",
                 keywords=[], comparator="ECG",
                 reference_standard="coronary angiography")
    result = _format_ebm_query(q)
    assert "Index Test: troponin" in result
    assert "Reference Standard: coronary angiography" in result


def test_format_ebm_query_none_values_become_na():
    q = EBMQuery(query_type="peo", patient="smokers",
                 primary_focus="smoking", outcome="lung cancer",
                 keywords=[], comparator=None)
    result = _format_ebm_query(q)
    assert "None" not in result


def test_format_ebm_query_prognosis():
    q = EBMQuery(query_type="prognosis", patient="HF patients",
                 primary_focus="EF < 40%", outcome="5-year mortality",
                 keywords=[], time_horizon="5 years")
    result = _format_ebm_query(q)
    assert "Prognostic Factor: EF < 40%" in result
    assert "Time Horizon: 5 years" in result


def test_summarize_downgrade_factors_detects_inconsistency():
    rationales = [
        {"inconsistency": "SERIOUS", "risk_of_bias": "NOT_SERIOUS",
         "indirectness": "NOT_SERIOUS", "imprecision": "NOT_SERIOUS"},
    ]
    result = _summarize_downgrade_factors(rationales)
    assert result["has_serious_inconsistency"] is True


def test_summarize_downgrade_factors_no_issues():
    rationales = [
        {"inconsistency": "NOT_SERIOUS", "risk_of_bias": "NOT_SERIOUS",
         "indirectness": "NOT_SERIOUS", "imprecision": "NOT_SERIOUS"},
    ]
    result = _summarize_downgrade_factors(rationales)
    assert result["has_serious_inconsistency"] is False


def test_summarize_downgrade_factors_counts_multiple():
    rationales = [
        {"inconsistency": "SERIOUS", "risk_of_bias": "SERIOUS",
         "indirectness": "NOT_SERIOUS", "imprecision": "NOT_SERIOUS"},
        {"inconsistency": "NOT_SERIOUS", "risk_of_bias": "NOT_SERIOUS",
         "indirectness": "NOT_SERIOUS", "imprecision": "NOT_SERIOUS"},
    ]
    result = _summarize_downgrade_factors(rationales)
    assert result["has_serious_inconsistency"] is True
    # key_downgrade_factors is a human-readable string; verify it's non-empty
    assert result["key_downgrade_factors"] != "无主要降级因素"
    assert len(result["key_downgrade_factors"]) > 0
