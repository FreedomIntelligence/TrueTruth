import os
import torch
from typing import Optional

from hypertensiondb.retrieval.hybrid import Candidate
from hypertensiondb.retrieval.reranker import BaseReranker

# Default: local ModelScope cache path; override via env BGE_RERANKER_PATH
_DEFAULT_MODEL_PATH = os.getenv(
    "BGE_RERANKER_PATH",
    "C:/Users/Winda/.cache/modelscope/BAAI/bge-reranker-base",
)


class BGEReranker(BaseReranker):
    """BGE cross-encoder reranker using local model weights.

    Uses transformers directly (avoids FlagEmbedding XLMRobertaTokenizer
    compatibility issue with newer transformers versions).

    Model path: set BGE_RERANKER_PATH env var or use default ModelScope cache.
    """

    def __init__(
        self,
        model_path: str = _DEFAULT_MODEL_PATH,
        batch_size: int = 30,
    ) -> None:
        self._model_path = model_path
        self._batch_size = batch_size
        self._tokenizer = None
        self._model = None

    def _load(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(self._model_path)
        model = AutoModelForSequenceClassification.from_pretrained(self._model_path)
        model.eval()
        return tokenizer, model

    def _get_model(self):
        if self._model is None:
            self._tokenizer, self._model = self._load()
        return self._tokenizer, self._model

    def rerank(
        self, query: str, candidates: list[Candidate]
    ) -> list[tuple[Candidate, float]]:
        if not candidates:
            return []
        tokenizer, model = self._get_model()
        pairs = [[query, c.text or ""] for c in candidates]
        all_scores: list[float] = []

        for i in range(0, len(pairs), self._batch_size):
            batch = pairs[i : i + self._batch_size]
            with torch.no_grad():
                inputs = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )
                logits = model(**inputs).logits.squeeze(-1)
                if logits.dim() == 0:
                    all_scores.append(float(logits))
                else:
                    all_scores.extend(logits.tolist())

        pairs_with_score = list(zip(candidates, all_scores))
        pairs_with_score.sort(key=lambda t: t[1], reverse=True)
        return pairs_with_score

    @property
    def model_name(self) -> str:
        return self._model_path.rstrip("/").split("/")[-1]
