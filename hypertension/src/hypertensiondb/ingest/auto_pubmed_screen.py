"""PubMed candidate discovery and automated evidence-tier screening.

This module intentionally writes a screening JSONL report instead of writing
formal evidence markdown. It is the staging step before full-text acquisition
and curated evidence ingestion.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Protocol

from hypertensiondb.ingest.ncbi_client import NCBIClient


@dataclass(frozen=True)
class PubMedTopic:
    name: str
    query: str
    tags: list[str]
    special_topic: bool = False


@dataclass(frozen=True)
class ScreenedPubMedCandidate:
    pmid: str
    doi: str | None
    pmc_id: str | None
    title: str
    abstract: str
    journal: str | None
    year: int | None
    publication_types: list[str]
    mesh_terms: list[str]
    authors: list[str]
    topic_name: str
    topic_tags: list[str]
    access_status: str
    evidence_type: str
    evidence_tier: str
    use_policy: str
    allowed_use: list[str]
    blocked_use: list[str]
    score: int
    reasons: list[str]
    population_relevance: str
    clinical_management_relevance: str
    matched_management_domains: list[str]
    study_design_verified: str
    download_eligible: bool
    download_blockers: list[str]


class PubMedClient(Protocol):
    def esearch(self, query: str, db: str = "pubmed", retmax: int = 50) -> list[str]:
        ...

    def efetch_pubmed(self, pmids: list[str]) -> list[dict[str, Any]]:
        ...


DEFAULT_TOPICS = [
    PubMedTopic(
        name="core_hypertension_guidelines",
        query=(
            'hypertension AND ("Practice Guideline"[pt] OR guideline[ti] '
            'OR "systematic review"[pt] OR meta-analysis[pt])'
        ),
        tags=["hypertension", "guideline"],
    ),
    PubMedTopic(
        name="fibromuscular_renovascular",
        query=(
            '("fibromuscular dysplasia" OR "renovascular hypertension") '
            'AND (angioplasty OR follow-up OR management)'
        ),
        tags=["renovascular_hypertension", "fibromuscular_dysplasia"],
        special_topic=True,
    ),
    PubMedTopic(
        name="paroxysmal_nocturnal_hypertension",
        query=(
            '("nocturnal hypertension" OR "paroxysmal hypertension" '
            'OR "blood pressure variability") AND management'
        ),
        tags=["nocturnal_hypertension", "paroxysmal_hypertension"],
        special_topic=True,
    ),
    PubMedTopic(
        name="hypertension_brachydactyly",
        query='"hypertension and brachydactyly" OR "PDE3A hypertension"',
        tags=["genetic_hypertension", "brachydactyly"],
        special_topic=True,
    ),
    PubMedTopic(
        name="supine_orthostatic",
        query='"supine hypertension" AND "orthostatic hypotension" AND management',
        tags=["supine_hypertension", "orthostatic_hypotension"],
        special_topic=True,
    ),
]


_GUIDELINE_TYPES = {
    "guideline",
    "practice guideline",
    "consensus development conference",
}
_REVIEW_TYPES = {
    "systematic review",
    "meta-analysis",
}
_RCT_TYPES = {
    "randomized controlled trial",
    "clinical trial",
}
_OBS_TYPES = {
    "observational study",
    "cohort study",
    "case-control studies",
}
_CASE_TYPES = {
    "case reports",
    "case report",
}

_HYPERTENSION_TERMS = {
    "hypertension",
    "blood pressure",
    "antihypertensive",
    "orthostatic hypotension",
    "supine hypertension",
    "renovascular",
    "fibromuscular dysplasia",
    "brachydactyly",
    "pde3a",
}

_ACTIONABLE_TERMS = {
    "recommendation",
    "recommendations",
    "treatment",
    "therapy",
    "management",
    "monitoring",
    "contraindication",
    "follow-up",
    "blood pressure target",
    "target",
}

_ANIMAL_TERMS = {
    "animals",
    "mice",
    "mouse",
    "rats",
    "rat",
    "murine",
    "animal model",
    "in vitro",
}

_HUMAN_TERMS = {
    "humans",
    "patients",
    "patient",
    "clinical",
    "trial",
    "cohort",
    "case report",
    "case series",
    "guideline",
    "review",
}

_MECHANISM_TERMS = {
    "mechanism",
    "mechanisms",
    "molecular",
    "pathway",
    "signaling",
    "biomarker",
    "biomarkers",
    "pathophysiology",
    "gene expression",
    "in vitro",
}

_MANAGEMENT_DOMAINS = {
    "diagnosis": {"diagnosis", "diagnostic", "screening", "assessment", "evaluate", "evaluation"},
    "treatment": {"treatment", "therapy", "management", "antihypertensive", "drug", "medication"},
    "bp_target": {"blood pressure target", "bp target", "target blood pressure", "target"},
    "monitoring": {"monitoring", "follow-up", "follow up", "ambulatory blood pressure", "home blood pressure"},
    "contraindication": {"contraindication", "contraindications", "safety", "adverse", "harm"},
    "referral": {"referral", "emergency", "urgent", "hospitalization"},
}


def screen_pubmed_topics(
    *,
    topics: list[PubMedTopic],
    client: PubMedClient | None = None,
    retmax: int = 25,
) -> list[ScreenedPubMedCandidate]:
    """Search PubMed topics and return classified candidate documents."""
    client = client or NCBIClient()
    all_records: list[tuple[PubMedTopic, dict[str, Any]]] = []

    for topic in topics:
        pmids = client.esearch(topic.query, db="pubmed", retmax=retmax)
        records = client.efetch_pubmed(pmids)
        for record in records:
            all_records.append((topic, record))

    seen: dict[str, tuple[PubMedTopic, dict[str, Any]]] = {}
    for topic, record in all_records:
        key = _dedupe_key(record)
        current = seen.get(key)
        if current is None or _record_priority(record) > _record_priority(current[1]):
            seen[key] = (topic, record)

    return [
        classify_pubmed_record(record, topic=topic)
        for topic, record in sorted(seen.values(), key=lambda item: _sort_record(item[1]))
    ]


def classify_pubmed_record(
    record: dict[str, Any],
    *,
    topic: PubMedTopic,
) -> ScreenedPubMedCandidate:
    title = str(record.get("title") or "").strip()
    abstract = str(record.get("abstract") or "").strip()
    publication_types = _string_list(record.get("publication_types"))
    mesh_terms = _string_list(record.get("mesh_terms"))
    evidence_type = _evidence_type(publication_types, title)
    access_status = "oa_fulltext" if str(record.get("pmc_id") or "").strip() else "abstract_only"
    score, reasons = _score_record(
        record=record,
        topic=topic,
        evidence_type=evidence_type,
        access_status=access_status,
    )
    population_relevance = _population_relevance(record)
    clinical_management_relevance, matched_domains = _clinical_management_relevance(record, topic)
    study_design_verified = _study_design_verified(evidence_type, population_relevance, record)
    evidence_tier, use_policy, allowed_use, blocked_use = _tier_and_policy(
        topic=topic,
        evidence_type=evidence_type,
        access_status=access_status,
        score=score,
        title=title,
        abstract=abstract,
        mesh_terms=mesh_terms,
        population_relevance=population_relevance,
        clinical_management_relevance=clinical_management_relevance,
    )
    download_eligible, download_blockers = _download_eligibility(
        access_status=access_status,
        pmc_id=_optional_string(record.get("pmc_id")),
        evidence_tier=evidence_tier,
        population_relevance=population_relevance,
        clinical_management_relevance=clinical_management_relevance,
        allowed_use=allowed_use,
    )

    return ScreenedPubMedCandidate(
        pmid=str(record.get("pmid") or ""),
        doi=_optional_string(record.get("doi")),
        pmc_id=_optional_string(record.get("pmc_id")),
        title=title,
        abstract=abstract,
        journal=_optional_string(record.get("journal")),
        year=_optional_int(record.get("year")),
        publication_types=publication_types,
        mesh_terms=mesh_terms,
        authors=_string_list(record.get("authors")),
        topic_name=topic.name,
        topic_tags=list(topic.tags),
        access_status=access_status,
        evidence_type=evidence_type,
        evidence_tier=evidence_tier,
        use_policy=use_policy,
        allowed_use=allowed_use,
        blocked_use=blocked_use,
        score=score,
        reasons=reasons,
        population_relevance=population_relevance,
        clinical_management_relevance=clinical_management_relevance,
        matched_management_domains=matched_domains,
        study_design_verified=study_design_verified,
        download_eligible=download_eligible,
        download_blockers=download_blockers,
    )


def deduplicate_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate records by PMID/DOI/title, preferring full text then recency."""
    by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _dedupe_key(record)
        current = by_key.get(key)
        if current is None or _record_priority(record) > _record_priority(current):
            by_key[key] = record
    return [by_key[key] for key in sorted(by_key, key=lambda item: _sort_record(by_key[item]))]


