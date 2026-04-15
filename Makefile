.PHONY: help dev dev-backend dev-frontend docker-up docker-down docker-logs \
        test lint format check-env cli

.DEFAULT_GOAL := help

SHELL := /bin/bash

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Development ─────────────────────────────────────────────────────────────

dev-backend: ## Start FastAPI backend with hot reload (port 8000)
	python3 -m uvicorn web.backend.app:app --reload --port 8000

dev-frontend: ## Start Vite dev server (port 5173)
	cd web/frontend && npm run dev

dev: ## Start backend + frontend together (Ctrl+C stops both)
	@trap 'kill 0' SIGINT; \
	 python3 -m uvicorn web.backend.app:app --reload --port 8000 & \
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
	python3 -m pytest tests/ --tb=short -q || [ $$? -eq 5 ]

lint: ## Check code style (ruff)
	python3 -m ruff check src/ web/backend/

format: ## Auto-format code (ruff)
	python3 -m ruff format src/ web/backend/

# ── Utilities ────────────────────────────────────────────────────────────────

check-env: ## Validate .env before running (run this first!)
	python3 scripts/check_env.py

cli: ## Run a clinical query via CLI  (usage: make cli QUERY="your question")
	@test -n "$(QUERY)" || (echo 'Usage: make cli QUERY="your clinical question"' && exit 1)
	python3 -m src.main "$(QUERY)"
