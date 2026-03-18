# Stage 1 MVP - Implementation Tasks (Part 5)

## Task 13: Main Entry Point and CLI

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing test**

Create `tests/test_main.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/main.py`:
```python
#!/usr/bin/env python3
"""
EBM 5A Clinical Decision Support System - Main Entry Point
"""
import sys
from typing import Dict, Any
from src.config.llm_config import get_llm
from src.agents.ask_agent import AskAgent
from src.agents.acquire_agent import AcquireAgent
from src.agents.appraise_agent import AppraiseAgent
from src.agents.apply_agent import ApplyAgent
from src.agents.assess_agent import AssessAgent
from src.coordinator.coordinator import Coordinator

def create_workflow() -> Coordinator:
    """
    Create and configure the workflow coordinator with all agents

    Returns:
        Configured Coordinator instance
    """
    # Initialize LLM
    llm = get_llm(temperature=0.0)

    # Initialize agents
    agents = {
        "Ask": AskAgent(llm=llm),
        "Acquire": AcquireAgent(llm=llm),
        "Appraise": AppraiseAgent(llm=llm),
        "Apply": ApplyAgent(llm=llm),
        "Assess": AssessAgent(llm=llm)
    }

    # Create coordinator
    coordinator = Coordinator(agents=agents)

    return coordinator

def run_clinical_question(question: str) -> Dict[str, Any]:
    """
    Run a clinical question through the complete 5A workflow

    Args:
        question: Clinical question to process

    Returns:
        Final workflow state with recommendation
    """
    coordinator = create_workflow()
    result = coordinator.execute_workflow(question)
    return result

def format_output(state: Dict[str, Any]) -> str:
    """
    Format workflow output for display

    Args:
        state: Final workflow state

    Returns:
        Formatted output string
    """
    output = []
    output.append("=" * 80)
    output.append("EBM 5A CLINICAL DECISION SUPPORT SYSTEM")
    output.append("=" * 80)
    output.append("")

    # Original question
    output.append(f"QUESTION: {state['original_question']}")
    output.append("")

    # PICO
    if state.get('pico_query'):
        pico = state['pico_query']
        output.append("STRUCTURED QUESTION (PICO):")
        output.append(f"  Patient: {pico.patient}")
        output.append(f"  Intervention: {pico.intervention}")
        output.append(f"  Comparison: {pico.comparison}")
        output.append(f"  Outcome: {pico.outcome}")
        output.append(f"  Keywords: {', '.join(pico.keywords)}")
        output.append("")

    # Evidence
    if state.get('evidence_list'):
        output.append(f"EVIDENCE FOUND: {len(state['evidence_list'])} articles")
        for i, evidence in enumerate(state['evidence_list'][:3], 1):
            output.append(f"  {i}. {evidence.title}")
            output.append(f"     Source: {evidence.source} (PMID: {evidence.pmid})")
            if evidence.grade_level:
                output.append(f"     Quality: {evidence.grade_level}")
        output.append("")

    # Recommendation
    if state.get('recommendation'):
        rec = state['recommendation']
        output.append("RECOMMENDATION:")
        output.append(f"  {rec.text}")
        output.append(f"  Strength: {rec.strength}")
        output.append(f"  Evidence Quality: {rec.evidence_quality}")
        output.append(f"  Rationale: {rec.rationale}")
        if rec.caveats:
            output.append("  Caveats:")
            for caveat in rec.caveats:
                output.append(f"    - {caveat}")
        output.append("")

    # Assessment
    if state.get('assessment'):
        assess = state['assessment']
        output.append("QUALITY ASSESSMENT:")
        output.append(f"  Quality Score: {assess.quality_score:.2f}/1.0")
        if assess.gaps:
            output.append("  Identified Gaps:")
            for gap in assess.gaps:
                output.append(f"    - {gap}")
        output.append("")

    # Workflow stats
    output.append("WORKFLOW STATISTICS:")
    output.append(f"  Total Iterations: {state['iteration_count']}")
    output.append(f"  Agent Calls: {state['agent_call_counts']}")
    output.append("")

    output.append("=" * 80)

    return "\n".join(output)

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main \"<clinical question>\"")
        print("\nExample:")
        print('  python -m src.main "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print("Processing clinical question...")
    print(f"Question: {question}\n")

    try:
        result = run_clinical_question(question)
        output = format_output(result)
        print(output)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main entry point and CLI"
```

---

