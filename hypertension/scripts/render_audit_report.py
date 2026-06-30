"""Render Chinese HTML/Markdown reports for PubMed audit artifacts."""

from __future__ import annotations

from pathlib import Path

from hypertensiondb.ingest.audit_report import main
from hypertensiondb.utils.env import load_env_files


load_env_files(Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main())
