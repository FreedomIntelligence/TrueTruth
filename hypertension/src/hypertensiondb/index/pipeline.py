from pathlib import Path

from hypertensiondb.index.chunker import split_evidence_into_chunks
from hypertensiondb.index.embedder import BaseEmbedder
from hypertensiondb.index.sparse import SparseVectorizer
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.schema.base import Status

_INDEXABLE_STATUSES = {Status.REVIEWED, Status.PUBLISHED}


class IndexPipeline:
    """Orchestrate: chunk -> embed -> sparse -> upsert."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        sparse_vectorizer: SparseVectorizer,
        qdrant_client: QdrantIndexClient,
        collection_name: str,
    ) -> None:
        self._embedder = embedder
        self._sparse = sparse_vectorizer
        self._qdrant = qdrant_client
        self._collection = collection_name
        self._qdrant.ensure_collection(dense_dim=self._embedder.dimension)

    def index_file(self, path: Path) -> int:
        """Index all chunks from one evidence file. Returns chunk count (0 if skipped)."""
        chunks = split_evidence_into_chunks(path)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        dense_vectors = self._embedder.embed(texts)
        sparse_vectors = [self._sparse.vectorize(t) for t in texts]
        self._qdrant.upsert_chunks(chunks, dense_vectors, sparse_vectors)
        return len(chunks)

    def rebuild(self, evidence_root: Path) -> int:
        """Delete + recreate collection, then index all reviewed/published files."""
        self._qdrant.delete_collection()
        self._qdrant.ensure_collection(dense_dim=self._embedder.dimension)
        total = 0
        failed = 0
        files = sorted(evidence_root.rglob("*.md"))
        files = [f for f in files if "_quarantine" not in f.parts]
        for i, md in enumerate(files, 1):
            try:
                n = self.index_file(md)
                total += n
                if i % 20 == 0 or i == len(files):
                    print(f"[INDEX] {i}/{len(files)} files  {total} chunks  ({failed} failed)", flush=True)
            except Exception as e:
                failed += 1
                print(f"[WARN] Failed to index {md.name}: {e}")
        if failed:
            print(f"[WARN] {failed}/{len(files)} files failed to index")
        return total
