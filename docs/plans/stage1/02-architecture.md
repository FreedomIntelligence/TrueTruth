# Stage 1 MVP - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User / CLI Interface                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Central Coordinator                        │
│  - State Graph Manager                                       │
│  - Gate Engine (Hard Rules)                                  │
│  - Router (LLM-assisted)                                     │
└───┬────────┬────────┬────────┬────────┬─────────────────────┘
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  Ask   │ │Acquire │ │Appraise│ │ Apply  │ │ Assess │
│ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
    │          │          │          │          │
    └──────────┴──────────┴──────────┴──────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Tool Registry       │
            │  - PubMed API         │
            │  - PICO Extractor     │
            │  - GRADE Evaluator    │
            │  - LLM Tools          │
            └───────────────────────┘
```

## Component Design

### 1. Central Coordinator

**Responsibility:** Orchestrate the workflow, manage state, enforce gates

**Implementation:** LangGraph StateGraph with custom routing logic

**Key Functions:**
- `initialize_workflow(question: str) -> StateGraph`
- `route_next(current_state: State) -> str` (returns next agent name)
- `check_gates(state: State) -> Optional[GateTrigger]`
- `execute_workflow() -> FinalOutput`

**State Schema:**
```python
class WorkflowState(TypedDict):
    original_question: str
    current_step: str
    iteration_count: int
    agent_call_counts: Dict[str, int]

    # Agent outputs
    pico_query: Optional[PICOQuery]
    evidence_list: Optional[List[Evidence]]
    appraisal_results: Optional[AppraisalResults]
    recommendation: Optional[Recommendation]
    assessment: Optional<br>Assessment]

    # Control flow
    gate_triggered: Optional[str]
    backtrack_reason: Optional[str]
    should_terminate: bool

    # Audit trail
    execution_history: List[ExecutionNode]
```

### 2. Gate Engine

**Responsibility:** Check gate conditions after each agent execution

**Implementation:** Pure Python functions (no LLM calls)

**Core Gates:**

```python
def check_evidence_quality_gate(state: State) -> Optional[GateTrigger]:
    """
    Trigger if all evidence has GRADE < Moderate
    Action: Backtrack to Acquire or Ask
    """
    if state.appraisal_results:
        all_low_quality = all(
            e.grade_level in ['Low', 'Very Low']
            for e in state.appraisal_results.evidence
        )
        if all_low_quality:
            return GateTrigger(
                gate_name="evidence_quality",
                reason="All evidence below Moderate quality",
                suggested_action="backtrack_to_acquire"
            )
    return None

def check_empty_results_gate(state: State) -> Optional[GateTrigger]:
    """
    Trigger if search returns 0 results
    Action: Backtrack to Ask
    """
    if state.evidence_list is not None and len(state.evidence_list) == 0:
        return GateTrigger(
            gate_name="empty_results",
            reason="No evidence found",
            suggested_action="backtrack_to_ask"
        )
    return None

def check_max_iterations_gate(state: State) -> Optional[GateTrigger]:
    """
    Trigger if total iterations > 20 or any agent called > 5 times
    Action: Terminate
    """
    if state.iteration_count > 20:
        return GateTrigger(
            gate_name="max_iterations",
            reason="Exceeded 20 total iterations",
            suggested_action="terminate"
        )

    for agent, count in state.agent_call_counts.items():
        if count > 5:
            return GateTrigger(
                gate_name="max_iterations",
                reason=f"Agent {agent} called {count} times",
                suggested_action="terminate"
            )
    return None

def check_conflict_gate(state: State) -> Optional[GateTrigger]:
    """
    Trigger if ≥2 evidence items of same quality have conflicting conclusions
    Action: Report to user (pause workflow)
    """
    if state.appraisal_results and state.appraisal_results.has_conflict:
        return GateTrigger(
            gate_name="conflict",
            reason="Conflicting evidence detected",
            suggested_action="report_to_user"
        )
    return None
```

### 3. Agent Architecture

**Common Pattern for All Agents:**

```python
class BaseAgent:
    def __init__(self, llm, tools: List[Tool]):
        self.llm = llm
        self.tools = tools
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> PromptTemplate:
        """Load agent-specific prompt from config/prompts/"""
        pass

    def execute(self, state: State) -> AgentOutput:
        """Main execution method"""
        pass
```

**Agent Implementations:**

#### Ask Agent
```python
class AskAgent(BaseAgent):
    """
    Refine clinical question into structured PICO format

    Tools:
    - PICO extractor (LLM-based)
    - MeSH term mapper

    Input: original_question, execution_history (if backtrack)
    Output: PICOQuery(patient, intervention, comparison, outcome, keywords)
    """
```

#### Acquire Agent
```python
class AcquireAgent(BaseAgent):
    """
    Search for evidence using PubMed API

    Tools:
    - Retrieval strategy generator (LLM-based)
    - PubMed API client
    - Evidence ranker (LLM-based)

    Input: pico_query
    Output: List[Evidence] (top 5 results with metadata)
    """
```

#### Appraise Agent
```python
class AppraiseAgent(BaseAgent):
    """
    Evaluate evidence quality using GRADE framework

    Tools:
    - GRADE evaluator (LLM-based)
    - Conflict detector (rule-based)

    Input: evidence_list
    Output: AppraisalResults(evidence_with_grades, has_conflict, summary)
    """
```

#### Apply Agent
```python
class ApplyAgent(BaseAgent):
    """
    Generate clinical recommendation

    Tools:
    - Response generator (LLM-based)
    - Recommendation strength calculator

    Input: appraisal_results, original_question
    Output: Recommendation(text, strength, rationale, caveats)
    """
