import pytest
from unittest.mock import Mock, patch
from src.main import create_workflow, run_clinical_question

@patch('src.main.get_llm')
def test_create_workflow_returns_coordinator(mock_get_llm):
    """Test that create_workflow returns a Coordinator instance"""
    mock_get_llm.return_value = Mock()

    coordinator = create_workflow()

    assert coordinator is not None
    assert hasattr(coordinator, 'execute_workflow')

@patch('src.main.create_workflow')
def test_run_clinical_question(mock_create_workflow):
    """Test that run_clinical_question executes workflow"""
    mock_coordinator = Mock()
    mock_coordinator.execute_workflow.return_value = {
        "recommendation": Mock(text="Test recommendation")
    }
    mock_create_workflow.return_value = mock_coordinator

    result = run_clinical_question("Should I prescribe aspirin?")

    assert result is not None
    mock_coordinator.execute_workflow.assert_called_once()
