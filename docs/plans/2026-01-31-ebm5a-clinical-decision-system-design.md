# EBM 5A Clinical Decision Support System - Design Document

**Date**: 2026-01-31
**Project**: Evidence-Based Medicine 5A Framework with ReAct Pattern
**Language**: Python

## 1. Overview

### 1.1 Project Goal
Build a clinical decision support system based on the Evidence-Based Medicine "5A" framework (Ask-Acquire-Appraise-Apply-Assess) using a ReAct pattern. The system takes a single clinical question and performs complete evidence-based analysis to support clinical decision-making.

### 1.2 Current Status
- No evidence-based medicine database yet
- Using general-purpose LLMs
- Need to clarify ReAct module structure, Reason/Act/Observe points, and gating mechanisms

### 1.3 Primary Use Case
**Single clinical question workflow**: A clinician asks one question (e.g., "Should I prescribe aspirin for this patient?") and receives a complete 5A analysis with recommendations.

### 1.4 ReAct Pattern
**Flexible ReAct with backtracking**: The system can jump between any 5A steps based on what it discovers. For example, during Appraise, if evidence quality is insufficient, the system can backtrack to Ask to refine the question or to Acquire to adjust search strategy.

## 2. System Architecture

### 2.1 Architecture Overview

The system uses a **coordinator-agent architecture** with six main components:

#### 2.1.1 Central Coordinator
- Manages the state graph and enforces hard rules
- Receives initial clinical question
- Routes requests to specialized agents
- Tracks all steps taken
- Decides when to trigger backtracking based on gate conditions
- **Implementation**: Hybrid mode - rule engine for gate checking + LLM for routing decisions

#### 2.1.2 Five Specialized Agents (Ask/Acquire/Appraise/Apply/Assess)
Each agent is an LLM instance with specialized prompt and toolset:
- **Ask Agent**: Refines clinical questions into PICO format (Patient/Problem, Intervention, Comparison, Outcome)
- **Acquire Agent**: Searches external sources (PubMed, guidelines) using refined queries
- **Appraise Agent**: Grades evidence quality using GRADE criteria, detects conflicts
- **Apply Agent**: Synthesizes evidence into clinical recommendations with calculations
- **Assess Agent**: Evaluates recommendation quality and identifies gaps

#### 2.1.3 State Graph Manager
- Maintains a directed graph where nodes represent states (which agent, inputs/outputs)
- Edges represent transitions
- Provides full audit trail
- Prevents redundant work

#### 2.1.4 Hard Rule Engine
Implements gate conditions with **hard rules as primary gates**, LLM reasoning as fallback:
- Evidence quality threshold not met → backtrack to Acquire or Ask
- Conflicting equal-quality evidence → present to user
- Missing critical information → backtrack to Ask
- Maximum iteration limit → escalate to user

**Gate Strategy**: Dynamic gates - start with 3-4 core gates, add new gates based on actual problems encountered during use.

#### 2.1.5 Tool Registry
Provides tools to agents:
- Search APIs (PubMed)
- Evidence grading functions (GRADE)
- Risk calculators
- Statistical analysis utilities
- LLM-powered tools (see section 3)

### 2.2 Action Space
The system can perform:
- **Search**: External sources (PubMed, clinical guidelines)
- **Computation**: Risk scores, dosage adjustments, statistical analysis of evidence quality
- **Conflict Resolution**: Grade evidence quality first; if quality is comparable, present conflicts to user

## 3. Coordinator Design & Gate System

### 3.1 Coordinator Implementation

**Hybrid Mode**:
- **Rule engine handles gate checking**: After each agent returns results, rule engine checks if gate conditions are triggered
- **LLM assists routing decisions**: When gate is triggered, LLM coordinator decides which step to backtrack to and how to adjust strategy

This ensures gate reliability (rule-driven) while maintaining routing flexibility (LLM-driven).

### 3.2 Initial Gate Set (3-4 Core Gates)

1. **Evidence Quality Gate** (Appraise → Acquire/Ask)
   - Trigger: All evidence GRADE scores < Moderate
   - Action: LLM decides whether to return to Acquire (improve search strategy) or Ask (reformulate question)

