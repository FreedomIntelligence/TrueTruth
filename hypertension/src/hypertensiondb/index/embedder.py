from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of float vectors."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""
