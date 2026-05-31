import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
from hypertensiondb.ingest.pipeline import IngestPipeline, IngestStatus


def _make_pdf(tmp_path: Path, pages: list[str], name: str = "in.pdf") -> Path:
    p = tmp_path / name
    c = canvas.Canvas(str(p), pagesize=letter)
    for text in pages:
        for i, line in enumerate(text.split("\n")):
            c.drawString(72, 720 - i * 14, line)
        c.showPage()
    c.save()
    return p


@pytest.fixture
def pipeline(tmp_path):
    return IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )


@pytest.mark.unit
def test_ingest_pdf_writes_evidence_md(pipeline, tmp_path):
    pdf = _make_pdf(tmp_path, [
        "Methods\nRandomized trial with " + "x " * 200,
        "Results\nSBP down 8mmHg " + "y " * 200,
    ])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.OK, result.error
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.output_path.name == "EV-RCT-2026-TEST-001.md"


@pytest.mark.unit
def test_ingest_pdf_returns_quarantine_on_validation_failure(tmp_path):
    """An extractor that returns invalid data triggers quarantine."""

    class BadExtractor:
        def extract(self, text, evidence_type):
            return {"type": evidence_type, "year": "not-a-year"}
        @property
        def model_name(self): return "bad"

    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=BadExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["Some text " + "x " * 200])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.QUARANTINED
    assert result.output_path is not None
    assert "_quarantine" in result.output_path.parts


@pytest.mark.unit
def test_ingest_pdf_moves_to_failed_on_parse_error(pipeline, tmp_path):
    fake_pdf = tmp_path / "broken.pdf"
    fake_pdf.write_text("this is not a pdf", encoding="utf-8")
    result = pipeline.ingest_pdf(fake_pdf, evidence_type="RCT")
    assert result.status == IngestStatus.PARSE_FAILED
    failed_path = tmp_path / "raw" / "_failed" / "broken.pdf"
    assert failed_path.exists()


@pytest.mark.unit
def test_ingest_pdf_dry_run_does_not_write(tmp_path):
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["Methods " + "x " * 200, "Results " + "y " * 200])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT", dry_run=True)
    assert result.status == IngestStatus.DRY_RUN
    assert result.output_path is None
    assert result.frontmatter is not None
    assert result.frontmatter["type"] == "RCT"


@pytest.mark.unit
def test_ingest_pdf_too_little_text_quarantines(tmp_path):
    """Parsed text below MIN_TEXT_CHARS → treat as parse failure."""
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["x"])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.PARSE_FAILED
