# Hypertension RAG Service Setup

The Acquire stage of EBM 5A queries a local FastAPI service backed by a vector database of hypertension landmark trials. The service must be running before you start the pipeline.

## Repository

The RAG service lives in a sibling directory `../hypertension/` (a separate git repo, not a submodule). Clone it alongside this project:

```bash
# parent directory
git clone https://github.com/FreedomIntelligence/TrueTruth.git
git clone <hypertension-repo-url> hypertension
```

## Start the service

```bash
cd hypertension
pip install -r requirements.txt
hdb serve run --port 8000
```

The service listens on `http://localhost:8000` by default. You can verify it is up:

```bash
curl http://localhost:8000/health
```

## Configuration (`.env`)

```dotenv
HYPERTENSION_API_URL=http://localhost:8000   # base URL of the service
HYPERTENSION_API_TIMEOUT=10                  # seconds per /search request
RAG_SEARCH_TOP_K=15                          # chunks to retrieve per query
RAG_MAX_PAPERS=6                             # papers surfaced to agents
RAG_MAX_PASSAGES_PER_PAPER=3                 # supporting passages kept per paper
```

All of these have defaults in `.env.example`; only `HYPERTENSION_API_URL` needs changing if you run the service on a different host or port.

## What happens if the service is down?

`hypertension_rag_client.py` retries twice with exponential backoff, then raises `RAGUnavailable`. The Acquire agent catches this and logs a clear error — the pipeline stops at that stage rather than silently producing empty results.
