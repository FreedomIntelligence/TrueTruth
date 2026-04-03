# Repo Usability Improvements Design

**Date:** 2026-04-03
**Status:** Approved
**Scope:** Developer experience, deployment, CI, documentation — no changes to business logic or agent code

---

## 1. Motivation

EBM 5A is a well-architected, research-grade system. The primary friction for new users and contributors is not code quality but discoverability and setup guidance. Specific gaps identified:

- No Docker deployment or one-command startup
- Web UI entirely undocumented in README
- No CI pipeline (no build status, no automated test/lint gates)
- No unified command entry point (Makefile)
- No setup validation before first run
- No troubleshooting guide or glossary
- No issue/PR templates

This spec covers all improvements in a single implementation pass (Approach A: comprehensive at once).

---

## 2. File Change Summary

### New files

| File | Purpose |
|------|---------|
| `Dockerfile.backend` | Python/FastAPI container |
| `Dockerfile.frontend` | Multi-stage Node build + Nginx static server |
| `docker-compose.yml` | Production one-command full-stack startup |
| `docker-compose.dev.yml` | Development override (source mounts, hot reload) |
| `.dockerignore` | Exclude logs, cache, .env, __pycache__ from build context |
| `Makefile` | Unified command entry point |
| `scripts/check_env.py` | .env validation script |
| `.github/workflows/ci.yml` | GitHub Actions CI (lint + test + docker-build) |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Bug report template |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Feature request template |
| `.github/pull_request_template.md` | PR template |
| `docs/troubleshooting.md` | Common errors and fixes |
| `docs/glossary.md` | GRADE, PICO, recommendation strengths, Judge score |

### Modified files

| File | Change |
|------|--------|
| `README.md` | Add badges, Web UI section, Docker quick start, screenshot placeholder |
| `QUICKSTART.md` | Add Docker startup instructions |

### Unchanged

- All `src/` agent/coordinator/judge/scheduling code
- All `web/` frontend and backend code
- `docs/internal/` (historical docs preserved as-is)

---

## 3. Docker Deployment

### Architecture

Two services defined in `docker-compose.yml`:

```
backend   — Python 3.11-slim, runs FastAPI via uvicorn on port 8000
frontend  — Multi-stage: node:20-alpine builds Vite bundle, nginx:alpine serves static files on port 80
```

No third service in this pass (Redis/queue deferred to future).

### Key decisions

- **`.env` injected via `env_file`, never COPY'd into image** — prevents accidental secret leakage in image layers
- **`data/cache/` and `logs/` mounted as named volumes** — PubMed cache and run logs persist across container restarts
- **Nginx reverse-proxies `/api` → `backend:8000`** — eliminates CORS issues; frontend uses a single origin
- **Frontend `VITE_API_URL` set to `/api` at build time** — aligns with Nginx proxy path
- **`docker-compose.dev.yml` override** — mounts `src/` and `web/` as volumes for hot reload during development

### User experience

```bash
cp .env.example .env      # fill in API key and PubMed email
make docker-up            # docker compose up --build -d
# open http://localhost
```

### Dockerfile details

**`Dockerfile.backend`**
- Base: `python:3.11-slim`
- Install `requirements.txt` then `requirements-web.txt`
- Working directory: `/app`
- Entrypoint: `uvicorn web.backend.app:app --host 0.0.0.0 --port 8000`

**`Dockerfile.frontend`**
- Stage 1 (build): `node:20-alpine`, runs `npm ci && npm run build`
- Stage 2 (serve): `nginx:alpine`, copies build output to `/usr/share/nginx/html`
- Includes `nginx.conf` with `/api` proxy pass to `backend:8000`

---

## 4. Makefile

`make` with no arguments prints help (default target). All commands have inline comments that are auto-parsed into the help output.

### Commands

```makefile
# Development
make dev-backend      # uvicorn with --reload
make dev-frontend     # npm run dev
make dev              # both in background (via & or screen)

# Docker
make docker-up        # docker compose up --build -d
make docker-down      # docker compose down
make docker-logs      # docker compose logs -f

# Quality
make test             # pytest
make lint             # ruff check src/ web/backend/
make format           # ruff format src/ web/backend/

# Utilities
make check-env        # python scripts/check_env.py
make cli QUERY="..."  # python -m src.main "$(QUERY)"

# Help
make help             # list all commands (default)
```

---

## 5. GitHub Actions CI

**File:** `.github/workflows/ci.yml`

**Triggers:** push to `main`, pull_request targeting `main`

### Jobs

```
lint  ──────────────────────────────────────────────┐
                                                     ├── docker-build
test  ──────────────────────────────────────────────┘
```

- `lint` and `test` run in parallel
- `docker-build` runs after both pass (needs: [lint, test])

### Job details

**lint**
- Python 3.11
- `pip install ruff`
- `ruff check src/ web/backend/`
- `ruff format --check src/ web/backend/`

