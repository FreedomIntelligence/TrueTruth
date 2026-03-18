# Stage 1 MVP - Scope and Goals

## Project Context

**Problem:** Clinicians need evidence-based decision support but lack tools that systematically apply the EBM 5A framework (Ask-Acquire-Appraise-Apply-Assess).

**Solution:** Build a ReAct-based system that takes a clinical question and produces evidence-based recommendations through the complete 5A workflow.

**Current State:**
- No evidence database exists yet
- Using general-purpose LLMs only
- Need to clarify ReAct structure (Reason/Act/Observe points and gate triggers)

## Stage 1 MVP Goals

### Primary Goal
Create a working end-to-end system that can:
1. Accept a single clinical question (e.g., "Should I prescribe aspirin for this patient?")
2. Process it through all 5A stages
3. Return an evidence-based recommendation with quality assessment
4. Provide complete audit trail of the decision process

### Success Criteria

**Must Have:**
- [ ] System successfully processes at least one simple clinical question end-to-end
- [ ] All 5 agents (Ask/Acquire/Appraise/Apply/Assess) are implemented and functional
- [ ] Coordinator correctly routes between agents based on gate conditions
- [ ] At least 3 core gates are implemented and working
- [ ] PubMed API integration returns real search results
- [ ] State graph captures complete execution history
- [ ] Basic tests pass for each component

**Quality Criteria:**
- [ ] Code follows TDD approach (tests written first)
- [ ] Each module has >80% test coverage
- [ ] All commits follow conventional commit format
- [ ] Documentation exists for each major component

### Non-Goals (Explicitly Out of Scope)

**Not in Stage 1:**
- Persistent storage (SQLite) - use in-memory only
- Evidence caching - acceptable to re-fetch
- Advanced calculators (CHADS2, Wells score, etc.) - placeholder only
- Conflict resolution UI - just log conflicts
- Performance optimization - correctness over speed
- Multi-turn user interaction - single question only
- Error recovery beyond basic retry
- Production deployment concerns

## Functional Requirements

### FR1: Question Processing (Ask Agent)
- Input: Natural language clinical question
- Output: Structured PICO format (Patient/Intervention/Comparison/Outcome)
- Must: Extract key medical terms and generate searchable keywords

### FR2: Evidence Acquisition (Acquire Agent)
- Input: Structured PICO query
- Output: Ranked list of evidence (papers, guidelines)
- Must: Query PubMed API with appropriate search strategy
- Must: Return at least top 5 relevant results

### FR3: Evidence Appraisal (Appraise Agent)
- Input: List of evidence
- Output: Quality scores (GRADE framework) and conflict detection
- Must: Assign quality level (High/Moderate/Low/Very Low) to each evidence
- Must: Detect conflicting recommendations

### FR4: Recommendation Generation (Apply Agent)
- Input: Appraised evidence
- Output: Clinical recommendation with strength rating
- Must: Synthesize evidence into actionable recommendation
- Must: Indicate recommendation strength (Strong/Weak)

### FR5: Quality Assessment (Assess Agent)
- Input: Generated recommendation + full state graph
- Output: Quality report and gap identification
- Must: Check if recommendation answers original question
- Must: Identify missing information or quality issues

### FR6: Coordinator & Gates
- Must: Route requests to appropriate agents
- Must: Track execution in state graph
- Must: Implement 3-4 core gates:
  1. Evidence quality gate (low quality → backtrack)
  2. Empty results gate (no results → refine question)
  3. Max iterations gate (prevent infinite loops)
  4. Conflict gate (conflicting evidence → report to user)

## Technical Requirements

### TR1: Framework
- Use LangGraph for state management
- Use LangChain for LLM abstraction
- Python 3.10+

### TR2: External APIs
- PubMed E-utilities API for literature search
- OpenAI-compatible API for LLM calls

### TR3: Testing
- pytest for all tests
- Minimum 80% code coverage
- Unit tests for each agent
- Integration test for full workflow

### TR4: Code Quality
- Type hints for all functions
- Docstrings for all public functions
- Follow PEP 8 style guide
- No hardcoded credentials (use .env)

## User Stories

**US1: Simple Clinical Question**
```
As a clinician
I want to ask "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"
So that I receive an evidence-based recommendation with quality assessment
```

**US2: Audit Trail**
```
As a clinician
I want to see which evidence was used and how the recommendation was derived
So that I can trust and verify the system's reasoning
```

**US3: Quality Transparency**
```
As a clinician
I want to know the quality level of the evidence (High/Moderate/Low/Very Low)
So that I can judge how confident to be in the recommendation
```

## Acceptance Test Scenario

**Scenario: Aspirin for Primary Prevention**

```
Given the system is running
When I input: "Should I prescribe aspirin for primary prevention in a 60-year-old patient with no cardiovascular disease?"
Then the system should:
1. Extract PICO: P=60yo no CVD, I=aspirin, C=no aspirin, O=cardiovascular events
2. Search PubMed and find relevant studies
3. Appraise evidence quality (expect Moderate to High quality RCTs)
4. Generate recommendation (likely: Weak recommendation against, due to bleeding risk vs benefit)
5. Assess recommendation completeness
6. Return structured output with:
   - Recommendation text
   - Strength (Strong/Weak)
   - Evidence quality (High/Moderate/Low/Very Low)
   - Key evidence sources (2-3 papers)
   - Audit trail (state graph)
```

## Deliverables

1. **Source Code**
   - All modules in `src/` directory
   - All tests in `tests/` directory
   - Configuration in `src/config/`

2. **Documentation**
   - README.md with setup instructions
   - API documentation for each agent
   - Example usage

3. **Tests**
   - Unit tests for each component
   - Integration test for end-to-end workflow
   - Test coverage report

4. **Demo**
   - Working CLI that processes one clinical question
   - Output showing complete 5A workflow
   - State graph visualization (text format acceptable)