2. **Evidence Conflict Gate** (Appraise → Present to User)
   - Trigger: ≥2 conflicting evidence items with same quality grade
   - Action: Pause workflow, present conflict to user

3. **Max Iteration Gate** (Any → Terminate)
   - Trigger: Total steps > 20 OR same agent called > 5 times
   - Action: Terminate and report unable to reach conclusion

4. **Empty Results Gate** (Acquire → Ask)
   - Trigger: Search returns 0 results
   - Action: Return to Ask to reformulate question

### 3.3 Gate Extension Mechanism
Pre-built gate registration interface in code. New gates can be added via configuration file without modifying core code.

## 4. Specialized Agents Design

### 4.1 Ask Agent - Question Refinement

**Responsibility**: Transform clinical question into structured PICO format, identify key elements

**Input**:
- Original clinical question
- State graph (if backtracking, includes previous search failure information)

**Tools**:
- PICO extractor
- Medical terminology standardization (MeSH mapping)

**Output**:
- Structured query (P/I/C/O elements + search keywords)

**Prompt Focus**:
- Emphasize searchability
- If backtracking scenario, analyze why previous search failed

### 4.2 Acquire Agent - Evidence Acquisition

**Responsibility**: Develop retrieval strategy, execute search, rank evidence

**Input**:
- Structured query
- Search strategy adjustment suggestions (if backtracking)

**LLM-Powered Tools**:
1. **Retrieval Strategy LLM**: Generate search strategy from PICO (keyword combinations, Boolean operators, filters)
2. **Evidence Ranking LLM**: Rank search results by relevance and perform initial screening

**Other Tools**:
- PubMed API
- Clinical guideline database interface

**Output**:
- Ranked evidence list (top N articles with metadata)

**Workflow**:
Structured query → Retrieval Strategy LLM → Execute search → Evidence Ranking LLM → Output

### 4.3 Appraise Agent - Evidence Evaluation

**Responsibility**: Assess evidence quality, detect conflicts

**Input**:
- Ranked evidence list

**LLM-Powered Tools**:
1. **Evidence Appraisal LLM**: Apply GRADE criteria to score each evidence item

**Other Tools**:
- Conflict detection algorithm
- Statistical analysis functions

**Output**:
- Quality scores
- Conflict report (if any)
- Comprehensive assessment

**Conflict Handling**:
- First compare evidence quality via GRADE
- If quality differs, no further issue
- If quality is comparable and conflicts exist, present to user

### 4.4 Apply Agent - Generate Recommendations

**Responsibility**: Synthesize appraised evidence to generate clinical recommendations and calculations

**Input**:
- Appraise output (quality-scored evidence + comprehensive assessment)
- Original clinical question

**LLM-Powered Tools**:
1. **Response Generator LLM**: Transform structured data (evidence scores, calculation results, statistical metrics) into natural language clinical recommendations, including recommendation strength, rationale, and precautions

**Other Tools**:
- Risk score calculators (CHADS2, Wells score, etc.)
- Dosage adjustment calculators (based on renal function, weight, etc.)
- Statistical analysis tools (NNT, NNH calculation)
- Recommendation strength assessment (based on evidence quality and effect size)

**Output**:
- Clinical recommendations (what to do, what not to do)
- Recommendation strength (strong/weak)
- Supporting calculation results (if applicable)
- Precautions and contraindications

**Workflow**:
Evidence + calculations → Response Generator LLM → Natural language recommendations

### 4.5 Assess Agent - Evaluate Recommendation Quality

**Responsibility**: Assess whether generated recommendations are complete and reasonable, identify potential issues

**Input**:
- Apply output
- Complete state graph

**LLM-Powered Tools**:
1. **Evidence Evaluator LLM**: Assess recommendation quality, logical consistency, evidence-recommendation alignment (ideally a specially trained model; currently using general LLM)

**Other Tools**:
- Completeness checklist (answered original question? considered contraindications?)
- Logic consistency checker

**Output**:
- Quality assessment report
- Identified gaps or issues (if any)
- Backtracking suggestions (if needed)

**Special Responsibility**:
Assess can trigger backtracking to any previous step

## 5. State Graph Structure & Data Flow

