from datetime import datetime, timezone
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseIndexParams,
    PointStruct, SparseVector,
)

from hypertensiondb.index.chunk import EvidenceChunk

_DENSE_VECTOR_NAME = "dense"
_SPARSE_VECTOR_NAME = "sparse"
_BATCH_SIZE = 64


class QdrantIndexClient:
    """Thin wrapper around QdrantClient focused on evidence indexing operations."""

    def __init__(self, qdrant: QdrantClient, collection_name: str) -> None:
        self._q = qdrant
        self._collection = collection_name

    def ensure_collection(self, dense_dim: int) -> None:
        """Create collection if it doesn't exist."""
        if self._q.collection_exists(self._collection):
            return
        self._q.create_collection(
            collection_name=self._collection,
            vectors_config={
                _DENSE_VECTOR_NAME: VectorParams(
                    size=dense_dim, distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                _SPARSE_VECTOR_NAME: SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            },
        )

    def upsert_chunks(
        self,
        chunks: list[EvidenceChunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[tuple[list[int], list[float]]],
    ) -> None:
        """Upsert chunks with both dense and sparse vectors in batches."""
        now = datetime.now(timezone.utc).isoformat()
        points = []
        for chunk, dense, (sp_indices, sp_values) in zip(chunks, dense_vectors, sparse_vectors):
            payload = {
                **chunk.metadata,
                "evidence_id": chunk.evidence_id,
                "section_name": chunk.section_name,
                "text": chunk.text,
                "is_clinical_bottom_line": chunk.is_clinical_bottom_line,
                "indexed_at": now,
            }
            points.append(PointStruct(
                id=chunk.point_id,
                vector={
                    _DENSE_VECTOR_NAME: dense,
                    _SPARSE_VECTOR_NAME: SparseVector(
                        indices=sp_indices, values=sp_values
                    ),
                },
                payload=payload,
            ))

        for i in range(0, len(points), _BATCH_SIZE):
            self._q.upsert(
                collection_name=self._collection,
                points=points[i:i + _BATCH_SIZE],
            )

    def get_evidence_indexed_at(self, evidence_id: str) -> Optional[str]:
        """Return the indexed_at ISO string for the given evidence_id, or None."""
        results, _ = self._q.scroll(
            collection_name=self._collection,
            scroll_filter={"must": [{"key": "evidence_id", "match": {"value": evidence_id}}]},
            limit=1,
            with_payload=["indexed_at"],
        )
        if results:
            return results[0].payload.get("indexed_at")
        return None

    def delete_collection(self) -> None:
        """Delete the collection if it exists."""
        if self._q.collection_exists(self._collection):
            self._q.delete_collection(collection_name=self._collection)
