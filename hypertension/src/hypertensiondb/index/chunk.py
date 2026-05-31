from dataclasses import dataclass, field


@dataclass
class EvidenceChunk:
    point_id: str               # UUID derived from sha1(evidence_id:section_name)
    evidence_id: str            # e.g. "EV-RCT-2026-PENG-001"
    section_name: str           # e.g. "results", "clinical_bottom_line"
    text: str                   # cleaned section text
    is_clinical_bottom_line: bool
    metadata: dict = field(default_factory=dict)  # full frontmatter fields