### 5.1 Node Structure

Each node represents one agent invocation:

```python
Node {
  id: unique_id,
  agent_type: "Ask" | "Acquire" | "Appraise" | "Apply" | "Assess",
  timestamp: datetime,
  inputs: {raw input data},
  outputs: {agent return results},
  tools_used: [list of tools used],
  gate_triggered: null | {gate_name, reason},
  status: "completed" | "failed" | "gated"
}
```

### 5.2 Edge Structure

Edges represent transition relationships:

```python
Edge {
  from_node: node_id,
  to_node: node_id,
  transition_type: "forward" | "backtrack" | "retry",
  reason: "normal flow" | "gate triggered" | "coordinator decision",
  coordinator_reasoning: LLM routing decision rationale (if applicable)
}
```

### 5.3 Data Flow

1. User question → Coordinator initializes state graph
2. Coordinator → Ask Agent → Create node A
3. Node A output → Gate check → No trigger → Coordinator → Acquire Agent → Create node B, add edge A→B
4. Node B output → Gate check → Trigger Empty Results Gate → Coordinator calls LLM for decision → Backtrack to Ask → Create node A', add edge B→A' (backtrack)
5. Repeat until Assess completes or termination gate triggers

### 5.4 State Graph Query Functions

- Query all history of a specific agent being called
- Query number of times a specific gate type was triggered
- Detect loops (prevent infinite A→B→A→B cycles)

## 6. Technical Stack & Implementation

### 6.1 Python Framework

**Recommended**: LangGraph as core framework
- Native state graph management (StateGraph)
- Built-in loops and conditional routing
- Integration with LangChain tool ecosystem
- Support for checkpoints and backtracking

### 6.2 Core Component Implementation

1. **Coordinator**: LangGraph conditional edges + custom routing function
2. **Agents**: LangGraph nodes, each agent is a function
3. **State Graph**: LangGraph StateGraph class + custom state schema
4. **Gate Engine**: Conditional functions executed after each agent node

### 6.3 LLM Interface

