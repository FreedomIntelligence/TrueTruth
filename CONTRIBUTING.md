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
