import pytest
from hypertensiondb.schema.guideline import GuidelineFrontmatter


@pytest.mark.unit
def test_valid_guideline():
    fm = GuidelineFrontmatter(
        id="EV-GL-2024-CHS-001",
        type="GL",
        title={"zh": "中国高血压防治指南2024"},
        authors=["CHS"],
        year=2024,
        language="zh",
        risk_of_bias={"tool": "AGREE-II", "overall": "low"},
        recommendations=[
            {"text": "初始治疗推荐CCB或ARB", "strength": "strong", "grade": "high"}
        ],
    )
    assert len(fm.recommendations) == 1
    assert fm.recommendations[0].strength == "strong"
