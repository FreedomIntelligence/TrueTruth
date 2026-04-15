"""Build the local obstetrics evidence database from PMC Open Access full-text articles.

Usage:
    python scripts/build_obstetrics_db.py

The script searches PMC for high-quality obstetrics articles per topic,
downloads their full-text XML, parses the JATS format, and indexes them
with BM25 + ChromaDB for hybrid retrieval by the local_evidence_db module.

Idempotent: re-running skips articles already present in articles.json.
"""

import json
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

import requests

# ---- Paths ----
_ROOT = Path(__file__).parent.parent
DB_DIR = _ROOT / "data" / "obstetrics_db"
CHROMA_DIR = _ROOT / "data" / "obstetrics_chroma"
ARTICLES_PATH = DB_DIR / "articles.json"
BM25_PATH = DB_DIR / "bm25.pkl"

# ---- NCBI E-utilities ----
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_DELAY = 0.4  # seconds between requests (NCBI rate limit: max 3/s without API key)

# ---- Chunking ----
CHUNK_SIZE = 512   # approximate words per chunk
CHUNK_OVERLAP = 64  # word overlap between consecutive chunks

# ---- Topics to cover (query, max_articles_per_topic) ----
# Each query searches PMC Open Access subset for relevant obstetrics articles.
SEARCH_TOPICS: List[Tuple[str, str, int]] = [
    (
        "preeclampsia_treatment",
        "preeclampsia treatment magnesium sulfate labetalol antihypertensive randomized",
        2,
    ),
    (
        "gestational_diabetes",
        "gestational diabetes mellitus treatment metformin insulin glycemic control",
        2,
    ),
    (
        "postpartum_hemorrhage",
        "postpartum hemorrhage prevention oxytocin uterotonics uterotonic",
        2,
    ),
    (
        "preterm_birth",
        "preterm birth prevention progesterone antenatal corticosteroids betamethasone",
        2,
    ),
    (
        "cesarean_section",
        "cesarean section versus vaginal delivery maternal neonatal outcomes",
        2,
    ),
]


# ---------------------------------------------------------------------------
# PMC E-utilities helpers
# ---------------------------------------------------------------------------