## Task 14: End-to-End Integration Test

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_end_to_end.py`

**Step 1: Write the integration test**

Create `tests/integration/__init__.py` (empty file)

Create `tests/integration/test_end_to_end.py`:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.main import run_clinical_question
from src.state.schema import Evidence

@pytest.fixture
def mock_llm_responses():
    """Mock LLM to return appropriate responses for each agent"""
    responses = {
        0: Mock(content='{"patient": "60yo male", "intervention": "aspirin", "comparison": "placebo", "outcome": "cardiovascular events", "keywords": ["aspirin", "primary prevention"]}'),
        1: Mock(content="aspirin AND primary prevention AND cardiovascular"),
        2: Mock(content='{"grades": ["Moderate"], "has_conflict": false, "summary": "Moderate quality RCT evidence"}'),
        3: Mock(content='{"recommendation": "Consider aspirin with caution", "strength": "Weak", "rationale": "Moderate evidence with bleeding risk", "caveats": ["Monitor for bleeding", "Consider patient preferences"]}'),
        4: Mock(content='{"quality_score": 0.8, "gaps": [], "needs_backtrack": false}')
    }

    call_count = [0]

    def side_effect(*args, **kwargs):
        result = responses[call_count[0]]
        call_count[0] += 1
        return result

    return side_effect

@pytest.fixture
def mock_pubmed_results():
    """Mock PubMed search results"""
    return [
        Evidence(
            title="Aspirin for Primary Prevention of Cardiovascular Events",
            source="JAMA",
            pmid="12345678",
            abstract="Large RCT on aspirin for primary prevention",
            relevance_score=0.95
        )
    ]

@patch('src.agents.acquire_agent.search_pubmed')
@patch('src.config.llm_config.get_llm')
def test_end_to_end_workflow(mock_get_llm, mock_search_pubmed, mock_llm_responses, mock_pubmed_results):
    """Test complete workflow from question to recommendation"""
    # Setup mocks
    mock_llm = Mock()
    mock_llm.invoke = MagicMock(side_effect=mock_llm_responses)
    mock_get_llm.return_value = mock_llm
    mock_search_pubmed.return_value = mock_pubmed_results

    # Run workflow
    question = "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"
    result = run_clinical_question(question)

    # Verify workflow completed
    assert result is not None
    assert result["original_question"] == question

    # Verify PICO extraction
    assert result["pico_query"] is not None
    assert result["pico_query"].intervention == "aspirin"

    # Verify evidence acquisition
    assert result["evidence_list"] is not None
    assert len(result["evidence_list"]) > 0

    # Verify appraisal
    assert result["appraisal_results"] is not None
    assert result["appraisal_results"].evidence[0].grade_level == "Moderate"

    # Verify recommendation
    assert result["recommendation"] is not None
    assert result["recommendation"].strength in ["Strong", "Weak"]
    assert result["recommendation"].evidence_quality == "Moderate"

    # Verify assessment
    assert result["assessment"] is not None
    assert 0 <= result["assessment"].quality_score <= 1

    # Verify workflow stats
    assert result["iteration_count"] >= 5  # At least one call per agent
    assert "Ask" in result["agent_call_counts"]
    assert "Acquire" in result["agent_call_counts"]
    assert "Appraise" in result["agent_call_counts"]
    assert "Apply" in result["agent_call_counts"]
    assert "Assess" in result["agent_call_counts"]

@patch('src.agents.acquire_agent.search_pubmed')
@patch('src.config.llm_config.get_llm')
def test_empty_results_gate_triggers(mock_get_llm, mock_search_pubmed):
    """Test that empty results gate triggers backtrack"""
    # Setup mocks - first search returns empty, second returns results
    mock_search_pubmed.side_effect = [
        [],  # First call returns empty
        [Evidence(
            title="Study",
            source="JAMA",
            pmid="123",
            abstract="test",
            relevance_score=0.9
        )]  # Second call returns results
    ]

    responses = [
        Mock(content='{"patient": "test", "intervention": "test", "comparison": "test", "outcome": "test", "keywords": ["test"]}'),
        Mock(content="test query"),
        Mock(content='{"patient": "refined test", "intervention": "test", "comparison": "test", "outcome": "test", "keywords": ["test", "refined"]}'),
        Mock(content="refined query"),
        Mock(content='{"grades": ["Moderate"], "has_conflict": false, "summary": "test"}'),
        Mock(content='{"recommendation": "test", "strength": "Weak", "rationale": "test", "caveats": []}'),
        Mock(content='{"quality_score": 0.7, "gaps": [], "needs_backtrack": false}')
    ]

    mock_llm = Mock()
    mock_llm.invoke = MagicMock(side_effect=responses)
    mock_get_llm.return_value = mock_llm

    question = "Test question"
    result = run_clinical_question(question)

    # Verify backtrack occurred
    assert result["agent_call_counts"]["Ask"] >= 2  # Called at least twice due to backtrack
    assert result["agent_call_counts"]["Acquire"] >= 2
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_end_to_end.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add end-to-end integration tests"
```

