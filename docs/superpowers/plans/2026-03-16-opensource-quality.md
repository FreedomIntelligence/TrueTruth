# Open-Source Quality Improvements — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the scaffolding (LICENSE, CI, contributor docs, packaging, doc structure) that a working codebase needs before it can be treated as a serious open-source project.

**Architecture:** All changes are purely additive — new files created, a few config files edited, internal dev-note files moved to `docs/internal/`. Zero changes to `src/`. The two operations that touch existing files (`.env.example` sanitisation and `.gitignore` edit) are ordered to prevent any credential exposure.

**Tech Stack:** Python 3.10, pytest, GitHub Actions, setuptools/pyproject.toml, standard Markdown templates.

---

## Chunk 1: P0 — Legal & Security

### Task 1: Sanitise `.env.example`

> ⚠️ This task MUST be completed and committed before Task 2. Reversing the order risks staging real credentials.

**Files:**
- Edit: `.env.example`

- [ ] **Step 1: Overwrite `.env.example` with placeholder-only content**

Replace the entire file with:

```dotenv
# Copy this file to .env and fill in your values.
# NEVER commit .env — it is gitignored.

# Required
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com

# Optional: use a faster/cheaper model for Judge and Scheduling (~30-40% faster)
# FAST_LLM_MODEL=gpt-3.5-turbo
```

- [ ] **Step 2: Verify no real credentials remain**

```bash
grep -E "(sk-|@gmail|huatuo)" .env.example
```
Expected: no output (zero matches).

- [ ] **Step 3: Commit sanitised template (still gitignored at this point)**

```bash
git add .env.example
git commit -m "security: replace real credentials in .env.example with placeholders"
```

---

### Task 2: Edit `.gitignore` — unblock template and tighten rules

**Files:**
- Edit: `.gitignore`

- [ ] **Step 1: Make the following changes to `.gitignore` in a single edit**

  - **Remove** the line: `.env.example`  ← allows the sanitised template to be tracked
  - **Remove** the line: `QUICKSTART.md`  ← README links to this file; it must be visible to cloners
  - **Add** the line: `*.log`  ← covers any `.log` files written to the project root (the existing `logs/` entry covers the directory but not root-level log files)
  - Leave `nul` as-is — it is already present; do not add a duplicate.

- [ ] **Step 2: Verify `.env.example` is now tracked**

`.env.example` was already committed in Task 1 — use `git ls-files` (not `git status`) to confirm it is tracked:

```bash
git ls-files .env.example
```
Expected: `.env.example` (file appears in the tracked list).

- [ ] **Step 3: Verify `QUICKSTART.md` is now tracked**

```bash
git ls-files QUICKSTART.md
```
Expected: `QUICKSTART.md` (file appears in the tracked list).

- [ ] **Step 4: Commit**

Do NOT re-stage `.env.example` — it is unchanged since Task 1's commit. Stage only the files modified in this task:

```bash
git add .gitignore QUICKSTART.md
git commit -m "chore: unblock .env.example and QUICKSTART.md; add *.log to gitignore"
```

---

### Task 3: Add `LICENSE`

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Create `LICENSE` with MIT text**

```
MIT License

Copyright (c) 2026 EBM 5A Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Verify file exists and starts with "MIT License"**

```bash
head -1 LICENSE
```
Expected: `MIT License`

- [ ] **Step 3: Commit**

```bash
git add LICENSE
git commit -m "chore: add MIT LICENSE file"
```

---

## Chunk 2: P1 — Contributor Experience

### Task 4: Create `requirements-dev.txt`

**Files:**
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create the file**

Pinned versions are copied verbatim from `requirements.txt`, minus `torch` and `transformers` (too heavy for CI):

```
langchain==0.1.0
langchain-openai==0.0.5
langgraph==0.0.20
requests==2.31.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
python-dotenv==1.0.0
```

- [ ] **Step 2: Verify all versions match `requirements.txt`**

```bash
grep -f <(grep -v "torch\|transformers" requirements.txt | grep "==") requirements-dev.txt
```
Expected: all lines echo back (every pinned version is present).

- [ ] **Step 3: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore: add requirements-dev.txt for CI (excludes heavy torch/transformers)"
```

---

### Task 5: Create GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/` directory and `ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements-dev.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest --tb=short
```

- [ ] **Step 2: Verify YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```
Expected: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (pytest on push/PR)"
```

---

### Task 6: Create Issue Templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`

- [ ] **Step 1: Create `bug_report.md`**

