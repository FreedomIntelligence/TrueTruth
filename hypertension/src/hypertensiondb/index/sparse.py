import math
import re
from collections import Counter

import jieba

_VOCAB_SIZE = 2**16  # 65536 - hash space for term indices
_MIN_TOKEN_LEN = 1
_STOPWORDS = {"的", "了", "是", "在", "和", "与", "或", "也", "都", "把", "被", "对"}


def _tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text using jieba."""
    tokens = []
    for token in jieba.cut(text):
        token = token.strip().lower()
        if (
            len(token) >= _MIN_TOKEN_LEN
            and not token.isspace()
            and not re.fullmatch(r"[\s\W]+", token)
            and token not in _STOPWORDS
        ):
            tokens.append(token)
    return tokens


def _term_to_index(term: str) -> int:
    """Map term string to a non-negative index via hash."""
    h = hash(term) % _VOCAB_SIZE
    return h if h >= 0 else h + _VOCAB_SIZE


class SparseVectorizer:
    """Convert text into sparse TF-weighted vectors for Qdrant hybrid search."""

    def vectorize(self, text: str) -> tuple[list[int], list[float]]:
        """Return (indices, values) for the given text.

        Uses normalized term frequency as weights.
        Handles hash collisions by summing weights.
        """
        if not text or not text.strip():
            return [], []

        tokens = _tokenize(text)
        if not tokens:
            return [], []

        tf = Counter(tokens)
        doc_len = len(tokens)
        norm = math.sqrt(doc_len)

        index_weights: dict[int, float] = {}
        for term, count in tf.items():
            idx = _term_to_index(term)
            weight = count / norm
            index_weights[idx] = index_weights.get(idx, 0.0) + weight

        indices = list(index_weights.keys())
        values = list(index_weights.values())
        return indices, values