```

#### Assess Agent
```python
class AssessAgent(BaseAgent):
    """
    Evaluate recommendation quality and completeness

    Tools:
    - Quality evaluator (LLM-based)
    - Completeness checker (rule-based)

    Input: recommendation, full state
    Output: Assessment(quality_score, gaps, needs_backtrack)
    """
```

### 4. Tool Registry

**Purpose:** Centralized tool management for agents

```python
class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, tool: Tool):
        self.tools[name] = tool

    def get(self, name: str) -> Tool:
        return self.tools[name]

    def get_tools_for_agent(self, agent_type: str) -> List[Tool]:
        """Return tools available to specific agent"""
        pass
```

**Tool Implementations:**

```python
# LLM-based tools
- pico_extractor: Extract PICO from natural language
- retrieval_strategy: Generate PubMed search query
- evidence_ranker: Rank search results by relevance
- grade_evaluator: Apply GRADE criteria to evidence
- response_generator: Generate natural language recommendation
- quality_evaluator: Assess recommendation quality

# API tools
- pubmed_search: Query PubMed E-utilities API

# Utility tools
- mesh_mapper: Map terms to MeSH vocabulary
- conflict_detector: Detect conflicting evidence
- completeness_checker: Check recommendation completeness
```

### 5. State Graph Structure

**Node Structure:**
```python
@dataclass
class ExecutionNode:
    id: str
    agent_type: str  # "Ask" | "Acquire" | "Appraise" | "Apply" | "Assess"
    timestamp: datetime
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    tools_used: List[str]
    gate_triggered: Optional[str]
    status: str  # "completed" | "failed" | "gated"
```

**Edge Structure:**
```python
@dataclass
class ExecutionEdge:
    from_node: str
    to_node: str
    transition_type: str  # "forward" | "backtrack" | "retry"
    reason: str
    coordinator_reasoning: Optional[str]
```

## Data Flow

**Normal Flow (No Gates Triggered):**
```
User Question
  → Coordinator initializes state
  → Ask Agent (PICO extraction)
  → Gate check (pass)
  → Acquire Agent (PubMed search)
  → Gate check (pass)
  → Appraise Agent (GRADE evaluation)
  → Gate check (pass)
  → Apply Agent (generate recommendation)
  → Gate check (pass)
  → Assess Agent (quality check)
  → Gate check (pass)
  → Return final output
```

**Backtrack Flow (Gate Triggered):**
```
... → Acquire Agent returns 0 results
  → Gate check (empty_results gate triggers)
  → Coordinator calls LLM router
  → Router decides: backtrack to Ask
  → Ask Agent (refine question with context)
  → Acquire Agent (retry search)
  → ...
```

## Technology Stack

### Core Framework
- **LangGraph 0.0.20+**: State graph management, conditional routing
- **LangChain 0.1.0+**: LLM abstraction, tool integration
- **Python 3.10+**: Type hints, dataclasses

### LLM Integration
- **langchain-openai**: OpenAI-compatible API client
- **python-dotenv**: Environment variable management

### External APIs
- **PubMed E-utilities**: Literature search
- **requests**: HTTP client for API calls

### Testing
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking for tests

### Development
- **black**: Code formatting
- **mypy**: Type checking
- **ruff**: Linting

## File Structure

```
ebm5a/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent class
│   │   ├── ask_agent.py
│   │   ├── acquire_agent.py
│   │   ├── appraise_agent.py
│   │   ├── apply_agent.py
│   │   └── assess_agent.py
│   ├── coordinator/
│   │   ├── __init__.py
│   │   ├── coordinator.py         # Main coordinator logic
│   │   ├── gate_engine.py         # Gate checking functions
│   │   └── router.py              # LLM-assisted routing
│   ├── state/
│   │   ├── __init__.py
│   │   ├── schema.py              # State data structures
│   │   └── graph.py               # State graph operations
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py            # Tool registry
│   │   ├── llm_tools.py           # LLM-based tools
│   │   ├── pubmed_api.py          # PubMed integration
│   │   └── utils.py               # Utility functions
│   └── config/
│       ├── __init__.py
│       ├── llm_config.py          # LLM configuration
│       └── prompts/               # Prompt templates
│           ├── ask_agent.txt
│           ├── acquire_agent.txt
│           ├── appraise_agent.txt
│           ├── apply_agent.txt
│           └── assess_agent.txt
├── tests/
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_coordinator/
│   ├── test_tools/
│   └── test_integration/
│       └── test_end_to_end.py
├── docs/
│   └── plans/
│       └── stage1/
├── data/
│   └── cache/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Design Decisions

### Why LangGraph?
- Native state graph support
- Built-in conditional routing
- Checkpoint and backtracking capabilities
- Good integration with LangChain ecosystem

### Why Hard Rules for Gates?
- Clinical decisions require reliability
- Deterministic behavior is auditable
- Easier to test and debug
- LLM only assists with routing decisions, not gate triggers

### Why In-Memory State for MVP?
- Simpler implementation
- Faster development
- Sufficient for single-question workflow
- Persistence can be added in Phase 2

### Why PubMed Only?
- Free API access
- Comprehensive medical literature
- Well-documented API
- Local evidence database can be added later

### Why 3-4 Gates Only?
- Start minimal, expand based on real usage
- Easier to test and validate
- Prevents over-engineering
- Additional gates can be added incrementally
