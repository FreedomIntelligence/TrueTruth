# Stage 1 MVP - Implementation Tasks (Part 2)

## Task 4: Gate Engine Implementation

**Files:**
- Create: `src/coordinator/__init__.py`
- Create: `src/coordinator/gate_engine.py`
- Create: `tests/coordinator/__init__.py`
- Create: `tests/coordinator/test_gate_engine.py`

**Step 1: Write the failing test**

Create `tests/coordinator/__init__.py` (empty file)

Create `tests/coordinator/test_gate_engine.py`:
```python
import pytest
from src.coordinator.gate_engine import (
    check_evidence_quality_gate,
    check_empty_results_gate,
    check_max_iterations_gate,
    check_conflict_gate
)
from src.state.schema import WorkflowState, Evidence, AppraisalResults

def test_evidence_quality_gate_triggers_on_low_quality():
    """Test that evidence quality gate triggers when all evidence is low quality"""
    state = WorkflowState(
        original_question="test",
        current_step="appraise",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        appraisal_results=AppraisalResults(
            evidence=[
                Evidence(
                    title="Study 1",
                    source="PubMed",
                    pmid="123",
                    abstract="test",
                    relevance_score=0.9,
                    grade_level="Low"
                )
            ],
            has_conflict=False,
            conflict_description=None,
            summary="Low quality evidence"
        )
    )

    trigger = check_evidence_quality_gate(state)
    assert trigger is not None
    assert trigger.gate_name == "evidence_quality"

def test_empty_results_gate_triggers():
    """Test that empty results gate triggers when no evidence found"""
    state = WorkflowState(
        original_question="test",
        current_step="acquire",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        evidence_list=[]
    )

    trigger = check_empty_results_gate(state)
    assert trigger is not None
    assert trigger.gate_name == "empty_results"

def test_max_iterations_gate_triggers():
    """Test that max iterations gate triggers"""
    state = WorkflowState(
        original_question="test",
        current_step="ask",
        iteration_count=21,
        agent_call_counts={},
        execution_history=[]
    )

    trigger = check_max_iterations_gate(state)
    assert trigger is not None
    assert trigger.gate_name == "max_iterations"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/coordinator/test_gate_engine.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/coordinator/__init__.py` (empty file)

Create `src/coordinator/gate_engine.py`:
```python
from typing import Optional
from src.state.schema import WorkflowState, GateTrigger

def check_evidence_quality_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if all evidence has low quality"""
    if state.get("appraisal_results") is None:
        return None

    appraisal = state["appraisal_results"]
    if not appraisal.evidence:
        return None

    all_low_quality = all(
        e.grade_level in ['Low', 'Very Low']
        for e in appraisal.evidence
        if e.grade_level is not None
    )

    if all_low_quality:
        return GateTrigger(
            gate_name="evidence_quality",
            reason="All evidence below Moderate quality",
            suggested_action="backtrack_to_acquire"
        )
    return None

def check_empty_results_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if search returned no results"""
    evidence_list = state.get("evidence_list")
    if evidence_list is not None and len(evidence_list) == 0:
        return GateTrigger(
            gate_name="empty_results",
            reason="No evidence found in search",
            suggested_action="backtrack_to_ask"
        )
    return None

def check_max_iterations_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if maximum iterations exceeded"""
    iteration_count = state.get("iteration_count", 0)
    agent_call_counts = state.get("agent_call_counts", {})

    if iteration_count > 20:
        return GateTrigger(
            gate_name="max_iterations",
            reason=f"Exceeded 20 total iterations",
            suggested_action="terminate"
        )

    for agent, count in agent_call_counts.items():
        if count > 5:
            return GateTrigger(
                gate_name="max_iterations",
                reason=f"Agent {agent} called {count} times",
                suggested_action="terminate"
            )
    return None

def check_conflict_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if conflicting evidence detected"""
    appraisal = state.get("appraisal_results")
    if appraisal and appraisal.has_conflict:
        return GateTrigger(
            gate_name="conflict",
            reason=f"Conflicting evidence: {appraisal.conflict_description}",
            suggested_action="report_to_user"
        )
    return None

def check_all_gates(state: WorkflowState) -> Optional[GateTrigger]:
    """Check all gates in priority order"""
    gates = [
        check_max_iterations_gate,
        check_empty_results_gate,
        check_evidence_quality_gate,
        check_conflict_gate
    ]

    for gate_func in gates:
        trigger = gate_func(state)
        if trigger is not None:
            return trigger
    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/coordinator/test_gate_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/coordinator/ tests/coordinator/
git commit -m "feat: implement gate engine with 4 core gates"
```