```markdown
---
name: Bug report
about: Something is not working as expected
labels: bug
---

## Description
A clear description of what the bug is.

## Steps to Reproduce
1. Run: `python -m src.main "..."`
2. See error

## Expected Behaviour
What you expected to happen.

## Actual Behaviour
What actually happened. Include the full error message and traceback if applicable.

## Environment
- OS:
- Python version (`python --version`):
- LLM provider / model:
- EBM 5A version / commit:
```

- [ ] **Step 2: Create `feature_request.md`**

```markdown
---
name: Feature request
about: Suggest an improvement or new capability
labels: enhancement
---

## Problem Statement
What problem does this feature solve? Who is affected?

## Proposed Solution
Describe the feature you'd like.

## Alternatives Considered
What other approaches did you consider, and why did you rule them out?

## Additional Context
Any other context, references, or screenshots.
```

- [ ] **Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "docs: add GitHub issue templates (bug report, feature request)"
```

---

### Task 7: Create PR Template

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Create the file**

```markdown
## Summary
_What does this PR do? Why?_

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactor / performance improvement
- [ ] Other (describe):

## Testing Done
_Describe how you tested this change. If you added or modified tests, list them here._

```bash
pytest
```

## Checklist
- [ ] I have read `CONTRIBUTING.md`
- [ ] My changes do not modify files under `src/` in a breaking way
- [ ] I have updated the relevant documentation (README, CHANGELOG, docstrings)
- [ ] Tests pass locally (`pytest`)
```

- [ ] **Step 2: Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "docs: add pull request template"
```

---

### Task 8: Create `CONTRIBUTING.md`

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Create the file**

```markdown
# Contributing to EBM 5A

Thank you for your interest in contributing. This guide covers everything you need to get started.

---

## Prerequisites

- Python 3.10+
- A PubMed-registered e-mail address (required by NCBI API policy)
- An OpenAI-compatible API key

---

## Local Setup

```bash
# 1. Fork and clone
git clone https://github.com/your-fork/ebm5a.git
cd ebm5a

# 2. Install full dependencies (includes torch/transformers for MedCPT)
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API key, model, and PubMed email

# 4. Verify setup
python -m src.main "Should aspirin be used for primary prevention in a 60-year-old?"
```

For running tests only (no GPU/torch required):

```bash
pip install -r requirements-dev.txt
```

---

## Running Tests

```bash
pytest                              # all tests
pytest --tb=short                   # concise failure output
pytest --cov=src --cov-report=html  # with coverage report
```

There are currently no automated tests — the test suite is a work in progress. If you are contributing a new feature or bug fix, adding a test is strongly encouraged.

---

## Code Style

- Follow existing patterns in the file you are editing.
- No hard tabs; use 4-space indentation.
- Keep files focused: each agent, tool, and module has a single clear responsibility.

---

## Commit Conventions

Use the conventional commit format:

```
type: short description (imperative, ≤72 chars)
```

Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`

Examples:
- `feat: add support for Harm question type in Acquire agent`
- `fix: handle empty PubMed result in three-tier fallback`
- `docs: update README installation section`

---

## Pull Request Process

1. Open an issue first for non-trivial changes — discuss the approach before writing code.
2. Fork the repo, create a feature branch: `git checkout -b feat/your-feature`.
3. Keep PRs focused on a single concern.
4. Ensure `pytest` passes locally before opening the PR.
5. Fill in the PR template.
6. A maintainer will review and merge.

---

## Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).
Include the full error traceback, your LLM provider and model, and the exact clinical question that triggered the issue.
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md"
```

---

## Chunk 3: P2 — Packaging & Doc Hygiene

### Task 9: Create `pyproject.toml`

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create the file**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ebm5a"
version = "0.1.0"
description = "Evidence-Based Medicine Clinical Decision Support System — multi-agent 5A pipeline"
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.10"
keywords = ["evidence-based medicine", "clinical decision support", "EBM", "PubMed", "GRADE", "LLM", "agents"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Topic :: Scientific/Engineering :: Medical Science Apps.",
]
dependencies = [
    "langchain==0.1.0",
    "langchain-openai==0.0.5",
    "langgraph==0.0.20",
    "requests==2.31.0",
    "python-dotenv==1.0.0",
    "torch>=2.0.0",
    "transformers>=4.36.0",
]

[project.scripts]
ebm5a = "src.main:main"

[project.urls]
Homepage = "https://github.com/your-org/ebm5a"
"Bug Tracker" = "https://github.com/your-org/ebm5a/issues"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Verify TOML is valid**

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))" && echo "TOML OK"
```
Expected: `TOML OK`

- [ ] **Step 3: Verify editable install works**

