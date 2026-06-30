"""Run PubMed candidate discovery and automated screening.

Usage from the hypertension/ directory:
    python scripts/auto_pubmed_screen.py --output tmp/pubmed_screen.jsonl --retmax 10
    python scripts/auto_pubmed_screen.py --topics config/pubmed_screen_topics.json --output tmp/pubmed_screen.jsonl
"""

from __future__ import annotations

from pathlib import Path

from hypertensiondb.ingest.auto_pubmed_screen import main
from hypertensiondb.utils.env import load_env_files


load_env_files(Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main())
