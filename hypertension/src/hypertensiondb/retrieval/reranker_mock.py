from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker import BaseReranker


class MockReranker(BaseReranker):
    """No-op reranker: sorts candidates by rrf_score descending, uses rrf as rerank score."""

    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        sorted_cands = sorted(candidates, key=lambda c: c.rrf_score, reverse=True)
        return [(c, c.rrf_score) for c in sorted_cands]

    @property
    def model_name(self) -> str:
        return "mock"
