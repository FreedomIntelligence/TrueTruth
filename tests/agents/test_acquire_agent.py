import pytest
from unittest.mock import Mock, patch
from src.agents.acquire_agent import AcquireAgent
from src.state.schema import WorkflowState, PICOQuery, Evidence

@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(
        content="aspirin AND primary prevention"
    ))
    return llm

@pytest.fixture
def sample_state():
    return WorkflowState(
        original_question="Should I prescribe aspirin?",
        current_step="acquire",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        pico_query=PICOQuery(
            patient="60yo male",
            intervention="aspirin",
            comparison="placebo",
            outcome="cardiovascular events",
            keywords=["aspirin", "primary prevention"]
        )
    )

@patch('src.agents.acquire_agent.search_pubmed')
def test_acquire_agent_execute_returns_evidence(mock_search, mock_llm, sample_state):
    """Test that AcquireAgent returns evidence list"""
    mock_search.return_value = [
        Evidence(
            title="Aspirin study",
            source="JAMA",
            pmid="12345",
            abstract="Study on aspirin",
            relevance_score=0.9
        )
    ]

    agent = AcquireAgent(llm=mock_llm, tools=[])
    result = agent.execute(sample_state)

    assert "evidence_list" in result
    assert len(result["evidence_list"]) > 0
