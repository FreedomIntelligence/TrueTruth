# Stage 1 MVP - Implementation Tasks (Part 3)

## Task 7: Ask Agent Implementation

**Files:**
- Create: `src/agents/ask_agent.py`
- Create: `src/config/prompts/ask_agent.txt`
- Create: `tests/agents/test_ask_agent.py`

**Step 1: Write the failing test**

Create `tests/agents/test_ask_agent.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_ask_agent.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create prompt template**

Create `src/config/prompts/ask_agent.txt`:
```
You are a clinical question refinement expert. Your task is to convert a natural language clinical question into a structured PICO format.

PICO stands for:
- P (Patient/Problem): Who is the patient or what is the problem?
- I (Intervention): What is the main intervention or exposure?
- C (Comparison): What is the alternative or comparison?
- O (Outcome): What are the relevant outcomes?

Clinical Question: {question}

{backtrack_context}

Return your response as a JSON object:
{{
  "patient": "description of patient/problem",
  "intervention": "main intervention",
  "comparison": "comparison or alternative",
  "outcome": "relevant outcomes",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Be specific and use medical terminology where appropriate.
```

**Step 4: Write minimal implementation**

Create `src/agents/ask_agent.py`:
```python
import json
from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent
from src.state.schema import WorkflowState, PICOQuery

class AskAgent(BaseAgent):
    """Agent for refining clinical questions into PICO format"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Ask")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "ask_agent.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Ask agent to extract PICO from question"""
        question = state["original_question"]

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = f"\nPrevious attempt failed: {state['backtrack_reason']}\nPlease refine the question."

        prompt = self.prompt_template.format(
            question=question,
            backtrack_context=backtrack_context
        )

        response = self.llm.invoke(prompt)

        try:
            pico_dict = json.loads(response.content)
        except json.JSONDecodeError:
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            pico_dict = json.loads(content[start:end])

        pico_query = PICOQuery(
            patient=pico_dict["patient"],
            intervention=pico_dict["intervention"],
            comparison=pico_dict["comparison"],
            outcome=pico_dict["outcome"],
            keywords=pico_dict["keywords"]
        )

        return {"pico_query": pico_query}
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/agents/test_ask_agent.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/agents/ask_agent.py src/config/prompts/ask_agent.txt tests/agents/test_ask_agent.py
git commit -m "feat: implement Ask agent for PICO extraction"
```

---

## Task 8: Acquire Agent Implementation

**Files:**
- Create: `src/agents/acquire_agent.py`
- Create: `src/config/prompts/acquire_agent.txt`
- Create: `tests/agents/test_acquire_agent.py`

**Step 1: Write the failing test**

Create `tests/agents/test_acquire_agent.py`:
```python
import pytest
from unittest.mock import Mock, patch
from src.agents.acquire_agent import AcquireAgent
from src.state.schema import WorkflowState, PICOQuery, Evidence

@pytest.fixture
def mock_llm():
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(
        content="aspirin AND primary prevention"
    ))
    return llm

@pytest.fixture
def sample_state():
    return WorkflowState(
        original_question="Should I prescribe aspirin?",
        current_step="acquire",
        iteration_count=1,
        agent_call_counts={},
        execution_history=[],
        pico_query=PICOQuery(
            patient="60yo male",
            intervention="aspirin",
            comparison="placebo",
            outcome="cardiovascular events",
            keywords=["aspirin", "primary prevention"]
        )
    )

@patch('src.agents.acquire_agent.search_pubmed')
def test_acquire_agent_execute_returns_evidence(mock_search, mock_llm, sample_state):
    """Test that AcquireAgent returns evidence list"""
    mock_search.return_value = [
        Evidence(
            title="Aspirin study",
            source="JAMA",
            pmid="12345",
            abstract="Study on aspirin",
            relevance_score=0.9
        )
    ]

    agent = AcquireAgent(llm=mock_llm, tools=[])
    result = agent.execute(sample_state)

    assert "evidence_list" in result
    assert len(result["evidence_list"]) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_acquire_agent.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create prompt template**

Create `src/config/prompts/acquire_agent.txt`:
```
You are a medical literature search expert. Generate an effective PubMed search query based on a structured PICO question.

PICO Components:
- Patient: {patient}
- Intervention: {intervention}
- Comparison: {comparison}
- Outcome: {outcome}
- Keywords: {keywords}

Generate a PubMed search query using Boolean operators (AND, OR).

Return only the search query string, nothing else.
```

**Step 4: Write minimal implementation**

Create `src/agents/acquire_agent.py`:
```python
from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent
from src.state.schema import WorkflowState, Evidence
from src.tools.pubmed_api import search_pubmed

class AcquireAgent(BaseAgent):
    """Agent for acquiring evidence from PubMed"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Acquire")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "acquire_agent.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Acquire agent to search for evidence"""
        pico = state.get("pico_query")
        if not pico:
            raise ValueError("No PICO query found in state")

        prompt = self.prompt_template.format(
            patient=pico.patient,
            intervention=pico.intervention,
            comparison=pico.comparison,
            outcome=pico.outcome,
            keywords=", ".join(pico.keywords)
        )

        response = self.llm.invoke(prompt)
        search_query = response.content.strip()

        evidence_list = search_pubmed(query=search_query, max_results=5)

        return {"evidence_list": evidence_list}
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/agents/test_acquire_agent.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/agents/acquire_agent.py src/config/prompts/acquire_agent.txt tests/agents/test_acquire_agent.py
git commit -m "feat: implement Acquire agent for evidence search"
```

---

## Task 9: Appraise Agent Implementation

**Files:**
- Create: `src/agents/appraise_agent.py`
- Create: `src/config/prompts/appraise_agent.txt`
- Create: `tests/agents/test_appraise_agent.py`

**Step 1: Write the failing test**

Create `tests/agents/test_appraise_agent.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_appraise_agent.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create prompt template**

Create `src/config/prompts/appraise_agent.txt`:
```
You are a clinical evidence appraisal expert. Evaluate the quality of evidence using the GRADE framework.

GRADE Quality Levels:
- High: Very confident in the effect estimate
- Moderate: Moderately confident
- Low: Limited confidence
- Very Low: Very little confidence

Evidence to appraise:
{evidence_list}

Return your response as JSON:
{{
  "grades": ["High", "Moderate", ...],
  "has_conflict": true/false,
  "conflict_description": "description if conflict exists",
  "summary": "overall assessment"
}}
```

**Step 4: Write minimal implementation**

Create `src/agents/appraise_agent.py`:
```python
import json
from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent
from src.state.schema import WorkflowState, AppraisalResults

class AppraiseAgent(BaseAgent):
    """Agent for appraising evidence quality using GRADE"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Appraise")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "appraise_agent.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Appraise agent to evaluate evidence quality"""
        evidence_list = state.get("evidence_list")
        if not evidence_list:
            raise ValueError("No evidence found in state")

        evidence_text = "\n\n".join([
            f"Evidence {i+1}:\nTitle: {e.title}\nSource: {e.source}\nPMID: {e.pmid}"
            for i, e in enumerate(evidence_list)
        ])

        prompt = self.prompt_template.format(evidence_list=evidence_text)
        response = self.llm.invoke(prompt)

        try:
            appraisal_dict = json.loads(response.content)
        except json.JSONDecodeError:
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            appraisal_dict = json.loads(content[start:end])

        graded_evidence = []
        for i, evidence in enumerate(evidence_list):
            evidence.grade_level = appraisal_dict["grades"][i] if i < len(appraisal_dict["grades"]) else "Low"
            graded_evidence.append(evidence)

        appraisal_results = AppraisalResults(
            evidence=graded_evidence,
            has_conflict=appraisal_dict.get("has_conflict", False),
            conflict_description=appraisal_dict.get("conflict_description"),
            summary=appraisal_dict["summary"]
        )

        return {"appraisal_results": appraisal_results}
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/agents/test_appraise_agent.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/agents/appraise_agent.py src/config/prompts/appraise_agent.txt tests/agents/test_appraise_agent.py
git commit -m "feat: implement Appraise agent for GRADE evaluation"
```