def search_pmc(query: str, max_results: int = 4) -> List[str]:
    """Search PMC Open Access subset; return list of PMCIDs (strings)."""
    full_query = f'({query}) AND "open access"[filter]'
    resp = requests.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={
            "db": "pmc",
            "term": full_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def fetch_pmc_xml(pmcid: str) -> Optional[str]:
    """Fetch full-text XML for a PMC article. Returns None on failure."""
    resp = requests.get(
        f"{NCBI_BASE}/efetch.fcgi",
        params={"db": "pmc", "id": pmcid, "retmode": "xml"},
        timeout=60,
    )
    if resp.status_code != 200:
        return None
    # A minimal validity check: real JATS XML starts with <?xml or <article
    text = resp.text.strip()
    if not (text.startswith("<?xml") or text.startswith("<article")):
        return None
    return text


# ---------------------------------------------------------------------------
# JATS XML parsing
# ---------------------------------------------------------------------------

def _iter_text(elem) -> str:
    """Recursively collect all text content of an XML element."""
    return " ".join(elem.itertext()).strip()


def parse_jats_xml(xml_text: str, pmcid: str) -> Optional[Dict]:
    """Parse JATS XML and extract structured fields.

    Returns a dict with keys: pmcid, pmid, title, abstract, full_text,
    journal, publication_date.  Returns None if the XML is malformed or
    lacks a title.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"    XML parse error: {e}")
        return None

    # Title
    title_elem = root.find(".//article-title")
    title = _iter_text(title_elem) if title_elem is not None else ""
    if not title:
        return None  # Can't use article without a title

    # Abstract (concatenate all <abstract> sections)
    abstract_parts = [_iter_text(a) for a in root.findall(".//abstract")]
    abstract = " ".join(abstract_parts).strip()

    # Full text: collect all <p> elements inside <body>
    full_text_parts: List[str] = []
    body = root.find(".//body")
    if body is not None:
        for p in body.iter("p"):
            text = _iter_text(p)
            if text:
                full_text_parts.append(text)
    full_text = " ".join(full_text_parts)

    # PMID
    pmid: Optional[str] = None
    for aid in root.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmid":
            pmid = (aid.text or "").strip() or None
            break

    # Journal title
    journal_elem = root.find(".//journal-title")
    journal = journal_elem.text.strip() if (journal_elem is not None and journal_elem.text) else "PMC"

    # Publication year
    pub_date: Optional[str] = None
    for date_elem in root.findall(".//pub-date"):
        year_elem = date_elem.find("year")
        if year_elem is not None and year_elem.text:
            pub_date = year_elem.text.strip()
            break

    return {
        "pmcid": pmcid,
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "full_text": full_text,
        "journal": journal,
        "publication_date": pub_date,
    }


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks: List[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_indexes(articles: List[Dict]) -> None:
    """Build BM25 pickle and ChromaDB vector index from parsed articles."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # ---- BM25 ----
    print("\nBuilding BM25 index...")
    from rank_bm25 import BM25Okapi

    corpus_ids: List[str] = []
    corpus_tokens: List[List[str]] = []
    for a in articles:
        text = f"{a['title']} {a['abstract']} {a['full_text']}"
        corpus_ids.append(a["pmcid"])
        corpus_tokens.append(text.lower().split())

    bm25 = BM25Okapi(corpus_tokens)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "corpus_ids": corpus_ids}, f)
    print(f"  BM25 index saved ({len(articles)} articles) → {BM25_PATH}")

    # ---- ChromaDB ----
    print("\nBuilding ChromaDB vector index...")
    print("  Loading sentence-transformers model (downloads ~90 MB on first run)...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Rebuild collection from scratch (idempotent)
    try:
        client.delete_collection("obstetrics_evidence")
    except Exception:
        pass
    collection = client.create_collection("obstetrics_evidence")

    all_texts: List[str] = []
    all_metadatas: List[dict] = []
    all_ids: List[str] = []

    for a in articles:
        full_doc = f"{a['title']} {a['abstract']} {a['full_text']}"
        chunks = chunk_text(full_doc)
        for i, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_metadatas.append({
                "pmcid": a["pmcid"],
                "pmid": a.get("pmid") or "",
                "title": a["title"][:200],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })
            all_ids.append(f"{a['pmcid']}_chunk_{i}")

    batch_size = 64
    for start in range(0, len(all_texts), batch_size):
        batch_texts = all_texts[start: start + batch_size]
        batch_metas = all_metadatas[start: start + batch_size]
        batch_ids = all_ids[start: start + batch_size]
        embeddings = model.encode(batch_texts).tolist()
        collection.add(
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_metas,
            ids=batch_ids,
        )
        print(f"  Embedded chunks {start}–{start + len(batch_texts) - 1}")

    print(
        f"  ChromaDB index built: {len(all_texts)} chunks "
        f"from {len(articles)} articles → {CHROMA_DIR}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing articles (enables idempotent re-runs)
    existing_articles: List[Dict] = []
    existing_pmcids: set = set()
    if ARTICLES_PATH.exists():
        with open(ARTICLES_PATH, encoding="utf-8") as f:
            existing_articles = json.load(f)
        existing_pmcids = {a["pmcid"] for a in existing_articles}
        print(f"Found {len(existing_articles)} already-indexed articles.")

    new_articles: List[Dict] = []

    for topic, query, max_n in SEARCH_TOPICS:
        print(f"\n{'─'*60}")
        print(f"[Topic: {topic}]  query: {query!r}")
        try:
            pmcids = search_pmc(query, max_results=max_n + 3)  # extra buffer for failures
        except Exception as e:
            print(f"  PMC search failed: {e}")
            continue

        found = 0
        for pmcid in pmcids:
            if found >= max_n:
                break
            if pmcid in existing_pmcids:
                print(f"  PMCID {pmcid}: already indexed, skipping")
                found += 1
                continue

            print(f"  Fetching PMCID {pmcid}...")
            time.sleep(NCBI_DELAY)
            xml_text = fetch_pmc_xml(pmcid)
            if xml_text is None:
                print(f"  PMCID {pmcid}: fetch failed, skipping")
                continue

            article = parse_jats_xml(xml_text, pmcid)
            if article is None:
                print(f"  PMCID {pmcid}: parse failed or no title, skipping")
                continue

            print(f"  PMCID {pmcid}: OK — {article['title'][:80]}")
            new_articles.append(article)
            existing_pmcids.add(pmcid)
            found += 1

    all_articles = existing_articles + new_articles

    if not all_articles:
        print("\nNo articles collected. Check network connectivity and try again.")
        return

    # Persist article JSON
    with open(ARTICLES_PATH, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_articles)} articles → {ARTICLES_PATH}")
    print(f"  ({len(new_articles)} new, {len(existing_articles)} existing)")

    # Rebuild indexes (always rebuild so BM25/ChromaDB reflect full article set)
    build_indexes(all_articles)

    print("\n" + "="*60)
    print("Local obstetrics evidence database is ready.")
    print(f"  Articles JSON : {ARTICLES_PATH}")
    print(f"  BM25 index   : {BM25_PATH}")
    print(f"  ChromaDB     : {CHROMA_DIR}")
    print("="*60)


if __name__ == "__main__":
    main()
