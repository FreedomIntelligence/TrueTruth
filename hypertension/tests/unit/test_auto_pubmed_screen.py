import json
from pathlib import Path

import pytest

from hypertensiondb.ingest.auto_pubmed_screen import (
    PubMedTopic,
    classify_pubmed_record,
    deduplicate_records,
    load_topics,
    screen_pubmed_topics,
    write_screening_jsonl,
)


def _record(**overrides):
    data = {
        "pmid": "1001",
        "doi": "10.1000/test",
        "pmc_id": "PMC1001",
        "title": "Guideline for hypertension management",
        "abstract": (
            "This guideline provides recommendations for blood pressure targets, "
            "antihypertensive treatment, monitoring, contraindications, and follow-up."
        ),
        "journal": "Journal of Hypertension",
        "year": 2025,
        "authors": ["Smith J"],
        "publication_types": ["Practice Guideline"],
        "mesh_terms": ["Hypertension", "Antihypertensive Agents"],
    }
    data.update(overrides)
    return data


@pytest.mark.unit
def test_classify_full_text_guideline_as_active_core():
    candidate = classify_pubmed_record(
        _record(),
        topic=PubMedTopic(
            name="core_hypertension",
            query="hypertension guideline",
            tags=["hypertension", "guideline"],
        ),
    )

    assert candidate.access_status == "oa_fulltext"
    assert candidate.evidence_type == "guideline"
    assert candidate.evidence_tier == "active_core"
    assert candidate.use_policy == "recommendation_support"
    assert candidate.score >= 80
    assert "guideline" in candidate.topic_tags
    assert candidate.population_relevance == "human_clinical"
    assert candidate.clinical_management_relevance == "direct"
    assert candidate.download_eligible is True
    assert candidate.download_blockers == []


@pytest.mark.unit
def test_classify_paywalled_rct_as_important_but_not_recommendation_support():
    candidate = classify_pubmed_record(
        _record(
            pmid="1002",
            doi="10.1000/paywalled",
            pmc_id=None,
            title="Randomized trial of antihypertensive therapy",
            abstract="Randomized controlled trial of blood pressure treatment.",
            publication_types=["Randomized Controlled Trial"],
        ),
        topic=PubMedTopic(
            name="core_hypertension",
            query="hypertension randomized controlled trial",
            tags=["hypertension"],
        ),
    )

    assert candidate.access_status == "abstract_only"
    assert candidate.evidence_type == "rct"
    assert candidate.evidence_tier == "paywalled_important"
    assert candidate.use_policy == "discovery_only"
    assert "recommendation_support" not in candidate.allowed_use
    assert candidate.download_eligible is False
    assert "no_open_fulltext" in candidate.download_blockers


@pytest.mark.unit
def test_special_topic_case_series_with_fulltext_enters_special_topic_not_core():
    candidate = classify_pubmed_record(
        _record(
            pmid="1003",
            title="Supine hypertension and orthostatic hypotension case series",
            abstract="Case series describing management of supine hypertension and orthostatic hypotension.",
            publication_types=["Case Reports"],
            mesh_terms=["Orthostatic Hypotension"],
        ),
        topic=PubMedTopic(
            name="supine_orthostatic",
            query="supine hypertension orthostatic hypotension",
            tags=["supine_hypertension", "orthostatic_hypotension"],
            special_topic=True,
        ),
    )

    assert candidate.evidence_type == "case_report"
    assert candidate.evidence_tier == "active_special_topic"
    assert candidate.use_policy == "limited_context_support"
    assert "supine_hypertension" in candidate.topic_tags
    assert candidate.population_relevance == "human_clinical"
    assert candidate.clinical_management_relevance == "direct"
    assert candidate.download_eligible is True


@pytest.mark.unit
def test_irrelevant_record_is_rejected_even_with_fulltext():
    candidate = classify_pubmed_record(
        _record(
            pmid="1004",
            title="Dental enamel color in adolescents",
            abstract="A study of dental enamel color.",
            publication_types=["Journal Article"],
            mesh_terms=["Dentistry"],
        ),
        topic=PubMedTopic(
            name="core_hypertension",
            query="hypertension",
            tags=["hypertension"],
        ),
    )

    assert candidate.evidence_tier == "rejected"
    assert candidate.use_policy == "do_not_use"
    assert candidate.clinical_management_relevance == "irrelevant"
    assert candidate.download_eligible is False
    assert "not_clinical_management" in candidate.download_blockers


@pytest.mark.unit
def test_animal_mechanistic_record_is_not_download_eligible():
    candidate = classify_pubmed_record(
        _record(
            pmid="1005",
            title="Beta-aminopropionitrile induced thoracic aortopathy in mice",
            abstract=(
                "A mouse model study of molecular mechanisms and signaling pathways "
                "in vascular remodeling."
            ),
            publication_types=["Journal Article"],
            mesh_terms=["Mice", "Animals", "Signal Transduction"],
        ),
        topic=PubMedTopic(
            name="genetic_hypertension",
            query="PDE3A hypertension",
            tags=["genetic_hypertension"],
            special_topic=True,
        ),
    )

    assert candidate.population_relevance == "animal_only"
    assert candidate.study_design_verified == "animal"
    assert candidate.clinical_management_relevance == "background"
    assert candidate.download_eligible is False
    assert "animal_or_mechanistic_only" in candidate.download_blockers