def write_screening_jsonl(
    candidates: Iterable[ScreenedPubMedCandidate],
    output_path: str | Path,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(json.dumps(asdict(candidate), ensure_ascii=False) + "\n")


def load_topics(path: str | Path) -> list[PubMedTopic]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    topics: list[PubMedTopic] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each topic must be an object")
        topics.append(
            PubMedTopic(
                name=str(item["name"]),
                query=str(item["query"]),
                tags=_string_list(item.get("tags")),
                special_topic=bool(item.get("special_topic", False)),
            )
        )
    return topics


def _score_record(
    *,
    record: dict[str, Any],
    topic: PubMedTopic,
    evidence_type: str,
    access_status: str,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if access_status == "oa_fulltext":
        score += 25
        reasons.append("legal full text is available via PMC")
    elif str(record.get("abstract") or "").strip():
        score += 8
        reasons.append("abstract is available but full text was not identified")

    type_scores = {
        "guideline": 35,
        "systematic_review": 30,
        "rct": 28,
        "observational": 16,
        "case_report": 8,
        "narrative_or_other": 5,
    }
    score += type_scores[evidence_type]
    reasons.append(f"evidence type classified as {evidence_type}")

    text = _record_text(record)
    if _contains_any(text, _HYPERTENSION_TERMS) or any(tag in text for tag in topic.tags):
        score += 20
        reasons.append("disease/topic-specific terms detected")
    else:
        score -= 35
        reasons.append("no disease/topic-specific signal detected")

    if _contains_any(text, _ACTIONABLE_TERMS):
        score += 10
        reasons.append("actionable management language detected")

    year = _optional_int(record.get("year"))
    if year is not None and year >= 2018:
        score += 8
        reasons.append("recent publication")
    elif year is not None and year < 2010:
        score -= 8
        reasons.append("older publication")

    if topic.special_topic:
        score += 7
        reasons.append("special-topic route allows lower-level evidence")

    return max(0, min(100, score)), reasons


def _tier_and_policy(
    *,
    topic: PubMedTopic,
    evidence_type: str,
    access_status: str,
    score: int,
    title: str,
    abstract: str,
    mesh_terms: list[str],
    population_relevance: str,
    clinical_management_relevance: str,
) -> tuple[str, str, list[str], list[str]]:
    text = " ".join([title, abstract, " ".join(mesh_terms)]).lower()
    if not (_contains_any(text, _HYPERTENSION_TERMS) or any(tag.lower() in text for tag in topic.tags)):
        return (
            "rejected",
            "do_not_use",
            [],
            ["recommendation_support", "indexing", "gap_detection"],
        )

    if population_relevance in {"animal_only", "mechanistic"}:
        return (
            "background",
            "background_context",
            ["gap_detection"],
            ["recommendation_support", "full_text_indexing", "strong_recommendation_support"],
        )

    if clinical_management_relevance == "irrelevant":
        return (
            "rejected",
            "do_not_use",
            [],
            ["recommendation_support", "indexing", "gap_detection"],
        )

    if access_status != "oa_fulltext":
        if evidence_type in {"guideline", "systematic_review", "rct"} and score >= 50:
            return (
                "paywalled_important",
                "discovery_only",
                ["gap_detection", "topic_routing", "citation_awareness"],
                ["recommendation_support", "full_text_indexing"],
            )
        return (
            "abstract_index",
            "discovery_only",
            ["gap_detection", "topic_routing"],
            ["recommendation_support", "full_text_indexing"],
        )

    if clinical_management_relevance == "background" and not topic.special_topic:
        return (
            "background",
            "background_context",
            ["background_context", "gap_detection"],
            ["strong_recommendation_support", "automatic_download"],
        )

    if evidence_type in {"guideline", "systematic_review", "rct"} and score >= 70:
        tier = "active_special_topic" if topic.special_topic else "active_core"
        return (
            tier,
            "recommendation_support",
            ["recommendation_support", "full_text_indexing", "gap_detection"],
            [],
        )

    if topic.special_topic and evidence_type in {"observational", "case_report", "narrative_or_other"}:
        return (
            "active_special_topic",
            "limited_context_support",
            ["full_text_indexing", "background_context", "gap_detection"],
            ["strong_recommendation_support"],
        )

    if score >= 45:
        return (
            "background",
            "background_context",
            ["background_context", "gap_detection"],
            ["strong_recommendation_support"],
        )

    return ("staging", "needs_review_or_rescore", ["gap_detection"], ["recommendation_support"])


def _evidence_type(publication_types: list[str], title: str) -> str:
    lowered = {item.lower() for item in publication_types}
    title_lower = title.lower()
    if lowered & _GUIDELINE_TYPES or "guideline" in title_lower:
        return "guideline"
    if lowered & _REVIEW_TYPES or "systematic review" in title_lower or "meta-analysis" in title_lower:
        return "systematic_review"
    if lowered & _RCT_TYPES or "randomized" in title_lower:
        return "rct"
    if lowered & _OBS_TYPES or "cohort" in title_lower:
        return "observational"
    if lowered & _CASE_TYPES or "case report" in title_lower or "case series" in title_lower:
        return "case_report"
    return "narrative_or_other"


def _population_relevance(record: dict[str, Any]) -> str:
    text = _record_text(record)
    mesh_terms = {item.lower() for item in _string_list(record.get("mesh_terms"))}
    if ("animals" in mesh_terms or _contains_any(text, _ANIMAL_TERMS)) and "humans" not in mesh_terms:
        return "animal_only"
    if _contains_any(text, _MECHANISM_TERMS) and not _contains_any(text, _HUMAN_TERMS):
        return "mechanistic"
    if _contains_any(text, _HUMAN_TERMS) or "humans" in mesh_terms:
        return "human_clinical"
    return "unclear"


def _clinical_management_relevance(
    record: dict[str, Any],
    topic: PubMedTopic,
) -> tuple[str, list[str]]:
    text = _record_text(record)
    if _contains_any(text, _ANIMAL_TERMS) or _contains_any(text, _MECHANISM_TERMS):
        return "background", []
    if not (_contains_any(text, _HYPERTENSION_TERMS) or any(tag.lower() in text for tag in topic.tags)):
        return "irrelevant", []

    matched_domains = [
        domain
        for domain, terms in _MANAGEMENT_DOMAINS.items()
        if _contains_any(text, terms)
    ]
    if matched_domains:
        return "direct", matched_domains
    if _contains_any(text, _MECHANISM_TERMS):
        return "background", []
    if topic.special_topic:
        return "indirect", []
    return "background", []


def _study_design_verified(
    evidence_type: str,
    population_relevance: str,
    record: dict[str, Any],
) -> str:
    if population_relevance == "animal_only":
        return "animal"
    text = _record_text(record)
    if population_relevance == "mechanistic" or _contains_any(text, _MECHANISM_TERMS):
        if evidence_type not in {"guideline", "systematic_review", "rct", "observational", "case_report"}:
            return "mechanistic"
    return evidence_type


def _download_eligibility(
    *,
    access_status: str,
    pmc_id: str | None,
    evidence_tier: str,
    population_relevance: str,
    clinical_management_relevance: str,
    allowed_use: list[str],
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if access_status != "oa_fulltext" or not pmc_id:
        blockers.append("no_open_fulltext")
    if evidence_tier in {"rejected", "staging", "paywalled_important", "abstract_index"}:
        blockers.append(f"tier:{evidence_tier}")
    if population_relevance in {"animal_only", "mechanistic"}:
        blockers.append("animal_or_mechanistic_only")
    if clinical_management_relevance not in {"direct", "indirect"}:
        blockers.append("not_clinical_management")
    if "full_text_indexing" not in allowed_use and "recommendation_support" not in allowed_use:
        blockers.append("not_allowed_for_fulltext_use")
    return not blockers, blockers


def _dedupe_key(record: dict[str, Any]) -> str:
    for key in ("doi", "pmid"):
        value = str(record.get(key) or "").strip().lower()
        if value:
            return f"{key}:{value}"
    return "title:" + " ".join(str(record.get("title") or "").lower().split())


def _record_priority(record: dict[str, Any]) -> tuple[int, int, int]:
    has_fulltext = 1 if str(record.get("pmc_id") or "").strip() else 0
    has_abstract = 1 if str(record.get("abstract") or "").strip() else 0
    year = _optional_int(record.get("year")) or 0
    return (has_fulltext, year, has_abstract)


def _sort_record(record: dict[str, Any]) -> tuple[int, str]:
    return (-(record.get("year") or 0), str(record.get("pmid") or ""))


def _record_text(record: dict[str, Any]) -> str:
    parts = [
        str(record.get("title") or ""),
        str(record.get("abstract") or ""),
        " ".join(_string_list(record.get("mesh_terms"))),
        " ".join(_string_list(record.get("publication_types"))),
    ]
    return " ".join(parts).lower()


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=Path, help="JSON topic registry; defaults to built-in topics.")
    parser.add_argument("--output", type=Path, required=True, help="Screening JSONL output path.")
    parser.add_argument("--retmax", type=int, default=25, help="PubMed records per topic.")
    args = parser.parse_args(argv)

    topics = load_topics(args.topics) if args.topics else DEFAULT_TOPICS
    candidates = screen_pubmed_topics(topics=topics, retmax=args.retmax)
    write_screening_jsonl(candidates, args.output)

    tier_counts: dict[str, int] = {}
    for candidate in candidates:
        tier_counts[candidate.evidence_tier] = tier_counts.get(candidate.evidence_tier, 0) + 1
    print(f"Wrote {len(candidates)} screened PubMed candidates to {args.output}")
    print(json.dumps(tier_counts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
