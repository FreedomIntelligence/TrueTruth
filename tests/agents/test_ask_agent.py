import pytest
from unittest.mock import Mock, MagicMock
from src.agents.ask_agent import AskAgent
from src.state.schema import WorkflowState, PICOQuery

@pytest.fixture
def mock_llm():
    """Mock LLM that returns PICO structure"""
    llm = Mock()
    llm.invoke = MagicMock(return_value=Mock(
        content='{"patient": "60yo male", "intervention": "aspirin", "comparison": "placebo", "outcome": "cardiovascular events", "keywords": ["aspirin", "primary prevention"]}'
    ))
    return llm

def test_ask_agent_initialization(mock_llm):
    """Test AskAgent can be initialized"""
    agent = AskAgent(llm=mock_llm, tools=[])
    assert agent.agent_type == "Ask"

def test_ask_agent_execute_returns_pico(mock_llm):
    """Test that AskAgent returns PICOQuery"""
    agent = AskAgent(llm=mock_llm, tools=[])
    state = WorkflowState(
        original_question="Should I prescribe aspirin for a 60yo male?",
        current_step="ask",
        iteration_count=0,
        agent_call_counts={},
        execution_history=[]
    )

    result = agent.execute(state)

    assert "pico_query" in result
    assert isinstance(result["pico_query"], PICOQuery)
    assert result["pico_query"].patient == "60yo male"
