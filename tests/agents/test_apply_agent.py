import pytest
from unittest.mock import Mock
from src.agents.apply_agent import ApplyAgent
from src.state.schema import WorkflowState, Evidence, AppraisalResults, Recommendation

@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(
        content='{"recommendation": "Consider aspirin with caution", "strength": "Weak", "rationale": "Moderate evidence with bleeding risk", "caveats": ["Monitor for bleeding"]}'
    ))
    return llm

@pytest.fixture
def sample_state():
    return WorkflowState(
        original_question="Should I prescribe aspirin?",
        current_step="apply",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        appraisal_results=AppraisalResults(
            evidence=[
                Evidence(
                    title="Study 1",
                    source="JAMA",
                    pmid="123",
                    abstract="RCT on aspirin",
                    relevance_score=0.9,
                    grade_level="Moderate"
                )
            ],
            has_conflict=False,
            conflict_description=None,
            summary="Moderate quality evidence"
        )
    )

def test_apply_agent_execute_returns_recommendation(mock_llm, sample_state):
    """Test that ApplyAgent returns Recommendation"""
    agent = ApplyAgent(llm=mock_llm, tools=[])
    result = agent.execute(sample_state)

    assert "recommendation" in result
    assert isinstance(result["recommendation"], Recommendation)
    assert result["recommendation"].strength in ["Strong", "Weak"]
