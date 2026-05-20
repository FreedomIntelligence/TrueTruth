"""
Tests for _compute_grade in appraise_agent.py.

Task 7 spec:
  SR+RCT → High
  SR+OBSERVATIONAL → Low
  COHORT+SERIOUS+all upgrades → Very Low (upgrade blocked by SERIOUS bias)
  COHORT+NOT_SERIOUS+all upgrades → Moderate (cap at min(points, 3))
  CROSS_SECTIONAL+all upgrades → Low (not in _UPGRADE_STUDY_TYPES)
"""
from src.agents.appraise_agent import _compute_grade


def test_sr_rct_high():
    """SR containing RCTs starts at 4 (High) with no downgrades → High."""
    appraisal = {
        "study_type": "SYSTEMATIC_REVIEW",
        "included_study_type": "RCT",
        "risk_of_bias": "NOT_SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "NA",
        "dose_response": "NA",
    }
    assert _compute_grade(appraisal) == "High"


def test_sr_observational_low():
    """SR containing observational studies starts at 2 (Low) with no downgrades → Low."""
    appraisal = {
        "study_type": "SYSTEMATIC_REVIEW",
        "included_study_type": "OBSERVATIONAL",
        "risk_of_bias": "NOT_SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "NA",
        "dose_response": "NA",
    }
    assert _compute_grade(appraisal) == "Low"


def test_cohort_serious_bias_upgrade_blocked():
    """COHORT with SERIOUS risk_of_bias: upgrade factors must be blocked → Very Low."""
    appraisal = {
        "study_type": "COHORT",
        "included_study_type": "NA",
        "risk_of_bias": "SERIOUS",       # -1 → points = 2-1 = 1
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "YES",           # should be blocked
        "dose_response": "YES",          # should be blocked
    }
    assert _compute_grade(appraisal) == "Very Low"


def test_cohort_not_serious_all_upgrades_capped_moderate():
    """COHORT with NOT_SERIOUS bias + both upgrades: cap at min(points, 3) → Moderate."""
    appraisal = {
        "study_type": "COHORT",
        "included_study_type": "NA",
        "risk_of_bias": "NOT_SERIOUS",   # 0 penalty
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "YES",           # +1 → 3
        "dose_response": "YES",          # +1 → 4, but capped at 3
    }
    assert _compute_grade(appraisal) == "Moderate"


def test_cross_sectional_upgrades_not_applied():
    """CROSS_SECTIONAL is not in _UPGRADE_STUDY_TYPES → upgrades ignored → Low."""
    appraisal = {
        "study_type": "CROSS_SECTIONAL",
        "included_study_type": "NA",
        "risk_of_bias": "NOT_SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "YES",           # should be ignored
        "dose_response": "YES",          # should be ignored
    }
    assert _compute_grade(appraisal) == "Low"


def test_cohort_confounding_bias_mitigates_upgrade():
    """confounding_bias_mitigates=YES should trigger +1 upgrade (third upgrade factor)."""
    appraisal = {
        "study_type": "COHORT",
        "risk_of_bias": "NOT_SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "NO",
        "dose_response": "NO",
        "confounding_bias_mitigates": "YES",  # +1
    }
    assert _compute_grade(appraisal) == "Moderate"  # 2+1=3, capped at 3


def test_sr_mixed_moderate():
    """SR with MIXED included studies → initial points 3 → Moderate."""
    appraisal = {
        "study_type": "SYSTEMATIC_REVIEW",
        "included_study_type": "MIXED",
        "risk_of_bias": "NOT_SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
    }
    assert _compute_grade(appraisal) == "Moderate"


def test_cohort_serious_bias_blocks_confounding_upgrade():
    """SERIOUS bias blocks confounding_bias_mitigates=YES upgrade."""
    appraisal = {
        "study_type": "COHORT",
        "risk_of_bias": "SERIOUS",
        "inconsistency": "NOT_SERIOUS",
        "indirectness": "NOT_SERIOUS",
        "imprecision": "NOT_SERIOUS",
        "publication_bias": "UNDETECTED",
        "large_effect": "NO",
        "dose_response": "NO",
        "confounding_bias_mitigates": "YES",
    }
    assert _compute_grade(appraisal) == "Very Low"  # 2-1=1, upgrade blocked