**Configuration**: OpenAI-compatible API format

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="your_api_url",
    api_key="your_key",
    model="your_model_name"
)
```

All agents and LLM-powered tools use this unified configuration.

- Use LangChain's LLM abstraction layer, supports switching different providers
- Each LLM-powered tool wrapped as LangChain Tool
- Support prompt template management and version control

### 6.4 Data Storage

- **Runtime state**: In-memory Python objects (managed by LangGraph)
- **Persistence**: SQLite stores complete state graph (for audit and analysis)
- **Evidence cache**: Local filesystem or Redis (avoid duplicate searches)

### 6.5 External API Integration

- PubMed E-utilities API (literature search)
- Reserved interface for future evidence database

## 7. Error Handling & Edge Cases

### 7.1 Error Handling Strategy

**Dynamic error handling design**: Start with core scenarios, add new handlers as issues are encountered.

**Initial Error Handlers**:

1. **LLM Call Failure** (network error, timeout, rate limit)
   - Auto-retry 3 times with exponential backoff
   - After failure, log to state graph, coordinator decides whether to terminate or skip

2. **Tool Call Failure** (PubMed API error, calculation error)
   - Log error information
   - Trigger specific gate or let agent continue with degraded strategy

3. **Gate Infinite Loop Detection**
   - State graph detects same path repeated >3 times → force terminate
   - Report loop cause to user

4. **Unable to Reach Conclusion**
   - Max iteration count reached
   - Output currently collected information and reason for inability to continue

### 7.2 Edge Cases

- User question too vague → Ask Agent refinement fails multiple times → Request user clarification
- All search results are low-quality evidence → Clearly inform insufficient evidence, provide limited recommendations
- All evidence conflicts → Present conflicts, do not force recommendations

## 8. Output Format & User Interaction

### 8.1 System Output Structure

Final output contains three levels:

**1. Executive Summary** (for clinicians)
- Clinical recommendations (natural language)
- Recommendation strength and evidence grade
- Key calculation results (if applicable)
- Precautions and contraindications

**2. Evidence Support** (expandable)
- List of evidence used (title, source, quality score)
- Conflicting evidence explanation (if any)
- Evidence-to-recommendation reasoning chain

**3. Audit Trail** (complete state graph)
- All agent invocation history
- Backtracking and gate trigger records
- Complete reasoning process

### 8.2 Interaction Modes

- **Standard mode**: User asks question → System runs automatically → Returns results
- **Conflict handling**: Encounters Evidence Conflict Gate → Pause → Present conflict → Wait for user choice or confirmation to continue
- **Failure handling**: Unable to reach conclusion → Present collected information → Ask if user wants to adjust question and retry

### 8.3 Output Format

- JSON format (easy to integrate into other systems)
- Optional Markdown report generation (easy to read and archive)

## 9. Project Structure & Code Organization

### 9.1 Directory Structure

```
ebm5a/
├── src/
│   ├── agents/              # Five specialized agents
│   │   ├── ask_agent.py
│   │   ├── acquire_agent.py
│   │   ├── appraise_agent.py
│   │   ├── apply_agent.py
│   │   └── assess_agent.py
│   ├── tools/               # LLM-powered tools and other tools
│   │   ├── retrieval_strategy.py
│   │   ├── evidence_ranking.py
│   │   ├── evidence_appraisal.py
│   │   ├── response_generator.py
│   │   ├── evidence_evaluator.py
│   │   ├── calculators.py   # Risk scores, dosage calculations, etc.
│   │   └── pubmed_api.py
│   ├── coordinator/         # Coordinator and routing logic
│   │   ├── coordinator.py
│   │   ├── gate_engine.py
│   │   └── router.py        # LLM routing decisions
│   ├── state/               # State graph management
│   │   ├── graph.py
│   │   ├── schema.py        # State data structures
│   │   └── persistence.py   # SQLite storage
│   ├── config/              # Configuration management
│   │   ├── llm_config.py
│   │   ├── gates_config.py  # Dynamic gate configuration
│   │   └── prompts/         # Prompt templates
│   └── main.py              # Entry point
├── tests/                   # Tests
├── docs/                    # Documentation
│   └── plans/              # Design documents
├── data/                    # Data and cache
│   ├── cache/              # Evidence cache
│   └── audit.db            # Audit database
└── requirements.txt
```

### 9.2 Core Module Responsibilities

- `agents/`: Each agent as independent module, contains prompt and execution logic
- `tools/`: Reusable tools, agents call via tool registry
- `coordinator/`: Orchestration logic, gate checking, routing decisions
- `state/`: State graph CRUD operations, integrates with LangGraph

## 10. Development Strategy & Future Extensions

### 10.1 Development Phases

**Phase 1: Core Workflow (MVP)**
- Implement Coordinator + 5 agent basic framework
- Use general LLM for all LLM-powered tools
- Implement 3-4 core gates
- PubMed API integration
- Simple state graph (in-memory storage)
- Test: Complete workflow for single simple clinical question

**Phase 2: Enhanced Features**
- SQLite persistence and audit trail
- Evidence caching mechanism
- More gates and error handling
- Output format optimization (JSON + Markdown)
- Test: Various types of clinical questions

**Phase 3: Optimization & Extension**
- Performance optimization (parallel search, caching strategy)
- More calculation tools (risk scores, dosage adjustment)
- Loop detection and protection
- User interaction improvements

### 10.2 Future Extension Points

**1. Evidence Database Construction**
- Reserved database interface (in `tools/`)
- When evidence database available, Acquire Agent can query both PubMed and local database

**2. Specialized Model Training**
- Evidence Evaluator LLM can be fine-tuned with annotated data
- Reserved model switching interface (in `config/llm_config.py`)

**3. Multi-language Support**
- Prompt template internationalization
- Medical terminology multi-language mapping

## 11. Key Design Principles

1. **Hard rules as primary gates**: Reliability and explainability for clinical decisions
2. **Dynamic extension**: Both gates and error handlers start minimal and expand based on actual use
3. **Full traceability**: State graph provides complete audit trail
4. **Flexible backtracking**: ReAct pattern allows jumping between any 5A steps
5. **Evidence-first**: Grade evidence quality before making recommendations
6. **Conflict transparency**: Present conflicts when evidence quality is comparable

---

**End of Design Document**