---

## Task 15: Documentation and README

**Files:**
- Create: `README.md`

**Step 1: Create README**

Create `README.md`:
```markdown
# EBM 5A Clinical Decision Support System

A ReAct-based clinical decision support system implementing the Evidence-Based Medicine "5A" framework (Ask-Acquire-Appraise-Apply-Assess).

## Overview

This system processes clinical questions through a complete evidence-based workflow:

1. **Ask**: Refine question into structured PICO format
2. **Acquire**: Search for evidence (PubMed)
3. **Appraise**: Evaluate evidence quality (GRADE framework)
4. **Apply**: Generate clinical recommendation
5. **Assess**: Evaluate recommendation quality

## Features

- Multi-agent architecture with specialized agents for each 5A step
- Hard-rule gate system for quality control and backtracking
- PubMed integration for evidence search
- GRADE framework for evidence appraisal
- Complete audit trail of decision process

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit `.env` file:
```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com
```

## Usage

### Command Line

```bash
python -m src.main "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"
```

### Python API

```python
from src.main import run_clinical_question

result = run_clinical_question(
    "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"
)

print(result["recommendation"].text)
print(f"Strength: {result['recommendation'].strength}")
print(f"Evidence Quality: {result['recommendation'].evidence_quality}")
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test:
```bash
pytest tests/agents/test_ask_agent.py -v
```

## Project Structure

```
ebm5a/
├── src/
│   ├── agents/          # 5 specialized agents
│   ├── coordinator/     # Workflow orchestration
│   ├── state/           # State management
│   ├── tools/           # PubMed API and utilities
│   ├── config/          # Configuration and prompts
│   └── main.py          # Entry point
├── tests/               # Test suite
├── docs/                # Documentation
└── data/                # Cache and data
```

## Architecture

- **Coordinator**: Manages workflow and enforces gates
- **Agents**: Specialized LLM-based agents for each 5A step
- **Gates**: Hard-rule quality checks (evidence quality, empty results, max iterations, conflicts)
- **State Graph**: Tracks complete execution history

## Gates

1. **Evidence Quality Gate**: Triggers if all evidence is Low/Very Low quality
2. **Empty Results Gate**: Triggers if search returns no results
3. **Max Iterations Gate**: Prevents infinite loops (max 20 iterations)
4. **Conflict Gate**: Reports conflicting evidence to user

## Example Output

```
================================================================================
EBM 5A CLINICAL DECISION SUPPORT SYSTEM
================================================================================

QUESTION: Should I prescribe aspirin for primary prevention in a 60-year-old patient?

STRUCTURED QUESTION (PICO):
  Patient: 60-year-old patient without cardiovascular disease
  Intervention: aspirin
  Comparison: no aspirin
  Outcome: cardiovascular events, bleeding
  Keywords: aspirin, primary prevention, cardiovascular

EVIDENCE FOUND: 3 articles
  1. Aspirin for Primary Prevention of Cardiovascular Events
     Source: JAMA (PMID: 12345678)
     Quality: Moderate

RECOMMENDATION:
  Consider aspirin with caution for primary prevention
  Strength: Weak
  Evidence Quality: Moderate
  Rationale: Moderate evidence shows small benefit but increased bleeding risk
  Caveats:
    - Monitor for bleeding complications
    - Consider patient preferences and bleeding risk factors
    - Reassess periodically

QUALITY ASSESSMENT:
  Quality Score: 0.85/1.0

WORKFLOW STATISTICS:
  Total Iterations: 5
  Agent Calls: {'Ask': 1, 'Acquire': 1, 'Appraise': 1, 'Apply': 1, 'Assess': 1}

================================================================================
```

## Development

This is Stage 1 MVP. Future enhancements:
- SQLite persistence for audit trail
- Evidence caching
- Advanced calculators (risk scores, dosage)
- Web UI
- Local evidence database

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README"
```

**Step 3: Final verification**

Run all tests:
```bash
pytest --cov=src
```

Expected: All tests pass with >80% coverage

**Step 4: Final commit**

```bash
git add .
git commit -m "chore: stage 1 MVP complete"
```

---

## Summary

Stage 1 MVP is now complete with:
- ✅ All 5 agents implemented (Ask/Acquire/Appraise/Apply/Assess)
- ✅ Coordinator with gate engine
- ✅ 4 core gates (quality, empty results, max iterations, conflicts)
- ✅ PubMed API integration
- ✅ Complete test suite with >80% coverage
- ✅ CLI interface
- ✅ End-to-end integration test
- ✅ Documentation

**Next Steps**: See `04-risks.md` for known limitations and mitigation strategies.
