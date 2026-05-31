import hashlib
import struct
from hypertensiondb.index.embedder import BaseEmbedder


class MockEmbedder(BaseEmbedder):
    """Deterministic mock embedder for tests. No API calls."""

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(t) for t in texts]

    def _text_to_vector(self, text: str) -> list[float]:
        """Derive a deterministic float vector from text via SHA-256."""
        digest = hashlib.sha256(text.encode()).digest()
        floats = []
        for i in range(self._dim):
            byte_offset = (i * 4) % len(digest)
            chunk = digest[byte_offset:byte_offset + 4]
            if len(chunk) < 4:
                chunk = chunk + digest[:4 - len(chunk)]
            (value,) = struct.unpack(">I", chunk)
            floats.append(value / 0xFFFFFFFF)
        return floats

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "mock"
