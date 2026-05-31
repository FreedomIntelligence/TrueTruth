import pytest
from hypertensiondb.schema.rct import RctFrontmatter
from hypertensiondb.schema.base import EvidenceType


def _base_rct_data() -> dict:
    return {
        "id": "EV-RCT-2026-PENG-001",
        "type": "RCT",
        "title": {"zh": "测试RCT"},
        "authors": ["Peng Y"],
        "year": 2026,
        "language": "zh",
        "pico": {
            "population": {"condition": "原发性高血压", "sample_size": 612},
            "intervention": {"name": "缬沙坦 + 氨氯地平"},
            "outcomes": {"primary": [], "secondary": []},
        },
        "risk_of_bias": {"tool": "RoB2", "overall": "low"},
        "grade": {"level": "moderate"},
    }


@pytest.mark.unit
def test_valid_rct():
    fm = RctFrontmatter(**_base_rct_data())
    assert fm.type == EvidenceType.RCT
    assert fm.pico.population.sample_size == 612


@pytest.mark.unit
def test_rct_type_must_be_rct():
    data = _base_rct_data()
    data["type"] = "SR"
    with pytest.raises(Exception):
        RctFrontmatter(**data)


@pytest.mark.unit
def test_rct_draft_allowed_without_review():
    data = _base_rct_data()
    data["status"] = "draft"
    fm = RctFrontmatter(**data)
    assert fm.reviewed_by is None
