import subprocess
import pytest
from pathlib import Path

VALID_RCT = Path("tests/fixtures/schema/valid_rct.md")
INVALID_GRADE = Path("tests/fixtures/schema/invalid_bad_grade.md")


@pytest.mark.integration
def test_validate_valid_file_exits_0():
    result = subprocess.run(
        ["py", "scripts/validate_evidence.py", str(VALID_RCT)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
def test_validate_invalid_file_exits_1():
    result = subprocess.run(
        ["py", "scripts/validate_evidence.py", str(INVALID_GRADE)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "grade" in result.stdout.lower() or "grade" in result.stderr.lower()


@pytest.mark.integration
def test_filename_id_mismatch_exits_1(tmp_path):
    """File inside evidence/ named differently from its frontmatter id should fail."""
    content = Path("tests/fixtures/schema/valid_rct.md").read_text(encoding="utf-8")
    # Must be in an 'evidence' directory to trigger filename check
    evidence_dir = tmp_path / "evidence" / "rcts"
    evidence_dir.mkdir(parents=True)
    wrong_name = evidence_dir / "EV-RCT-2099-WRONG-999.md"
    wrong_name.write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["py", "scripts/validate_evidence.py", str(wrong_name)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "mismatch" in result.stdout.lower() or "mismatch" in result.stderr.lower()
