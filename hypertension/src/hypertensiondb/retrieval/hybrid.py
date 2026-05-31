from dataclasses import dataclass
from typing import Optional, Any

from qdrant_client import QdrantClient, models as qm

_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"


@dataclass
class Candidate:
    point_id: Any
    rrf_score: float
    evidence_id: str
    section_name: str
    text: str
    payload: dict


class HybridSearcher:
    """Hybrid dense + sparse search using Qdrant Query API with RRF fusion."""

    def __init__(self, qdrant: QdrantClient, collection_name: str) -> None:
        self._q = qdrant
        self._collection = collection_name

    def search(
        self,
        dense_vector: list[float],
        sparse_indices: list[int],
        sparse_values: list[float],
        limit: int,
        prefetch_limit: int,
        query_filter: Optional[qm.Filter],
    ) -> list[Candidate]:
        prefetch: list[qm.Prefetch] = [
            qm.Prefetch(
                query=dense_vector, using=_DENSE_VECTOR_NAME, limit=prefetch_limit
            ),
        ]
        if sparse_indices and sparse_values:
            prefetch.append(qm.Prefetch(
                query=qm.SparseVector(indices=sparse_indices, values=sparse_values),
                using=_SPARSE_VECTOR_NAME,
                limit=prefetch_limit,
            ))

        response = self._q.query_points(
            collection_name=self._collection,
            prefetch=prefetch,
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )

        candidates: list[Candidate] = []
        for p in response.points:
            payload = p.payload or {}
            candidates.append(Candidate(
                point_id=p.id,
                rrf_score=float(p.score),
                evidence_id=payload.get("evidence_id", ""),
                section_name=payload.get("section_name", ""),
                text=payload.get("text", ""),
                payload=payload,
            ))
        return candidates
