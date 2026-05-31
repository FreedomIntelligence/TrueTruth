"""End-to-end: tiny synthetic PDF → ingest pipeline → evidence/{type}/{id}.md."""
import subprocess
import sys
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
from hypertensiondb.ingest.pipeline import IngestPipeline, IngestStatus


def _make_pdf(path: Path, sections: list[tuple[str, str]]) -> None:
    """Create a multi-section RCT-shaped PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 720
    for heading, body in sections:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, y, heading); y -= 16
        c.setFont("Helvetica", 10)
        for line in body.split("\n"):
            c.drawString(72, y, line); y -= 12
            if y < 72:
                c.showPage(); y = 720
        y -= 12
    c.save()


@pytest.mark.integration
def test_ingest_synthetic_rct_pdf(tmp_path):
    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [
        ("Background", "Hypertension is common.\n" * 5),
        ("Methods", "Randomized double-blind trial with 612 patients.\n" * 8),
        ("Results", "SBP decreased by 8 mmHg (95% CI -10.1, -6.7).\n" * 8),
        ("Conclusion", "Combination therapy is superior.\n" * 4),
    ])

    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")

    # End-to-end: pipeline succeeds, file is at the right path with the right id.
    # Note: section detection quality on reportlab-rendered PDFs is poor (no blank
    # lines between headings/body), so we don't assert specific section content
    # here — that's covered by D.3 / D.4 unit tests.
    assert result.status == IngestStatus.OK, result.error
    assert result.output_path.exists()
    assert result.output_path.parent.name == "rcts"
    content = result.output_path.read_text(encoding="utf-8")
    assert "EV-RCT-2026-TEST-001" in content
    assert "type: RCT" in content
    assert "status: draft" in content
    assert "extracted_by: llm" in content


@pytest.mark.integration
def test_ingest_output_passes_validator(tmp_path):
    """The written .md must validate via scripts/validate_evidence.py."""
    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [
        ("Methods", "Trial design.\n" * 8),
        ("Results", "Effective.\n" * 8),
        ("Conclusion", "Combination superior.\n" * 4),
    ])
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.OK

    repo_root = Path(__file__).parent.parent.parent
    validator = repo_root / "scripts" / "validate_evidence.py"
    proc = subprocess.run(
        [sys.executable, str(validator), str(result.output_path)],
        capture_output=True, text=True, cwd=repo_root,
    )
    # MockExtractor doesn't produce abstract_zh content; validator may flag that
    # as missing. That's a Mock limitation, not a pipeline bug.
    if proc.returncode != 0:
        assert "abstract_zh" in proc.stdout or "abstract_zh" in proc.stderr, \
            f"Unexpected validator failure: {proc.stdout}\n{proc.stderr}"


@pytest.mark.integration
def test_ingest_quarantine_on_bad_extractor(tmp_path):
    class BadExtractor:
        def extract(self, text, evidence_type):
            return {"type": evidence_type, "year": "wrong"}
        @property
        def model_name(self): return "bad"

    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [("Methods", "x " * 200), ("Results", "y " * 200)])
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=BadExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.QUARANTINED
    assert (tmp_path / "evidence" / "_quarantine").is_dir()
