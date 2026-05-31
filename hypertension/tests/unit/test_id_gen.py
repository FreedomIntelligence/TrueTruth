import pytest
from pathlib import Path
from unittest.mock import patch
from hypertensiondb.utils.id_gen import next_id


@pytest.mark.unit
def test_next_id_first_entry(tmp_path):
    """When no existing files, returns 001."""
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        (tmp_path / "rcts").mkdir()
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-001"


@pytest.mark.unit
def test_next_id_increments(tmp_path):
    """Finds highest existing serial and returns next."""
    rcts = tmp_path / "rcts"
    rcts.mkdir()
    (rcts / "EV-RCT-2026-PENG-001.md").touch()
    (rcts / "EV-RCT-2026-PENG-002.md").touch()
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-003"


@pytest.mark.unit
def test_next_id_different_type_no_collision(tmp_path):
    """SR files don't affect RCT serial counter."""
    srs = tmp_path / "systematic_reviews"
    srs.mkdir()
    (tmp_path / "rcts").mkdir()
    (srs / "EV-SR-2026-PENG-001.md").touch()
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-001"
