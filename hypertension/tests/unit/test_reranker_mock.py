import pytest
from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker_mock import MockReranker


def _make_cand(point_id, text, rrf=0.5):
    return Candidate(
        point_id=point_id, rrf_score=rrf,
        evidence_id="EV-RCT-2026-X-001", section_name="results",
        text=text, payload={"text": text, "section_name": "results"},
    )


@pytest.mark.unit
def test_mock_reranker_returns_same_count():
    r = MockReranker()
    cands = [_make_cand("p1", "甲"), _make_cand("p2", "乙"), _make_cand("p3", "丙")]
    out = r.rerank("query", cands)
    assert len(out) == 3


@pytest.mark.unit
def test_mock_reranker_preserves_order_by_rrf():
    r = MockReranker()
    cands = [
        _make_cand("p1", "甲", rrf=0.3),
        _make_cand("p2", "乙", rrf=0.9),
        _make_cand("p3", "丙", rrf=0.6),
    ]
    out = r.rerank("query", cands)
    assert [o.point_id for o, _ in out] == ["p2", "p3", "p1"]


@pytest.mark.unit
def test_mock_reranker_returns_tuples_with_score():
    r = MockReranker()
    cands = [_make_cand("p1", "x")]
    out = r.rerank("query", cands)
    assert len(out) == 1
    cand, score = out[0]
    assert cand.point_id == "p1"
    assert isinstance(score, float)


@pytest.mark.unit
def test_mock_reranker_empty_input():
    r = MockReranker()
    assert r.rerank("q", []) == []


@pytest.mark.unit
def test_mock_reranker_model_name():
    assert MockReranker().model_name == "mock"
