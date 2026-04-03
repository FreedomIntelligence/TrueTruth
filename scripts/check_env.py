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
