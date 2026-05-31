import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from hypertensiondb.ingest.parse_pdf import BasePdfParser
from hypertensiondb.ingest.clean import clean_text
from hypertensiondb.ingest.section_mapper import detect_sections
from hypertensiondb.ingest.frontmatter_extractor import BaseFrontmatterExtractor
from hypertensiondb.ingest.writer import (
    write_evidence_md, write_quarantine_md, EvidenceWriteResult,
)
from hypertensiondb.schema.base import EvidenceType
from hypertensiondb.schema.loader import _TYPE_MODEL

MIN_TEXT_CHARS = 50


class IngestStatus(StrEnum):
    OK = "ok"
    PARSE_FAILED = "parse_failed"
    QUARANTINED = "quarantined"
    DRY_RUN = "dry_run"


@dataclass
class IngestResult:
    status: IngestStatus
    output_path: Optional[Path] = None
    frontmatter: Optional[dict] = None
    sections: Optional[dict] = None
    error: Optional[str] = None


def _default_id_generator(fm: dict, evidence_root: Path) -> str:
    """Build a plausible ID using utils.id_gen.next_id() if possible.

    Note: next_id signature is (ev_type, year, author_pinyin) — no evidence_root arg.
    """
    try:
        from hypertensiondb.utils.id_gen import next_id
        from hypertensiondb.utils.pinyin import to_first_author_pinyin

        first_author = fm.get("authors", ["Unknown"])[0]
        pinyin = to_first_author_pinyin(first_author)
        return next_id(fm.get("type", "RCT"), fm.get("year", date.today().year), pinyin)
    except Exception:
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        return f"EV-{fm.get('type', 'RCT')}-{fm.get('year', 2026)}-UNKNOWN-{ts}"


class IngestPipeline:
    """Orchestrate PDF → parsed → cleaned → sectioned → extracted → validated → written."""

    def __init__(
        self,
        parser: BasePdfParser,
        extractor: BaseFrontmatterExtractor,
        evidence_root: Path,
        failed_root: Path,
        id_generator: Optional[Callable[[dict, Path], str]] = None,
    ) -> None:
        self._parser = parser
        self._extractor = extractor
        self._evidence_root = Path(evidence_root)
        self._failed_root = Path(failed_root)
        self._id_gen = id_generator or _default_id_generator

    def ingest_pdf(
        self,
        pdf_path: Path,
        evidence_type: str,
        dry_run: bool = False,
    ) -> IngestResult:
        pdf_path = Path(pdf_path)

        # Step 1: Parse
        try:
            parsed = self._parser.parse(pdf_path)
        except Exception as e:
            self._move_to_failed(pdf_path, error=str(e))
            return IngestResult(status=IngestStatus.PARSE_FAILED, error=str(e))

        # Step 2: Sanity check
        if len(parsed.raw_text.strip()) < MIN_TEXT_CHARS:
            self._move_to_failed(pdf_path, error=f"text too short ({len(parsed.raw_text)} chars)")
            return IngestResult(
                status=IngestStatus.PARSE_FAILED,
                error=f"Parsed text is suspiciously short: {len(parsed.raw_text)} chars",
            )

        # Step 3: Clean
        cleaned_text = clean_text(parsed.pages)

        # Step 4: Section
        sections = detect_sections(cleaned_text)

        # Step 5: Extract frontmatter
        fm = self._extractor.extract(text=cleaned_text, evidence_type=evidence_type)

        # Step 6: Assign ID
        fm["id"] = self._id_gen(fm, self._evidence_root)

        # Step 7: Validate via Pydantic
        try:
            ev_type_enum = EvidenceType(evidence_type)
            model_cls = _TYPE_MODEL[ev_type_enum]
            model_cls(**fm)
        except (ValidationError, KeyError, TypeError, ValueError) as e:
            if dry_run:
                return IngestResult(
                    status=IngestStatus.DRY_RUN,
                    frontmatter=fm, sections=sections,
                    error=f"Would have quarantined: {e}",
                )
            qr: EvidenceWriteResult = write_quarantine_md(
                partial_frontmatter=fm, sections=sections,
                error=str(e), evidence_root=self._evidence_root,
                source_filename=pdf_path.name,
            )
            return IngestResult(
                status=IngestStatus.QUARANTINED,
                output_path=qr.path, frontmatter=fm, sections=sections,
                error=str(e),
            )

        # Step 8: Write (or dry_run)
        if dry_run:
            return IngestResult(
                status=IngestStatus.DRY_RUN,
                frontmatter=fm, sections=sections,
            )

        wr = write_evidence_md(
            frontmatter=fm, sections=sections, evidence_root=self._evidence_root,
        )
        # Auto-promote to reviewed so hdb index update picks it up immediately.
        if wr.path and wr.path.exists():
            text = wr.path.read_text(encoding="utf-8")
            wr.path.write_text(text.replace("status: draft", "status: reviewed", 1), encoding="utf-8")
        return IngestResult(
            status=IngestStatus.OK,
            output_path=wr.path, frontmatter=fm, sections=sections,
        )

    def _move_to_failed(self, pdf_path: Path, error: str) -> None:
        self._failed_root.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(pdf_path, self._failed_root / pdf_path.name)
            (self._failed_root / f"{pdf_path.name}.error.txt").write_text(
                error, encoding="utf-8"
            )
        except Exception:
            pass
