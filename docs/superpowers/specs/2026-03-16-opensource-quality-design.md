# Open-Source Quality Improvements — Design Spec

**Date:** 2026-03-16
**Scope:** Additive-only changes (zero modifications to existing `src/` code)
**Constraint:** Every change in this spec must be a new file, a non-breaking edit to a config file, or a git-tracked file move that is explicitly documented together with any README/link impact.

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

### 2. `.env.example` — sanitise then unblock
- **Action:** Two-step operation, ORDER IS CRITICAL:
  1. **Step 1 — Overwrite content first:** Replace the existing `.env.example` with placeholder-only content (see below). This must happen before any `.gitignore` change.
  2. **Step 2 — Remove from `.gitignore`:** Only after the file contains no real credentials, remove the `.env.example` line from `.gitignore` so the sanitised template enters version control.
- **Placeholder content:**
  ```dotenv
  LLM_BASE_URL=https://api.openai.com/v1
  LLM_API_KEY=your_api_key_here
  LLM_MODEL=gpt-4
  PUBMED_EMAIL=your_email@example.com
  # FAST_LLM_MODEL=gpt-3.5-turbo
  ```
- **Why two steps in this order:** If `.gitignore` is edited first, git immediately sees the file with real credentials as untracked and an accidental `git add .` would stage them. Always sanitise content first.

### 3. `.gitignore` — tighten (second edit, separate from step 2 above)
- **Action:** In the same edit where `.env.example` is removed from ignore:
  - Remove: `.env.example` line
  - Add: `*.log` (not already present)
  - Skip `nul` — it is already present on line 18; do not add a duplicate
  - Remove: `QUICKSTART.md` line (see item 3b below)
- **Note:** `COMPLETION_SUMMARY.md`, `IMPLEMENTATION_STATUS.md`, `description.md` are handled in P2; add them to `.gitignore` only if they are NOT moved to `docs/internal/`

### 3b. `QUICKSTART.md` — unblock
- **Action:** Remove `QUICKSTART.md` from `.gitignore` so the file becomes tracked
- **Why:** README's Documentation table in both English and Chinese sections links to `QUICKSTART.md`, but the file is currently gitignored, making that link silently broken for anyone who clones the repo. The file exists on disk and contains useful quick-start content; it should simply be tracked.

---

## P1 Changes

### 4. GitHub Actions CI — `.github/workflows/ci.yml`
- **Trigger:** `push` and `pull_request` on `main`
- **Dependency strategy:** `torch` and `transformers` are heavy (~2–3 GB) and have no unit tests against them in this repo. The CI job installs from a separate `requirements-dev.txt` (created as part of this change) that contains only lightweight test/lint dependencies, NOT torch/transformers. This avoids runner timeouts and cache bloat.
- **`requirements-dev.txt` content:** `langchain==0.1.0`, `langchain-openai==0.0.5`, `langgraph==0.0.20`, `requests==2.31.0`, `pytest==7.4.3`, `pytest-cov==4.1.0`, `pytest-mock==3.12.0`, `python-dotenv==1.0.0`
- **Jobs:** `test` (pytest with `--tb=short`, using `requirements-dev.txt`)
- **Python version matrix:** 3.10
- **Why:** Even with zero tests today, the CI scaffold is in place; contributors see a badge and the framework runs on PRs

### 5. Issue Templates — `.github/ISSUE_TEMPLATE/`
- `bug_report.md` — fields: description, steps to reproduce, expected vs actual, environment (Python version, LLM provider, OS)
- `feature_request.md` — fields: problem statement, proposed solution, alternatives considered

### 6. PR Template — `.github/PULL_REQUEST_TEMPLATE.md`
- Sections: Summary, Type of change (bug fix / feature / docs), Testing done, Checklist

### 7. `CONTRIBUTING.md`
- Sections: Prerequisites, Local setup (`pip install -r requirements.txt` for full; `requirements-dev.txt` for test-only), Running tests (`pytest`), Code style, Commit conventions, PR process
- Links back to README for project overview

---

## P2 Changes

