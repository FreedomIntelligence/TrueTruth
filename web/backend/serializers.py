"""Serialize WorkflowState dataclass fields to JSON-safe dicts for SSE events."""

from dataclasses import asdict, is_dataclass
from typing import List


def serialize_evidence_list(evidence_list) -> List[dict]:
    """Evidence list → JSON-safe list (drop full_text, truncate abstract)."""
    result = []
    for e in evidence_list or []:
        result.append(
            {
                "title": e.title,
                "pmid": getattr(e, "pmid", None),
                "pmcid": getattr(e, "pmcid", None),
                "source": getattr(e, "source", ""),
                "study_type": getattr(e, "study_type", None),
                "relevance_score": getattr(e, "relevance_score", 0.0),
                "grade_level": getattr(e, "grade_level", None),
                "abstract_preview": (getattr(e, "abstract", "") or "")[:200],
                "key_sentences": getattr(e, "key_sentences", None),
            }
        )
    return result


def serialize_agent_output(agent_name: str, state: dict) -> dict:
    """Extract and serialize a specific agent's output from the workflow state."""
    if agent_name == "Ask":
        pico = state.get("pico_query")
        return {
            "pico_query": asdict(pico) if (pico and is_dataclass(pico)) else pico,
            "question_type": state.get("question_type"),
        }

    elif agent_name == "Acquire":
        return {
            "total_results": state.get("total_results", 0),
            "selected_count": state.get("selected_count", 0),
            "study_type_distribution": state.get("study_type_distribution", {}),
            "evidence_list": serialize_evidence_list(state.get("evidence_list")),
        }

    elif agent_name == "Appraise":
        appraisal = state.get("appraisal_results")
        if appraisal and is_dataclass(appraisal):
            return {
                "has_conflict": appraisal.has_conflict,
                "conflict_description": appraisal.conflict_description,
                "summary": appraisal.summary,
                "evidence_grades": [
                    {
                        "title": e.title,
                        "grade_level": e.grade_level,
                        "study_type": e.study_type,
                        "relevance_score": e.relevance_score,
                    }
                    for e in appraisal.evidence
                ],
            }
        return {}

    elif agent_name == "Apply":
        rec = state.get("recommendation")
        if rec and is_dataclass(rec):
            return {
                "recommendation": {
                    "text": rec.text,
                    "strength": rec.strength,
                    "rationale": rec.rationale,
                    "caveats": rec.caveats,
                    "evidence_quality": rec.evidence_quality,
                }
            }
        return {}

    elif agent_name == "Assess":
        assess = state.get("assessment")
        if assess and is_dataclass(assess):
            return {
                "assessment": {
                    "quality_score": assess.quality_score,
                    "gaps": assess.gaps,
                }
            }
        return {}

    return {}
