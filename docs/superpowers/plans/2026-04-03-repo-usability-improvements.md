# Repo Usability Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Docker deployment, Makefile, GitHub Actions CI, setup validation, troubleshooting docs, glossary, issue/PR templates, and README Web UI docs — with no changes to agent or frontend feature code.

**Architecture:** Each deliverable is a self-contained file. Tasks 1–5 build the Docker/Makefile foundation; Tasks 6–8 add automation and validation; Tasks 9–12 add documentation. All tasks are independent except Task 12 (README) which references commands finalised in Tasks 2–5.

**Tech Stack:** Docker + Docker Compose, Nginx (alpine), Python 3.11-slim, Node 20-alpine, GitHub Actions, ruff (linting), pytest (test runner already in requirements.txt)

---

## File Map

| File | Action | Task |
|------|--------|------|
| `.gitignore` | Modify — add `node_modules/` | 1 |
| `.env.example` | Modify — add comments for all vars | 1 |
| `Dockerfile.backend` | Create | 2 |
| `nginx.conf` | Create | 3 |
| `Dockerfile.frontend` | Create | 3 |
| `docker-compose.yml` | Create | 4 |
| `docker-compose.dev.yml` | Create | 4 |
| `.dockerignore` | Create | 4 |
| `Makefile` | Create | 5 |
| `scripts/check_env.py` | Create | 6 |
| `.github/workflows/ci.yml` | Create | 7 |
| `docs/troubleshooting.md` | Create | 8 |
| `docs/glossary.md` | Create | 9 |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Create | 10 |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Create | 10 |
| `.github/pull_request_template.md` | Create | 10 |
| `README.md` | Modify — add CI badge, Docker section, Web UI section | 11 |
| `QUICKSTART.md` | Modify — add Docker as first option | 11 |

---

## Task 1: Audit `.gitignore` and `.env.example`

**Files:**
- Modify: `.gitignore`
- Modify: `.env.example`

- [ ] **Step 1: Add `node_modules/` to `.gitignore`**

The current `.gitignore` is missing `node_modules/`. Open `.gitignore` and add after the `venv/` line:

```
node_modules/
web/frontend/dist/
```

- [ ] **Step 2: Update `.env.example` with full comments**

Replace the entire `.env.example` with:

```bash
# Copy this file to .env and fill in your values.
# Run 'make check-env' to validate your configuration before first run.
# NEVER commit .env — it is gitignored.

# ── Required ────────────────────────────────────────────────────────────────

# Base URL of your OpenAI-compatible LLM API
# OpenAI:    https://api.openai.com/v1
# Azure:     https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT
# HuaTuo:    https://api.huatuogpt.cn/v1
LLM_BASE_URL=https://api.openai.com/v1

# Your API key for the LLM provider above
LLM_API_KEY=your_api_key_here

# Model name — must match your provider's model identifier
# OpenAI examples:  gpt-4  gpt-4o  gpt-3.5-turbo
# Claude examples:  claude-opus-4-6  claude-sonnet-4-6
LLM_MODEL=gpt-4

# Your email address — required by NCBI/PubMed API (https://www.ncbi.nlm.nih.gov/home/develop/api/)
# NCBI will use this to contact you if your scripts cause problems.
PUBMED_EMAIL=your_email@example.com

# ── Optional ─────────────────────────────────────────────────────────────────

# Use a faster/cheaper model for Judge and Scheduling agents (~30–40% faster overall)
# If unset, LLM_MODEL is used for all agents.
# FAST_LLM_MODEL=gpt-3.5-turbo
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .env.example
git commit -m "chore: update .gitignore (node_modules) and improve .env.example comments"
```

---

## Task 2: Create `Dockerfile.backend`

**Files:**
- Create: `Dockerfile.backend`

- [ ] **Step 1: Create `Dockerfile.backend`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for Docker health check
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps in a separate layer for Docker cache efficiency.
# PyTorch (~2 GB) is in requirements.txt — this layer only rebuilds when deps change.
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy application source
COPY src/ ./src/
COPY web/ ./web/

# Create non-root user, app directories, fix ownership.
# mkdir here so Docker named volumes inherit appuser ownership at runtime.
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data/cache /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "web.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Note on PyTorch: `--index-url https://download.pytorch.org/whl/cpu` installs the CPU-only wheel (~800 MB vs ~2.5 GB for CUDA). The system uses PyTorch for MedCPT re-ranking (CPU inference only). If GPU support is needed in future, change the index URL.

- [ ] **Step 2: Verify the image builds**

Run from the project root (takes several minutes first time due to PyTorch):

