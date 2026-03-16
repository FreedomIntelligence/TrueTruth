# Open-Source Quality Improvements — Design Spec

**Date:** 2026-03-16
**Scope:** Additive-only changes (zero modifications to existing `src/` code)
**Constraint:** Every change in this spec must be a new file or a non-breaking edit to a config file.

---

## Problem Statement

The project has a complete, working implementation but lacks the scaffolding expected of a public open-source project. The gaps fall into three priority tiers:

- **P0 — Legal & security blockers**: No LICENSE file; `.env.example` contains real credentials and is gitignored (unavailable to contributors)
- **P1 — Contributor experience**: No CI/CD, no issue/PR templates, no CONTRIBUTING.md
- **P2 — Packaging & documentation hygiene**: No `pyproject.toml`; internal dev artifacts clutter root and `docs/`

---

## P0 Changes

### 1. `LICENSE`
- **Action:** Create `/LICENSE` with standard MIT text
- **Content:** Year 2026, placeholder `<author>`
- **Why:** README declares MIT but there is no LICENSE file; legally all rights are reserved without it

### 2. `.env.example` — fix and unblock
- **Action:** Create a clean `/data/wuyuang/ebm5a/.env.example` with all values replaced by descriptive placeholders; remove `.env.example` from `.gitignore`
- **Content:**
  ```dotenv
  LLM_BASE_URL=https://api.openai.com/v1
  LLM_API_KEY=your_api_key_here
  LLM_MODEL=gpt-4
  PUBMED_EMAIL=your_email@example.com
  # FAST_LLM_MODEL=gpt-3.5-turbo
  ```
- **Why:** Current file contains real credentials; it is also gitignored, so cloners get no template

### 3. `.gitignore` — tighten
- **Action:** Edit `.gitignore` to:
  - Remove the `.env.example` line (it should be tracked)
  - Add `*.log`, `nul`, `COMPLETION_SUMMARY.md`, `IMPLEMENTATION_STATUS.md` to keep root clean going forward
- **Note:** Does NOT delete existing files; only prevents future noise

---

## P1 Changes

### 4. GitHub Actions CI — `.github/workflows/ci.yml`
- **Trigger:** `push` and `pull_request` on `main`
- **Jobs:** `lint` (flake8, optional), `test` (pytest with `--tb=short`)
- **Python version:** 3.10
- **Why:** Even with zero tests today, the workflow infrastructure is in place; contributors see a green/red badge

### 5. Issue Templates — `.github/ISSUE_TEMPLATE/`
- `bug_report.md` — fields: description, steps to reproduce, expected vs actual, environment (Python version, LLM provider, OS)
- `feature_request.md` — fields: problem statement, proposed solution, alternatives considered

### 6. PR Template — `.github/PULL_REQUEST_TEMPLATE.md`
- Sections: Summary, Type of change (bug fix / feature / docs), Testing done, Checklist

### 7. `CONTRIBUTING.md`
- Sections: Prerequisites, Local setup, Running tests (`pytest`), Code style, Commit conventions, PR process
- Links back to README for project overview

---

## P2 Changes

### 8. `pyproject.toml`
- **Action:** Create `/pyproject.toml` alongside existing `requirements.txt` (does not replace it)
- **Content:** `[project]` metadata (name, version, description, Python ≥3.10, dependencies mirroring requirements.txt), `[build-system]` using setuptools
- **Why:** Enables `pip install -e .` for local dev; makes the project importable as a package without sys.path hacks

### 9. Reorganise `docs/`
- **Action:** Create `docs/internal/` and move internal dev artifacts there
- **Files to move:** `docs/acquire_agent_fix.md`, `docs/mvp_implementation_complete.md`, `docs/analysis/`, `docs/plans/`
- **New file:** `docs/architecture.md` — a real public-facing architecture overview (stub that links to README sections)
- **Root files to move:** `COMPLETION_SUMMARY.md`, `IMPLEMENTATION_STATUS.md`, `description.md` → `docs/internal/`
- **Why:** `docs/` currently contains only internal working notes; README references `docs/` as if it has user-facing content

---

## Out of Scope

- Any changes to `src/` (agents, coordinator, tools, config, state)
- Any changes to `requirements.txt` pinned versions (dependency upgrade is a separate decision)
- Adding actual test cases (CI scaffold only; tests are left for a future iteration)

---

## File Change Summary

| File | Action |
|------|--------|
| `LICENSE` | Create |
| `.env.example` | Create (placeholder values) |
| `.gitignore` | Edit (remove `.env.example` line, add noise patterns) |
| `.github/workflows/ci.yml` | Create |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Create |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Create |
| `.github/PULL_REQUEST_TEMPLATE.md` | Create |
| `CONTRIBUTING.md` | Create |
| `pyproject.toml` | Create |
| `docs/internal/` | Create dir; move internal docs |
| `docs/architecture.md` | Create (stub) |
| `COMPLETION_SUMMARY.md` → `docs/internal/` | Move |
| `IMPLEMENTATION_STATUS.md` → `docs/internal/` | Move |
| `description.md` → `docs/internal/` | Move |

**Total: 9 new files, 1 edited file, 3 files moved. Zero `src/` changes.**
