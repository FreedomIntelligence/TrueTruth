import pytest
from unittest.mock import MagicMock, patch, call
from qdrant_client.models import Distance

from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
from hypertensiondb.index.chunk import EvidenceChunk


def _make_chunk(evidence_id="EV-RCT-2026-PENG-001", section="results") -> EvidenceChunk:
    return EvidenceChunk(
        point_id="00000000-0000-0000-0000-000000000001",
        evidence_id=evidence_id,
        section_name=section,
        text="SBP 下降 8 mmHg",
        is_clinical_bottom_line=False,
        metadata={"type": "RCT", "year": 2026},
    )


@pytest.fixture
def mock_qdrant():
    return MagicMock()


@pytest.fixture
def client(mock_qdrant):
    return QdrantIndexClient(qdrant=mock_qdrant, collection_name="test_col")


@pytest.mark.unit
def test_ensure_collection_creates_when_missing(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = False
    client.ensure_collection(dense_dim=8)
    mock_qdrant.create_collection.assert_called_once()
    args, kwargs = mock_qdrant.create_collection.call_args
    assert kwargs.get("collection_name") == "test_col" or args[0] == "test_col"


@pytest.mark.unit
def test_ensure_collection_skips_if_exists(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = True
    client.ensure_collection(dense_dim=8)
    mock_qdrant.create_collection.assert_not_called()


@pytest.mark.unit
def test_upsert_chunks_calls_upsert(client, mock_qdrant):
    chunk = _make_chunk()
    dense = [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]]
    sparse = [([1, 2, 3], [0.5, 0.3, 0.2])]
    client.upsert_chunks([chunk], dense, sparse)
    mock_qdrant.upsert.assert_called_once()


@pytest.mark.unit
def test_delete_collection_calls_delete(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = True
    client.delete_collection()
    mock_qdrant.delete_collection.assert_called_once_with(collection_name="test_col")


@pytest.mark.unit
def test_delete_collection_skips_if_not_exists(client, mock_qdrant):
    mock_qdrant.collection_exists.return_value = False
    client.delete_collection()
    mock_qdrant.delete_collection.assert_not_called()