---

## Task 5: PubMed API Tool

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/pubmed_api.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/test_pubmed_api.py`

**Step 1: Write the failing test**

Create `tests/tools/__init__.py` (empty file)

Create `tests/tools/test_pubmed_api.py`:
```python
import pytest
from unittest.mock import Mock, patch
from src.tools.pubmed_api import PubMedClient, search_pubmed
from src.state.schema import Evidence

@pytest.fixture
def mock_response():
    return {
        "esearchresult": {
            "idlist": ["12345678"],
            "count": "1"
        }
    }

@pytest.fixture
def mock_summary():
    return {
        "result": {
            "12345678": {
                "title": "Aspirin for primary prevention",
                "source": "JAMA",
                "pubdate": "2023"
            }
        }
    }

def test_pubmed_client_initialization():
    """Test PubMedClient can be initialized"""
    client = PubMedClient(email="test@example.com")
    assert client.email == "test@example.com"

@patch('requests.get')
def test_search_pubmed_returns_evidence_list(mock_get, mock_response, mock_summary):
    """Test that search_pubmed returns list of Evidence objects"""
    mock_get.side_effect = [
        Mock(json=lambda: mock_response, status_code=200),
        Mock(json=lambda: mock_summary, status_code=200)
    ]

    results = search_pubmed(
        query="aspirin primary prevention",
        max_results=1,
        email="test@example.com"
    )

    assert len(results) == 1
    assert isinstance(results[0], Evidence)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_pubmed_api.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/tools/__init__.py` (empty file)

Create `src/tools/pubmed_api.py`:
```python
import os
import requests
from typing import List
from dotenv import load_dotenv
from src.state.schema import Evidence

load_dotenv()

class PubMedClient:
    """Client for PubMed E-utilities API"""

    def __init__(self, email: str = None):
        self.email = email or os.getenv("PUBMED_EMAIL", "")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search PubMed and return list of PMIDs"""
        url = f"{self.base_url}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "email": self.email
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_summaries(self, pmids: List[str]) -> dict:
        """Fetch article summaries for given PMIDs"""
        if not pmids:
            return {}

        url = f"{self.base_url}/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "email": self.email
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

def search_pubmed(query: str, max_results: int = 5, email: str = None) -> List[Evidence]:
    """Search PubMed and return Evidence objects"""
    client = PubMedClient(email=email)
    pmids = client.search(query, max_results)

    if not pmids:
        return []

    summaries = client.fetch_summaries(pmids)
    evidence_list = []

    for pmid in pmids:
        article = summaries.get("result", {}).get(pmid, {})
        if not article:
            continue

        evidence = Evidence(
            title=article.get("title", "No title"),
            source=article.get("source", "PubMed"),
            pmid=pmid,
            abstract=article.get("abstract", ""),
            relevance_score=1.0,
            grade_level=None
        )
        evidence_list.append(evidence)

    return evidence_list
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_pubmed_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/ tests/tools/
git commit -m "feat: implement PubMed API client"
```

---

## Task 6: Base Agent Class

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/base.py`
- Create: `tests/agents/__init__.py`
- Create: `tests/agents/test_base.py`

**Step 1: Write the failing test**

Create `tests/agents/__init__.py` (empty file)

Create `tests/agents/test_base.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_base.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/agents/__init__.py` (empty file)

Create `src/agents/base.py`:
```python
from typing import List, Any, Dict
from abc import ABC, abstractmethod
from src.state.schema import WorkflowState

class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, llm, tools: List[Any], agent_type: str):
        """
        Initialize agent

        Args:
            llm: Language model instance
            tools: List of tools available to this agent
            agent_type: Type identifier (Ask/Acquire/Appraise/Apply/Assess)
        """
        self.llm = llm
        self.tools = tools
        self.agent_type = agent_type

    @abstractmethod
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Execute agent logic

        Args:
            state: Current workflow state

        Returns:
            Dictionary with agent outputs
        """
        raise NotImplementedError("Subclasses must implement execute()")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/ tests/agents/
git commit -m "feat: add base agent class"
```
