import pytest
from hypertensiondb.schema.sr_meta import SrFrontmatter, MetaFrontmatter


def _base_sr() -> dict:
    return {
        "id": "EV-SR-2024-ZHANG-001",
        "type": "SR",
        "title": {"zh": "系统评价示例"},
        "authors": ["Zhang W"],
        "year": 2024,
        "language": "zh",
        "pico": {
            "population": {"condition": "高血压"},
            "intervention": {"name": "ARB"},
            "outcomes": {},
        },
        "risk_of_bias": {"tool": "AMSTAR2", "overall": "low"},
        "grade": {"level": "high"},
        "included_studies": ["10.1000/xyz123"],
    }


@pytest.mark.unit
def test_valid_sr():
    fm = SrFrontmatter(**_base_sr())
    assert fm.included_studies == ["10.1000/xyz123"]


@pytest.mark.unit
def test_valid_meta():
    data = _base_sr()
    data["id"] = "EV-META-2024-ZHANG-001"
    data["type"] = "META"
    data["heterogeneity"] = {"i_squared": 45.2, "q_p": 0.03}
    fm = MetaFrontmatter(**data)
    assert fm.heterogeneity["i_squared"] == 45.2
