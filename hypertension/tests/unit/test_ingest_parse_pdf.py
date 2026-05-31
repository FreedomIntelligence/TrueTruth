import io
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser, ParsedPdf, BasePdfParser


def _make_test_pdf(tmp_path: Path, pages_text: list[str]) -> Path:
    """Generate a tiny PDF with one paragraph per page."""
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    for text in pages_text:
        c.setFont("Helvetica", 11)
        for i, line in enumerate(text.split("\n")):
            c.drawString(72, 720 - i * 14, line)
        c.showPage()
    c.save()
    return path


@pytest.mark.unit
def test_pymupdf_parser_returns_parsed_pdf(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["Page one content.", "Page two content."])
    parser = PyMuPDFParser()
    result = parser.parse(pdf)
    assert isinstance(result, ParsedPdf)
    assert len(result.pages) == 2
    assert "Page one content" in result.pages[0]
    assert "Page two content" in result.pages[1]


@pytest.mark.unit
def test_pymupdf_parser_raw_text_joins_pages(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["First.", "Second."])
    result = PyMuPDFParser().parse(pdf)
    assert "First" in result.raw_text
    assert "Second" in result.raw_text


@pytest.mark.unit
def test_pymupdf_parser_extracts_metadata(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["test"])
    result = PyMuPDFParser().parse(pdf)
    assert isinstance(result.metadata, dict)
    assert "page_count" in result.metadata
    assert result.metadata["page_count"] == 1


@pytest.mark.unit
def test_pymupdf_parser_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        PyMuPDFParser().parse(tmp_path / "nonexistent.pdf")


@pytest.mark.unit
def test_pymupdf_parser_raises_on_non_pdf(tmp_path):
    not_pdf = tmp_path / "notpdf.txt"
    not_pdf.write_text("hello", encoding="utf-8")
    with pytest.raises(Exception):
        PyMuPDFParser().parse(not_pdf)


@pytest.mark.unit
def test_base_parser_is_abstract():
    with pytest.raises(TypeError):
        BasePdfParser()
