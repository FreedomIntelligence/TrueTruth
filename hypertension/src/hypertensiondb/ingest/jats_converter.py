from typing import Optional

from lxml import etree


_SEC_TYPE_TO_KEY = {
    "intro": "background",
    "introduction": "background",
    "background": "background",
    "methods": "methods",
    "materials|methods": "methods",
    "results": "results",
    "discussion": "discussion",
    "conclusions": "conclusion",
    "conclusion": "conclusion",
}

_STANDARD_KEYS = [
    "clinical_bottom_line", "abstract_zh", "abstract_en",
    "background", "methods", "results", "discussion", "conclusion",
]


def jats_to_evidence(xml_text: str, evidence_type: str) -> tuple[dict, dict]:
    """Parse JATS XML into (frontmatter dict, sections dict).

    The frontmatter always carries status='draft' and extracted_by='api'.
    """
    root = etree.fromstring(xml_text.encode("utf-8"))

    fm: dict = {
        "type": evidence_type,
        "language": "en",
        "status": "draft",
        "extracted_by": "api",
        "authors": [],
        "tags": [],
    }

    title_el = root.find(".//article-meta/title-group/article-title")
    title_en = _flatten_text(title_el) if title_el is not None else None
    fm["title"] = {"zh": None, "en": title_en or "Untitled"}

    for contrib in root.findall(".//article-meta/contrib-group/contrib[@contrib-type='author']"):
        surname = _text(contrib, ".//surname")
        given = _text(contrib, ".//given-names")
        if surname:
            initials = "".join(p[0] for p in (given or "").split() if p)
            fm["authors"].append(f"{surname} {initials}".strip())

    year_str = (
        _text(root, ".//article-meta/pub-date[@pub-type='epub']/year")
        or _text(root, ".//article-meta/pub-date[@pub-type='ppub']/year")
        or _text(root, ".//article-meta/pub-date/year")
    )
    if year_str and year_str.isdigit():
        fm["year"] = int(year_str)

    journal = _text(root, ".//journal-meta//journal-title")
    if journal:
        fm["journal"] = journal

    for art_id in root.findall(".//article-meta/article-id"):
        id_type = art_id.get("pub-id-type")
        value = (art_id.text or "").strip()
        if not value:
            continue
        if id_type == "doi":
            fm["doi"] = value
        elif id_type == "pmid":
            fm["pmid"] = value
        elif id_type == "pmc":
            fm["url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{value}/"

    sections: dict[str, str] = {k: "" for k in _STANDARD_KEYS}

    abstract_paragraphs = root.findall(".//article-meta/abstract//p")
    if abstract_paragraphs:
        sections["abstract_en"] = "\n\n".join(
            _flatten_text(p) for p in abstract_paragraphs if _flatten_text(p)
        )

    for sec in root.findall(".//body/sec"):
        sec_type = (sec.get("sec-type") or "").lower().strip()
        key = _SEC_TYPE_TO_KEY.get(sec_type)
        if not key:
            title = _text(sec, "title")
            if title:
                key = _infer_section_from_title(title)
        if not key:
            continue
        paras = [
            _flatten_text(p) for p in sec.findall(".//p")
            if _flatten_text(p)
        ]
        if paras:
            new_text = "\n\n".join(paras)
            if sections[key]:
                sections[key] = sections[key] + "\n\n" + new_text
            else:
                sections[key] = new_text

    return fm, sections


def _flatten_text(el) -> str:
    """Recursively extract all text content from an element."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _text(node, xpath: str) -> Optional[str]:
    el = node.find(xpath)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _infer_section_from_title(title: str) -> Optional[str]:
    t = title.lower().strip()
    if "method" in t or "材料" in t:
        return "methods"
    if "result" in t or "finding" in t:
        return "results"
    if "conclusion" in t or "summary" in t:
        return "conclusion"
    if "discussion" in t:
        return "discussion"
    if "introduction" in t or "background" in t:
        return "background"
    return None
