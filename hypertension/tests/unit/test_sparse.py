import pytest
from hypertensiondb.index.sparse import SparseVectorizer


@pytest.fixture
def vectorizer():
    return SparseVectorizer()


@pytest.mark.unit
def test_chinese_text_produces_nonempty_vector(vectorizer):
    indices, values = vectorizer.vectorize("原发性高血压是心血管疾病的主要危险因素")
    assert len(indices) > 0
    assert len(indices) == len(values)


@pytest.mark.unit
def test_english_text_produces_nonempty_vector(vectorizer):
    indices, values = vectorizer.vectorize("primary hypertension cardiovascular risk")
    assert len(indices) > 0
    assert len(indices) == len(values)


@pytest.mark.unit
def test_mixed_text(vectorizer):
    indices, values = vectorizer.vectorize("ARB联合CCB treatment of hypertension")
    assert len(indices) > 0


@pytest.mark.unit
def test_all_values_positive(vectorizer):
    _, values = vectorizer.vectorize("缬沙坦联合氨氯地平治疗高血压")
    assert all(v > 0 for v in values)


@pytest.mark.unit
def test_all_indices_nonnegative(vectorizer):
    indices, _ = vectorizer.vectorize("hypertension ARB CCB combination therapy")
    assert all(idx >= 0 for idx in indices)


@pytest.mark.unit
def test_no_duplicate_indices(vectorizer):
    indices, _ = vectorizer.vectorize("high blood pressure hypertension blood")
    assert len(indices) == len(set(indices))


@pytest.mark.unit
def test_empty_text_returns_empty(vectorizer):
    indices, values = vectorizer.vectorize("")
    assert indices == []
    assert values == []
