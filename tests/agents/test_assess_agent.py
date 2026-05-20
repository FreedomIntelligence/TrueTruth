import pytest
from unittest.mock import Mock
from src.agents.assess_agent import AssessAgent
from src.state.schema import WorkflowState, Recommendation, Assessment

@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(
        content='{"quality_score": 0.85, "gaps": [], "needs_backtrack": false}'
    ))
    return llm

@pytest.fixture
def sample_state():
    return WorkflowState(
        original_question="Should I prescribe aspirin?",
        current_step="assess",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        recommendation=Recommendation(
            text="Consider aspirin with caution",
            strength="Weak",
            rationale="Moderate evidence",
            caveats=["Monitor for bleeding"],
            evidence_quality="Moderate"
        )
    )

def test_assess_agent_execute_returns_assessment(mock_llm, sample_state):
    """Test that AssessAgent returns Assessment"""
    agent = AssessAgent(llm=mock_llm, tools=[])
    result = agent.execute(sample_state)

    assert "assessment" in result
    assert isinstance(result["assessment"], Assessment)
    assert 0 <= result["assessment"].quality_score <= 1
