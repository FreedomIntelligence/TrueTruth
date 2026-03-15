import hashlib
import json
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from src.state.schema import Evidence

load_dotenv()

# ---------------------------------------------------------------------------
# Disk-based PubMed results cache
# ---------------------------------------------------------------------------
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_CACHE_TTL_SECONDS = 86400  # 24 hours


def _cache_key(query: str, max_results: int) -> str:
    """Stable cache key from query + max_results."""
    return hashlib.sha256(f"{query}||{max_results}".encode()).hexdigest()[:16]


def _load_cache(key: str) -> Optional[List[Evidence]]:
    """Return cached Evidence list if present and not expired, else None."""
    path = _CACHE_DIR / f"pubmed_{key}.json"
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > _CACHE_TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Evidence(**item) for item in data]
    except Exception:
        return None


def _save_cache(key: str, evidence_list: List[Evidence]) -> None:
    """Persist Evidence list to disk cache. Write failure is non-fatal."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / f"pubmed_{key}.json"
    try:
        path.write_text(
            json.dumps([asdict(e) for e in evidence_list], ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


class PubMedClient:
    """Client for PubMed E-utilities API"""

    def __init__(self, email: str = None):
        self.email = email or os.getenv("PUBMED_EMAIL", "")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search PubMed and return list of PMIDs"""
        url = f"{self.base_url}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
            "email": self.email
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_abstracts(self, pmids: List[str]) -> dict:
        """Fetch article abstracts for given PMIDs"""
        if not pmids:
            return {}

        url = f"{self.base_url}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self.email
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)

        abstracts = {}
        for article in root.findall('.//PubmedArticle'):
            pmid_elem = article.find('.//PMID')
            abstract_elem = article.find('.//Abstract/AbstractText')

            if pmid_elem is not None:
                pmid = pmid_elem.text
                abstract = abstract_elem.text if abstract_elem is not None else ""
                abstracts[pmid] = abstract

        return abstracts

    def fetch_summaries(self, pmids: List[str]) -> dict:
        """Fetch article summaries for given PMIDs"""
        if not pmids:
            return {}

        url = f"{self.base_url}/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "email": self.email
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()


def search_pubmed(query: str, max_results: int = 5, email: str = None) -> List[Evidence]:
    """Search PubMed and return Evidence objects.

    Results are cached on disk for 24 hours so that repeated identical queries
    (e.g. Acquire retries within the same run, or repeated test runs) skip the
    3-request network round-trip entirely.
    """
    key = _cache_key(query, max_results)
    cached = _load_cache(key)
    if cached is not None:
        print(f"[CACHE HIT] PubMed cache — skipping network fetch ({len(cached)} articles)")
        return cached

    client = PubMedClient(email=email)
    pmids = client.search(query, max_results)

    if not pmids:
        return []

    # Fetch summaries and abstracts in parallel — both only need the PMIDs list
    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_summaries = executor.submit(client.fetch_summaries, pmids)
        fut_abstracts = executor.submit(client.fetch_abstracts, pmids)
        summaries = fut_summaries.result()
        abstracts = fut_abstracts.result()

    evidence_list = []

    for pmid in pmids:
        article = summaries.get("result", {}).get(pmid, {})
        if not article:
            continue

        pub_date = article.get("pubdate", "")
        if not pub_date and "epubdate" in article:
            pub_date = article.get("epubdate", "")

        abstract = abstracts.get(pmid, "")

        evidence = Evidence(
            title=article.get("title", "No title"),
            source=article.get("source", "PubMed"),
            pmid=pmid,
            abstract=abstract,
            relevance_score=1.0,
            study_type=None,
            publication_date=pub_date,
            grade_level=None
        )
        evidence_list.append(evidence)

    _save_cache(key, evidence_list)
    return evidence_list
