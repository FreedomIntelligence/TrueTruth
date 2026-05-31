import pytest
from datetime import datetime
from src.state.schema import (
    WorkflowState,
    ExecutionNode,
    PICOQuery,
    Evidence,
    AppraisalResults,
    Recommendation,
    Assessment,
    GateTrigger
)

def test_workflow_state_initialization():
    """Test WorkflowState can be created with required fields"""
    state = WorkflowState(
        original_question="Test question",
        current_step="ask",
        iteration_count=0,
        agent_call_counts={},
        execution_history=[]
    )
    assert state["original_question"] == "Test question"
    assert state["current_step"] == "ask"

def test_pico_query_structure():
    """Test PICOQuery dataclass"""
    pico = PICOQuery(
        patient="60yo male",
        intervention="aspirin",
        comparison="placebo",
        outcome="cardiovascular events",
        keywords=["aspirin", "primary prevention"]
    )
    assert pico.patient == "60yo male"
    assert len(pico.keywords) == 2
