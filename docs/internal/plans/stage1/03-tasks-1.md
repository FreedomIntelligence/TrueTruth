# Stage 1 MVP - Implementation Tasks (Part 1)

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: Create requirements.txt**

```txt
langchain==0.1.0
langchain-openai==0.0.5
langgraph==0.0.20
requests==2.31.0
pytest==7.4.3
pytest-cov==7.4.3
pytest-mock==3.12.0
python-dotenv==1.0.0
```

**Step 2: Create project structure**

Run:
```bash
mkdir -p src/agents src/tools src/coordinator src/state src/config/prompts tests/agents tests/tools tests/coordinator tests/state tests/integration data/cache
touch src/__init__.py tests/__init__.py
```

**Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
.env
*.db
data/cache/*
.pytest_cache/
.venv/
venv/
.coverage
htmlcov/
```

**Step 4: Create .env.example**

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com
```

**Step 5: Initialize git and commit**

Run:
```bash
git init
git add .
git commit -m "chore: initial project setup"
```

---

## Task 2: LLM Configuration Module

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/llm_config.py`
- Create: `tests/config/__init__.py`
- Create: `tests/config/test_llm_config.py`

**Step 1: Write the failing test**

Create `tests/config/__init__.py` (empty file)

Create `tests/config/test_llm_config.py`:
```python
import pytest
from src.config.llm_config import get_llm

def test_get_llm_returns_chatmodel():
    """Test that get_llm returns a ChatOpenAI instance"""
    llm = get_llm()
    assert llm is not None
    assert hasattr(llm, 'invoke')

def test_get_llm_with_custom_temperature():
    """Test that get_llm accepts temperature parameter"""
    llm = get_llm(temperature=0.7)
    assert llm.temperature == 0.7
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_llm_config.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/config/__init__.py` (empty file)

Create `src/config/llm_config.py`:
```python
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    Get configured LLM instance

    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", "gpt-4"),
        temperature=temperature
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_llm_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config/ tests/config/ .env.example
git commit -m "feat: add LLM configuration module"
```

---

## Task 3: State Schema Definition

**Files:**
- Create: `src/state/__init__.py`
- Create: `src/state/schema.py`
- Create: `tests/state/__init__.py`
- Create: `tests/state/test_schema.py`

**Step 1: Write the failing test**

Create `tests/state/__init__.py` (empty file)

Create `tests/state/test_schema.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_schema.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

Create `src/state/__init__.py` (empty file)

Create `src/state/schema.py`:
```python
from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PICOQuery:
    """Structured clinical question in PICO format"""
    patient: str
    intervention: str
    comparison: str
    outcome: str
    keywords: List[str]

@dataclass
class Evidence:
    """Single piece of evidence"""
    title: str
    source: str
    pmid: Optional[str]
    abstract: str
    relevance_score: float
    grade_level: Optional[str] = None

@dataclass
class AppraisalResults:
    """Results from evidence appraisal"""
    evidence: List[Evidence]
    has_conflict: bool
    conflict_description: Optional[str]
    summary: str

@dataclass
class Recommendation:
    """Clinical recommendation"""
    text: str
    strength: str
    rationale: str
    caveats: List[str]
    evidence_quality: str

@dataclass
class Assessment:
    """Quality assessment of recommendation"""
    quality_score: float
    gaps: List[str]
    needs_backtrack: bool
    backtrack_reason: Optional[str]

@dataclass
class GateTrigger:
    """Gate trigger information"""
    gate_name: str
    reason: str
    suggested_action: str

@dataclass
class ExecutionNode:
    """Node in execution graph"""
    id: str
    agent_type: str
    timestamp: datetime
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    tools_used: List[str]
    gate_triggered: Optional[str]
    status: str

class WorkflowState(TypedDict):
    """Main state for the workflow"""
    original_question: str
    current_step: str
    iteration_count: int
    agent_call_counts: Dict[str, int]
    pico_query: Optional[PICOQuery]
    evidence_list: Optional[List[Evidence]]
    appraisal_results: Optional[AppraisalResults]
    recommendation: Optional[Recommendation]
    assessment: Optional[Assessment]
    gate_triggered: Optional[str]
    backtrack_reason: Optional[str]
    should_terminate: bool
    execution_history: List[ExecutionNode]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_schema.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/state/ tests/state/
git commit -m "feat: add state schema definitions"
```
