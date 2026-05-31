import pytest
from hypertensiondb.schema.tcm import TcmFrontmatter


@pytest.mark.unit
def test_valid_tcm():
    fm = TcmFrontmatter(
        id="EV-TCM-2023-CHEN-001",
        type="TCM",
        title={"zh": "半夏白术天麻汤治疗痰湿壅盛型高血压RCT"},
        authors=["Chen L"],
        year=2023,
        language="zh",
        pico={
            "population": {"condition": "痰湿壅盛型高血压", "sample_size": 80},
            "intervention": {"name": "半夏白术天麻汤"},
            "outcomes": {},
        },
        risk_of_bias={"tool": "RoB2", "overall": "some_concerns"},
        grade={"level": "low"},
        tcm_syndrome={"pattern": "痰湿壅盛", "formula": "半夏白术天麻汤"},
    )
    assert fm.tcm_syndrome["pattern"] == "痰湿壅盛"