```bash
docker build -f Dockerfile.backend -t ebm5a-backend:test .
```

Expected: `Successfully built <image-id>` with no errors. The final image should be ~3–4 GB.

- [ ] **Step 3: Verify non-root user**

```bash
docker run --rm ebm5a-backend:test whoami
```

Expected output: `appuser`

- [ ] **Step 4: Clean up test image**

```bash
docker rmi ebm5a-backend:test
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile.backend
git commit -m "feat: add Dockerfile.backend (non-root, CPU-only torch)"
```

---

## Task 3: Create `nginx.conf` and `Dockerfile.frontend`

**Files:**
- Create: `nginx.conf`
- Create: `Dockerfile.frontend`

- [ ] **Step 1: Create `nginx.conf`**

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: React state-based navigation still benefits from this —
    # prevents 404 if a user directly navigates to any path on refresh.
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse proxy to FastAPI backend.
    # Preserves the /api prefix — backend routes are registered as /api/sessions etc.
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";

        # Critical for Server-Sent Events (SSE): disable nginx buffering
        # so workflow progress events are forwarded to the browser immediately.
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }
}
```

- [ ] **Step 2: Create `Dockerfile.frontend`**

```dockerfile
# Stage 1: Build the React/Vite app
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (separate layer — only rebuilds when package.json changes)
COPY web/frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY web/frontend/ ./
RUN npm run build
# Output is in /app/dist

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom Nginx config (replaces the default)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Verify frontend image builds**

```bash
docker build -f Dockerfile.frontend -t ebm5a-frontend:test .
```

Expected: `Successfully built <image-id>`. Final image is ~30–50 MB (nginx:alpine is tiny).

- [ ] **Step 4: Verify nginx config is valid inside the image**

```bash
docker run --rm ebm5a-frontend:test nginx -t
```

Expected: `nginx: configuration file /etc/nginx/nginx.conf test is successful`

- [ ] **Step 5: Clean up test image**

```bash
docker rmi ebm5a-frontend:test
```

- [ ] **Step 6: Commit**

```bash
git add nginx.conf Dockerfile.frontend
git commit -m "feat: add nginx.conf (SPA routing + SSE proxy) and Dockerfile.frontend"
```

---

## Task 4: Create `docker-compose.yml`, `docker-compose.dev.yml`, `.dockerignore`

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    volumes:
      # Persist PubMed cache (24h TTL) and run logs across container restarts
      - ebm5a_cache:/app/data/cache
      - ebm5a_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 40s

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy

volumes:
  ebm5a_cache:
  ebm5a_logs:
