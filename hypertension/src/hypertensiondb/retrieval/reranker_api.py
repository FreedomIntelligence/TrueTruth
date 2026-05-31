"""API-based reranker using OpenAI-compatible /rerank endpoint.

Compatible with HuatuoGPT gateway which exposes BAAI/bge-reranker-v2-m3
via a /rerank REST endpoint.
"""
from __future__ import annotations

import os
import time

import httpx

from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker import BaseReranker

_DEFAULT_BASE_URL = "https://api.huatuogpt.cn/v1"
_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"
_BATCH_SIZE = 50  # max documents per request
_BACKOFFS = [1.0, 3.0, 8.0]


class APIReranker(BaseReranker):
    """Reranker that calls a remote /rerank API endpoint.

    No local model required.  Falls back to RRF order on any API failure.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.getenv("LLM_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        if not candidates:
            return []

        all_scores: list[float] = []
        for i in range(0, len(candidates), _BATCH_SIZE):
            batch = candidates[i : i + _BATCH_SIZE]
            docs = [c.text or "" for c in batch]
            scores = self._call_api(query, docs)
            all_scores.extend(scores)

        pairs = list(zip(candidates, all_scores))
        pairs.sort(key=lambda t: t[1], reverse=True)
        return pairs

    def _call_api(self, query: str, documents: list[str]) -> list[float]:
        url = f"{self._base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self._model, "query": query, "documents": documents}

        last_exc: Exception | None = None
        for attempt, backoff in enumerate([0] + _BACKOFFS):
            if backoff:
                time.sleep(backoff)
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                data = resp.json()
                results = sorted(data["results"], key=lambda r: r["index"])
                return [r["relevance_score"] for r in results]
            except Exception as exc:
                last_exc = exc
                print(f"[WARN] APIReranker attempt {attempt+1} failed: {exc}")

        # All retries failed — return neutral scores (preserve RRF order)
        print(f"[WARN] APIReranker all retries failed, using RRF order: {last_exc}")
        return [0.0] * len(documents)

    @property
    def model_name(self) -> str:
        return self._model
