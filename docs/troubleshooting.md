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
