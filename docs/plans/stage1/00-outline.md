# EBM 5A Stage 1 MVP - Implementation Plan Outline

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core workflow of the EBM 5A clinical decision support system with basic coordinator, 5 agents, core gates, and PubMed integration.

**Architecture:** Multi-agent architecture using LangGraph for state management. Central coordinator routes between 5 specialized agents (Ask/Acquire/Appraise/Apply/Assess) with hard rule gates and LLM-assisted routing.

**Tech Stack:** Python 3.10+, LangGraph, LangChain, PubMed E-utilities API, pytest

---

## Plan Structure

This implementation plan is divided into the following documents:

1. **00-outline.md** (this file) - Overview and plan structure
2. **01-scope.md** - Detailed scope, goals, and success criteria
3. **02-architecture.md** - Technical architecture and design decisions
4. **03-tasks.md** - Step-by-step implementation tasks with code
5. **04-risks.md** - Risks, edge cases, and mitigation strategies

## Quick Start

To execute this plan:
1. Read all 5 documents to understand the full scope
2. Start with Task 1 in `03-tasks.md`
3. Follow TDD approach: write test → run test (fail) → implement → run test (pass) → commit
4. Each task should take 2-5 minutes
5. Commit frequently with descriptive messages

## Key Principles

- **TDD First**: Write failing tests before implementation
- **DRY**: Don't repeat yourself - extract common patterns
- **YAGNI**: You aren't gonna need it - build only what's required for MVP
- **Frequent Commits**: Commit after each passing test
- **Hard Rules for Gates**: Use deterministic rules, not LLM judgment for gate conditions
- **Complete Traceability**: State graph tracks all decisions

## MVP Scope Summary

**In Scope:**
- Basic coordinator with state graph management
- 5 specialized agents (Ask/Acquire/Appraise/Apply/Assess)
- 3-4 core gates (evidence quality, empty results, max iterations, conflicts)
- PubMed API integration
- In-memory state storage
- Simple CLI interface
- Basic end-to-end test with one clinical question

**Out of Scope (Future Phases):**
- SQLite persistence
- Evidence caching
- Advanced calculators (risk scores, dosage)
- Multi-language support
- Web UI
- Local evidence database
