import os

import openai
from hypertensiondb.index.embedder import BaseEmbedder

# The ``openai.embeddings`` symbol is a lazy proxy that constructs a default
# global client on first attribute access; that construction fails unless an
# API key is available somewhere. Ensure a placeholder is present at import
# time so that callers (including ``unittest.mock.patch``) can resolve
# ``openai.embeddings.create`` even before an ``OpenAIEmbedder`` is built.
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-placeholder-for-module-import"


class OpenAIEmbedder(BaseEmbedder):
    """Embedder backed by OpenAI Embeddings API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-large", dim: int = 3072) -> None:
        openai.api_key = api_key
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = openai.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model
