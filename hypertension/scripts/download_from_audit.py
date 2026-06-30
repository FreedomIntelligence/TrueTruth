"""Download eligible PMC XML files from a PubMed screening audit JSONL.

Usage from the hypertension/ directory:
    python scripts/download_from_audit.py --audit audits/pubmed-screen.jsonl \
      --decisions staging/download-decisions.jsonl --output-dir staging/pmc_xml
"""

from __future__ import annotations

from pathlib import Path

from hypertensiondb.ingest.audit_download import main
from hypertensiondb.utils.env import load_env_files


load_env_files(Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main())
