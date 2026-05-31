import time
import httpx
from hypertensiondb.index.embedder import BaseEmbedder

_ZHIPU_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/embeddings"
_DEFAULT_MODEL = "embedding-3"
_DEFAULT_DIM = 2048
_BATCH_SIZE = 25  # Zhipu API limit per request
_INTER_BATCH_SLEEP = 1.5  # seconds between batches to stay under rate limit


class ZhipuEmbedder(BaseEmbedder):
    """Embedder backed by Zhipu AI Embeddings API (国内可直接访问)."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        dim: int = _DEFAULT_DIM,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dim = dim
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            if i > 0:
                time.sleep(_INTER_BATCH_SLEEP)
            results.extend(self._call_api_with_retry(texts[i : i + _BATCH_SIZE]))
        return results

    def _call_api_with_retry(self, texts: list[str]) -> list[list[float]]:
        backoffs = [2.0, 5.0, 15.0, 30.0]
        for attempt, backoff in enumerate(backoffs):
            try:
                return self._call_api(texts)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    print(f"[EMBED] 429 rate-limit, waiting {backoff}s (attempt {attempt+1}/{len(backoffs)})")
                    time.sleep(backoff)
                    continue
                raise
        # final attempt
        return self._call_api(texts)

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "input": texts}
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(_ZHIPU_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model
