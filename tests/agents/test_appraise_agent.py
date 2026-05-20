import pytest
from unittest.mock import Mock
from src.agents.appraise_agent import AppraiseAgent
from src.state.schema import WorkflowState, Evidence, AppraisalResults

@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(
        content='{"grades": ["Moderate"], "has_conflict": false, "summary": "Good quality evidence"}'
    ))
    return llm

@pytest.fixture
def sample_state():
    return WorkflowState(
        original_question="Should I prescribe aspirin?",
        current_step="appraise",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        evidence_list=[
            Evidence(
                title="Study 1",
                source="JAMA",
                pmid="123",
                abstract="RCT on aspirin",
                relevance_score=0.9
            )
        ]
    )

def test_appraise_agent_execute_returns_appraisal(mock_llm, sample_state):
    """Test that AppraiseAgent returns AppraisalResults"""
    agent = AppraiseAgent(llm=mock_llm, tools=[])
    result = agent.execute(sample_state)

    assert "appraisal_results" in result
    assert isinstance(result["appraisal_results"], AppraisalResults)
    assert result["appraisal_results"].evidence[0].grade_level == "Moderate"