@pytest.mark.unit
def test_indirect_background_record_is_not_download_eligible_for_core_topic():
    candidate = classify_pubmed_record(
        _record(
            pmid="1006",
            title="Hypertension pathophysiology and vascular biomarkers",
            abstract="This review describes biomarkers and mechanisms of hypertension.",
            publication_types=["Review"],
            mesh_terms=["Hypertension", "Biomarkers"],
        ),
        topic=PubMedTopic(
            name="core_hypertension",
            query="hypertension",
            tags=["hypertension"],
        ),
    )

    assert candidate.clinical_management_relevance == "background"
    assert candidate.download_eligible is False
    assert "not_clinical_management" in candidate.download_blockers


@pytest.mark.unit
def test_deduplicate_records_prefers_fulltext_and_newer_records():
    records = [
        _record(pmid="1001", doi="10.1000/a", pmc_id=None, year=2023),
        _record(pmid="1001", doi="10.1000/a", pmc_id="PMC1001", year=2022),
        _record(pmid="1002", doi="10.1000/b", pmc_id=None, year=2025),
        _record(pmid="1003", doi="10.1000/b", pmc_id="PMC1003", year=2020),
    ]

    deduped = deduplicate_records(records)

    assert [r["pmid"] for r in deduped] == ["1001", "1003"]
    assert deduped[0]["pmc_id"] == "PMC1001"
    assert deduped[1]["pmc_id"] == "PMC1003"


@pytest.mark.unit
def test_screen_pubmed_topics_fetches_and_classifies_records():
    class FakeClient:
        def esearch(self, query, db="pubmed", retmax=50):
            assert db == "pubmed"
            assert retmax == 5
            return ["1001", "1002"]

        def efetch_pubmed(self, pmids):
            assert pmids == ["1001", "1002"]
            return [
                _record(pmid="1001", pmc_id="PMC1001"),
                _record(
                    pmid="1002",
                    doi="10.1000/second",
                    pmc_id=None,
                    publication_types=["Randomized Controlled Trial"],
                    title="Randomized trial in hypertension",
                ),
            ]

    candidates = screen_pubmed_topics(
        topics=[
            PubMedTopic(
                name="core_hypertension",
                query="hypertension",
                tags=["hypertension"],
            )
        ],
        client=FakeClient(),
        retmax=5,
    )

    assert len(candidates) == 2
    assert {c.pmid for c in candidates} == {"1001", "1002"}
    assert {c.evidence_tier for c in candidates} == {"active_core", "paywalled_important"}


@pytest.mark.unit
def test_screen_pubmed_topics_pauses_between_topics():
    calls = []

    class FakeClient:
        def esearch(self, query, db="pubmed", retmax=50):
            return [query]

        def efetch_pubmed(self, pmids):
            return [_record(pmid=pmids[0], doi=f"10.1000/{pmids[0]}")]

    candidates = screen_pubmed_topics(
        topics=[
            PubMedTopic(name="topic_a", query="1001", tags=["hypertension"]),
            PubMedTopic(name="topic_b", query="1002", tags=["hypertension"]),
        ],
        client=FakeClient(),
        retmax=5,
        request_pause_seconds=0.5,
        sleeper=calls.append,
    )

    assert len(candidates) == 2
    assert calls == [0.5]


@pytest.mark.unit
def test_write_screening_jsonl(tmp_path: Path):
    candidate = classify_pubmed_record(
        _record(),
        topic=PubMedTopic(name="core", query="hypertension", tags=["hypertension"]),
    )
    output = tmp_path / "screening.jsonl"

    write_screening_jsonl([candidate], output)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["pmid"] == "1001"
    assert rows[0]["evidence_tier"] == "active_core"
    assert rows[0]["access_status"] == "oa_fulltext"
    assert rows[0]["download_eligible"] is True
    assert rows[0]["matched_management_domains"] == [
        "treatment",
        "bp_target",
        "monitoring",
        "contraindication",
    ]


@pytest.mark.unit
def test_nasal_pubmed_topic_config_is_loadable():
    topics = load_topics("config/pubmed_screen_topics_nasal.json")

    assert 8 <= len(topics) <= 10
    names = {topic.name for topic in topics}
    assert "chronic_rhinosinusitis" in names
    assert "allergic_rhinitis" in names
    assert "nasal_polyps_biologics" in names
    assert all("nasal" in topic.tags for topic in topics)


@pytest.mark.unit
def test_nasal_topic_reason_uses_generic_disease_wording():
    candidate = classify_pubmed_record(
        _record(
            pmid="2001",
            title="Guideline for allergic rhinitis management",
            abstract="Patients with rhinitis may receive intranasal corticosteroid treatment and follow-up.",
            mesh_terms=["Rhinitis, Allergic"],
        ),
        topic=PubMedTopic(
            name="allergic_rhinitis",
            query="allergic rhinitis treatment",
            tags=["nasal", "allergic_rhinitis", "rhinitis"],
        ),
    )

    assert candidate.evidence_tier == "active_core"
    assert "disease/topic-specific terms detected" in candidate.reasons
    assert "hypertension or topic-specific terms detected" not in candidate.reasons
