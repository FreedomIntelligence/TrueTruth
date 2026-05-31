import pytest
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType, Language, Status


@pytest.mark.unit
def test_valid_base_minimal():
    fm = BaseFrontmatter(
        id="EV-RCT-2026-PENG-001",
        type=EvidenceType.RCT,
        title={"zh": "测试标题", "en": "Test title"},
        authors=["Peng Y"],
        year=2026,
        language=Language.ZH,
    )
    assert fm.id == "EV-RCT-2026-PENG-001"
    assert fm.status == Status.DRAFT


@pytest.mark.unit
def test_id_must_match_pattern():
    with pytest.raises(Exception):
        BaseFrontmatter(
            id="bad-id",
            type=EvidenceType.RCT,
            title={"zh": "标题"},
            authors=["Peng Y"],
            year=2026,
            language=Language.ZH,
        )


@pytest.mark.unit
def test_year_range():
    with pytest.raises(Exception):
        BaseFrontmatter(
            id="EV-RCT-2026-PENG-001",
            type=EvidenceType.RCT,
            title={"zh": "标题"},
            authors=["Peng Y"],
            year=1800,
            language=Language.ZH,
        )
