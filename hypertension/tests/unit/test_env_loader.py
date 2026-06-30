import os
from pathlib import Path

import pytest

from hypertensiondb.utils.env import get_quality_base_url, load_env_files


@pytest.mark.unit
def test_load_env_files_reads_parent_before_child_without_overwriting_shell(monkeypatch, tmp_path: Path):
    root = tmp_path / "TrueTruth"
    child = root / "hypertension"
    child.mkdir(parents=True)
    (root / ".env").write_text(
        "MOCK_EXPERIMENT_MODEL=parent-model\n"
        "NCBI_EMAIL=user@example.com\n"
        "SHELL_ONLY=from-parent\n",
        encoding="utf-8",
    )
    (child / ".env").write_text(
        "MOCK_EXPERIMENT_MODEL=child-model\n"
        "LOCAL_ONLY=from-child\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_ONLY", raising=False)
    monkeypatch.delenv("SHELL_ONLY", raising=False)
    monkeypatch.setenv("MOCK_EXPERIMENT_MODEL", "shell-model")

    loaded = load_env_files(child)

    assert loaded == [root / ".env", child / ".env"]
    assert os.environ["MOCK_EXPERIMENT_MODEL"] == "shell-model"
    assert os.environ["NCBI_EMAIL"] == "user@example.com"
    assert os.environ["LOCAL_ONLY"] == "from-child"
    assert os.environ["SHELL_ONLY"] == "from-parent"


@pytest.mark.unit
def test_get_quality_base_url_adds_openai_v1_suffix(monkeypatch):
    monkeypatch.setenv("MOCK_EXPERIMENT_URL", "https://api.example.test")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    assert get_quality_base_url() == "https://api.example.test/v1"


@pytest.mark.unit
def test_get_quality_base_url_keeps_existing_v1_suffix(monkeypatch):
    monkeypatch.setenv("MOCK_EXPERIMENT_URL", "https://api.example.test/v1")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    assert get_quality_base_url() == "https://api.example.test/v1"
