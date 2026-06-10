from pathlib import Path
from typing import Union
import frontmatter
from pydantic import ValidationError

from hypertensiondb.schema.base import EvidenceType
from hypertensiondb.schema.rct import RctFrontmatter
from hypertensiondb.schema.sr_meta import SrFrontmatter, MetaFrontmatter
from hypertensiondb.schema.guideline import GuidelineFrontmatter
from hypertensiondb.schema.tcm import TcmFrontmatter
from hypertensiondb.schema.label import LabelFrontmatter
from hypertensiondb.schema.sections import split_sections

AnyFrontmatter = Union[
    RctFrontmatter, SrFrontmatter, MetaFrontmatter, GuidelineFrontmatter,
    TcmFrontmatter, LabelFrontmatter,
]

_TYPE_MODEL = {
    EvidenceType.RCT: RctFrontmatter,
    EvidenceType.SR: SrFrontmatter,
    EvidenceType.META: MetaFrontmatter,
    EvidenceType.GL: GuidelineFrontmatter,
    EvidenceType.TCM: TcmFrontmatter,
    EvidenceType.DRUG_SAFETY: LabelFrontmatter,
}


def load_evidence(path: Path) -> tuple[AnyFrontmatter, dict[str, str]]:
    """Parse an evidence .md file into (frontmatter model, sections dict).

    Raises ValidationError if frontmatter is invalid.
    Raises ValueError if evidence type is unknown.
    """
    raw = frontmatter.load(str(path))
    meta = dict(raw.metadata)
    body = raw.content

    ev_type_str = meta.get("type", "")
    try:
        ev_type = EvidenceType(ev_type_str)
    except ValueError:
        raise ValueError(f"Unknown evidence type '{ev_type_str}' in {path}")

    model_cls = _TYPE_MODEL[ev_type]
    fm = model_cls(**meta)
    sections = split_sections(body)
    return fm, sections
