import os
from typing import Optional

import httpx
from lxml import etree


_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH_URL = f"{_EUTILS_BASE}/esearch.fcgi"
_EFETCH_URL = f"{_EUTILS_BASE}/efetch.fcgi"


class NCBIClient:
    """Thin client over NCBI E-utilities.

    Pass NCBI_API_KEY env var to get 10 req/s (vs 3 req/s without).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def _params(self, **kwargs) -> dict:
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key
        return kwargs

    def esearch(self, query: str, db: str = "pubmed", retmax: int = 50) -> list[str]:
        """Search and return list of IDs (PMIDs or PMCIDs)."""
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_ESEARCH_URL, params=self._params(
                db=db, term=query, retmax=retmax, retmode="xml",
            ))
            resp.raise_for_status()
        root = etree.fromstring(resp.text.encode("utf-8"))
        return [el.text for el in root.findall(".//IdList/Id") if el.text]

    def efetch_pubmed(self, pmids: list[str]) -> list[dict]:
        """Fetch PubMed metadata for given PMIDs, return list of parsed dicts."""
        if not pmids:
            return []
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_EFETCH_URL, params=self._params(
                db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml",
            ))
            resp.raise_for_status()
        return _parse_pubmed_xml(resp.text)

    def efetch_pmc_xml(self, pmc_id: str) -> str:
        """Fetch JATS XML for a PMC OA article. Accepts 'PMC9999999' or '9999999'."""
        clean_id = pmc_id.removeprefix("PMC")
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_EFETCH_URL, params=self._params(
                db="pmc", id=clean_id, rettype="xml", retmode="xml",
            ))
            resp.raise_for_status()
        return resp.text


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse the PubMed efetch XML into a list of dicts."""
    root = etree.fromstring(xml_text.encode("utf-8"))
    records: list[dict] = []
    for art in root.findall(".//PubmedArticle"):
        rec: dict = {}
        rec["pmid"] = _text(art, ".//MedlineCitation/PMID")
        rec["title"] = _text(art, ".//ArticleTitle")
        rec["abstract"] = " ".join(
            t.text or "" for t in art.findall(".//Abstract/AbstractText")
        ).strip()
        rec["journal"] = _text(art, ".//Journal/Title")
        rec["doi"] = _id_by_type(art, "doi")
        rec["pmc_id"] = _id_by_type(art, "pmc")

        authors: list[str] = []
        for a in art.findall(".//AuthorList/Author"):
            last = _text(a, "LastName")
            fore = _text(a, "ForeName")
            initials = "".join(p[0] for p in (fore or "").split() if p)
            if last:
                authors.append(f"{last} {initials}".strip())
        rec["authors"] = authors

        year_str = _text(art, ".//PubMedPubDate[@PubStatus='pubmed']/Year") \
                   or _text(art, ".//PubDate/Year")
        rec["year"] = int(year_str) if year_str and year_str.isdigit() else None

        records.append(rec)
    return records


def _text(node, xpath: str) -> Optional[str]:
    el = node.find(xpath)
    return el.text.strip() if (el is not None and el.text) else None


def _id_by_type(art, id_type: str) -> Optional[str]:
    for el in art.findall(".//ArticleIdList/ArticleId"):
        if el.get("IdType") == id_type:
            return el.text
    return None