**test**
- Python 3.11
- `pip install -r requirements.txt -r requirements-web.txt`
- Environment: `LLM_API_KEY=test`, `PUBMED_EMAIL=ci@test.com`
- `pytest tests/ --tb=short; STATUS=$?; [ $STATUS -eq 5 ] && exit 0 || exit $STATUS`
- Handles pytest exit code 5 ("no tests collected") gracefully — CI passes if tests/ is empty or has no test files; real failures (exit code 1) still fail CI

**docker-build**
- `docker compose build` (no run, no real API keys needed)
- Validates Dockerfiles and compose config are valid

### README badges

```markdown
[![CI](https://github.com/USER/ebm5a/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/ebm5a/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
```

Note: `USER` placeholder must be replaced with actual GitHub username when repo is known.

---

## 6. Setup Validation Script

**File:** `scripts/check_env.py`

Checks performed in order:

1. `.env` file exists in project root
2. `LLM_API_KEY` is set and non-empty
3. `LLM_API_BASE` is set and reachable (HTTP HEAD, 5s timeout)
4. `PUBMED_EMAIL` is set and matches basic email format
5. Python version >= 3.10
6. Core packages importable: `langchain`, `torch`, `fastapi`, `uvicorn`
7. `FAST_LLM_MODEL` set (optional — prints advisory if missing, not failure)

Output format:
```
[✓] .env file found
[✓] LLM_API_KEY is set
[✓] LLM_API_BASE reachable (200 OK)
[✓] PUBMED_EMAIL format valid
[✓] Python 3.11.x >= 3.10
[✓] Core dependencies installed
[~] FAST_LLM_MODEL not set (optional — Judge/Scheduling will use LLM_MODEL)

All required checks passed. Ready to run.
```

On failure, each `[✗]` line includes a specific fix hint, e.g.:
```
[✗] LLM_API_KEY not set → Add LLM_API_KEY=sk-... to your .env file
```

Exit code 0 on pass, 1 on any required check failure.

---

## 7. Documentation

### `docs/troubleshooting.md`

Sections:
- **Setup errors** — missing .env, invalid API key, wrong LLM_API_BASE URL
- **PubMed issues** — rate limiting, unregistered email, network timeout
- **Runtime behavior** — why a run takes 2–10 minutes (normal), what backtrack events mean
- **Web UI issues** — CORS errors (use Docker or set VITE_API_URL), frontend blank page
- **Log interpretation** — what `[TIMING]`, `[FAST-PATH]`, `Judge score` lines mean

### `docs/glossary.md`

Terms defined:
- **5A Framework** — Ask, Acquire, Appraise, Apply, Assess
- **GRADE** — evidence quality levels: High, Moderate, Low, Very Low
- **PICO** — Patient, Intervention, Comparison, Outcome
- **Recommendation strength** — Strong, Conditional, Consensus-based, Insufficient Evidence
- **Judge score** — 0–1 quality gate, threshold 0.7 to proceed
- **ReAct loop** — Reasoning + Acting control loop with backtrack capability
- **Question types** — Therapy, Diagnosis, Prognosis, Harm, Prevention

### `README.md` changes

1. Add badges block at top (CI, License, Python version)
2. Add screenshot placeholder section: `docs/assets/screenshot.png`
3. New section **"Quick Start (Docker)"** with 3-command flow
4. New section **"Web UI"** with manual startup instructions (backend + frontend)
5. Reference `make check-env` in the setup steps
6. Link to `docs/troubleshooting.md` and `docs/glossary.md`

### `QUICKSTART.md` changes

Add Docker startup as the first (recommended) option before the existing manual steps.

---

## 8. Issue and PR Templates

### `.github/ISSUE_TEMPLATE/bug_report.md`

Fields:
- Environment (OS, Python version, LLM provider, interface: CLI or Web UI)
- Steps to reproduce
- Expected vs actual behavior
- Relevant log excerpt (from `logs/` directory)

### `.github/ISSUE_TEMPLATE/feature_request.md`

Fields:
- Feature description
- Use case / motivation
- Possible implementation approach (optional)

### `.github/pull_request_template.md`

Fields:
- Summary of changes
- Related issue (Closes #xxx)
- How to test
- Checklist: lint passes, tests pass, docs updated if needed

---

## 9. Implementation Order

Tasks can be executed largely in parallel except where noted:

1. **Dockerfiles + docker-compose** (foundation — other docs reference these commands)
2. **Makefile** (depends on knowing Docker commands from step 1)
3. **`scripts/check_env.py`** (independent)
4. **GitHub Actions CI** (references Makefile commands)
5. **`docs/troubleshooting.md`** (independent)
6. **`docs/glossary.md`** (independent)
7. **Issue/PR templates** (independent)
8. **README.md + QUICKSTART.md updates** (depends on steps 1–2 being final — references real commands)

---

## 10. Out of Scope

- Changes to `src/` agent, coordinator, judge, or scheduling logic
- Changes to `web/` frontend or backend feature code
- Redis or other infrastructure services
- Deploy/publish CI steps (push to registry, deploy to server)
- Cleaning up `docs/internal/` historical files
- Adding new tests (CI runs existing tests only)