### 8. `pyproject.toml`
- **Action:** Create `/pyproject.toml` alongside existing `requirements.txt` (does not replace it)
- **Content:** `[project]` metadata (name `ebm5a`, version `0.1.0`, description, Python ≥3.10, dependencies mirroring requirements.txt), `[build-system]` using `setuptools`
- **Why:** Enables `pip install -e .` for local dev; makes the project importable without sys.path hacks

### 9. Reorganise `docs/`
- **Scope:** Internal working-note files are moved to `docs/internal/`. `docs/superpowers/` (this spec and future specs) is explicitly **out of scope** — it is not an internal dev artifact but a design record that should remain in `docs/`.
- **Files to move via `git mv`:**
  - `docs/acquire_agent_fix.md` → `docs/internal/acquire_agent_fix.md`
  - `docs/mvp_implementation_complete.md` → `docs/internal/mvp_implementation_complete.md`
  - `docs/analysis/` → `docs/internal/analysis/`
  - `docs/plans/` → `docs/internal/plans/`
- **Root files to move via `git mv`:**
  - `COMPLETION_SUMMARY.md` → `docs/internal/COMPLETION_SUMMARY.md`
  - `IMPLEMENTATION_STATUS.md` → `docs/internal/IMPLEMENTATION_STATUS.md`
  - `description.md` → `docs/internal/description.md`
- **Root files intentionally left in place:** `CHANGELOG.md` — this is a standard open-source convention file; it belongs in the project root alongside README and LICENSE and must NOT be moved.
- **README impact:** README references `docs/` in the Documentation table as "Architecture design". After the move, `docs/` will contain `docs/internal/`, `docs/superpowers/`, and the new `docs/architecture.md` stub. The README link still resolves to a valid directory. The README Documentation table must be updated to add a row for `docs/internal/` ("Internal development notes") to reflect the new structure. This README edit is included in the file change summary below.

### 10. `docs/architecture.md` (stub)
- **Action:** Create `docs/architecture.md` as a minimal public-facing architecture overview
- **Content:** One-paragraph summary + links to the relevant README sections (How It Works, Project Structure)
- **Why:** README's Documentation table promises an architecture doc at `docs/`; this fulfils that promise

---

## Out of Scope

- Any changes to `src/` (agents, coordinator, tools, config, state)
- Any changes to `requirements.txt` pinned versions (dependency upgrade is a separate decision)
- Adding actual test cases (CI scaffold only; tests are left for a future iteration)
- Moving `docs/superpowers/` (this is a design record, not an internal dev artifact)

---

## File Change Summary

| File | Action |
|------|--------|
| `LICENSE` | **Create** |
| `.env.example` | **Edit** (overwrite with placeholders — must precede .gitignore edit) |
| `.gitignore` | **Edit** (remove `.env.example` line; add `*.log`, `nul`) |
| `requirements-dev.txt` | **Create** (lightweight deps for CI) |
| `.github/workflows/ci.yml` | **Create** |
| `.github/ISSUE_TEMPLATE/bug_report.md` | **Create** |
| `.github/ISSUE_TEMPLATE/feature_request.md` | **Create** |
| `.github/PULL_REQUEST_TEMPLATE.md` | **Create** |
| `CONTRIBUTING.md` | **Create** |
| `pyproject.toml` | **Create** |
| `docs/architecture.md` | **Create** (stub) |
| `docs/internal/` | **Create dir** |
| `docs/acquire_agent_fix.md` | **Move** → `docs/internal/` |
| `docs/mvp_implementation_complete.md` | **Move** → `docs/internal/` |
| `docs/analysis/` | **Move** → `docs/internal/analysis/` |
| `docs/plans/` | **Move** → `docs/internal/plans/` |
| `COMPLETION_SUMMARY.md` | **Move** → `docs/internal/` |
| `IMPLEMENTATION_STATUS.md` | **Move** → `docs/internal/` |
| `description.md` | **Move** → `docs/internal/` |
| `QUICKSTART.md` | **Unblock** (remove from `.gitignore`) |

| `README.md` | **Edit** (update Documentation table to include `docs/internal/` row) |

**Total: 10 new files, 4 edited files, 7 items moved, 1 unblocked. Zero `src/` changes.**
