import pytest
from pathlib import Path
from typer.testing import CliRunner
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.cli import app

runner = CliRunner()


def _make_pdf(tmp_path: Path, body: str, name: str = "in.pdf") -> Path:
    p = tmp_path / name
    c = canvas.Canvas(str(p), pagesize=letter)
    y = 720
    for line in body.split("\n"):
        c.drawString(72, y, line)
        y -= 14
        if y < 72:
            c.showPage(); y = 720
    c.save()
    return p


@pytest.fixture
def evidence_env(tmp_path, monkeypatch):
    ev = tmp_path / "evidence"
    raw = tmp_path / "raw"
    (raw / "_failed").mkdir(parents=True, exist_ok=True)
    (raw / "incoming").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EVIDENCE_ROOT", str(ev))
    monkeypatch.setenv("RAW_ROOT", str(raw))
    monkeypatch.setenv("INGEST_EXTRACTOR", "mock")
    return tmp_path


@pytest.mark.unit
def test_ingest_pdf_command_success(evidence_env):
    body = "\n".join(["Methods"] + ["sentence " + str(i) for i in range(50)] +
                     ["Results"] + ["result " + str(i) for i in range(50)])
    pdf = _make_pdf(evidence_env, body)
    result = runner.invoke(app, ["ingest", "pdf", str(pdf), "--type", "RCT"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output or "written" in result.output.lower()


@pytest.mark.unit
def test_ingest_pdf_command_missing_file(evidence_env):
    result = runner.invoke(app, ["ingest", "pdf", "no-such.pdf", "--type", "RCT"])
    assert result.exit_code != 0


@pytest.mark.unit
def test_ingest_dry_run_does_not_write(evidence_env):
    body = "\n".join(["Methods"] + ["sentence " + str(i) for i in range(50)] +
                     ["Results"] + ["result " + str(i) for i in range(50)])
    pdf = _make_pdf(evidence_env, body)
    result = runner.invoke(app, ["ingest", "dry-run", str(pdf), "--type", "RCT"])
    assert result.exit_code == 0, result.output
    assert not list((evidence_env / "evidence").rglob("EV-*.md"))
