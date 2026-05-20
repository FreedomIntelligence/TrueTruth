import pytest
from unittest.mock import Mock
from src.agents.base import BaseAgent
from src.state.schema import WorkflowState

def test_base_agent_initialization():
    """Test BaseAgent can be initialized"""
    llm = Mock()
    agent = BaseAgent(llm=llm, tools=[], agent_type="Test")
    assert agent.llm == llm
    assert agent.agent_type == "Test"

def test_base_agent_execute_not_implemented():
    """Test that execute method must be implemented by subclasses"""
    llm = Mock()
    agent = BaseAgent(llm=llm, tools=[], agent_type="Test")
    state = WorkflowState(
        original_question="test",
        current_step="test",
        iteration_count=0,
        agent_call_counts={},
        execution_history=[]
    )

    with pytest.raises(NotImplementedError):
        agent.execute(state)
