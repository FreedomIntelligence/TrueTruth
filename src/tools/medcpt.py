"""MedCPT Cross-Encoder wrapper for biomedical relevance scoring.

Model: ncbi/MedCPT-Cross-Encoder
Reference: Jin et al., MedCPT: Contrastive Pre-trained Transformers with Large-scale
           PubMed Search Logs for Zero-shot Biomedical Information Retrieval. 2023.

Replaces LLM-based per-article relevance scoring in AcquireAgent.
Scores are continuous [0, 1] via sigmoid(logit), much more reliable than
LLM discrete 0.2-step scoring for information retrieval tasks.
"""
from __future__ import annotations

from typing import List

_tokenizer = None
_model = None
_device = None


def _load() -> None:
    global _tokenizer, _model, _device
    if _model is not None:
        return

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    print("[MedCPT] Loading ncbi/MedCPT-Cross-Encoder...")
    _tokenizer = AutoTokenizer.from_pretrained("ncbi/MedCPT-Cross-Encoder")
    _model = AutoModelForSequenceClassification.from_pretrained("ncbi/MedCPT-Cross-Encoder")
    _model.eval()

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = _model.to(_device)
    print(f"[MedCPT] Model loaded on {_device}")


def score_relevance(query: str, passages: List[str]) -> List[float]:
    """Score relevance of passages against a query using MedCPT Cross-Encoder.

    Args:
        query: Natural language clinical query derived from PICO.
        passages: List of article texts (title + abstract).

    Returns:
        List of relevance scores in [0, 1], same length and order as passages.
    """
    import torch

    if not passages:
        return []

    _load()

    # Truncate each passage to avoid exceeding the 512-token limit.
    # Title alone rarely exceeds 60 tokens; 800 chars of abstract is safe.
    pairs = [[query, p[:800]] for p in passages]

    with torch.no_grad():
        encoded = _tokenizer(
            pairs,
            truncation=True,
            padding=True,
            return_tensors="pt",
            max_length=512,
        )
        encoded = {k: v.to(_device) for k, v in encoded.items()}
        logits = _model(**encoded).logits.squeeze(-1)
        scores = torch.sigmoid(logits).cpu().tolist()

    # Ensure list return even for a single passage
    if isinstance(scores, float):
        scores = [scores]

    return scores
