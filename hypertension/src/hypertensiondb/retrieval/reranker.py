from abc import ABC, abstractmethod

from hypertensiondb.retrieval.hybrid import Candidate


class BaseReranker(ABC):
    """Abstract interface for rerankers.

    Implementations return (candidate, rerank_score) pairs sorted descending
    by rerank_score. The original RRF score is preserved on Candidate.rrf_score.
    """

    @abstractmethod
    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
