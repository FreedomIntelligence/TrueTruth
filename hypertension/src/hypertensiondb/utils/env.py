"""Environment loading helpers shared by CLI and standalone scripts."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_files(start: str | Path | None = None) -> list[Path]:
    """Load .env files from ancestors, preserving already-set variables.

    The repository has a top-level TrueTruth/.env plus optional subproject .env
    files. Loading ancestors first lets shared values such as NCBI_EMAIL and
    MOCK_EXPERIMENT_MODEL be available from hypertension scripts.
    """
    start_path = Path(start or Path.cwd()).resolve()
    if start_path.is_file():
        start_path = start_path.parent

    env_paths = [path / ".env" for path in reversed([start_path, *start_path.parents]) if (path / ".env").exists()]
    loaded: list[Path] = []
    for env_path in env_paths:
        _load_dotenv(env_path)
        loaded.append(env_path)
    return loaded


def get_quality_model(default: str = "gpt-4o-mini") -> str:
    return (
        os.getenv("MOCK_EXPERIMENT_MODEL")
        or os.getenv("OPENAI_EXTRACT_MODEL")
        or os.getenv("LLM_MODEL")
        or default
    )


def get_quality_api_key() -> str:
    return os.getenv("MOCK_EXPERIMENT_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""


def get_quality_base_url() -> str | None:
    url = os.getenv("MOCK_EXPERIMENT_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    return _normalize_openai_base_url(url) if url else None


def _normalize_openai_base_url(url: str) -> str:
    """Accept either gateway root URLs or explicit OpenAI-compatible /v1 URLs.

    TrueTruth's main LLM config already applies this normalization. Keeping the
    same behavior here prevents one .env value from working in the main project
    but returning the provider's HTML dashboard in hypertension quality ingest.
    """
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"


def _load_dotenv(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")
