import pytest
from unittest.mock import MagicMock, patch

from hypertensiondb.retrieval.hybrid import Candidate


def _cand(pid="p1", text="降压效果"):
    return Candidate(
        point_id=pid, rrf_score=0.5,
        evidence_id="EV-RCT-2026-X-001", section_name="results",
        text=text, payload={"text": text},
    )


@pytest.mark.unit
def test_bge_reranker_model_name():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    r = BGEReranker(model_name="BAAI/bge-reranker-v2-m3")
    assert r.model_name == "BAAI/bge-reranker-v2-m3"


@pytest.mark.unit
def test_bge_reranker_lazy_loads_model():
    """Model is only loaded on first rerank() call, not at construction."""
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    with patch("hypertensiondb.retrieval.reranker_bge.BGEReranker._load_model") as m:
        BGEReranker()
        m.assert_not_called()


@pytest.mark.unit
def test_bge_reranker_rerank_sorts_descending():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker

    fake_model = MagicMock()
    fake_model.compute_score.return_value = [0.2, 0.9, 0.5]

    r = BGEReranker()
    with patch.object(r, "_get_model", return_value=fake_model):
        cands = [_cand("p1"), _cand("p2"), _cand("p3")]
        out = r.rerank("查询", cands)

    assert [c.point_id for c, _ in out] == ["p2", "p3", "p1"]
    assert [score for _, score in out] == [0.9, 0.5, 0.2]


@pytest.mark.unit
def test_bge_reranker_empty_input():
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    r = BGEReranker()
    assert r.rerank("q", []) == []


@pytest.mark.unit
def test_bge_reranker_handles_single_score_return():
    """FlagReranker returns a scalar instead of list when given 1 pair."""
    from hypertensiondb.retrieval.reranker_bge import BGEReranker
    fake_model = MagicMock()
    fake_model.compute_score.return_value = 0.77
    r = BGEReranker()
    with patch.object(r, "_get_model", return_value=fake_model):
        out = r.rerank("q", [_cand("p1")])
    assert len(out) == 1
    assert out[0][1] == 0.77