```

Note: The backend is not exposed on the host — all traffic goes through nginx on port 80. Frontend calls `/api/*` which nginx proxies to `backend:8000` on the internal Docker network.

- [ ] **Step 2: Create `docker-compose.dev.yml`**

This file is used as `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` to override the backend for hot-reload development:

```yaml
services:
  backend:
    volumes:
      # Mount source code for hot reload (overrides image-baked code)
      - ./src:/app/src
      - ./web:/app/web
    command: uvicorn web.backend.app:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: Create `.dockerignore`**

```
# Version control
.git/
.gitignore

# Secrets — never include in image
.env

# Python artifacts
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/

# Virtual envs
.venv/
venv/

# Frontend build artifacts and deps
web/frontend/node_modules/
web/frontend/dist/

# Data and logs (mounted as volumes at runtime)
data/
logs/

# Dev tooling
.claude/
docs/
*.md
```

- [ ] **Step 4: Validate compose config**

```bash
docker compose config
```

Expected: YAML printed with no errors. Should show both `backend` and `frontend` services, two named volumes (`ebm5a_cache`, `ebm5a_logs`), and the healthcheck on backend.

- [ ] **Step 5: End-to-end smoke test (requires a valid `.env`)**

If you have a valid `.env` with real API keys:

```bash
docker compose up --build -d
# Wait ~60s for backend to pass health check
docker compose ps
```

Expected: both services `running` or `healthy`. Then open `http://localhost` — the EBM 5A web UI should load.

```bash
docker compose down
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml .dockerignore
git commit -m "feat: add docker-compose.yml, dev override, and .dockerignore"
```

---

## Task 5: Create `Makefile`

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create `Makefile`**

```makefile
.PHONY: help dev dev-backend dev-frontend docker-up docker-down docker-logs \
        test lint format check-env cli

.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Development ─────────────────────────────────────────────────────────────

dev-backend: ## Start FastAPI backend with hot reload (port 8000)
	uvicorn web.backend.app:app --reload --port 8000

dev-frontend: ## Start Vite dev server (port 5173)
	cd web/frontend && npm run dev

dev: ## Start backend + frontend together (Ctrl+C stops both)
	@trap 'kill 0' SIGINT; \
	 uvicorn web.backend.app:app --reload --port 8000 & \
	 (cd web/frontend && npm run dev) & \
	 wait

# ── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Build and start all services in the background
	docker compose up --build -d

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## Tail logs from all Docker services
	docker compose logs -f

# ── Quality ──────────────────────────────────────────────────────────────────

test: ## Run test suite with pytest
	pytest tests/ --tb=short -q

lint: ## Check code style (ruff)
	ruff check src/ web/backend/

format: ## Auto-format code (ruff)
	ruff format src/ web/backend/

# ── Utilities ────────────────────────────────────────────────────────────────

check-env: ## Validate .env before running (run this first!)
	python scripts/check_env.py

cli: ## Run a clinical query via CLI  (usage: make cli QUERY="your question")
	python -m src.main "$(QUERY)"
```

- [ ] **Step 2: Verify help output**

```bash
make help
```

Expected output (colours in terminal):
```
  dev-backend        Start FastAPI backend with hot reload (port 8000)
  dev-frontend       Start Vite dev server (port 5173)
  dev                Start backend + frontend together (Ctrl+C stops both)
  docker-up          Build and start all services in the background
  docker-down        Stop all Docker services
  docker-logs        Tail logs from all Docker services
  test               Run test suite with pytest
  lint               Check code style (ruff)
  format             Auto-format code (ruff)
  check-env          Validate .env before running (run this first!)
  cli                Run a clinical query via CLI  (usage: make cli QUERY="your question")
```

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: add Makefile with dev, docker, lint, test, and check-env targets"
```

---

## Task 6: Create `scripts/check_env.py`

**Files:**
- Create: `scripts/check_env.py`

- [ ] **Step 1: Create `scripts/check_env.py`**

```python
#!/usr/bin/env python3
"""Validate .env configuration before running EBM 5A.

Usage:
    python scripts/check_env.py
    make check-env

Exit code 0: all required checks passed.
Exit code 1: one or more required checks failed.
"""

import importlib.util
import os
import re
import sys
import urllib.request
from pathlib import Path

OK = "[✓]"
FAIL = "[✗]"
WARN = "[~]"

_errors = 0


def ok(msg: str) -> None:
    print(f"{OK} {msg}")


def fail(msg: str, hint: str) -> None:
    global _errors
    _errors += 1
    print(f"{FAIL} {msg}")
    print(f"    → {hint}")


def warn(msg: str) -> None:
    print(f"{WARN} {msg}")


# ── 1. Load .env ─────────────────────────────────────────────────────────────

env_path = Path(".env")
if not env_path.exists():
    fail(
        ".env file not found",
        "Run: cp .env.example .env   then fill in your values",
    )
    sys.exit(1)

ok(".env file found")

env_vars: dict[str, str] = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip().strip('"').strip("'")

os.environ.update(env_vars)

# ── 2. LLM_API_KEY ───────────────────────────────────────────────────────────

api_key = os.getenv("LLM_API_KEY", "")
if not api_key or api_key in ("your_api_key_here", ""):
    fail(
        "LLM_API_KEY not set or still placeholder",
        "Add LLM_API_KEY=<your-key> to .env",
    )
else:
    ok("LLM_API_KEY is set")

# ── 3. LLM_BASE_URL ──────────────────────────────────────────────────────────

base_url = os.getenv("LLM_BASE_URL", "")
if not base_url:
    fail(
        "LLM_BASE_URL not set",
        "Add LLM_BASE_URL=https://api.openai.com/v1 to .env",
    )
else:
    try:
        req = urllib.request.Request(base_url, method="HEAD")
        urllib.request.urlopen(req, timeout=5)
        ok(f"LLM_BASE_URL reachable ({base_url})")
    except Exception as e:
        # Many providers return 4xx on HEAD /v1 — that still means the host is up
        code = getattr(e, "code", None)
        if code is not None and code < 500:
            ok(f"LLM_BASE_URL reachable — HTTP {code} (normal for this endpoint)")
        else:
            fail(
                f"LLM_BASE_URL not reachable: {e}",
                "Check LLM_BASE_URL in .env — is the server running / accessible?",
            )

# ── 4. PUBMED_EMAIL ──────────────────────────────────────────────────────────

email = os.getenv("PUBMED_EMAIL", "")
if not email or not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
    fail(
        "PUBMED_EMAIL not set or invalid format",
        "Add PUBMED_EMAIL=your@email.com to .env (required by NCBI API)",
    )
else:
    ok("PUBMED_EMAIL format valid")

# ── 5. Python version ────────────────────────────────────────────────────────

vi = sys.version_info
if vi < (3, 10):
    fail(
        f"Python {vi.major}.{vi.minor} — need 3.10+",
        "Upgrade Python: https://www.python.org/downloads/",
    )
else:
    ok(f"Python {vi.major}.{vi.minor}.{vi.micro} >= 3.10")

# ── 6. Core dependencies ─────────────────────────────────────────────────────

required_pkgs = {
    "langchain": "langchain",
    "torch": "torch",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
}

missing = [name for name, pkg in required_pkgs.items()
           if importlib.util.find_spec(pkg) is None]

if missing:
    fail(
        f"Missing packages: {', '.join(missing)}",
        "Run: pip install -r requirements.txt -r requirements-web.txt",
    )
else:
    ok("Core dependencies installed (langchain, torch, fastapi, uvicorn)")

# ── 7. Optional: FAST_LLM_MODEL ──────────────────────────────────────────────

if not os.getenv("FAST_LLM_MODEL"):
    warn(
        "FAST_LLM_MODEL not set (optional) — "
        "Judge/Scheduling will use LLM_MODEL; set a faster model for ~30% speedup"
    )
else:
    ok(f"FAST_LLM_MODEL = {os.getenv('FAST_LLM_MODEL')}")

# ── Summary ───────────────────────────────────────────────────────────────────

print()
if _errors:
    print(f"❌  {_errors} required check(s) failed — fix the above before running.")
    sys.exit(1)
else:
    print("✅  All required checks passed. Ready to run.")
```

- [ ] **Step 2: Run against a valid `.env` — expect all green**

```bash
python scripts/check_env.py
```

Expected (with a valid `.env`):
```
[✓] .env file found
[✓] LLM_API_KEY is set
[✓] LLM_BASE_URL reachable (https://api.openai.com/v1)
[✓] PUBMED_EMAIL format valid
[✓] Python 3.11.x >= 3.10
[✓] Core dependencies installed (langchain, torch, fastapi, uvicorn)
[~] FAST_LLM_MODEL not set (optional) — ...

✅  All required checks passed. Ready to run.
```

- [ ] **Step 3: Test failure path — rename `.env` temporarily**

```bash
mv .env .env.bak
python scripts/check_env.py
mv .env.bak .env
```

Expected: script prints `[✗] .env file not found` and exits with code 1:
```bash
echo $?   # should print: 1
```

- [ ] **Step 4: Commit**

```bash
git add scripts/check_env.py
git commit -m "feat: add scripts/check_env.py — validates .env before first run"
```

---

## Task 7: Create `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the directory and workflow file**

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ── Job 1: Lint ─────────────────────────────────────────────────────────────
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ruff
        run: pip install ruff

      - name: Check style (ruff)
        run: ruff check src/ web/backend/

      - name: Check formatting (ruff)
        run: ruff format --check src/ web/backend/

  # ── Job 2: Test ─────────────────────────────────────────────────────────────
  test:
    name: Test
    runs-on: ubuntu-latest
    env:
      # Placeholder values — CI never calls real APIs.
      # POLICY: do NOT replace these with real keys in YAML or GitHub Secrets.
      # Real API keys would cause live (costly) calls on every PR.
      LLM_API_KEY: ci-placeholder-not-real
      LLM_BASE_URL: https://api.openai.com/v1
      LLM_MODEL: gpt-4
      PUBMED_EMAIL: ci@example.com
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: |
            requirements.txt
            requirements-web.txt

      - name: Install PyTorch (CPU-only wheel — faster than default CUDA wheel)
        run: pip install torch --index-url https://download.pytorch.org/whl/cpu

      - name: Install remaining dependencies
        run: pip install -r requirements.txt -r requirements-web.txt

      - name: Run tests
        # Exit code 5 = "no tests collected" — treat as pass until tests are added.
        # Real failures (exit code 1) still fail CI.
        run: |
          pytest tests/ --tb=short -q
          STATUS=$?
          [ $STATUS -eq 5 ] && exit 0 || exit $STATUS
        shell: bash

  # ── Job 3: Docker Build ─────────────────────────────────────────────────────
  docker-build:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.backend
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.frontend
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Validate YAML syntax locally**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML valid')"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: add GitHub Actions CI (lint + test + docker-build with caching)"
```

After pushing to GitHub, the Actions tab will show the workflow running. First run of the `test` job will be slow (~10–15 min) due to PyTorch download; subsequent runs use the pip cache (~2–3 min).

---

## Task 8: Create `docs/troubleshooting.md`

**Files:**
- Create: `docs/troubleshooting.md`

- [ ] **Step 1: Create `docs/troubleshooting.md`**

```markdown
# Troubleshooting

Common issues and how to fix them.

---

## Setup Errors

### `.env` file not found

**Symptom:** `FileNotFoundError: .env not found` or `make check-env` reports missing file.

**Fix:**
```bash
cp .env.example .env
# Then edit .env and fill in your LLM_API_KEY and PUBMED_EMAIL
```

---

### `LLM_API_KEY` invalid or quota exceeded

**Symptom:** `AuthenticationError`, `401 Unauthorized`, or `429 Too Many Requests` in logs.

**Fix:**
- Verify the key in `.env` matches your provider's format.
- Check your API quota / billing dashboard.
- If using a custom `LLM_BASE_URL`, ensure the base URL does not include a trailing `/chat/completions` — it should end at `/v1`.

---

### `LLM_BASE_URL` unreachable

**Symptom:** `ConnectionError` or `make check-env` reports `[✗] LLM_BASE_URL not reachable`.

**Fix:**
- Check the URL is reachable from your machine: `curl -I https://your-provider/v1`
- If behind a proxy, ensure `HTTPS_PROXY` is set in your environment.
- If using a local LLM server (e.g., Ollama), ensure it is running.

---

## PubMed Issues

### Rate limiting (`HTTP 429` from PubMed)

**Symptom:** `429` errors in logs during the Acquire stage.

**Cause:** NCBI limits unauthenticated requests to 3/second. The client respects this by default, but network latency variations can occasionally trigger it.

**Fix:** This is usually transient — the next run will succeed. If persistent, register for an [NCBI API key](https://www.ncbi.nlm.nih.gov/account/) (allows 10 req/s).

---

### PubMed returns no results

**Symptom:** Acquire stage completes with 0 articles; Apply stage receives no evidence.

**Causes:**
- The clinical question uses highly specific terminology not present in PubMed MeSH terms. Try rephrasing.
- `PUBMED_EMAIL` is unset or invalid — NCBI may silently throttle requests without a valid email.

---

## Runtime Behaviour

### A run takes 5–10 minutes — is it stuck?

**No, this is normal.** Each stage involves one or more LLM calls:
- Ask: ~10s
- Acquire: ~30–60s (PubMed fetch + MedCPT re-ranking)
- Appraise: ~60–120s (parallel LLM calls for up to 10 articles)
- Apply: ~30–90s (may retry if Judge score < 0.7)
- Assess: ~20s

Total: 2–10 minutes depending on model speed and evidence complexity.

The CLI prints `[TIMING]` lines at each stage. The Web UI shows live progress.

---

### Backtrack events in logs — is something wrong?

**No, backtracks are by design.** When a stage scores below the Judge threshold (0.7/1.0), the Scheduling LLM may decide to retry the stage or backtrack to a previous stage. This is the quality-gating mechanism working correctly.

If a run produces more than 3–4 backtracks and never completes, the question may be outside the system's evidence coverage — it will eventually return `Insufficient Evidence`.

---

### `[FAST-PATH]` in logs — what does this mean?

The coordinator detected that the current stage can be skipped:
- `FAST-PATH`: `pass_threshold=True` and no critical/major issues → proceed without calling the Scheduling LLM.
- `FAST-PATH-2`: The current set of major issues has been seen before (loop detected) → auto-proceed to prevent infinite loops.

Both are expected behaviour.

---

## Web UI Issues

### Frontend loads but API calls fail (network error)

**Symptom:** Web UI shows "Failed to start session" immediately after submitting a question.

**Cause (manual dev mode):** The frontend dev server (port 5173) calls the backend (port 8000) cross-origin. The backend allows `*` CORS, but the browser may block it in some configurations.

**Fix options:**
1. Use Docker mode (`make docker-up`) — nginx handles the proxy on the same origin.
2. Ensure the backend is actually running: `make dev-backend` in a separate terminal.

---

### Blank page at `http://localhost` (Docker mode)

**Cause:** Frontend container started before backend passed its health check.

**Fix:**
```bash
docker compose down
docker compose up --build -d
# Wait 30–60 seconds, then refresh
docker compose ps   # both services should show "healthy" or "running"
```

---

### SSE stream stops mid-workflow in Docker

**Symptom:** Progress updates stop after a few events; the browser shows the connection closed.

**Cause:** Nginx has a default `proxy_read_timeout` of 60s, which may expire for long workflows.

Our `nginx.conf` sets `proxy_read_timeout 600s` (10 min) which should be sufficient. If you modified `nginx.conf`, ensure this setting is present.

---

## Log Interpretation

| Log pattern | Meaning |
|-------------|---------|
| `[TIMING] Acquire: 45.2s` | Stage took 45.2 seconds |
| `[FAST-PATH] proceed` | Skipped Scheduling LLM — stage passed cleanly |
| `[FAST-PATH-2] loop detected, auto-proceed` | Repeated major-issue pattern — forced proceed |
| `Judge score: 0.82 / threshold: 0.70` | Stage passed quality gate |
| `Judge score: 0.61 / threshold: 0.70` | Stage failed — Scheduling LLM will decide next action |
| `Backtrack to Acquire` | System re-running Acquire with a revised query |
| `Insufficient Evidence` | Final result — no recommendation was forced |
```

- [ ] **Step 2: Commit**

```bash
git add docs/troubleshooting.md
git commit -m "docs: add troubleshooting guide (setup, PubMed, runtime, Web UI, logs)"
```

---

## Task 9: Create `docs/glossary.md`

**Files:**
- Create: `docs/glossary.md`

- [ ] **Step 1: Create `docs/glossary.md`**

```markdown
# Glossary

Key terms used in EBM 5A and the Evidence-Based Medicine framework.

---

## 5A Framework

The international EBM workflow operationalised by this system:

| Stage | Full name | What it does |
|-------|-----------|-------------|
| **Ask** | Ask a structured question | Converts a free-text clinical question into a structured PICO format and identifies the question type |
| **Acquire** | Acquire the evidence | Searches PubMed with appropriate filters, re-ranks results with MedCPT |
| **Appraise** | Appraise the evidence | Rates each article's study type and assigns a GRADE evidence level |
| **Apply** | Apply to the patient | Synthesises the evidence into a recommendation with strength and quality ratings |
| **Assess** | Assess the outcome | Reviews the full workflow and produces a final structured summary |

---

## PICO

A framework for structuring clinical questions:

- **P** — Patient / Population / Problem
- **I** — Intervention (treatment, test, exposure)
- **C** — Comparison (alternative intervention, placebo, or no treatment)
- **O** — Outcome (what you are trying to measure or achieve)

Example: *"In [P: 68-year-old with NSTEMI and GI bleed], does [I: DAPT] compared to [C: clopidogrel monotherapy] reduce [O: recurrent MI] without increasing [O: GI bleeding]?"*

---

## Question Types

EBM 5A automatically identifies the question type during the Ask stage to apply the appropriate PubMed search filter:

| Type | Description | Search filter used |
|------|-------------|-------------------|
| **Therapy** | Does treatment X work better than Y? | High Sensitivity Search Strategy (HSSS) — RCTs and SRs |
| **Diagnosis** | How accurate is test X for condition Y? | Diagnostic test accuracy studies |
| **Prognosis** | What is the likely outcome for a patient with X? | Observational studies (cohort) |
| **Harm** | Does exposure X cause harm Y? | Observational studies (cohort + case-control) |
| **Prevention** | Does intervention X prevent condition Y? | RCTs and observational studies |

---

## GRADE Evidence Quality

GRADE (Grading of Recommendations Assessment, Development, and Evaluation) is the international standard for rating evidence quality. In EBM 5A, GRADE levels are **computed by deterministic Python code** — the LLM classifies study types and design features; Python calculates the final grade.

| Level | Meaning | Typical study types |
|-------|---------|-------------------|
| **High** | Very confident the effect estimate is close to the true effect | Systematic review / meta-analysis, well-designed RCT |
| **Moderate** | Moderately confident; true effect likely close to estimate, but may differ | RCT with limitations, well-designed observational |
| **Low** | Limited confidence; true effect may differ substantially | Observational study (cohort, case-control) |
| **Very Low** | Very little confidence in the effect estimate | Case series, expert opinion, narrative review |

Factors that **downgrade** evidence: risk of bias, inconsistency, indirectness, imprecision, publication bias.
Factors that **upgrade** evidence: large effect size, dose-response gradient, all plausible confounders reduce effect.

---

## Recommendation Strength

The Apply agent assigns a recommendation strength based on evidence quality and clinical context:

| Strength | Meaning | When used |
|----------|---------|-----------|
| **Strong** | Benefits clearly outweigh harms for most patients | High/Moderate GRADE evidence with consistent direction |
| **Conditional** | Benefits probably outweigh harms, but uncertainty exists | Lower GRADE evidence, indirect evidence, or significant patient variability |
| **Consensus-based** | No direct evidence; based on clinical guidelines or expert consensus | Diagnosis questions, topics covered by major guidelines (ESC, AHA, etc.) |
| **Insufficient Evidence** | Cannot make a recommendation — evidence is absent, conflicting, or too weak | No relevant studies retrieved or all studies critically flawed |

---

## Judge Score

Each stage's output is evaluated by the Judge LLM, which produces a score from 0.0 to 1.0.

- **Threshold:** 0.70 — stages scoring below this threshold are flagged for retry or backtrack.
- **Composition:** The Judge classifies individual quality dimensions as `pass` / `minor` / `major` / `critical`. Python code converts these labels to a numerical score.
- **Purpose:** Prevents low-quality intermediate outputs from propagating to the final recommendation.

---

## ReAct Loop

**Re**asoning + **Act**ing — the control loop pattern used by EBM 5A's coordinator:

1. Run stage → produce output
2. Judge scores the output
3. Scheduling LLM decides: proceed / retry / backtrack
4. Repeat until all stages pass or max iterations reached

This loop ensures quality gates are enforced at every stage and allows the system to recover from poor intermediate outputs.

---

## MedCPT

A biomedical dense retrieval model (from NCBI) used to re-rank PubMed search results by relevance to the clinical question. Runs locally using PyTorch (CPU inference). Improves article relevance compared to keyword-only BM25 ranking.
```

- [ ] **Step 2: Commit**

```bash
git add docs/glossary.md
git commit -m "docs: add glossary (5A, PICO, GRADE, recommendation strength, Judge score, ReAct)"
```

---

## Task 10: Create GitHub Issue and PR Templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Create `.github/ISSUE_TEMPLATE/bug_report.md`**

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

```markdown
---
name: Bug Report
about: Something isn't working as expected
labels: bug
---

## Environment

- **OS:** (e.g. Ubuntu 22.04, macOS 14, Windows 11)
- **Python version:** (e.g. 3.11.2) — run `python --version`
- **Interface:** CLI / Web UI / Both
- **LLM provider:** (e.g. OpenAI, Azure OpenAI, HuaTuoGPT, local Ollama)
- **EBM 5A version / commit:** (run `git log --oneline -1`)

## Steps to Reproduce

1.
2.
3.

## Expected Behaviour

What should have happened.

## Actual Behaviour

What actually happened.

## Relevant Log Output

Paste the relevant section from `logs/` or the terminal output.
Use a code block:

```
[paste log here]
```

## Additional Context

Any other context (screenshots, related issues, config details).
```

- [ ] **Step 2: Create `.github/ISSUE_TEMPLATE/feature_request.md`**

```markdown
---
name: Feature Request
about: Suggest a new feature or improvement
labels: enhancement
---

## What would you like?

A clear description of the feature you are requesting.

## Why is this useful?

Describe the use case or motivation. Who benefits, and how?

## Possible implementation approach (optional)

If you have ideas about how it could be implemented, share them here.
```

- [ ] **Step 3: Create `.github/pull_request_template.md`**

```markdown
## Summary

<!-- What does this PR do? 2–3 bullet points. -->

- 
- 

## Related Issue

Closes #

## How to Test

<!-- Steps to verify the change works as expected. -->

1.
2.

## Checklist

- [ ] `make lint` passes
- [ ] `make test` passes (or no tests affected)
- [ ] Docs updated if behaviour changed
- [ ] `.env.example` updated if new env vars added
```

- [ ] **Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/ .github/pull_request_template.md
git commit -m "chore: add GitHub issue and PR templates"
```

---

## Task 11: Update `README.md` and `QUICKSTART.md`

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`

- [ ] **Step 1: Add CI badge to `README.md`**

Find the existing badges block (lines 8–12 in the current file):

```markdown
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-green.svg)](https://python.langchain.com/)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg)](https://platform.openai.com/)
[![PubMed](https://img.shields.io/badge/data-PubMed%20Real--time-326599.svg)](https://pubmed.ncbi.nlm.nih.gov/)
```

Replace with (add CI badge as the first badge; replace `YOUR_GITHUB_USERNAME` with the actual GitHub username):

```markdown
[![CI](https://github.com/YOUR_GITHUB_USERNAME/ebm5a/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/ebm5a/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-green.svg)](https://python.langchain.com/)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg)](https://platform.openai.com/)
[![PubMed](https://img.shields.io/badge/data-PubMed%20Real--time-326599.svg)](https://pubmed.ncbi.nlm.nih.gov/)
```

Note: find the actual GitHub username with `git remote -v`. Replace `YOUR_GITHUB_USERNAME` and the repo name accordingly.

- [ ] **Step 2: Add Docker Quick Start and Web UI sections to `README.md`**

Find the English section that begins with `### What is EBM 5A?`. Insert the following **before** this heading (immediately after the `<a id="english"></a>` anchor line):

```markdown
### Quick Start

**Docker (recommended — one command, no environment setup):**

```bash
cp .env.example .env      # fill in LLM_API_KEY, PUBMED_EMAIL
make docker-up            # builds and starts backend + frontend
# Open http://localhost
```

**Manual (CLI only):**

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your values
make check-env            # validate configuration
make cli QUERY="68-year-old with NSTEMI and acute GI bleed: DAPT or clopidogrel monotherapy?"
```

### Interfaces

| Interface | How to start | URL |
|-----------|-------------|-----|
| **Web UI** (Docker) | `make docker-up` | http://localhost |
| **Web UI** (manual) | `make dev-backend` + `make dev-frontend` | http://localhost:5173 |
| **CLI** | `make cli QUERY="..."` | — |

The Web UI provides real-time workflow visualisation, stage-by-stage scores, evidence tables, and history. The CLI outputs the full audit trail to `logs/`.

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and [docs/glossary.md](docs/glossary.md) for GRADE/PICO/recommendation strength definitions.

---
```

- [ ] **Step 3: Add Chinese equivalents to `README.md`**

Find the Chinese section anchor `<a id="chinese"></a>` (search for it). After the Chinese section header that corresponds to "What is EBM 5A?", insert the Chinese equivalent:

```markdown
### 快速开始

**Docker（推荐——一行命令，无需配置环境）：**

```bash
cp .env.example .env      # 填写 LLM_API_KEY 和 PUBMED_EMAIL
make docker-up            # 构建并启动后端 + 前端
# 访问 http://localhost
```

**手动（仅 CLI）：**

```bash
pip install -r requirements.txt
cp .env.example .env      # 填写相关配置
make check-env            # 验证配置
make cli QUERY="68岁男性，NSTEMI合并急性消化道出血：DAPT还是单用氯吡格雷？"
```

### 界面

| 界面 | 启动方式 | 访问地址 |
|------|---------|--------|
| **Web UI**（Docker） | `make docker-up` | http://localhost |
| **Web UI**（手动） | `make dev-backend` + `make dev-frontend` | http://localhost:5173 |
| **CLI** | `make cli QUERY="..."` | — |

Web UI 提供实时工作流可视化、逐阶段评分、证据表格和历史记录。CLI 将完整审计日志输出到 `logs/`。

常见问题请参阅 [docs/troubleshooting.md](docs/troubleshooting.md)；GRADE / PICO / 推荐强度等术语请参阅 [docs/glossary.md](docs/glossary.md)。

---
```

- [ ] **Step 4: Update `QUICKSTART.md` — add Docker as the first option**

The current `QUICKSTART.md` starts with `## 1. 配置环境`. Insert a new section **before** this, at the very top after the `# EBM 5A系统快速开始指南` title:

```markdown
## 方式一：Docker（推荐）

最快的上手方式——一行命令启动前后端，无需手动配置 Python 环境。

**前提：** 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Docker Compose。

```bash
# 1. 复制并填写配置文件
cp .env.example .env
# 用编辑器打开 .env，填写 LLM_API_KEY 和 PUBMED_EMAIL

# 2. 启动
make docker-up

# 3. 访问 Web UI
# 浏览器打开 http://localhost
```

停止服务：
```bash
make docker-down
```

查看日志：
```bash
make docker-logs
```

---

## 方式二：手动安装
```

Then rename the existing `## 1. 配置环境` heading to keep it as part of "方式二" by adding it right after the `## 方式二：手动安装` line (no change to content, just continuity).

- [ ] **Step 5: Commit**

```bash
git add README.md QUICKSTART.md
git commit -m "docs: add Docker quick start, Web UI section, CI badge to README and QUICKSTART"
```

---

## Self-Review Checklist

After completing all tasks, verify:

- [ ] `make help` shows all expected commands
- [ ] `make check-env` runs without crash (exit 0 with valid .env, exit 1 without)
- [ ] `docker compose config` validates without error
- [ ] `docker compose build` succeeds for both images
- [ ] `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` is valid
- [ ] `docs/troubleshooting.md` and `docs/glossary.md` exist and render correctly
- [ ] `.github/ISSUE_TEMPLATE/` has two files; `.github/pull_request_template.md` exists
- [ ] README shows CI badge, Docker Quick Start, and Web UI table
- [ ] `QUICKSTART.md` has Docker section as the first option
