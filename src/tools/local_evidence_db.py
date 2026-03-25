"""Local obstetrics evidence database: BM25 + vector search with RRF fusion.

Usage (from AcquireAgent):
    from src.tools.local_evidence_db import search_local
    results = search_local(query="preeclampsia treatment magnesium", top_k=20)

The database must be built first:
    python scripts/build_obstetrics_db.py
"""

import json
import pickle
import re
from pathlib import Path
from typing import List, Optional, Tuple

from src.state.schema import Evidence

_DB_DIR = Path(__file__).parent.parent.parent / "data" / "obstetrics_db"
_CHROMA_DIR = Path(__file__).parent.parent.parent / "data" / "obstetrics_chroma"
_BM25_PATH = _DB_DIR / "bm25.pkl"
_ARTICLES_PATH = _DB_DIR / "articles.json"

_RRF_K = 60
_CANDIDATE_N = 20  # candidates per retrieval path before RRF

# Module-level lazy caches to avoid reloading on every call
_bm25_cache = None
_corpus_ids_cache = None
_articles_cache = None
_embed_model_cache = None
_chroma_collection_cache = None


def _load_bm25():
    global _bm25_cache, _corpus_ids_cache
    if _bm25_cache is None:
        with open(_BM25_PATH, "rb") as f:
            data = pickle.load(f)
        _bm25_cache = data["bm25"]
        _corpus_ids_cache = data["corpus_ids"]
    return _bm25_cache, _corpus_ids_cache


def _load_articles() -> dict:
    global _articles_cache
    if _articles_cache is None:
        with open(_ARTICLES_PATH, "r", encoding="utf-8") as f:
            _articles_cache = {a["pmcid"]: a for a in json.load(f)}
    return _articles_cache


def _load_embed_model():
    global _embed_model_cache
    if _embed_model_cache is None:
        from sentence_transformers import SentenceTransformer
        _embed_model_cache = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model_cache


def _load_chroma():
    global _chroma_collection_cache
    if _chroma_collection_cache is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _chroma_collection_cache = client.get_collection("obstetrics_evidence")
    return _chroma_collection_cache


def _rrf_fuse(
    bm25_hits: List[Tuple[str, int]],
    vector_hits: List[Tuple[str, int]],
    k: int = _RRF_K,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion: rrf_score(d) = Σ 1/(k + rank_i(d))"""
    scores: dict = {}
    for pmcid, rank in bm25_hits:
        scores[pmcid] = scores.get(pmcid, 0.0) + 1.0 / (k + rank)
    for pmcid, rank in vector_hits:
        scores[pmcid] = scores.get(pmcid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _extract_spans(abstract_text: str, query_keywords: List[str]) -> Optional[str]:
    """Extract key sentence spans from an abstract that match query keywords.

    Algorithm:
    1. Split abstract into sentences on . ! ? 。 boundaries.
    2. Score each sentence by count of query_keywords it contains (case-insensitive).
    3. threshold = 1 (at least one keyword match required).
    4. Merge adjacent sentences that both score >= threshold into a single span.
    5. If >= 60% of sentences score >= threshold, return the full abstract as one span.
    6. Return top-3 spans ranked by max sentence score, each capped at 200 chars.
    7. If no sentence scores >= threshold, return None.
    """
    if not abstract_text or not query_keywords:
        return None

    keywords_lower = [kw.lower() for kw in query_keywords if kw]
    sentences = [s.strip() for s in re.split(r'[.!?。]+', abstract_text) if s.strip()]
    if not sentences:
        return None

    # Score each sentence
    scores = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for kw in keywords_lower if kw in sent_lower)
        scores.append(score)

    threshold = 1
    above = sum(1 for s in scores if s >= threshold)

    # If >=60% of sentences match, return full abstract
    if above / len(sentences) >= 0.6:
        return abstract_text[:400]

    # Merge adjacent sentences that both score >= threshold
    spans = []
    i = 0
    while i < len(sentences):
        if scores[i] >= threshold:
            span_sents = [sentences[i]]
            span_max = scores[i]
            j = i + 1
            while j < len(sentences) and scores[j] >= threshold:
                span_sents.append(sentences[j])
                span_max = max(span_max, scores[j])
                j += 1
            spans.append((' '.join(span_sents), span_max))
            i = j
        else:
            i += 1

    if not spans:
        return None

    # Sort by max sentence score descending, take top 3, cap each at 200 chars
    spans.sort(key=lambda x: x[1], reverse=True)
    top = [s[:200] for s, _ in spans[:3]]
    return ' … '.join(top)


def search_local(query: str, top_k: int = 20) -> List[Evidence]:
    """Search the local obstetrics evidence database using BM25 + vector RRF.

    Args:
        query: Natural language or Boolean search string.
        top_k: Maximum number of Evidence objects to return.

    Returns:
        List[Evidence] compatible with the existing Acquire pipeline.
        Relevance scores are rank-normalized (rank 1 → 1.0, rank top_k → ~0.1).

    Raises:
        FileNotFoundError: If the local DB has not been built yet.
    """
    if not _BM25_PATH.exists() or not _ARTICLES_PATH.exists():
        raise FileNotFoundError(
            "Local obstetrics DB not found. "
            "Run: python scripts/build_obstetrics_db.py"
        )

    bm25, corpus_ids = _load_bm25()
    articles = _load_articles()

    # BM25 retrieval
    tokens = query.lower().split()
    bm25_scores = bm25.get_scores(tokens)
    bm25_ranked = sorted(
        range(len(corpus_ids)), key=lambda i: bm25_scores[i], reverse=True
    )[:_CANDIDATE_N]
    bm25_hits = [(corpus_ids[i], rank + 1) for rank, i in enumerate(bm25_ranked)]

    # Vector retrieval
    vector_hits: List[Tuple[str, int]] = []
    try:
        model = _load_embed_model()
        collection = _load_chroma()
        query_embedding = model.encode([query])[0].tolist()
        n_results = min(_CANDIDATE_N, collection.count())
        if n_results > 0:
            vector_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["metadatas"],
            )
            # Aggregate chunk-level to article-level (keep best rank per article)
            pmcid_best_rank: dict = {}
            for rank, meta in enumerate(vector_results["metadatas"][0]):
                pmcid = meta["pmcid"]
                if pmcid not in pmcid_best_rank:
                    pmcid_best_rank[pmcid] = rank + 1
            vector_hits = list(pmcid_best_rank.items())
    except Exception as e:
        print(f"[DEBUG] Vector search failed ({e}), using BM25 only")

    # RRF fusion
    fused = _rrf_fuse(bm25_hits, vector_hits)

    # Build Evidence list with rank-normalized relevance scores
    results: List[Evidence] = []
    n = min(top_k, len(fused))
    for rank, (pmcid, _score) in enumerate(fused[:top_k]):
        a = articles.get(pmcid)
        if a is None:
            continue
        # Linear rank-normalized score: rank 0 → 1.0, rank n-1 → 0.1
        relevance = round(1.0 - (rank / max(n, 1)) * 0.9, 3) if n > 1 else 1.0
        results.append(Evidence(
            title=a.get("title", ""),
            source=a.get("journal", "PMC"),
            pmid=a.get("pmid"),
            abstract=a.get("abstract", ""),
            relevance_score=relevance,
            study_type=None,            # inferred later by AcquireAgent._infer_study_type()
            publication_date=a.get("publication_date"),
            grade_level=None,
            pmcid=pmcid,
            full_text=a.get("full_text"),  # used only at retrieval stage; not in prompts
            key_sentences=_extract_spans(a.get("abstract", ""), tokens),
        ))

    return results