```bash
pip install -e . --no-deps --quiet && python -c "from src.main import main; print('import OK')"
```
Expected: `import OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pyproject.toml for package metadata and editable install"
```

---

### Task 10: Reorganise `docs/` — move internal files

**Files:**
- Move (via `git mv`): 7 files/dirs → `docs/internal/`

> Note: `git mv` preserves history. `docs/superpowers/` is intentionally left in place (it is a design record, not an internal dev artifact). `CHANGELOG.md` is intentionally left in root (standard open-source convention).

- [ ] **Step 1: Create `docs/internal/` and move files**

```bash
mkdir -p docs/internal

git mv docs/acquire_agent_fix.md        docs/internal/acquire_agent_fix.md
git mv docs/mvp_implementation_complete.md docs/internal/mvp_implementation_complete.md
git mv docs/analysis                    docs/internal/analysis
git mv docs/plans                       docs/internal/plans
git mv COMPLETION_SUMMARY.md            docs/internal/COMPLETION_SUMMARY.md
git mv IMPLEMENTATION_STATUS.md         docs/internal/IMPLEMENTATION_STATUS.md
git mv description.md                   docs/internal/description.md
```

- [ ] **Step 2: Verify moves completed cleanly**

```bash
git status --short | grep "^R"
```
Expected: 7 rename lines, one per moved item.

- [ ] **Step 3: Verify `docs/superpowers/` and `CHANGELOG.md` are untouched**

```bash
ls docs/superpowers/specs/ && ls CHANGELOG.md
```
Expected: both exist with no errors.

- [ ] **Step 4: Commit**

`git mv` already stages the renames; commit directly without re-running `git add`:

```bash
git commit -m "refactor: move internal dev notes to docs/internal/"
```

---

### Task 11: Create `docs/architecture.md`

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Create the stub**

```markdown
# Architecture Overview

EBM 5A is a multi-agent pipeline that operationalises the Evidence-Based Medicine **5A framework**
(Ask → Acquire → Appraise → Apply → Assess) using a **ReAct** control loop.

For the full architecture description, see the README:

- [How It Works](../README.md#how-it-works) — pipeline diagram and scheduling rules
- [Project Structure](../README.md#project-structure) — file-level breakdown
- [Key Engineering Decisions](../README.md#key-engineering-decisions) — design rationale

For the detailed design spec, see:
- [`docs/superpowers/specs/2026-03-16-opensource-quality-design.md`](superpowers/specs/2026-03-16-opensource-quality-design.md)
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture.md stub linking to README sections"
```

---

### Task 12: Update `README.md` Documentation table

**Files:**
- Edit: `README.md` (two tables — English and Chinese)

- [ ] **Step 1: Add `docs/internal/` row to the English Documentation table**

Find the English Documentation table (search for `| Architecture design`). Add one row:

```markdown
| Internal development notes | [`docs/internal/`](docs/internal/) |
```

- [ ] **Step 2: Add the same row to the Chinese Documentation table**

Find the Chinese Documentation table (search for `| 架构设计文档`). Add one row:

```markdown
| 内部开发记录 | [`docs/internal/`](docs/internal/) |
```

- [ ] **Step 3: Verify both tables render correctly**

```bash
grep -n "docs/internal" README.md
```
Expected: 2 lines (one per language section).

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add docs/internal/ entry to README documentation tables"
```

---

## Final Verification

- [ ] Run `git log --oneline` — expect 12+ new commits on top of the previous baseline
- [ ] Run `pip install -e . --no-deps --quiet` — expect success
- [ ] Run `python -c "from src.main import main"` — expect no import error
- [ ] Confirm `LICENSE` exists: `head -1 LICENSE` — expect `MIT License`
- [ ] Confirm no real credentials in repo: `git grep -rE "(sk-P|@gmail|huatuo)" -- ':!*.log'` — expect no output
- [ ] Confirm `.env.example` is tracked: `git ls-files .env.example` — expect `.env.example`
- [ ] Confirm `QUICKSTART.md` is tracked: `git ls-files QUICKSTART.md` — expect `QUICKSTART.md`
- [ ] Confirm CI file valid: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo OK`
- [ ] Confirm TOML valid: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))" && echo OK`
- [ ] Confirm `CHANGELOG.md` still in root: `ls CHANGELOG.md` — expect `CHANGELOG.md`
- [ ] Confirm `docs/superpowers/` untouched: `ls docs/superpowers/specs/` — expect spec file listed
- [ ] Confirm `docs/internal/` populated: `ls docs/internal/` — expect 7 items
